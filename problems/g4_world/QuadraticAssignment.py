from pycsp3 import *

"""
 See QAPLib and https://en.wikipedia.org/wiki/Quadratic_assignment_problem
"""

w = data.weights  # facility weights
distances = data.distances  # location distances
all_distances = {d for row in distances for d in row}
n = len(w)

table = {(i, j, distances[i][j]) for i in range(n) for j in range(n) if i != j}

# x[i] is the location assigned to the ith facility
x = VarArray(size=n, dom=range(n))

# d[i][j] is the distance between the locations assigned to the ith and jth facilities
d = VarArray(size=[n, n], dom=lambda i, j: all_distances if i < j and w[i][j] != 0 else None)

satisfy(
    # all locations must be different
    AllDifferent(x),

    # computing the distances
    [(x[i], x[j], d[i][j]) in table for i, j in combinations(range(n), 2) if w[i][j] != 0]
)

minimize(
    #  minimizing summed up distances multiplied by flows
    Sum(w[i][j] * d[i][j] for i, j in combinations(range(n), 2) if w[i][j] != 0)
)
