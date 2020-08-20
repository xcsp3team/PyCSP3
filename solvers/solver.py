import os
import subprocess
import time
from io import IOBase

from lxml import etree
from py4j.java_gateway import JavaGateway, Py4JNetworkError

from pycsp3.classes.main.variables import Variable, VariableInteger
from pycsp3.classes.entities import VarEntities, EVarArray, EVar
from pycsp3.tools.utilities import Stopwatch, flatten
from pycsp3.dashboard import options

class Instantiation:
    def __init__(self, pretty_solution, variables, values):
        self.pretty_solution = pretty_solution
        self.variables = variables
        self.values = values

    def __repr__(self):
        return self.variables, self.values

    def __str__(self):
        return str(self.pretty_solution)

class SolverPy4J:
    gateways = []
    processes = []

    def __init__(self, *, name, command):
        self.gateway, self.process = SolverPy4J.connexion(command)
        SolverPy4J.gateways.append(self.gateway)
        SolverPy4J.processes.append(self.process)
        self.solver = self.gateway.entry_point.getSolver()
        self.name = name

    @staticmethod
    def connexion(command):
        process = subprocess.Popen(command.split())
        cnt = 0
        while True:
            time.sleep(0.1)
            cnt += 1
            print("Py4J Connection " + str(cnt) + " ...")
            try:
                gateway = JavaGateway(eager_load=True)
            except Py4JNetworkError:
                print("Py4J Connection failed: No JVM listening ...")
            else:
                print("Py4J Successfully connected to the JVM")
                return gateway, process
        return gateway, process

    @staticmethod
    def close():
        for element in SolverPy4J.gateways:
            element.close()

    def loadXCSP3(self, arg):
        if isinstance(arg, str):
            self.solver.loadXCSP3(arg)
        elif isinstance(arg, IOBase):
            self.solver.loadXCSP3(arg.name)


class SolverProcess:
    def __init__(self, *, name, command):
        self.name = name
        self.command = command
        self.stdout = None
        self.stderr = None

    def directory_of_solver(self, name):
        # assert name in {"abscon", "choco"}  #  for the moment, two embedded solvers"
        return os.sep.join(__file__.split(os.sep)[:-1]) + os.sep + name + os.sep

    def class_path(self):
        raise NotImplementedError("Must be overridden")
    
    def parse_options(self, string_options, dict_options, dict_simplified_options):
        raise NotImplementedError("Must be overridden")
    
    def solve(self, model, string_options="", dict_options=dict(), dict_simplified_options=dict()):
        stopwatch = Stopwatch()
        args_solver = self.parse_options(string_options, dict_options, dict_simplified_options)    
        verbose = options.solve or "verbose" in dict_simplified_options
        command = self.command + " " + model + " " + args_solver + (" " + options.solverargs if options.solverargs else "")
        if not verbose:
            print("\n  * Solving by " + self.name + " in progress ... ")
        if verbose:
            print("\n  command: ", command + "\n")
        else:
            print("    command: ", command)
        result = self.execute(command, verbose)
        if not verbose:
            print("  * Solved by " + self.name + " in " + stopwatch.elapsed_time()
                  + " seconds (use the solver option v to see directly the output of the solver).\n")
        return self.solution() if result else None

    def execute(self, command, verbose):
        try:
            if verbose:
                subprocess.Popen(command.split()).communicate()
                return False  # in verbose mode, the solution is ignored
            else:
                p = subprocess.Popen(command.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                out, error = p.communicate()
                self.stdout, self.stderr = out.decode('utf-8'), error.decode('utf-8')
                return True
        except KeyboardInterrupt:
            return False

    def solution(self):
        if self.stdout.find("<unsatisfiable") != -1 or self.stdout.find("s UNSATISFIABLE") != -1:
            return Instantiation("unsatisfiable", None, None)
        if self.stdout.find("<instantiation") == -1 or self.stdout.find("</instantiation>") == -1:
            print("  actually, the instance was not solved (add the option -ev to have more details")
            return None
        left, right = self.stdout.rfind("<instantiation"), self.stdout.rfind("</instantiation>")
        s = self.stdout[left:right + len("</instantiation>")].replace("\nv", "")
        root = etree.fromstring(s, etree.XMLParser(remove_blank_text=True))
        variables = []
        for token in root[0].text.split():
            r = VarEntities.get_item_with_name(token)
            if isinstance(r, (EVar, Variable)):  # TODO why do we need these two classes of variables?
                variables.append(r)
            else:
                for x in flatten(r.variables, keep_none=True):
                    variables.append(x)
        values = root[1].text.split()  # a list with all values given as strings (possibly '*')
        assert len(variables) == len(values)
        for i, v in enumerate(values):
            if variables[i]:
                variables[i].value = v  # we add new field (may be useful)

        pretty_solution = etree.tostring(root, pretty_print=True, xml_declaration=False).decode("UTF-8").strip()
        return Instantiation(pretty_solution, variables, values)
