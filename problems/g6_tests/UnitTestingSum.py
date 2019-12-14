from pycsp3 import *

x, y, z = VarArray(size=3, dom={0, 1})

try:
    satisfy(Sum([1, 2, 3]) < 5)
except TypeError as e:
    print("Test assert terms sum parameter 1:")
    print(str(e))
    print()

try:
    satisfy(Sum(None) < 5)
except TypeError as e:
    print("Test assert terms sum parameter 2:")
    print(str(e))
    print()

satisfy(Sum(x) < 5)

try:
    satisfy(Sum(x, [1]) < 10)
except TypeError as e:
    print("Test assert terms sum parameter 3:")
    print(str(e))
    print()

satisfy(Sum(x, y) < 10)

try:
    satisfy(Sum(x))
except AssertionError as e:
    print("Test assert partial constraint:")
    print(str(e))
    print()

try:
    satisfy(Sum(x) > None)
except TypeError as e:
    print("Test assert type partial constraint 1:")
    print(str(e))
    print()

try:
    satisfy(Sum(x) > {1, 2, 3})
except TypeError as e:
    print("Test assert type partial constraint 2:")
    print(str(e))
    print()

satisfy(Sum(x) in {1, 2, 3})

try:
    satisfy(Sum(x) in [1, 2, 3])
except AssertionError as e:
    print("Test assert bad partial constraint:")
    print(str(e))
    print()

try:
    satisfy(Sum(x, condition=[]))
    satisfy(Sum(x, condition=(0)))
except AssertionError as e:
    print("Test assert condition in keyword argument:")
    print(str(e))
    print()

satisfy(Sum(x, condition=("EQ", 0)))
satisfy(Sum(x, condition=["GE", 0]))
