import atexit
import os, sys

__python_version__ = str(sys.version).split(os.linesep)[0].split(' ')[0]

if sys.version_info[0] < 3 or sys.version_info[1] < 5:
    __message_version__ = os.linesep + " Python should be at least 3.5" + os.linesep + " Your version is Python " + __python_version__
    raise Exception(__message_version__)

from pycsp3.functions import *  # keep it at first position (before Compilation)
from pycsp3.compiler import Compilation

__version__ = open(os.path.join(os.path.dirname(__file__), 'version.txt'), encoding='utf-8').read()

if sys.argv:
    if len(sys.argv) == 1 and sys.argv[0] == "-m":
        import shutil
        import pycsp3

        print("Python version: ", __python_version__)
        print("pycsp3 version: ", __version__)
        problems = os.sep.join(pycsp3.__file__.split(os.sep)[:-1]) + os.sep + "problems" + os.sep
        target = os.getcwd() + os.sep + "problems" + os.sep
        print("Source of files found: ", problems)
        shutil.copytree(problems, target, ignore=shutil.ignore_patterns('g6_testing', 'g7_todo', 'tests', '__init__.py', '__pycache__*'))
        print("Successfully created the directory " + target + " containing the problems !")
        exit(0)
    elif sys.argv[0] == '':
        Compilation.load(console=True)
        data = None
    else:
        # TODO: analysing if we have to compile (e..g, when running the tester, we should not try to do that); Trying this with the inspector?
        if "pycsp3/problems/tests/" not in sys.argv[0]:  # TODO is it correct?
            Compilation.load()
            data = Compilation.data
        else:
            Compilation.done = True


def compile(user_filename=None):
    Compilation.set_filename(user_filename)
    return Compilation.compile()


@atexit.register
def end():
    if not Compilation.done:
        Compilation.compile()
