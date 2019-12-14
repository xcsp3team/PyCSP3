from pycsp3 import *

distances = data.distances
nTeams, nRounds = len(distances), len(distances) * 2 - 2
assert nTeams % 2 == 0, "An even number of teams is expected"
nConsecutiveGames = 2 if variant("a2") else 3  # used in one comment


def table_end(i):
    # note that when playing at home (whatever the opponent, travel distance is 0)
    return {(1, ANY, 0)} | {(0, j, distances[i][j]) for j in range(nTeams) if j != i}


def table_other(i):
    t = [(1, 1, ANY, ANY, 0)]
    t += [(0, 1, j, ANY, distances[i][j]) for j in range(nTeams) if j != i]
    t += [(1, 0, ANY, j, distances[i][j]) for j in range(nTeams) if j != i]
    t += [(0, 0, j1, j2, distances[j1][j2]) for j1 in range(nTeams) for j2 in range(nTeams) if different_values(i, j1, j2)]
    return t


def automaton():
    t = [("q", 0, "q01"), ("q", 1, "q11"), ("q01", 0, "q02"), ("q01", 1, "q11")]
    t += [("q11", 0, "q01"), ("q11", 1, "q12"), ("q02", 1, "q11"), ("q12", 0, "q01")]
    t += [("q02", 0, "q03"), ("q12", 1, "q13"), ("q03", 1, "q11"), ("q13", 0, "q01")] if variant("a3") else []
    return Automaton(start="q", final=["q01", "q02", "q11", "q12"] + (["q03", "q13"] if variant("a3") else []), transitions=t)


automaton = automaton()

#  o[i][k] is the opponent (team) of the ith team  at the kth round
o = VarArray(size=[nTeams, nRounds], dom=range(nTeams))

#  h[i][k] is 1 iff the ith team plays at home at the kth round
h = VarArray(size=[nTeams, nRounds], dom={0, 1})

# a[i][k] is 0 iff the ith team plays away at the kth round
a = VarArray(size=[nTeams, nRounds], dom={0, 1})

# t[i][k] is the travelled distance by the ith team at the kth round. An additionnal round is considered for returning at home.
t = VarArray(size=[nTeams, nRounds + 1], dom={d for row in distances for d in row})

satisfy(

    # each team must play exactly two times against each other team
    [Cardinality(o[i], occurrences={j: 2 for j in range(nTeams) if j != i}, closed=True) for i in range(nTeams)],

    # ensuring symmetry of games: if team i plays against j at round k, then team j plays against i at round k
    [o[o[i][k]][k] == i for i in range(nTeams) for k in range(nRounds)],

    # playing home at round k iff not playing away at round k
    [h[i][k] == ~a[i][k] for i in range(nTeams) for k in range(nRounds)],

    # channeling the three arrays
    [h[o[i][k]][k] == a[i][k] for i in range(nTeams) for k in range(nRounds)],

    # playing against the same team must be done once at home and once away
    [imply(o[i][k1] == o[i][k2], h[i][k1] != h[i][k2]) for i in range(nTeams) for k1 in range(nRounds) for k2 in range(k1 + 2, nRounds)],

    # at each round, opponents are all different  tag(redundant-constraints)
    [AllDifferent(o[ANY, k]) for k in range(nRounds)],

    # tag(symmetry-breaking)
    o[0][0] < o[0][- 1],

    # at most 'nConsecutiveGames' consecutive games at home, or consecutive games away
    [h[i] in automaton for i in range(nTeams)],

    # handling travelling for the first game
    [(h[i][0], o[i][0], t[i][0]) in table_end(i) for i in range(nTeams)],

    #  handling travelling for the last game
    [(h[i][- 1], o[i][- 1], t[i][-1]) in table_end(i) for i in range(nTeams)],

    #  handling travelling for two successive games
    [(h[i][k], h[i][k + 1], o[i][k], o[i][k + 1], t[i][k + 1]) in table_other(i) for i in range(nTeams) for k in range(nRounds - 1)]

)

minimize(
    # minimizing summed up travelled distance
    Sum(t)
)

# TODO changer en channel ? (chriss)