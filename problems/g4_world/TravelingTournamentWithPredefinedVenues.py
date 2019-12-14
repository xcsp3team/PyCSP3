from pycsp3 import *

# Problem 068 at CSPLib

predefinedVenues = data.predefinedVenues
nTeams, nRounds = data.nTeams, data.nTeams - 1
assert nTeams % 2 == 0, "an even number of teams is expected"
nConsecutiveGames = 2 if variant("a2") else 3  # used in one comment


def circ_distance(i, j):
    return min(abs(i - j), nTeams - abs(i - j))


def table_end(i):
    # when playing at home (whatever the opponent, travel distance is 0)
    return [(1, ANY, 0)] + [(0, j, circ_distance(i, j)) for j in range(nTeams) if j != i]


def table_intern(i):
    return ([(1, 1, ANY, ANY, 0)]
            + [(0, 1, j, ANY, circ_distance(j, i)) for j in range(nTeams) if j != i]
            + [(1, 0, ANY, j, circ_distance(i, j)) for j in range(nTeams) if j != i]
            + [(0, 0, j1, j2, circ_distance(j1, j2)) for j1 in range(nTeams) for j2 in range(nTeams) if different_values(i, j1, j2)])


def automaton():
    t = [("q", 0, "q01"), ("q", 1, "q11"), ("q01", 0, "q02"), ("q01", 1, "q11"), ("q11", 0, "q01"), ("q11", 1, "q12"), ("q02", 1, "q11"), ("q12", 0, "q01")]
    if variant("a3"):
        t += [("q02", 0, "q03"), ("q12", 1, "q13"), ("q03", 1, "q11"), ("q13", 0, "q01")]
    return Automaton(start="q", final=["q01", "q02", "q11", "q12"] + ([] if variant("a2") else ["q03", "q13"]), transitions=t)


automaton = automaton()

#  o[i][k] is the opponent (team) of the ith team  at the kth round
o = VarArray(size=[nTeams, nRounds], dom=range(nTeams))

#  h[i][k] is 1 iff the ith team plays at home at the kth round
h = VarArray(size=[nTeams, nRounds], dom={0, 1})

#  t[i][k] is the travelled distance by the ith team at the kth round. An additional round is considered for returning at home.
t = VarArray(size=[nTeams, nRounds + 1], dom=range(nTeams // 2 + 1))

satisfy(
    #  a team cannot play against itself
    [o[i][k] != i for i in range(nTeams) for k in range(nRounds)],

    # Ensuring predefined venues  
    [predefinedVenues[i][o[i][k]] == h[i][k] for i in range(nTeams) for k in range(nRounds)],

    # ensuring symmetry of games: if team i plays against j, then team j plays against i
    [o.col(k)[o[i][k]] == i for i in range(nTeams) for k in range(nRounds)],

    # each team plays once against all other teams 
    [AllDifferent(row) for row in o],

    # at most 'nConsecutiveGames' consecutive games at home, or consecutive games away 
    [h[i] in automaton for i in range(nTeams)],

    # handling travelling for the first game 
    [(h[i][0], o[i][0], t[i][0]) in table_end(i) for i in range(nTeams)],

    # handling travelling for the last game
    [(h[i][- 1], o[i][- 1], t[i][-1]) in table_end(i) for i in range(nTeams)],

    # handling travelling for two successive games
    [(h[i][k], h[i][k + 1], o[i][k], o[i][k + 1], t[i][k + 1]) in table_intern(i) for i in range(nTeams) for k in range(nRounds - 1)],

    # at each round, opponents are all different
    # tag(redundant-constraints)
    [AllDifferent(col) for col in columns(o)],

    # tag(symmetry-breaking)
    o[0][0] < o[0][- 1]
)

minimize(
    Sum(t)
)