import sys

opcode_table = {
    'ADD': '18',
    'AND': '40',
    'COMP': '28',
    'DIV': '24',
    'J': '3C',
    'JEQ': '30',
    'JGT': '34',
    'JLT': '38',
    'JSUB': '48',
    'LDA': '00',
    'LDCH': '50',
    'LDL': '08',
    'LDX': '04',
    'MUL': '20',
    'OR': '44',
    'RD': 'D8',
    'RSUB': '4C',
    'STA': '0C',
    'STCH': '54',
    'STL': '14',
    'STSW': 'E8',
    'STX': '10',
    'SUB': '1C',
    'TD': 'E0',
    'TIX': '2C',
    'WD': 'DC'
}
directives_table = {
    'BYTE': 'C0',
    'WORD': 'C4',
    'RESB': 'C8',
    'RESW': 'CC',
    'START': 'C0',
    'END': 'C0'
}


class sic_assembler:
    def __init__(self, file_name):
        self.symbol_table = {}
        self.program_name = ''
        self.program_start = ''
        self.program_len = ''
        self.t_record = []
        self.file_name = file_name
        self.file_lines = []
        self.file_lines_no_comments = []
        self.ins = []
        self.read_file()
        self.parse_lines()
        self.pass_one()
        self.pass_two()
        self.write_to_file()

    def read_file(self):
        with open(self.file_name, 'r') as file:
            self.file_lines = file.readlines()
        for line in self.file_lines:
            if line[0] != '.':
                self.file_lines_no_comments.append(line)

    def parse_lines(self):
        for line in self.file_lines_no_comments:
            tokens = line.split()
            self.ins.append(instruction(tokens))

    def pass_one(self):
        LOCCTR = 0
        for ins in self.ins:
            if ins.op == 'START':
                if ins.label:
                    self.program_name = ins.label
                LOCCTR = int(ins.operand, 16)
                self.program_start = ins.operand
            elif ins.op == 'END':
                self.program_len = (hex(LOCCTR - int(self.program_start, 16))[2:]).upper()
                break

            if ins.label:
                self.symbol_table[ins.label] = LOCCTR

            if ins.op in opcode_table:
                LOCCTR += 3
            elif ins.op == 'RESB':
                LOCCTR += int(ins.operand)
            elif ins.op == 'RESW':
                LOCCTR += 3 * int(ins.operand)
            elif ins.op == 'BYTE':
                if ins.operand[0] == 'X':
                    LOCCTR += (len(ins.operand) - 3) // 2
                elif ins.operand[0] == 'C':
                    LOCCTR += len(ins.operand) - 3
            elif ins.op == 'WORD':
                LOCCTR += 3

    def pass_two(self):
        LOCCTR = int(self.program_start, 16)
        t_addr_start = LOCCTR
        t_line = ''
        for ins in self.ins:
            if ins.op == 'END':
                if t_line:
                    t_len = hex(len(t_line) // 2)[2:].upper()
                    t_len = '0' * (2 - len(t_len)) + t_len
                    t_addr_start = hex(t_addr_start)[2:].upper()
                    t_addr_start = '0' * (6 - len(t_addr_start)) + t_addr_start
                    self.t_record.append(t_addr_start + t_len + t_line)
                break
            if LOCCTR + 3 - t_addr_start > 30:
                t_len = hex(len(t_line) // 2)[2:].upper()
                t_addr_start = hex(t_addr_start)[2:].upper()
                t_addr_start = '0' * (6 - len(t_addr_start)) + t_addr_start
                self.t_record.append(t_addr_start + t_len + t_line)
                t_addr_start = LOCCTR
                t_line = ''
            if ins.op in opcode_table:
                t_line += self.ins_to_hex(ins)
                LOCCTR += 3
            elif ins.op == 'BYTE':
                if ins.operand[0] == 'X':
                    operandlen = (len(ins.operand) - 3) // 2
                    t_line += ins.operand[2:len(ins.operand) - 1]
                elif ins.operand[0] == 'C':
                    operandlen = len(ins.operand) - 3
                    for c in ins.operand[2:len(ins.operand) - 1]:
                        t_line += hex(ord(c))[2:].upper()
                LOCCTR += operandlen
            elif ins.op == 'WORD':
                words_hex = hex(int(ins.operand))[2:].upper()
                t_line += '0' * (6 - len(words_hex)) + words_hex
                LOCCTR += 3
            elif ins.op == 'RESB':
                LOCCTR += int(ins.operand)
            elif ins.op == 'RESW':
                LOCCTR += 3 * int(ins.operand)

    def ins_to_hex(self, ins):
        hex_str = ins.opcode
        if ins.operand:
            x_bit = 0
            if ins.isX:
                x_bit = 32768
            if ins.operand in self.symbol_table:
                addr_hex = hex(self.symbol_table[ins.operand] + x_bit)[2:].upper()
                hex_str += '0' * (3 - len(addr_hex)) + addr_hex
        else:
            hex_str += '0' * 4
        return hex_str

    def write_to_file(self):
        objfile = []
        header = 'H' \
                 + self.program_name + (6 - len(self.program_name)) * ' ' \
                 + (6 - len(self.program_start)) * '0' + self.program_start \
                 + (6 - len(self.program_len)) * '0' + self.program_len \
                 + '\n'
        objfile.append(header)
        for t_line in self.t_record:
            text = 'T' + t_line + '\n'
            objfile.append(text)
        end = 'E' + (6 - len(self.program_start)) * '0' + self.program_start + '\n'
        objfile.append(end)
        with open(self.file_name[:-4] + '.obj', 'w') as f:
            f.writelines(objfile)


class instruction:
    def __init__(self, tokens):
        self.label = None
        self.op = None
        self.opcode = None
        self.operand = None
        self.isX = False
        self.instruction = []
        self.parse_instruction(tokens)

    def parse_instruction(self, tokens):
        if len(tokens) == 1:
            self.op = tokens[0]
        elif len(tokens) == 2:
            if tokens[0] in opcode_table or tokens[0] in directives_table:
                self.op = tokens[0]
                self.operand = tokens[1]
            else:
                self.label = tokens[0]
                self.op = tokens[1]
        elif len(tokens) == 3:
            self.label = tokens[0]
            self.op = tokens[1]
            self.operand = tokens[2]
        if self.op in opcode_table:
            self.opcode = opcode_table[self.op]
        if self.operand:
            if self.operand.endswith('X'):
                self.operand = self.operand[0:len(self.operand) - 2]
                self.isX = True
        instruction = [self.label, self.op, self.operand]


if __name__ == '__main__':
    assembler = sic_assembler(sys.argv[1])
    # print(assembler.file_lines)
    # print(assembler.file_lines_no_comments)
    # for i in assembler.ins:
    #     print(i.label, i.op, i.operand)
    # print(assembler.symbol_table)
    # print(assembler.program_name)
    # print(assembler.program_len)
    # print(assembler.program_start)
    # print(assembler.t_record)
