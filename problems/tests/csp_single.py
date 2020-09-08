import os

from pycsp3.problems.tests.tester import Tester, run

run(Tester("csp" + os.sep + "single")
    .add("TravelingWorld")  # unsat
    .add("TravelingWorld", variant="integer")  # unsat
    .add("Riddle", variant="v1")  # 1 solution
    .add("Riddle", variant="v2")  # 1 solution
    .add("Riddle", variant="v3a")  # 1 solution
    .add("Riddle", variant="v3b")  # 1 solution
    .add("Riddle", variant="v4a")  # 1 solution
    .add("Riddle", variant="v4b")  # 1 solution
    .add("Riddle", variant="v5")  # 1 solution
    .add("SimpleColoring")  # unsat

    .add("Agatha")  # 4 solutions
    .add("Allergy")  # 1 solution
    .add("Alpha")  # 1 solution
    .add("Alpha", variant="var")  # 1 solution
    .add("LabeledDice")  # 48 solutions
    .add("NFractions")  # 22 solutions
    .add("Picnic")  # 1 solution
    .add("Purdey")  # 1 solution
    .add("Sandwich")  # 8 solutions
    .add("SendMore")  # 1 solution
    .add("TrafficLights")  # 4 solutions
    .add("Zebra")  # 48 solutions
    )
