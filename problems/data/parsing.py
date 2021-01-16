import re
from collections import OrderedDict

from pycsp3.dashboard import options

data = None
_data_file = None
_dataParser = None


def register_fields(data_file):
    global data, _data_file, _dataParser
    data = OrderedDict()
    _data_file = data_file
    _dataParser = DataParser(data_file)
    return data


class DataParser:
    def __init__(self, data_file):
        if data_file:
            with open(data_file) as f:
                self.lines = [line[:-1].strip() if line[-1] == '\n' else line.strip() for line in f.readlines() if len(line.strip()) > 0]
        self.curr_line_index = 0
        self.curr_line_tokens = None

    def curr_line(self):
        if self.curr_line_index >= len(self.lines):
            print("Warning: no more line")
            return None
        return self.lines[self.curr_line_index]

    def next_line(self):
        self.curr_line_index += 1
        self.curr_line_tokens = None
        return self.curr_line()

    def next(self, to_int=True):
        if self.curr_line_tokens is None:
            if self.curr_line() is not None:
                self.curr_line_tokens = self.curr_line().split()
                self.curr_line_tokens_index = 0
        res = int(self.curr_line_tokens[self.curr_line_tokens_index]) if to_int else self.curr_line_tokens[self.curr_line_tokens_index]
        self.curr_line_tokens_index += 1
        if self.curr_line_tokens_index >= len(self.curr_line_tokens):
            next_line()
            while self.curr_line() is not None and len(self.curr_line().strip()) == 0:
                self.next_line()
        return res


def line():
    return _dataParser.curr_line()


def next_line(repeat=0):
    for _ in range(repeat + 1):
        l = _dataParser.next_line()
    return l


def next_int():
    return _dataParser.next(to_int=True)


def next_str():
    return _dataParser.next(to_int=False)


def remaining_lines(skip_curr=False):
    if skip_curr:
        next_line()
    return _dataParser.lines[_dataParser.curr_line_index:]


def number_in(line):
    assert line is not None
    return int(re.search(r'[-]?\d+', line).group(0))


def numbers_in(line):
    assert line is not None
    return [int(v) for v in re.findall(r'[-]?\d+', line)]  # [int(v) for v in line().split() if v.isdigit()]


def numbers_in_lines_until(stop):
    s = ""
    while not next_line().endswith(stop):
        s += line()
    return numbers_in(s + line())


def decrement(t):
    assert isinstance(t, list)
    for i in range(len(t)):
        if isinstance(t[i], list):
            decrement(t[i])
        else:
            assert isinstance(t[i], int)
            t[i] -= 1
    return t


def split_with_colums_of_size(t, k):
    assert isinstance(t, list) and len(t) % k == 0, str(type(list)) + " " + str(len(t)) + " " + str(k)
    return [[t[i * k + j] for j in range(k)] for i in range(len(t) // k)]


def ask_number(message):
    parameter = options.consume_parameter()
    return int(parameter) if parameter else int(input(message + " "))


def ask_string(message):
    parameter = options.consume_parameter()
    return parameter if parameter else input(message + " ")
