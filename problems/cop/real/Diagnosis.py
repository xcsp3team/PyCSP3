"""
See Problem 042 on CSPLib

Example of Execution:
  python3 Diagnosis.py -data=Diagnosis_example.json
"""

from pycsp3 import *

functions, gates = data  # note that the two first gates are special, inserted for reserving indexes 0 and 1 (for false and true)
nGates = len(gates)

# x[i] is -1 if the ith gate is not faulty (otherwise 0 or 1 when stuck-at-0 or stuck-at-1)
x = VarArray(size=nGates, dom=lambda i: {-1} if i < 2 else {-1, 0, 1})

# y[i] is the possibly faulty output of the ith gate
y = VarArray(size=nGates, dom=lambda i: {0} if i == 0 else {1} if i == 1 else {0, 1})

satisfy(
    # ensuring that y is coherent with the observed output
    [y[i] == gate.out for i, gate in enumerate(gates) if i > 1 and gate.out != -1],

    # ensuring that each gate either meets expected outputs based on its function or is broken (either stuck on or off)
    [(y[i] == x[i]) | (y[i] == functions[gate.f][y[gate.in1]][y[gate.in2]]) & (x[i] == -1) for i, gate in enumerate(gates) if i > 1]
)

minimize(
    # minimizing the number of faulty gates
    Sum(x[i] != -1 for i in range(2, nGates))
)
