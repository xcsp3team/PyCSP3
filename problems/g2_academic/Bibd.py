from pycsp3 import *

# Problem 028 at CSPLib

v, b, r, k, l = data.v, data.b, data.r, data.k, data.l
b = (l * v * (v - 1)) // (k * (k - 1)) if b == 0 else b
r = (l * (v - 1)) // (k - 1) if r == 0 else r

# x[i][j] is the value of the matrix at row i and column j
x = VarArray(size=[v, b], dom={0, 1})

if not variant():
    satisfy(
        # constraints on rows
        [Sum(row) == r for row in x],

        # constraints on columns
        [Sum(col) == k for col in columns(x)],

        # scalar constraints with respect to lambda
        [row1 * row2 == l for (row1, row2) in combinations(x, 2)]
    )

elif variant("aux"):
    #  s[i][j][k] is the product of x[i][k] and x[j][k]
    s = VarArray(size=[v, v, b], dom={0, 1})

    satisfy(
        # constraints on rows
        [Sum(x[i]) == r for i in range(v)],

        # constraints on columns
        [Sum(x[:, j]) == k for j in range(b)],  # or use Sum(x[ANY, j])

        # computing scalar variables
        [s[i][j][k] == x[i][k] * x[j][k] for i in range(v) for j in range(i + 1, v) for k in range(b)],

        # scalar constraints with respect to lambda
        [Sum(s[i][j]) == l for i in range(v) for j in range(i + 1, v)]
    )

satisfy(
    # Increasingly ordering both rows and columns tag(symmetry-breaking)
    LexIncreasing(x, matrix=True)
)

'''
Possible data passing:
    -data=Bibd-3-4-6.json
    -data=[9,0,0,3,9]  # Important: order is imposed by the order in which fields are accessed
    -data=[v=9,b=0,r=0,k=3,l=9] ou -data=[b=0,v=9,r=0,k=3,l=9]  # no more need to pay attention to order
    example of data: 46,69,9,6,1
'''