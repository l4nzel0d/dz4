import json
import math

ADDRESS_WIDTH_BITS = 16
COMMAND_WIDTH_BYTES = 4
OPERATION_CODE_WIDTH_BITS = 4 

NUMBER_OF_ADDRESSES = (1 << ADDRESS_WIDTH_BITS)

class Assembler:
    def __init__(self, path_to_program : str, path_to_binary : str, path_to_log_file : str):
        self.FREE_MEMORY_ADDRESS = -1
        self.AC : int = 0
        self.NAMESPACE = {}
        self.INPUT_FILE = path_to_program
        self.OUTPUT_FILE = path_to_binary
        self.LOG_FILE = path_to_log_file
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
                        const_binary_command = self.generate_bytes_const(value)
                        self.write_to_binary(const_binary_command)

                        # Store value from AC to memory
                        address = self.add_var_to_namespace(variable_name)
                        store_binary_command = self.generate_bytes_store(address)
                        self.write_to_binary(store_binary_command)
                    case 'mov':
                        to_variable_name, from_variable_name = command_parts[1:3]

                        if from_variable_name not in self.NAMESPACE.keys():
                            raise Exception(f"Variable {from_variable_name} was not declared.")
                        
                        from_address = self.NAMESPACE[from_variable_name]
                        shift = (from_address - self.AC) % (NUMBER_OF_ADDRESSES)
                        print(shift, from_address, )
                        read_binary_command = self.generate_bytes_read(from_address)


                        if to_variable_name not in self.NAMESPACE.keys():
                            to_address = self.add_var_to_namespace(to_variable_name)
                        else:
                            to_address = self.NAMESPACE[to_variable_name]

                        store_binary_command = self.generate_bytes_store(to_address)
                        self.write_to_binary(store_binary_command)
                        
    
    def generate_bytes_const(self, value : int) -> list:
        # initialize bytes array
        print("generate_bytes_const():")
        bytes = [''] * 4


        command_code : str = '1000'

        print("Value: ", value)
        # convert value to binary and pad with zeros
        value_bin : str = bin(value)[2:]
        value_bin = self.pad_with_zeroes(value_bin, 28)
        print("Value bin: ", value_bin)

        # set first byte
        bytes[0] = value_bin[-4:] + command_code

        # set the rest of the bytes
        value_bin_rest = value_bin[:-4]
        bytes[1:4] = [value_bin_rest[i:i+8] for i in range(0, len(value_bin_rest), 8)][::-1]

        # convert each byte hex
        bytes = [hex(int(byte, 2)) for byte in bytes]
        print(bytes)
        return bytes

    def generate_bytes_store(self, address : int) -> list:
        print("generate_bytes_store():")
        # initialize bytes array
        bytes = [''] * 4


        command_code : str = '1001'

        print("Address: ", address)
        # convert value to binary and pad with zeros
        address_bin : str = bin(address)[2:]
        print("Address bin: ", address_bin)
        address_bin = self.pad_with_zeroes(address_bin, 28)

        # set first byte
        bytes[0] = address_bin[-4:] + command_code

        # set the rest of the bytes
        address_bin_rest = address_bin[:-4]
        bytes[1:4] = [address_bin_rest[i:i+8] for i in range(0, len(address_bin_rest), 8)][::-1]

        # convert each byte hex
        bytes = [hex(int(byte, 2)) for byte in bytes]
        print(bytes)
        return bytes

    def generate_bytes_read(self, shift: int) -> list:
        ...

    def write_to_binary(self, bytes : list):
        with open(self.OUTPUT_FILE, 'ab') as f:
            for hex_str in bytes:
                byte = int(hex_str, 16).to_bytes(1)
                f.write(byte)

    def pad_with_zeroes(self, bin_number : str, desired_length : int) -> str:
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

        print("Commands: ",commands)
        for command in commands:
            command_type = self.get_command_slice(command, 0, OPERATION_CODE_WIDTH_BITS)
            print("Command type: ", command_type)
            match(command_type):
                case "1000": # Loading constant into AC
                    value = int(self.get_command_slice(command, OPERATION_CODE_WIDTH_BITS, 31), 2)
                    print(value)
                    self.AC = value

                case "1010": # Reading value from memory
                    shift = int(self.get_command_slice(command, OPERATION_CODE_WIDTH_BITS, 11), 2)
                    address = (self.AC + shift) % len(self.MEMORY)
                    value = self.MEMORY[address]
                    self.AC = value

                case "1001": # Writing value to memory
                    value = self.AC
                    address = int(self.get_command_slice(command, OPERATION_CODE_WIDTH_BITS, 15), 2)
                    self.MEMORY[address] = value

                case "0010": # Perform bswap
                    self.AC = self.bswap(self.AC)

        self.log_result()

    def log_result(self):
        data = {}
        data["AC"] = self.AC
        data["MEMORY"] = []
        for i in range(len(self.MEMORY)):
            data["MEMORY"].append({"0b" + bin(i)[2:].zfill(ADDRESS_WIDTH_BITS): self.MEMORY[i]})
        with open(self.RESULT_FILE, 'a') as f:
            json.dump(data, f)

    @staticmethod
    def bswap(value : int):
        # Ensure it's within 32-bit range
        value &= 0xFFFFFFFF

        return ((value & 0xFF000000) >> 24) | ((value & 0x00FF0000) >> 8) | \
               ((value & 0x0000FF00) << 8) | ((value & 0x000000FF) << 24)

    @staticmethod
    def get_command_slice(command : str, index1 : int, index2 : int):
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