import ast
import datetime
import inspect
import json
import lzma
import os
import os.path
import sys
from collections import OrderedDict, namedtuple, Mapping
from importlib import util

from lxml import etree

from pycsp3.dashboard import options
from pycsp3.problems.data import dataparser
from pycsp3.tools.aggregator import build_similar_constraints
from pycsp3.tools.compactor import build_compact_forms
from pycsp3.tools.curser import OpOverrider, ListInt, convert_to_namedtuples, is_namedtuple
from pycsp3.tools.slider import handle_slides
from pycsp3.tools.utilities import Stopwatch
from pycsp3.tools.xcsp import build_document


class Compilation:
    string_model = None
    string_data = None
    model = None
    data = None
    stopwatch1 = None
    stopwatch2 = None
    done = False

    @staticmethod
    def load(console=False):
        _load(console=console)

    @staticmethod
    def compile():
        return _compile()


class DataVisitor(ast.NodeVisitor):
    def __init__(self, raw_data):
        self.raw_data = raw_data  # raw data under the form [x,y,z] with x, y, z values
        self.ordered_data = []
        self.cnt = 0
        self.compilation_data = OrderedDict()  # the object used for recording the data, available in the model

    def visit(self, node):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "data" and node.attr not in self.compilation_data:
            assert self.cnt < len(self.raw_data), \
                "The number of fields in the object 'data' must be equal to the number of values specified with the option -data "
            value = int(self.raw_data[self.cnt]) if self.raw_data[self.cnt] and self.raw_data[self.cnt].isdigit() else self.raw_data[self.cnt]
            if options.debug:
                print("Load data", value, "in", node.attr)
            self.compilation_data[node.attr] = value
            self.ordered_data.append(value)
            self.cnt += 1
        ast.NodeVisitor.visit(self, node)
        return self.compilation_data, self.ordered_data


def _load_data_names(raw_data):
    return DataVisitor(raw_data).visit(ast.parse(inspect.getsource(Compilation.model)))


def _load_options():
    options.set_values("dataparser", "data", "dataexport", "variant", "output", "checker")
    options.set_flags("dataexport", "ev", "compress", "debug", "display", "time", "nocomment", "solve")
    if options.checker is None:
        options.checker = "fast"
    assert options.checker in {"complete", "fast", "none"}
    options.parse(sys.argv[1:])


def _load_model():
    try:
        name = sys.argv[0]
        assert name.strip().endswith(".py"), "The first argument has to be a python file."
        model_string = name[name.rfind(os.sep) + 1:name.rfind(".")]
        specification = util.spec_from_file_location("", name)
        model = util.module_from_spec(specification)
        # model.specification = specification
        return model, model_string
    except:
        usage("It was not possible to read the file: " + sys.argv[0])
        raise


def _load_data():
    None_Values = ['None', '']  # adding 'none' and 'null'?
    data = options.data
    compilation_data = OrderedDict()  # the object used for recording the data, available in the model
    if data is None:
        return compilation_data, ""
    if data.endswith(".json"):
        assert os.path.exists(data), "The file " + data + " does not exist (in the specified directory)."
        with open(data) as f:
            compilation_data = json.loads(f.read(), object_pairs_hook=OrderedDict)
            string_data = "-" + data.split(os.sep)[-1:][0].split(".")[:1][0]
    else:
        #  if '{' in data and '}' in data:
        #    compilation_data = json.loads(data, object_hook=lambda d: namedtuple('X', d.keys())(*d.values()), object_pairs_hook=OrderedDict)
        #    for k, v in compilation_data.items(): setattr(compilation_data, k, v)  ordered_data = list(compilation_data.values())
        if '[' in data and ']' in data:
            args = [None if arg in None_Values else arg for arg in data[1:-1].split(",")]
            if '=' in data:
                assert data.count('=') == data.count(',') + 1, "badly formed string of data " + data
                ordered_data = []
                for arg in args:
                    t = arg.split('=')
                    value = int(t[1]) if t[1].isdigit() else None if t[1] in None_Values else t[1]
                    compilation_data[t[0]] = value
                    ordered_data.append(value)
            else:
                compilation_data, ordered_data = _load_data_names(args)
        else:
            compilation_data, ordered_data = _load_data_names([data if data not in None_Values else None])
        string_data = "-" + "-".join(str(v) for v in ordered_data)
    if options.debug:
        print("Compilation data:", compilation_data, "\nString data:", string_data)
    return compilation_data, string_data


def _load_dataparser(parser_file, data_file):
    try:
        compilation_data = dataparser.register_fields(data_file)  # the object used for recording data is returned, available in the model
        specification = util.spec_from_file_location("", parser_file)
        specification.loader.exec_module(util.module_from_spec(specification))
        string_data = "-" + options.data.split(os.sep)[-1:][0].split(".")[:1][0] if options.data else None
        if string_data is None:
            string_data = Compilation.string_data if Compilation.string_data else ""  # in case data are recorded through the dataparser (after asking the user)
        return compilation_data, string_data
    except:
        usage("It was not possible to correctly read the file: " + parser_file)
        raise


def _load(*, console=False):
    _load_options()
    if options.time:
        Compilation.stopwatch1, Compilation.stopwatch2 = Stopwatch(), Stopwatch()
    if console is False:
        Compilation.model, Compilation.string_model = _load_model()
        if options.dataparser:
            Compilation.data, Compilation.string_data = _load_dataparser(options.dataparser, options.data)
        else:
            Compilation.data, Compilation.string_data = _load_data()
        Compilation.data = convert_to_namedtuples(Compilation.data)
    else:
        Compilation.string_model = "Console"
        Compilation.string_data = ""
    OpOverrider.enable()


def _compile():
    # used to save data in jSON
    def prepare_for_json(obj):
        if is_namedtuple(obj):
            r = obj._asdict()
            for k in r:
                r[k] = prepare_for_json(r[k])
            return r
        if isinstance(obj, list):
            for i in range(len(obj)):
                obj[i] = prepare_for_json(obj[i])
            return obj
        return str(obj) if isinstance(obj, datetime.time) else obj

    OpOverrider.disable()
    if options.debug or options.display:
        print("\n", sys.argv, "\n")
        if sys.argv[1].endswith(".json"):
            with open(sys.argv[1], 'r') as f:
                print(f.read())

    if options.time:
        print("\tWall time to put the model in memory:", Compilation.stopwatch1.elapsed_time(reset=True), "seconds")
    build_similar_constraints()
    if options.time:
        print("\tWall time for creating groups:", Compilation.stopwatch1.elapsed_time(reset=True), "seconds")
    handle_slides()
    if options.time:
        print("\tWall time for creating slides:", Compilation.stopwatch1.elapsed_time(reset=True), "seconds")
    build_compact_forms()
    if options.time:
        print("\tWall time for creating compact forms:", Compilation.stopwatch1.elapsed_time(reset=True), "seconds")

    filename_prefix = Compilation.string_model + ("-" + options.variant if options.variant else "") + Compilation.string_data

    filename = filename_prefix + ".xml"
    root = build_document()
    if root is not None:
        pretty_text = etree.tostring(root, pretty_print=True, xml_declaration=False).decode("UTF-8")
        with open(filename, "w") as f:
            f.write(pretty_text)
            print("  Generation of the file " + filename + " completed.")
        if options.compress:
            with lzma.open(filename + ".lzma", "w") as f:
                f.write(bytes(pretty_text, 'utf-8'))
                print("\tGeneration of the file " + filename + ".lzma completed.")
        if options.debug or options.display:
            print("\n", pretty_text)
        if options.time is True:
            print("\tWall time for creating the XML file:", Compilation.stopwatch1.elapsed_time(reset=True), "seconds")

    if options.dataexport:
        if isinstance(options.dataexport, bool):
            json_prefix = options.data.split("/")[-1:][0].split(".")[:1][0] if options.dataparser else filename_prefix
            # TODO if data are given with name as e.g., in [k=3,l=9,b=0,r=0,v=9] for Bibd, maybe we should sort them
        else:
            json_prefix = str(options.dataexport)
        with open(json_prefix + '.json', 'w') as f:
            json.dump(prepare_for_json(Compilation.data), f)
        print("  Generation for data saving of the file " + json_prefix + '.json' + " completed.")

    if options.time is True:
        print("\tTotal wall clock time:", Compilation.stopwatch2.elapsed_time(), "seconds")

    Compilation.done = True

    if options.solve is True:
        from pycsp3.solvers.abscon import AbsConProcess
        solution = AbsConProcess().solve(filename)
        print()
        print(solution)

    return filename


def usage(message):
    print(message)
    print("\nThe PyCSP3 Compiler allows us to generate XCSP3 files.")
    print("\n\nUsage: python3.5 <model> <data>")
    print("  - <model> is the name of a Python file containing a PyCSP3 model (i.e., a Python file with code to post variables/constraints/objectives)")
    print("  - <data> is either a fixed list of elementary data or the name of a JSON file")
