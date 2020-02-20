from pycsp3 import *

nDepots, nRestaurants = data.nDepots, len(data.restaurants)
positions = [restaurant.position for restaurant in data.restaurants]
# NOTE: cp_array is necessary for using the constraint Element in the main variant
distances = cp_array([abs(positions[j] - positions[i]) for j in range(nRestaurants)] for i in range(nRestaurants))

# d[i][j] is the distance between the ith restaurant and the jth depot
d = VarArray(size=[nRestaurants, nDepots], dom=lambda i, j: distances[i])

# md[i] is the minimum distance between the ith restaurant and any depot
md = VarArray(size=nRestaurants, dom=lambda i: distances[i])

if not variant():
    # x[j] is the index of the restaurant used as the jth depot
    x = VarArray(size=nDepots, dom=range(nRestaurants))

    satisfy(
        # linking positions of depots with their distances to the restaurants
        distances[i][x[j]] == d[i][j] for i in range(nRestaurants) for j in range(nDepots)
    )

elif variant("table"):
    # x[i] is the position of the ith depot
    x = VarArray(size=nDepots, dom=set(positions))

    satisfy(
        # linking positions of depots with their distances to the restaurants
        (x[j], d[i][j]) in {(p, abs(p - positions[i])) for p in positions} for i in range(nRestaurants) for j in range(nDepots)
    )

satisfy(
    # computing minimum distances
    [Minimum(d[i]) == md[i] for i in range(nRestaurants)],

    # tag(symmetry-breaking)
    Increasing(x, strict=True)
)

minimize(
    Sum(md)
    # TODO in a future version, being able to post Sum(Minimum(d[i] for i in range(nRestaurants). But requires an extension of XCSP3 (or automatic reformulation).
)
