from pycsp3 import *

"""
 see BPPLIB – A Bin Packing Problem Library
"""

capacity = data.binCapacity
weights = sorted(data.itemWeights)
nItems = len(weights)


def n_bins():
    cnt = 0
    curr_load = 0
    for i, weight in enumerate(weights):
        curr_load += weight
        if curr_load > capacity:
            cnt += 1
            curr_load = weight
    return cnt


def max_items_per_bin():
    curr = 0
    for i, weight in enumerate(weights):
        curr += weight
        if curr > capacity:
            return i
    return -1


def occurrences_of_weights():
    pairs = []
    cnt = 1
    for i in range(1, nItems):
        if weights[i] != weights[i - 1]:
            pairs.append((weights[i - 1], cnt))
            cnt = 0
        cnt += 1
    pairs.append((weights[-1], cnt))
    return pairs


nBins, maxPerBin = n_bins(), max_items_per_bin()

# w[i][j] is the weight of the jth object put in the ith bin. It is 0 if less than j objects are present in the bin.
w = VarArray(size=[nBins, maxPerBin], dom={0, *weights})

if not variant():
    satisfy(
        # not exceeding the capacity of each bin
        [Sum(w[i]) <= capacity for i in range(nBins)],

        # items are stored decreasingly in each bin according to their weights
        [Decreasing(w[i]) for i in range(nBins)]
    )
elif variant("table"):
    def table():
        def table_recursive(n_stored, i, curr):
            assert len(tuples) < 200000000, "impossible to build a table of moderate size"  # hard coding (value)
            assert curr + weights[i] <= capacity
            tmp[n_stored] = weights[i]
            curr += weights[i]
            tuples.add(tuple(tmp[j] if j < n_stored + 1 else 0 for j in range(maxPerBin)))
            for j in range(i):
                if curr + weights[j] > capacity:
                    break
                if j == i - 1 or weights[j] != weights[j + 1]:
                    table_recursive(n_stored + 1, j, curr)

        tmp = [0] * maxPerBin
        tuples = {tuple(tmp)}
        for i in range(nItems):
            if i == nItems - 1 or weights[i] != weights[i + 1]:
                table_recursive(0, i, 0)
        return tuples


    table = table()
    satisfy(
        w[i] in table for i in range(nBins)
    )

satisfy(
    # ensuring that each item is stored in a bin
    Cardinality(w, occurrences={0: nBins * maxPerBin - nItems} + {wgt: occ for (wgt, occ) in occurrences_of_weights()}),

    # tag(symmetry-breaking)
    LexDecreasing(w)
)

maximize(
    # maximizing the number of unused bins
    Sum(w[i][0] == 0 for i in range(nBins))
)
