import json
import math

ADDRESS_WIDTH_BITS = 11
COMMAND_WIDTH_BYTES = 4
OPERATION_CODE_WIDTH_BITS = 4 

NUMBER_OF_ADDRESSES = (1 << ADDRESS_WIDTH_BITS)

def bswap(value : int):
    # Ensure it's within 16-bit range
    value &= 0xFFFF
    return ((value & 0xFF00) >> 8) | ((value & 0x00FF) << 8)


class Assembler:
    def __init__(self, path_to_program : str, path_to_binary : str, path_to_log_file : str):
        self.MEMORY = [0 for _ in range(NUMBER_OF_ADDRESSES)]
        self.FREE_MEMORY_ADDRESS = -1
        self.AC : int = 0
        self.NAMESPACE = {}
        self.INPUT_FILE = path_to_program
        self.OUTPUT_FILE = path_to_binary
        self.LOG_FILE = path_to_log_file
        self.log_list = []
        open(self.OUTPUT_FILE, 'w').close()
        open(self.LOG_FILE, 'w').close()

        self.LOG_ARRAY = []
    
    def get_free_address(self):
        self.FREE_MEMORY_ADDRESS += 1
        return self.FREE_MEMORY_ADDRESS
    
    def add_var_to_namespace(self, variable_name : str) -> int:
        ADDRESS = self.get_free_address()
        self.NAMESPACE[variable_name] = ADDRESS
        return ADDRESS
    
    def run(self):
        print('---Assembler running:')

        with open(self.INPUT_FILE, 'r') as f:
            lines = f.readlines()
        
        for line in lines:
            code_line = line.split(';')[0].strip()
            if code_line:
                command_parts = code_line.split()
                command_type = command_parts[0]
                match(command_type):

                    case 'set':
                        variable_name = command_parts[1] 
                        value = int(command_parts[2])
                        # Load constant into AC
                        self.AC = value
                        const_binary_command = self.generate_bytes(8, value)
                        self.write_to_binary(const_binary_command)
                        self.add_to_log_list([8, value], const_binary_command)

                        # Store value from AC to memory
                        if variable_name not in self.NAMESPACE.keys():
                            address = self.add_var_to_namespace(variable_name)
                        else:
                            address = self.NAMESPACE[variable_name]
                        self.MEMORY[address] = value
                        store_binary_command = self.generate_bytes(9, address)
                        self.write_to_binary(store_binary_command)
                        self.add_to_log_list([10, address], store_binary_command)

                    case 'mov':
                        to_variable_name, from_variable_name = command_parts[1:3]

                        if from_variable_name not in self.NAMESPACE.keys():
                            raise Exception(f"Variable {from_variable_name} was not declared.")
                        
                        from_address = self.NAMESPACE[from_variable_name]
                        shift = (from_address - self.AC) % NUMBER_OF_ADDRESSES
                        self.AC = self.MEMORY[from_address]
                        read_binary_command = self.generate_bytes(10, shift)
                        self.write_to_binary(read_binary_command)
                        self.add_to_log_list([9, shift], read_binary_command)

                        if to_variable_name not in self.NAMESPACE.keys():
                            to_address = self.add_var_to_namespace(to_variable_name)
                        else:
                            to_address = self.NAMESPACE[to_variable_name]

                        store_binary_command = self.generate_bytes(9, to_address)
                        self.write_to_binary(store_binary_command)
                        self.add_to_log_list([10, to_address], store_binary_command)

                    
                    case 'bswap':
                        self.AC = bswap(self.MEMORY[self.AC])
                        bswap_binary_command = self.generate_bytes(2, 0)
                        self.write_to_binary(bswap_binary_command)
                        self.add_to_log_list([2], bswap_binary_command)

        self.write_log_file()

    def write_log_file(self):
        with open(self.LOG_FILE, 'a') as log_file:
            json.dump(self.log_list, log_file)
        
    def add_to_log_list(self, command_parts_decimal, binary_command):
        log_object = {}
        A = command_parts_decimal[0]
        log_object["A"] = A
        if len(command_parts_decimal) == 2:
            B = command_parts_decimal[1]
            log_object["B"] = B
        
        log_object["hex"] = binary_command
        self.log_list.append(log_object)

        
                        
    
    def generate_bytes(self, A, B):
        bytes = [''] * 4
        command_code : str = bin(A)[2:]
        command_code = self.pad_with_zeros(command_code, 4)
        
        second_field_bin = bin(B)[2:]
        second_field_bin = self.pad_with_zeros(second_field_bin, 28)

        bytes[0] = second_field_bin[-4:] + command_code

        second_field_bin_rest = second_field_bin[:-4]
        bytes[1:4] = [second_field_bin_rest[i:i+8] for i in range(0, len(second_field_bin_rest), 8)][::-1]
        
        bytes = [hex(int(byte, 2)) for byte in bytes]
        return bytes
    
    def write_to_binary(self, bytes : list):
        with open(self.OUTPUT_FILE, 'ab') as f:
            for hex_str in bytes:
                byte = int(hex_str, 16).to_bytes(1)
                f.write(byte)

    def pad_with_zeros(self, bin_number : str, desired_length : int) -> str:
        bin_number_length = len(bin_number)
        for _ in range(desired_length - bin_number_length):
            bin_number = '0' + bin_number
        
        return bin_number
    

                        

class Interpreter:
    def __init__(self, path_to_binary : str, path_to_result : str):
        with open(path_to_binary, 'rb') as f:
            self.BINARY = f.read()
        self.MEMORY = [0 for _ in range(NUMBER_OF_ADDRESSES)]
        self.AC = 0 # 32-bit register
        self.RESULT_FILE = path_to_result
        open(self.RESULT_FILE, 'w').close()

    def run(self):
        print('---Interpreter running:')
        commands = [''] * math.ceil(len(self.BINARY) / COMMAND_WIDTH_BYTES)
        for i, byte in enumerate(self.BINARY):
            command_index = i // COMMAND_WIDTH_BYTES
            commands[command_index] = format(byte, '08b') + commands[command_index]

        for command in commands:
            command_type = self.get_command_slice(command, 0, OPERATION_CODE_WIDTH_BITS)
            match(command_type):
                case "1000": # Loading constant into AC
                    value = int(self.get_command_slice(command, OPERATION_CODE_WIDTH_BITS, 31), 2)
                    self.AC = value

                case "1010": # Reading value from memory
                    shift = int(self.get_command_slice(command, OPERATION_CODE_WIDTH_BITS, 15), 2)
                    address = (self.AC + shift) % NUMBER_OF_ADDRESSES
                    value = self.MEMORY[address]
                    self.AC = value

                case "1001": # Writing value to memory
                    value = self.AC
                    address = int(self.get_command_slice(command, OPERATION_CODE_WIDTH_BITS, 15), 2)
                    self.MEMORY[address] = value

                case "0010": # Perform bswap
                    self.AC = bswap(self.MEMORY[self.AC])

        self.log_result()

    def log_result(self):
        data = {}
        data["AC"] = self.AC
        data["MEMORY"] = []
        for i in range(NUMBER_OF_ADDRESSES):
            data["MEMORY"].append({"0b" + bin(i)[2:].zfill(ADDRESS_WIDTH_BITS): self.MEMORY[i]})
        with open(self.RESULT_FILE, 'a') as f:
            json.dump(data, f)


    @staticmethod
    def get_command_slice(command : str, index1 : int, index2 : int) -> str:
        if index1 == 0:
            return command[-index2:]
        return command[-index2:-index1]

def main():
    assembler = Assembler("test_program.txt", "assembled.bin", "assembler_log.json")
    assembler.run()

    interpreter = Interpreter("assembled.bin", "result.json")
    interpreter.run()

if __name__ == "__main__":
    main()