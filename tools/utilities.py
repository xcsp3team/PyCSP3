import os
import sys
import types
from collections.abc import Iterable
from decimal import Decimal
from itertools import product
from multiprocessing import cpu_count, Pool
from time import time

from pycsp3.classes.auxiliary import conditions
from pycsp3.classes.main.variables import Variable
from pycsp3.classes.main.domains import Domain
from pycsp3.dashboard import options


class Stopwatch:
    def __init__(self):
        self.initial_time = time()

    def elapsed_time(self, *, reset=False):
        elapsed_time = time() - self.initial_time
        if reset:
            self.initial_time = time()
        return "{:8.2f}".format(elapsed_time)


class _Star(float):
    def __init__(self, val):
        super().__init__()

    def __repr__(self):
        return "*"

    def __str__(self):
        return "*"


ANY = _Star("Inf")  #: used to represent * in short tables


def flatten(*args, keep_none=False):
    # if not hasattr(flatten, "cache"):  # cannot work (changing to TupleInt and TupleVar instead of ListInt and ListVar while guaranteeing the lifetime? how?)
    #     flatten.cache = {}
    # elif len(args) == 1 and id(args[0]) in flatten.cache:
    #     return flatten.cache[id(args[0])]
    t = []
    for arg in args:
        if arg is None:
            if keep_none:
                t.append(arg)
        elif isinstance(arg, (str, range, Domain)):  # Iterable but must be appended, not extended
            t.append(arg)
        elif isinstance(arg, Iterable):
            t.extend(flatten(*arg, keep_none=keep_none))
        elif isinstance(arg, types.GeneratorType):
            t.extend(flatten(*list(arg), keep_none=keep_none))
        else:
            t.append(arg)
    # if len(args) == 1:
    #     flatten.cache[id(args[0])] = t
    return t


def is_containing(l, types, *, check_first_only=False):
    if isinstance(l, (list, tuple, set, frozenset)):
        if len(l) == 0:
            return None
        found = False
        for v in l:
            if not is_containing(v, types, check_first_only=check_first_only):
                return False
            if check_first_only:
                return True
            found = True
        return True if found else None
    else:
        return isinstance(l, types)


def unique_type_in(l, tpe=None):
    if isinstance(l, (list, tuple, set, frozenset)):
        if len(l) == 0:
            return None
        for v in l:
            t = unique_type_in(v, tpe)
            if t is False:
                return False
            if tpe is None:
                tpe = t
        return tpe
    else:
        return None if l is None else type(l) if tpe is None else tpe if isinstance(l, tpe) else False


def is_1d_list(l, types=None):
    if types is not None and len(l) == 0:
        return False
    return isinstance(l, list) and all(isinstance(v, types) if types else not isinstance(v, list) for v in l)


def is_1d_tuple(l, types):
    if types is not None and len(l) == 0:
        return False
    return isinstance(l, tuple) and all(isinstance(v, types) for v in l)


def is_2d_list(m, types=None):
    return isinstance(m, list) and all(is_1d_list(l, types) for l in m)


def is_matrix(m, types=None):
    return is_2d_list(m, types) and all(len(l) == len(m[0]) for l in m)


def is_square_matrix(m, types=None):
    return is_matrix(m, types) and len(m) == len(m[0])


def transpose(m):
    assert is_matrix(m)
    return [[m[j][i] for j in range(len(m))] for i in range(len(m[0]))]


def alphabet_positions(s):
    assert isinstance(s, str)
    return tuple(ord(c) - ord('a') for c in s.lower())


def all_primes(limit):
    """ Returns a list of primes < limit """
    sieve = [True] * limit
    for i in range(3, int(limit ** 0.5) + 1, 2):
        if sieve[i]:
            sieve[i * i::2 * i] = [False] * ((limit - i * i - 1) // (2 * i) + 1)
    return [2] + [i for i in range(3, limit, 2) if sieve[i]]


def value_in_base(decimal_value, length, base):
    assert type(decimal_value) == type(length) == type(base) is int
    value = [0] * length
    for i in range(len(value) - 1, -1, -1):
        value[i] = decimal_value % base
        decimal_value = decimal_value // base
    assert decimal_value == 0, "The given array is too small to contain all the digits of the conversion"
    return value


def integer_scaling(values):  # convert all (possibly decimal) specified values into integers by means of scaling
    values = list(values) if isinstance(values, types.GeneratorType) else values
    scale = 0
    for v in values:
        pos = v.find('.')
        if pos >= 0:
            i = len(v) - 1
            while v[i] == '0':
                i -= 1
            if i - pos > scale:
                scale = i - pos
    return [int(w * (10 ** scale)) for w in [Decimal(v) for v in values]]


def matrix_to_string(m):
    return "".join(["(" + ",".join([str(v) for v in t]) + ")" for t in m])
    # return "\n" + "\n".join(["\t(" + ",".join([str(v) for v in t]) + ")" for t in m]) + "\n"


def table_to_string(table, restricting_domains=None, *, parallel=False):
    def _tuple_to_string(t):
        return "(" + ",".join(
            str(v) if isinstance(v, (int)) else
            str(set(v)) if isinstance(v, tuple) else
            conditions.inside(v).str_tuple() if isinstance(v, range) else
            v if isinstance(v, (str)) else
            "*" if v == ANY else v.str_tuple()
            for v in t) + ")"

    LIMIT = 100000  # hard coding
    if not parallel or len(table) < LIMIT:
        s = []
        previous = ""
        for t in table:  # table is assumed to be sorted (adding an assert?) ; only distinct tuples are kept
            if t != previous:
                if restricting_domains is None or isinstance(t[0], str) \
                        or all(t[i] == ANY or t[i] in restricting_domains[i].all_values() for i in range(len(t))):
                    s.append(_tuple_to_string(t))
                previous = t
        return "".join(s)
    else:
        print("Creation of a table of size: " + str(len(table)) + (" in parallel" if parallel and len(table) >= LIMIT else ""))
        n_threads = cpu_count()
        size = len(table) // n_threads
        pool = Pool(n_threads)
        left, right = 0, size
        t = []
        for piece in range(n_threads):
            t.append(pool.apply_async(table_to_string, args=(table[left:right], restricting_domains)))  # call not in parallel
            left += size
            right = len(table) if piece in {n_threads - 2, n_threads - 1} else right + size
        assert right == len(table)
        pieces = [r.get() for r in t]
        pool.close()
        pool.join()
        # checking and removing similar tuples at the frontiers before returning the string ?
        previous = None
        for piece in pieces:
            if previous and previous[-1] == piece[0]:
                previous.pop()
            previous = piece
        return "".join("".join(piece) for piece in pieces)


def integers_to_string(numbers):
    if len(numbers) == 0:
        return ''
    numbers = sorted(numbers)
    t = list()
    prev = numbers[0]
    for curr in numbers:
        if curr != prev + 1:
            t.append([curr])  # the start of a possible interval
        elif len(t[-1]) > 1:
            t[-1][-1] = curr  # to modify the end of the interval
        else:
            t[-1].append(curr)  # to set the end of the interval
        prev = curr
    return ' '.join(str(i[0]) if len(i) == 1 else str(i[0]) + ('..' if i[0] != i[1] - 1 else ' ') + str(i[1]) for i in t)


def to_ordinary_table(table, domains, *, keep_any=False):
    doms = [range(d) if isinstance(d, int) else d.all_values() if isinstance(d, Domain) else d for d in domains]
    tbl = set()
    if keep_any:
        for t in table:
            if any(isinstance(v, conditions.Condition) for v in t):  # v may be a Condition object (with method 'filtering')
                tbl.update(product(*({v} if isinstance(v, int) or v == ANY else v.filtering(doms[i]) for i, v in enumerate(t))))
            else:
                tbl.add(t)
    else:
        for t in table:
            if any(v == ANY or isinstance(v, conditions.Condition) for v in t):  # v may be a ConditionValue object (with method 'filtering')
                tbl.update(product(*({v} if isinstance(v, int) else doms[i] if v == ANY else v.filtering(doms[i]) for i, v in enumerate(t))))
            else:
                tbl.add(t)
    return tbl


def display_constraints(ctr_entities, separator=""):
    for ce in ctr_entities:
        if ce is not None:
            if hasattr(ce, "entities"):
                print(separator + str(ce))
                display_constraints(ce.entities, separator + "\t")
            else:
                print(separator + str(ce.constraint))


def is_windows():
    return os.name == 'nt'


def _proxy_color(s):
    return "" if is_windows() else s


PURPLE, BLUE, GREEN, ORANGE, RED, WHITE, WHITE_BOLD, UNDERLINE = _proxy_color('\033[95m'), _proxy_color('\033[94m'), _proxy_color('\033[92m'), _proxy_color(
    '\033[93m'), _proxy_color('\033[91m'), _proxy_color('\033[0m'), _proxy_color('\033[1m'), _proxy_color('\033[4m')


def string_color(s, start, final=WHITE):
    return start + s + final


class Error:
    errorOccurrence = False


def warning(message):
    print("\n  " + ORANGE + "Warning: " + WHITE + message)


def error(s):
    Error.errorOccurrence = True
    print("\n\t" + RED + "ERROR: " + WHITE, s, "\n")
    print("\t\t(add option -ev to your command if you want to see the trace of the error)\n")
    if options.ev:
        raise TypeError(s)
    else:
        sys.exit(1)


def error_if(test, s):
    if test:
        error(s)
