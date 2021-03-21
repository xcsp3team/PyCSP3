import os
from collections import OrderedDict

from pycsp3 import functions
from pycsp3.classes.auxiliary.conditions import Condition, ConditionInterval, ConditionSet
from pycsp3.classes.auxiliary.ptypes import TypeVar, TypeCtr, TypeCtrArg, TypeXML, TypeConditionOperator, TypeRank
from pycsp3.classes.auxiliary.values import IntegerEntity
from pycsp3.classes.entities import EVarArray, ECtr, EMetaCtr, TypeNode, Node
from pycsp3.classes.main.domains import Domain
from pycsp3.classes.main.variables import Variable, VariableInteger
from pycsp3.dashboard import options
from pycsp3.tools import curser
from pycsp3.tools.utilities import ANY, is_1d_list, matrix_to_string, transitions_to_string, integers_to_string, table_to_string, flatten, is_matrix, error, \
    to_ordinary_table, warning


class Diffs:
    """"
      Objects of this class are used to record the differences between two (or more) close constraints.
      This allows us to build groups in an automatic way.
    """

    fusion = None  # the current Diffs object memorizing the arguments that differ between two (or more) constraints

    @staticmethod
    def reset():
        Diffs.fusion = None

    def __init__(self, records=[]):
        self.argument_names = [name for (name, flag) in records]
        self.argument_flags = [flag for (name, flag) in records]

    def merge(self):
        if Diffs.fusion is None:
            Diffs.fusion = self  # this is the first time such an object is built (since the last reset); we simply record it
        else:  # the recorded object (fusion) and the last built one are compatible (we know that at time of calling); so, we simply update flags
            for i, name in enumerate(self.argument_names):
                index = Diffs.fusion.argument_names.index(name)  # note that self.argument_names must be be included in Diffs.fusion.argument_names
                Diffs.fusion.argument_flags[index] |= self.argument_flags[i]
                # for i in range(len(Diffs.fusion.argument_flags)): Diffs.fusion.argument_flags[i] |= self.argument_flags[i]


class ConstraintArgument:
    def __init__(self, name, content, attributes=[], content_compressible=True, content_ordered=False, lifted=False):
        assert isinstance(name, (TypeCtrArg, TypeXML)), str(name) + " " + str(type(name))
        self.name = name  # name of the argument
        self.attributes = attributes  # list of pairs (key, value) representing the attributes
        self.content = content  # content of the argument
        self.content_compressible = content_compressible  # indicates if we can try to make the content more compact
        self.content_ordered = content_ordered  # indicates if the content must be kept as it is (order is important)
        self.lifted = lifted  # indicates if the constraint is lifted to several lists (or sets); see specifications

    def __eq__(self, other):  # must be called in protection mode (see in functions.py the function protect())
        if not isinstance(other, ConstraintArgument) or self.name != other.name or len(self.attributes) > 0 or len(other.attributes) > 0:
            return False  # attributes not currently completely taken into account
        if self.content_compressible != other.content_compressible or self.content_ordered != other.content_ordered or self.lifted != other.lifted:
            return False
        return curser.OpOverrider.eq_protected(self.content, other.content)

        # #print(type(self.content),type(other.content))
        # if isinstance(self.content, list):  #
        #     return list.__eq__(self.content, other.content)
        # #if isinstance(self.content, (EMetaCtr, Variable, Node)):
        # #    return object.__eq__(self.content, other.content)
        # return object.__eq__(self.content, other.content)
        # return self.content == other.content

    def __str__(self):
        return str(self.name) + ":" + str(self.content)


class Constraint:
    def __init__(self, name):
        self.name = name
        self.attributes = []
        self.arguments = OrderedDict()  # arguments of the constraint (such as list, supports, condition, ...)
        self.n_parameters = 0  # used when building abstract forms of constraints (e.g., in groups for %0 %1 %2 ...)

    def __eq__(self, other):  # must be called in protection mode (see in functions.py the function protect())
        if not isinstance(other, Constraint) or self.name != other.name or len(self.attributes) > 0 or len(other.attributes) > 0:
            return False  # attributes not currently completely taken into account
        if self.n_parameters > 0 or other.n_parameters > 0:
            return False
        return self.arguments == other.arguments

    def equal_except_condition(self, other):
        if not isinstance(other, Constraint) or self.name != other.name or len(self.attributes) > 0 or len(other.attributes) > 0:
            return False  # attributes not currently completely taken into account
        if self.n_parameters > 0 or other.n_parameters > 0:
            return False
        return [v for v in self.arguments.items() if str(v[0]) != "condition"] == [v for v in other.arguments.items() if str(v[0]) != "condition"]

    def arg(self, name, content, *, attributes=[], content_compressible=True, content_ordered=False, lifted=False):
        self.arguments[name] = ConstraintArgument(name, content, attributes, content_compressible, content_ordered, lifted)
        return self

    def set_condition(self, operator, right_operand):
        return self.arg(TypeCtrArg.CONDITION, Condition.build_condition((operator, right_operand)))

    def set_value(self, new_value):
        return self.arg(TypeCtrArg.VALUE, new_value)

    def similar_structure(self, other):
        if type(self) != type(other) or self.attributes != other.attributes:
            return False
        args1, args2 = list(self.arguments.values()), list(other.arguments.values())
        if len(args1) != len(args2):
            return False
        if any(args1[i].attributes != args2[i].attributes or args1[i].lifted != args2[i].lifted for i in range(len(args1))):
            return False
        return any(type(args1[i].content) == type(args2[i].content) for i in range(len(args1)))

    def close_to(self, other):
        if not self.similar_structure(other):
            return False
        args1, args2 = list(self.arguments.values()), list(other.arguments.values())
        records = []
        for i in range(len(args1)):
            if str(args1[i].content) != str(args2[i].content):
                if args1[i].name == TypeCtrArg.CONDITION and args1[i].content.operator != args2[i].content.operator:
                    return False  # the operators are different in the two conditions
                b = hasattr(args1[i].content, '__len__') and hasattr(args2[i].content, '__len__') and len(args1[i].content) != len(args2[i].content)
                records.append((args1[i].name, b))
        if len(records) > 2:
            return False  # too many differences
        diffs = Diffs(records)
        if len(records) == 0:
            return diffs
        if Diffs.fusion and not all(
                name in Diffs.fusion.argument_names for name in diffs.argument_names):  # diffs.argument_names != Diffs.fusion.argument_names:
            return False  # because arguments are not the same (so it is not possible to make a unique abstraction)
        if len([flag for flag in diffs.argument_flags if flag]) > 1:
            return False  # two arguments of different size cannot be currently abstracted
        return diffs

    def parameter_form(self, p):
        length = len(p) if isinstance(p, list) else 1
        self.n_parameters += length
        return " ".join("%" + str(v + self.n_parameters - length) for v in range(length))

    def __str__(self):
        return str(self.name) + ": " + " ".join(str(a) for a in self.attributes) + " ".join(str(v) for k, v in self.arguments.items())


class ConstraintUnmergeable(Constraint):
    def __init__(self, name):
        super().__init__(name)

    def close_to(self, other):
        return False


class ConstraintWithCondition(Constraint):
    def __init__(self, name):
        super().__init__(name)

    def min_possible_value(self):
        pass

    def max_possible_value(self):
        pass


''' Generic Constraints '''


class ConstraintIntension(Constraint):
    def __init__(self, tree):
        super().__init__(TypeCtr.INTENSION)
        self.arg(TypeCtrArg.FUNCTION, tree)

    def abstract_tree(self):
        return self.arguments[TypeCtrArg.FUNCTION].content.abstract_tree()

    def abstract_values(self):
        return self.arguments[TypeCtrArg.FUNCTION].content.abstract_values()

    def close_to(self, other):
        if not self.similar_structure(other):
            return False
        return Diffs() if self.abstract_tree() == other.abstract_tree() else False


class ConstraintExtension(Constraint):
    cache = dict()
    cache_smart = dict()

    @staticmethod
    def convert_smart_to_ordinary(scope, table):
        for i, t in enumerate(table):
            tpl = None
            for j, v in enumerate(t):
                if isinstance(v, int) or v == ANY:
                    if tpl:
                        tpl.append(v)
                else:
                    if isinstance(v, range):
                        if not tpl:
                            tpl = list(t[:j])
                        tpl.append(ConditionInterval(TypeConditionOperator.IN, v.start, v.stop - 1))
                    elif isinstance(v, (tuple, list, set, frozenset)):
                        assert all(isinstance(w, int) for w in v)
                        if not tpl:
                            tpl = list(t[:j])
                        tpl.append(ConditionSet(TypeConditionOperator.IN, set(v)))
                    else:
                        assert isinstance(v, Condition), "An element of this table should not be of type: " + str(type(v))
                        if tpl:
                            tpl.append(v)
            if tpl:
                table[i] = tuple(tpl)

        return sorted(list(to_ordinary_table(table, [x.dom for x in scope], keep_any=True)))

    @staticmethod
    def remove_redundant_tuples(table):
        tbl = None
        for i in range(len(table) - 1):
            if table[i] != table[i + 1]:
                if tbl:
                    tbl.append(table[i])
            else:
                if not tbl:
                    tbl = table[:i]
        if tbl:
            tbl.append(table[-1])
            table = tbl
        return table

    def process_table(self, scope, table):
        if len(table) == 0:
            return None

        # we compute the hash code of the table
        try:
            h = hash(tuple(table))
        except TypeError:
            for i, t in enumerate(table):
                if any(isinstance(v, set) for v in t):
                    table[i] = tuple(tuple(v) if isinstance(v, set) else v for v in t)
            h = hash(tuple(table))

        if len(scope) == 1:  # if arity 1
            if h not in ConstraintExtension.cache:
                ConstraintExtension.cache[h] = integers_to_string(table) if isinstance(table[0], int) else " ".join(v for v in sorted(table))
            return ConstraintExtension.cache[h]

        possible_parallelism = not options.safe and os.name != 'nt'
        if h in ConstraintExtension.cache_smart:
            smart = ConstraintExtension.cache_smart[h]
        else:
            smart = any(not (isinstance(v, (int, str)) or v == ANY) for t in table for v in t)  # A parallelisation attempt showed no gain.
            ConstraintExtension.cache_smart[h] = smart
        if not smart:
            if not self.restrictTablesWrtDomains:
                # we can use caching here
                if h not in ConstraintExtension.cache:
                    table.sort()
                    table = ConstraintExtension.remove_redundant_tuples(table)
                    ConstraintExtension.cache[h] = table_to_string(table, parallel=possible_parallelism)
                return ConstraintExtension.cache[h]
            else:
                # if ever we would want to use caching, we should include domains when computing hashes
                table.sort()
                return table_to_string(table, restricting_domains=[x.dom for x in scope], parallel=possible_parallelism)
        else:  # it is smart
            if self.keepsmartconditions:  # currently, no restriction of tables (wrt domains) in that case
                self.attributes.append((TypeXML.TYPE, "smart"))
                if h not in ConstraintExtension.cache:
                    table = ConstraintExtension.remove_redundant_tuples(table)
                    ConstraintExtension.cache[h] = table_to_string(table, parallel=possible_parallelism)
                return ConstraintExtension.cache[h]
            else:
                # if ever we would want to use caching, we should include domains when computing hashes
                table = ConstraintExtension.convert_smart_to_ordinary(scope, table)
                table = ConstraintExtension.remove_redundant_tuples(table)
                return table_to_string(table, restricting_domains=[x.dom for x in scope] if self.restrictTablesWrtDomains else None,
                                       parallel=possible_parallelism)

    def __init__(self, scope, table, positive=True, keepsmartconditions=False, restrictTablesWrtDomains=False):
        super().__init__(TypeCtr.EXTENSION)
        self.keepsmartconditions = keepsmartconditions
        self.restrictTablesWrtDomains = restrictTablesWrtDomains
        assert is_1d_list(scope, Variable)
        assert len(table) == 0 or (len(scope) == 1 and (is_1d_list(table, int) or is_1d_list(table, str))) or (len(scope) > 1 and len(scope) == len(table[0]))
        self.arg(TypeCtrArg.LIST, scope, content_ordered=True)
        self.arg(TypeCtrArg.SUPPORTS if positive else TypeCtrArg.CONFLICTS, self.process_table(scope, table), content_compressible=False)

    def close_to(self, other):
        if not self.similar_structure(other):
            return False
        if len(self.arguments[TypeCtrArg.LIST].content) != len(other.arguments[TypeCtrArg.LIST].content):
            return False
        if TypeCtrArg.SUPPORTS in self.arguments and self.arguments[TypeCtrArg.SUPPORTS].content != other.arguments[TypeCtrArg.SUPPORTS].content:
            return False
        elif TypeCtrArg.CONFLICTS in self.arguments and self.arguments[TypeCtrArg.CONFLICTS].content != other.arguments[TypeCtrArg.CONFLICTS].content:
            return False
        return Diffs([(TypeCtrArg.LIST, False)])


''' Constraints defined from languages'''


class ConstraintRegular(Constraint):
    def __init__(self, lst, automaton):
        super().__init__(TypeCtr.REGULAR)
        self.arg(TypeCtrArg.LIST, lst, content_ordered=True)
        self.arg(TypeCtrArg.TRANSITIONS, transitions_to_string(automaton.transitions))
        self.arg(TypeCtrArg.START, automaton.start)
        self.arg(TypeCtrArg.FINAL, automaton.final)

    def close_to(self, other):
        diffs = super().close_to(other)
        return False if not diffs or TypeCtrArg.TRANSITIONS in diffs.argument_names else diffs


class ConstraintMdd(Constraint):
    def __init__(self, lst, transitions):
        super().__init__(TypeCtr.MDD)
        self.arg(TypeCtrArg.LIST, lst, content_ordered=True)
        # TODO reordering transitions in order to guarantee to have:
        # - the root as the src of the first transition
        # - the terminal as the dst of the last transition
        # - no transition with a src occurring before it was reached
        self.arg(TypeCtrArg.TRANSITIONS, transitions_to_string(transitions))


''' Comparison-based Constraints '''


class ConstraintAllDifferent(Constraint):
    def __init__(self, lst, excepting):
        super().__init__(TypeCtr.ALL_DIFFERENT)
        self.arg(TypeCtrArg.LIST, lst)
        self.arg(TypeCtrArg.EXCEPT, excepting)


class ConstraintAllDifferentList(ConstraintUnmergeable):
    def __init__(self, lst, excepting):
        super().__init__(TypeCtr.ALL_DIFFERENT)
        self.arg(TypeCtrArg.LIST, lst, content_ordered=True, lifted=True)
        self.arg(TypeCtrArg.EXCEPT, excepting)


class ConstraintAllDifferentMatrix(ConstraintUnmergeable):
    def __init__(self, lst):
        super().__init__(TypeCtr.ALL_DIFFERENT)
        self.arg(TypeCtrArg.MATRIX, matrix_to_string(lst), content_compressible=lst)


class ConstraintAllEqual(Constraint):
    def __init__(self, lst):
        super().__init__(TypeCtr.ALL_EQUAL)
        self.arg(TypeCtrArg.LIST, lst)


class ConstraintOrdered(Constraint):
    def __init__(self, lst, operator, lengths):
        super().__init__(TypeCtr.ORDERED)
        self.arg(TypeCtrArg.LIST, lst, content_ordered=True)
        self.arg(TypeCtrArg.LENGTHS, lengths, content_ordered=True)
        self.arg(TypeCtrArg.OPERATOR, operator)


class ConstraintLex(ConstraintUnmergeable):
    def __init__(self, lst, operator):
        super().__init__(TypeCtr.LEX)
        self.arg(TypeCtrArg.LIST, lst, content_ordered=True, lifted=True)
        self.arg(TypeCtrArg.OPERATOR, operator)


class ConstraintLexMatrix(ConstraintUnmergeable):
    def __init__(self, lst, operator):
        super().__init__(TypeCtr.LEX)
        self.arg(TypeCtrArg.MATRIX, matrix_to_string(lst), content_compressible=lst)
        self.arg(TypeCtrArg.OPERATOR, operator)


''' Counting and Summing Constraints '''


class ConstraintSum(ConstraintWithCondition):
    def __init__(self, lst, coefficients, condition):
        super().__init__(TypeCtr.SUM)
        self.arg(TypeCtrArg.LIST, lst, content_ordered=True)
        if coefficients is not None and any(not isinstance(v, int) or v != 1 for v in coefficients):
            self.arg(TypeCtrArg.COEFFS, coefficients, content_ordered=True)
        self.arg(TypeCtrArg.CONDITION, condition)

    def min_possible_value(self):
        vs = self.arguments[TypeCtrArg.LIST].content
        cs = self.arguments[TypeCtrArg.COEFFS].content if TypeCtrArg.COEFFS in self.arguments else None
        if cs is None:
            return sum(x.dom.smallest_value() if isinstance(x, Variable) else x.possible_values()[0] for x in vs)
        assert len(vs) == len(cs)
        t = []
        for i, x in enumerate(vs):
            xmin, xmax = x.dom.smallest_value(), x.dom.greatest_value()
            if isinstance(cs[i], int):
                t.append(min(xmin * cs[i], xmax * cs[i]))
            else:
                cmin, cmax = cs[i].dom.smallest_value(), cs[i].dom.greatest_value()
                t.append(min(xmin * cmin, xmin * cmax, xmax * cmin, xmax * cmax))
        return sum(t)

    def max_possible_value(self):
        vs = self.arguments[TypeCtrArg.LIST].content
        cs = self.arguments[TypeCtrArg.COEFFS].content if TypeCtrArg.COEFFS in self.arguments else None
        if cs is None:
            return sum(x.dom.greatest_value() if isinstance(x, Variable) else x.possible_values()[-1] for x in vs)
        assert len(vs) == len(cs)
        t = []
        for i, x in enumerate(vs):
            xmin, xmax = x.dom.smallest_value(), x.dom.greatest_value()
            if isinstance(cs[i], int):
                t.append(max(xmin * cs[i], xmax * cs[i]))
            else:
                cmin, cmax = cs[i].dom.smallest_value(), cs[i].dom.greatest_value()
                t.append(max(xmin * cmin, xmin * cmax, xmax * cmin, xmax * cmax))
        return sum(t)

    def revert_coeffs(self):
        if TypeCtrArg.COEFFS in self.arguments:
            self.arguments[TypeCtrArg.COEFFS].content = [-v for v in self.arguments[TypeCtrArg.COEFFS].content]
        else:
            self.arg(TypeCtrArg.COEFFS, [-1 for _ in range(len(self.arguments[TypeCtrArg.LIST]))])
        return self


class ConstraintCount(ConstraintWithCondition):
    def __init__(self, lst, values, condition):
        super().__init__(TypeCtr.COUNT)
        self.arg(TypeCtrArg.LIST, lst, content_ordered=False)
        self.arg(TypeCtrArg.VALUES, values)
        self.arg(TypeCtrArg.CONDITION, condition)

    def min_possible_value(self):
        return 0

    def max_possible_value(self):
        return len(self.arguments[TypeCtrArg.LIST].content)


class ConstraintNValues(ConstraintWithCondition):
    def __init__(self, lst, excepting, condition):
        super().__init__(TypeCtr.N_VALUES)
        self.arg(TypeCtrArg.LIST, lst)
        self.arg(TypeCtrArg.EXCEPT, excepting)
        self.arg(TypeCtrArg.CONDITION, condition)

    def min_possible_value(self):
        return 1

    def max_possible_value(self):
        return len(self.arguments[TypeCtrArg.LIST].content)


class ConstraintCardinality(Constraint):
    def __init__(self, lst, values, occurs, closed=False):
        super().__init__(TypeCtr.CARDINALITY)
        self.arg(TypeCtrArg.LIST, lst)
        assert len(values) == len(occurs)
        self.arg(TypeCtrArg.VALUES, values, content_ordered=True, attributes=[(TypeXML.CLOSED, "true")] if closed else [])
        self.arg(TypeCtrArg.OCCURS, occurs, content_ordered=True)


''' Connection Constraints '''


def _index_att(v):
    return []  # [(TypeCtrArg.START_INDEX, v)] if v is not None and v != 0 else []


class ConstraintMaximum(ConstraintWithCondition):
    def __init__(self, lst, index=None, start_index=0, type_rank=TypeRank.ANY, condition=None):
        super().__init__(TypeCtr.MAXIMUM)
        self.arg(TypeCtrArg.LIST, lst, content_ordered=index is not None, attributes=_index_att(start_index))
        if index:
            self.arg(TypeCtrArg.INDEX, index, attributes=[(TypeCtrArg.RANK, type_rank)] if type_rank else [])
        self.arg(TypeCtrArg.CONDITION, condition)

    def min_possible_value(self):
        return max(x.dom.smallest_value() if isinstance(x, Variable) else x.possible_values()[0] for x in self.arguments[TypeCtrArg.LIST].content)

    def max_possible_value(self):
        return max(x.dom.greatest_value() if isinstance(x, Variable) else x.possible_values()[-1] for x in self.arguments[TypeCtrArg.LIST].content)


class ConstraintMinimum(ConstraintMaximum):
    def __init__(self, lst, index=None, start_index=0, type_rank=TypeRank.ANY, condition=None):
        super().__init__(lst, index, start_index, type_rank, condition)
        self.name = TypeCtr.MINIMUM

    def min_possible_value(self):
        return min(x.dom.smallest_value() if isinstance(x, Variable) else x.possible_values()[0] for x in self.arguments[TypeCtrArg.LIST].content)

    def max_possible_value(self):
        return min(x.dom.greatest_value() if isinstance(x, Variable) else x.possible_values()[-1] for x in self.arguments[TypeCtrArg.LIST].content)


class ConstraintElement(ConstraintWithCondition):  # currently, not exactly with a general condition
    def __init__(self, lst, index, value=None, type_rank=None):
        super().__init__(TypeCtr.ELEMENT)
        smallest = index.dom[0].smallest() if isinstance(index.dom[0], IntegerEntity) else index.dom[0]
        self.arg(TypeCtrArg.LIST, lst, content_ordered=index is not None, attributes=_index_att(smallest))
        self.arg(TypeCtrArg.INDEX, index, attributes=[(TypeCtrArg.RANK, type_rank)] if type_rank else [])
        if value:
            self.arg(TypeCtrArg.CONDITION, Condition.build_condition((TypeConditionOperator.EQ, value)))
        # self.arg(TypeCtrArg.VALUE, value)

    def min_possible_value(self):
        if isinstance(self.arguments[TypeCtrArg.LIST].content[0], int):
            return min(v for v in self.arguments[TypeCtrArg.LIST].content)
        return min(x.dom.smallest_value() for x in self.arguments[TypeCtrArg.LIST].content)

    def max_possible_value(self):
        if isinstance(self.arguments[TypeCtrArg.LIST].content[0], int):
            return max(v for v in self.arguments[TypeCtrArg.LIST].content)
        return max(x.dom.greatest_value() for x in self.arguments[TypeCtrArg.LIST].content)


class ConstraintElementMatrix(Constraint):
    def __init__(self, lst, index1, index2, value=None, start_row_index=0, start_col_index=0):
        super().__init__(TypeCtr.ELEMENT)
        self.matrix = lst
        self.arg(TypeCtrArg.MATRIX, matrix_to_string(lst), content_compressible=lst,
                 attributes=([(TypeCtrArg.ST.START_ROW_INDEX, start_row_index)] if start_row_index else []) + (
                     [(TypeCtrArg.START_COL_INDEX, start_col_index)] if start_col_index else []))
        self.arg(TypeCtrArg.INDEX, [index1, index2], content_ordered=True)
        if value:
            self.arg(TypeCtrArg.CONDITION, Condition.build_condition((TypeConditionOperator.EQ, value)))
        # self.arg(TypeCtrArg.VALUE, value)

    def min_possible_value(self):
        if isinstance(self.matrix[0][0], int):
            return min(v for row in self.matrix for v in row)
        return min(x.dom.smallest_value() for row in self.matrix for x in row)

    def max_possible_value(self):
        if isinstance(self.matrix[0][0], int):
            return max(v for row in self.matrix for v in row)
        return max(x.dom.greatest_value() for row in self.matrix for x in row)


class ConstraintChannel(ConstraintUnmergeable):
    def __init__(self, list1, start_index1, list2, start_index2):
        super().__init__(TypeCtr.CHANNEL)
        assert list1 is not None
        if list2 is None:  # first variant of channel
            assert start_index2 == 0
            self.arg(TypeCtrArg.LIST, list1, content_ordered=True, attributes=_index_att(start_index1))
        elif len(list2) > 1:  # second variant of channel
            assert 1 < len(list1) <= len(list2)
            self.arg(TypeCtrArg.LIST, [list1, list2], content_ordered=True, lifted=True, attributes=_index_att(start_index1) + _index_att(start_index2))
        else:  # third variant of channel
            assert all(var.dom.is_binary() for var in list1) and len(list2) == 1
            self.arg(TypeCtrArg.LIST, list1, content_ordered=True, attributes=_index_att(start_index1))
            self.arg(TypeCtrArg.VALUE, list2)


''' Packing and Scheduling Constraints '''


class ConstraintNoOverlap(ConstraintUnmergeable):
    def __init__(self, origins, lengths, zero_ignored):
        super().__init__(TypeCtr.NO_OVERLAP)
        self.arg(TypeCtrArg.ORIGINS, "".join(["(" + ",".join(str(v) for v in t) + ")" for t in origins]) if isinstance(origins[0], tuple) else origins,
                 content_ordered=True)
        self.arg(TypeCtrArg.LENGTHS, "".join(["(" + ",".join(str(v) for v in t) + ")" for t in lengths]) if isinstance(lengths[0], tuple) else lengths,
                 content_ordered=True)
        if zero_ignored:
            self.attributes.append((TypeCtrArg.ZERO_IGNORED, zero_ignored))


class ConstraintCumulative(Constraint):  # TODO inheriting from ConstraintWithCondition instead? is this a pb?
    def __init__(self, origins, lengths, ends, heights, condition):
        super().__init__(TypeCtr.CUMULATIVE)
        self.arg(TypeCtrArg.ORIGINS, origins, content_ordered=True)
        self.arg(TypeCtrArg.LENGTHS, lengths, content_ordered=True)
        self.arg(TypeCtrArg.ENDS, ends, content_ordered=True)
        self.arg(TypeCtrArg.HEIGHTS, heights, content_ordered=True)
        self.arg(TypeCtrArg.CONDITION, condition)


class ConstraintBinPacking(Constraint):
    def __init__(self, lst, sizes, condition):
        super().__init__(TypeCtr.BIN_PACKING)
        self.arg(TypeCtrArg.LIST, lst, content_ordered=True)
        self.arg(TypeCtrArg.SIZES, sizes, content_ordered=True)
        self.arg(TypeCtrArg.CONDITION, condition)


''' Constraints on Graphs'''


class ConstraintCircuit(Constraint):
    def __init__(self, variables, start_index, size):
        super().__init__(TypeCtr.CIRCUIT)
        if start_index != 0:
            self.attributes.append((TypeCtrArg.START_INDEX, start_index))
        self.arg(TypeCtrArg.LIST, variables, content_ordered=True)
        self.arg(TypeCtrArg.SIZE, size)


''' Elementary Constraints '''


class ConstraintClause(Constraint):
    def __init__(self, variables, phases):
        super().__init__(TypeCtr.CLAUSE)
        self.arg(TypeCtrArg.LIST, [str(v) if phases[i] else "not(" + str(v) + ")" for i, v in enumerate(variables)], content_ordered=True)


class ConstraintInstantiation(Constraint):
    def __init__(self, variables, values):
        super().__init__(TypeCtr.INSTANTIATION)
        self.arg(TypeCtrArg.LIST, variables, content_ordered=True)
        self.arg(TypeCtrArg.VALUES, values, content_ordered=True)


''' PartialConstraints and ScalarProduct '''


class PartialConstraint:  # constraint whose condition has not been given such as 'Sum', 'Count', 'Element', 'maximum', etc.
    def __init__(self, constraint):
        self.constraint = constraint

    def add_condition(self, operator, right_operand):
        if isinstance(right_operand, (int, Variable)):
            return ECtr(self.constraint.set_condition(operator, right_operand))
        # TODO : which kind of right operand is authorized? just a partial sum?
        assert isinstance(self.constraint, ConstraintSum)
        pc = PartialConstraint.combine_partial_objects(self, TypeNode.SUB, right_operand)  # the 'complex' right operand is moved to the left
        return ECtr(pc.constraint.set_condition(operator, 0))

    def _simplify_with_auxiliary_variables(self, other):
        if isinstance(other, (int, Variable)):
            return other
        if isinstance(other, Node):
            return auxiliary().replace_node(other)
        assert isinstance(other, (ScalarProduct, PartialConstraint)), "Wrong type for " + str(other)
        if isinstance(self.constraint, ConstraintSum) and (isinstance(other, ScalarProduct) or isinstance(other.constraint, ConstraintSum)):
            return other
        assert isinstance(self.constraint, ConstraintWithCondition) and isinstance(other.constraint, ConstraintWithCondition), "Wrong type for " + str(
            other.constraint) + " or/and " + str(self.constraint)
        return auxiliary().replace_partial_constraint(other)

    def _simplify_operation(self, other):
        assert isinstance(self.constraint, ConstraintWithCondition)
        if isinstance(self.constraint, ConstraintSum) and (not isinstance(other, PartialConstraint) or isinstance(other.constraint, ConstraintSum)):
            return None  # we can combine partial sums and terms
        if not isinstance(self.constraint, ConstraintSum) and not isinstance(other, PartialConstraint):
            return auxiliary().replace_partial_constraint(self), other
        assert isinstance(other.constraint, ConstraintWithCondition)
        return auxiliary().replace_partial_constraint(self), auxiliary().replace_partial_constraint(other)

    def __eq__(self, other):
        other = self._simplify_with_auxiliary_variables(other)
        if isinstance(self.constraint, (ConstraintElement, ConstraintElementMatrix)) and isinstance(other, (int, Variable)):
            if isinstance(self.constraint, ConstraintElement):
                arg = self.constraint.arguments[TypeCtrArg.LIST]
                arg.content = flatten(arg.content)  # we need to flatten now because it has not been done before
            # return ECtr(self.constraint.set_value(other))  # only value must be replaced for these constraints
            return ECtr(self.constraint.set_condition(TypeConditionOperator.EQ, other))  # the condition must be replaced
        return self.add_condition(TypeConditionOperator.EQ, other)
        # pair = self._simplify_with_auxiliary_variables(other)
        # return Node.build(TypeNode.EQ, pair) if pair else self.add_condition(TypeConditionOperator.EQ, other)

    def __ne__(self, other):
        return self.add_condition(TypeConditionOperator.NE, self._simplify_with_auxiliary_variables(other))

    def __lt__(self, other):
        return self.add_condition(TypeConditionOperator.LT, self._simplify_with_auxiliary_variables(other))

    def __le__(self, other):
        return self.add_condition(TypeConditionOperator.LE, self._simplify_with_auxiliary_variables(other))

    def __ge__(self, other):
        return self.add_condition(TypeConditionOperator.GE, self._simplify_with_auxiliary_variables(other))

    def __gt__(self, other):
        return self.add_condition(TypeConditionOperator.GT, self._simplify_with_auxiliary_variables(other))

    def __add__(self, other):
        pair = self._simplify_operation(other)
        return Node.build(TypeNode.ADD, pair) if pair else PartialConstraint.combine_partial_objects(self, TypeNode.ADD, other)

    def __sub__(self, other):
        pair = self._simplify_operation(other)
        return Node.build(TypeNode.SUB, pair) if pair else PartialConstraint.combine_partial_objects(self, TypeNode.SUB, other)

    def __mul__(self, other):
        if not isinstance(other, int):
            pair = self._simplify_operation(other)
            return Node.build(TypeNode.MUL, pair) if pair else PartialConstraint.combine_partial_objects(self, TypeNode.MUL, other)
        if not isinstance(self.constraint, ConstraintSum):
            return Node.build(TypeNode.MUL, self._simplify_operation(other))
        args = self.constraint.arguments
        cs = args[TypeCtrArg.COEFFS].content if TypeCtrArg.COEFFS in args else [1] * len(args[TypeCtrArg.LIST].content)
        value = args[TypeCtrArg.CONDITION]
        del args[TypeCtrArg.CONDITION]  # we delete and put back below this argument so as to have arguments in the right order
        self.constraint.arg(TypeCtrArg.COEFFS, [c * other for c in cs])
        args[TypeCtrArg.CONDITION] = value
        return self

    def __rmul__(self, other):
        return PartialConstraint.__mul__(self, other)

    def __getitem__(self, i):
        assert isinstance(self.constraint, ConstraintElement)
        lst = self.constraint.arguments[TypeCtrArg.LIST].content
        index = self.constraint.arguments[TypeCtrArg.INDEX].content
        if isinstance(i, Variable):
            assert is_matrix(lst), "Variables in element constraint must be in the form of matrix"
            self.constraint = ConstraintElementMatrix(lst, index, i)
        elif isinstance(i, int):
            self.constraint = ConstraintElement(lst[:, i], index)
        return self

    def __str__(self):
        c = self.constraint
        # assert len(c.arguments) == 2
        s = str(c.name) + "("
        for k, v in c.arguments.items():
            s = s + str(v) + ","
        return s[:-1] + ")"
        # return s + str(compact(c.arguments[TypeCtrArg.LIST].content)) + ")"

    @staticmethod
    def combine_partial_objects(obj1, operator, obj2):  # currently, only partial sums can be combined
        assert operator in {TypeNode.ADD, TypeNode.SUB}
        if isinstance(obj1, ScalarProduct):
            obj1 = PartialConstraint(ConstraintSum(obj1.variables, obj1.coeffs, None))  # to be sure to have at least one PartialConstraint
        assert isinstance(obj1, PartialConstraint) or isinstance(obj2, PartialConstraint)
        inverted, obj1, obj2 = (False, obj1, obj2) if isinstance(obj1, PartialConstraint) else (True, obj2, obj1)
        pair = obj2.var_val_if_binary_type(TypeNode.MUL) if isinstance(obj2, Node) else None
        if pair:
            obj2 = PartialConstraint(ConstraintSum([pair[0]], [pair[1]], None))
        elif isinstance(obj2, (Variable, Node)):
            obj2 = PartialConstraint(ConstraintSum([obj2], [1], None))
        elif isinstance(obj2, ScalarProduct):
            obj2 = PartialConstraint(ConstraintSum(obj2.variables, obj2.coeffs, None))
        elif not isinstance(obj2, PartialConstraint):
            error("The type of the operand of the partial constraint is wrong as it is " + str(type(obj2)))
        obj1, obj2 = (obj1, obj2) if not inverted else (obj2, obj1)  # we invert back
        assert isinstance(obj1, PartialConstraint) and isinstance(obj2, PartialConstraint)
        assert isinstance(obj1.constraint, ConstraintSum) and isinstance(obj2.constraint, ConstraintSum)
        args1, args2 = obj1.constraint.arguments, obj2.constraint.arguments
        vs1, vs2 = args1[TypeCtrArg.LIST].content, args2[TypeCtrArg.LIST].content
        cs1 = args1[TypeCtrArg.COEFFS].content if TypeCtrArg.COEFFS in args1 else [1] * len(vs1)
        cs2 = args2[TypeCtrArg.COEFFS].content if TypeCtrArg.COEFFS in args2 else [1] * len(vs2)
        cs2 = [-c for c in cs2] if operator == TypeNode.SUB else cs2
        return PartialConstraint(ConstraintSum(vs1 + vs2, cs1 + cs2, None))


class ScalarProduct:
    def __init__(self, variables, coefficients):
        variables = list(variables) if isinstance(variables, tuple) else variables
        coefficients = list(coefficients) if isinstance(coefficients, tuple) else coefficients
        assert isinstance(variables, list) and isinstance(coefficients, (int, list, range)), variables
        self.variables = flatten(variables)  # for example, in order to remove None occurrences
        self.coeffs = flatten([coefficients] * len(variables) if isinstance(coefficients, int) else coefficients)
        assert len(self.variables) == len(self.coeffs), str(self.variables) + " " + str(self.coeffs)

    def _combine_with(self, operator, right_operand):
        return PartialConstraint(ConstraintSum(self.variables, self.coeffs, None)).add_condition(operator, right_operand)

    def __lt__(self, other):
        return self._combine_with(TypeConditionOperator.LT, other)

    def __le__(self, other):
        return self._combine_with(TypeConditionOperator.LE, other)

    def __ge__(self, other):
        return self._combine_with(TypeConditionOperator.GE, other)

    def __gt__(self, other):
        return self._combine_with(TypeConditionOperator.GT, other)

    def __eq__(self, other):
        return self._combine_with(TypeConditionOperator.EQ, other)

    def __ne__(self, other):
        return self._combine_with(TypeConditionOperator.NE, other)

    def __add__(self, other):
        return PartialConstraint.combine_partial_objects(self, TypeNode.ADD, other)

    def __sub__(self, other):
        return PartialConstraint.combine_partial_objects(self, TypeNode.SUB, other)


class _Auxiliary:
    def __init__(self):
        self._introduced_variables = []
        self._collected_constraints = []
        self.prefix = "aux_gb"
        self.cache = []

    def __replace(self, obj, dom):
        assert dom.get_type() == TypeVar.INTEGER
        index = len(self._introduced_variables)
        name = self.prefix + "[" + str(index) + "]"
        var = VariableInteger(name, dom)
        Variable.name2obj[name] = var
        if index == 0:
            self._introduced_variables = EVarArray([var], self.prefix, self.prefix + "[i] is the ith auxiliary variable having been automatically introduced")
        else:
            self._introduced_variables.extend_with(var)
        self._collected_constraints.append((obj, var))
        return var

    def replace_partial_constraint(self, pc):
        assert isinstance(pc, PartialConstraint)
        for c, x in self.cache:
            if pc.constraint.equal_except_condition(c):
                # if functions.protect().execute(pc.constraint.equal_except_condition(c)):
                # if functions.protect().execute(pc.constraint == c):
                return x
        aux = self.__replace(pc, Domain(range(pc.constraint.min_possible_value(), pc.constraint.max_possible_value() + 1)))
        self.cache.append((pc.constraint, aux))
        return aux

    def replace_nodes_and_partial_constraints(self, terms, nodes_too=False):
        assert isinstance(terms, list)
        for i, t in enumerate(terms):
            if isinstance(t, PartialConstraint):
                terms[i] = self.replace_partial_constraint(t)
            elif nodes_too and isinstance(t, Node):
                terms[i] = self.replace_node(t)
        return terms

    def replace_node(self, node):
        assert isinstance(node, Node)
        values = node.possible_values()
        values = {v for v in values} if len(values) <= 2 else values  # in order to avoid having a range for just 1 or 2 values
        return self.__replace(node, Domain(values))

    def collected(self):
        t = self._collected_constraints
        self._collected_constraints = []
        return t


def auxiliary():
    if not hasattr(auxiliary, "obj"):
        auxiliary.obj = _Auxiliary()
    return auxiliary.obj


def global_indirection(c):
    pc = None
    if options.usemeta:
        return None  # to force using meta-constraints
    if isinstance(c, ConstraintWithCondition):
        condition = c.arguments[TypeCtrArg.CONDITION].content
        c.arguments[TypeCtrArg.CONDITION] = None
        pc = PartialConstraint(c)
    if isinstance(c, ConstraintAllDifferent):
        lst = c.arguments[TypeCtrArg.LIST].content
        pc = PartialConstraint(ConstraintNValues(lst, c.arguments[TypeCtrArg.EXCEPT].content, None))
        condition = Condition.build_condition((TypeConditionOperator.EQ, len(lst)))
    if isinstance(c, ConstraintAllEqual):
        pc = PartialConstraint(ConstraintNValues(c.arguments[TypeCtrArg.LIST].content, None, None))
        condition = Condition.build_condition((TypeConditionOperator.EQ, 1))
    if pc is None:
        warning("You use a global constraint in a complex expression.\n" +
                "\tHowever, this constraint cannot be externalized by introducing an auxiliary variable.\n" +
                "\tHence a meta-constraint function (Or, And, Not, IfThen, IfThenElse, Iff) is automatically called.\n" +
                "\tCheck that it is relevant, or modify your model.\n")
        return None
    return Node.build(condition.operator, auxiliary().replace_partial_constraint(pc), condition.right_operand())


def manage_global_indirection(*args):
    assert len(args) > 1
    if any(isinstance(arg, EMetaCtr) for arg in args):
        return None
    t = []
    for arg in args:
        if isinstance(arg, ECtr):
            gi = global_indirection(arg.constraint)
            if gi is None:
                return None
            arg = gi
        t.append(arg)
    return tuple(t)
