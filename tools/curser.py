import types
from collections import deque, namedtuple

from pycsp3.classes.entities import Node, TypeNode, ECtr, EMetaCtr
from pycsp3.classes.main.constraints import (
    ScalarProduct, PartialConstraint, ConstraintSum, ConstraintElement, ConstraintElementMatrix,
    ConstraintInstantiation,
    auxiliary, global_indirection, manage_global_indirection)
from pycsp3.classes.main.variables import Variable, VariableInteger
from pycsp3.libs.forbiddenfruit import curse
from pycsp3.tools.inspector import checkType
from pycsp3.tools.utilities import flatten, is_containing, unique_type_in, is_1d_tuple, is_1d_list, is_matrix, ANY, warning, error_if

from pycsp3 import functions

queue_in = deque()  # To store partial constraints when using the IN operator

unsafe_cache = False  # see for example Pic since the table is released as it occurs as a parameter


def cursing():
    def _dict_add(self, other):  # for being able to merge dictionaries
        if isinstance(other, dict):
            d = self.copy()
            d.update(other)
            return d
        raise NotImplementedError  # return save_dict_add(self, other)

    def _tuple_mul(self, other):  # for being able to use scalar products
        if is_containing(self, (Variable, Node), check_first_only=True):
            return ScalarProduct(self, other)
        if is_containing(self, int) and isinstance(other, (list, tuple)) and is_containing(other, (Variable, Node), check_first_only=True):
            return ScalarProduct(other, self)
        return tuple.__mul__(self, other)

    def _list_mul(self, other):  # for being able to use scalar products
        if is_containing(self, (Variable, Node), check_first_only=True):
            return ScalarProduct(self, other)
        # if is_containing(self, int) and is_containing(other, (Variable, Node)):
        #     return ScalarProduct(self, other)
        return list.__mul__(self, other)

    # def _list_rmul(self, other):
    #     return _list_mul(other, self)

    def _tuple_contains(self, other):
        if not OpOverrider.activated:
            return self.__contains__(other)
        if is_containing(other, Variable) and len(self) > 0 and isinstance(self[0], (tuple, int)):
            queue_in.append((list(self), other))
            return True
        if isinstance(other, int) and (is_1d_list(self, Variable) or is_1d_tuple(self, Variable)):  # member/element constraint
            queue_in.append((self, other))
            return True
        return self.__contains__(other)

    def _list_contains(self, other):  # for being able to use 'in' when expressing extension constraints
        if not OpOverrider.activated:
            return self.__contains__(other)
        if isinstance(other, types.GeneratorType):
            other = list(other)
        if is_containing(other, Variable) and len(self) > 0 and isinstance(self[0], (list, tuple, int)):
            queue_in.append((self, other))
            return True
        if is_containing(other, Variable) and len(self) == 0:
            return other in set(self)
        error_if(is_containing(other, Variable),
                 "It seems that you should use a set and not a list, as in x in {...}." + " Your arguments are " + str(other) + " " + str(self))
        if isinstance(other, int) and (is_1d_list(self, Variable) or is_1d_tuple(self, Variable)):  # member/element constraint
            queue_in.append((self, other))
            return True
        return self.__contains__(other)

    def _set_contains(self, other):  # for being able to use 'in' when expressing intension/extension constraints
        if not OpOverrider.activated:
            return self.__contains__(other)
        if isinstance(other, types.GeneratorType):
            other = list(other)
        tself = unique_type_in(self)
        # if isinstance(other, Variable) and len(self) > 0 and is_containing(self, int):  # unary table constraint
        if isinstance(other, Variable) and tself in {int, str}:  # unary table constraint
            queue_in.append((list(self), other))
            return True
        # if isinstance(other, (Variable, PartialConstraint)) or isinstance(other, (int, str)) and is_containing(self, Variable):  # intension constraint
        if isinstance(other, (Variable, PartialConstraint)) or isinstance(other, (int, str)) and tself and issubclass(tself, Variable):  # intension constraint
            queue_in.append((self, other))
            return True
        # if is_1d_tuple(other, Variable) or is_1d_list(other, Variable):  # non-unary table constraint
        #     queue_in.append((list(self), other))
        #     return True
        if isinstance(other, (tuple, list)) and is_containing(other, (Variable, Node)):  # non-unary table constraint
            ll = flatten(other)
            for i in range(len(ll)):  # we replace nodes by auxiliary variables if present
                if isinstance(ll[i], Node):
                    ll[i] = auxiliary().replace_node(ll[i])
                    # if is_containing(other, Variable):  # non-unary table constraint
            if unsafe_cache:
                if not hasattr(_set_contains, "cache"):
                    _set_contains.cache = {}
                if id(self) not in _set_contains.cache:
                    _set_contains.cache[id(self)] = list({tuple(v) if isinstance(v, types.GeneratorType) else v for v in self})
            queue_in.append((_set_contains.cache[id(self)] if unsafe_cache else list(self), ll))  # flatten(other)))
            return True
        return self.__contains__(other)

    def _range_contains(self, other):  # for being able to use 'in' when expressing conditions of constraints
        if not OpOverrider.activated:
            return range.__contains__(other)
        if isinstance(other, ScalarProduct):
            other = PartialConstraint(ConstraintSum(other.variables, other.coeffs, None))  # functions.Sum(other)
        if isinstance(other, Variable):  # unary table constraint (based on a range)
            queue_in.append((list(self), other))
            return True
        if isinstance(other, PartialConstraint):
            queue_in.append((self, other))
            return True
        if isinstance(other, Node):
            other = auxiliary().replace_node(other)
            queue_in.append((self, other))
            return True

        return range.__contains__(self, other)

    def _enumerate_contains(self, other):
        if not OpOverrider.activated:
            return self.__contains__(other)
        if is_containing(other, Variable):
            tmp = list(self)
            if len(tmp) > 0 and isinstance(tmp[0], (tuple, int)):
                queue_in.append((tmp, other))
                return True
        return self.__contains__(other)

    curse(dict, "__add__", _dict_add)
    curse(tuple, "__mul__", _tuple_mul)
    curse(list, "__mul__", _list_mul)
    # curse(list, "__rmul__", _list_rmul)
    curse(tuple, "__contains__", _tuple_contains)
    curse(list, "__contains__", _list_contains)
    curse(set, "__contains__", _set_contains)
    curse(range, "__contains__", _range_contains)
    curse(enumerate, "__contains__", _enumerate_contains)


cursing()


class OpOverrider:
    activated = False

    @staticmethod
    def enable():
        OpOverrider.activated = True

        ListVar.__eq__ = OpOverrider.__eq__lv
        ListVar.__ne__ = OpOverrider.__ne__lv
        ListVar.__getitem__ = OpOverrider.__getitem__lv
        ListInt.__getitem__ = OpOverrider.__getitem__li
        ListInt.__contains__ = OpOverrider.__contains__li

        EMetaCtr.__eq__ = Variable.__eq__ = Node.__eq__ = OpOverrider.__eq__
        EMetaCtr.__ne__ = Variable.__ne__ = Node.__ne__ = OpOverrider.__ne__
        Variable.__lt__ = Node.__lt__ = OpOverrider.__lt__
        Variable.__le__ = Node.__le__ = OpOverrider.__le__
        Variable.__ge__ = Node.__ge__ = OpOverrider.__ge__
        Variable.__gt__ = Node.__gt__ = OpOverrider.__gt__

        Variable.__neg__ = Node.__neg__ = OpOverrider.__neg__
        Variable.__add__ = Node.__add__ = OpOverrider.__add__
        Variable.__radd__ = Node.__radd__ = OpOverrider.__radd__
        Variable.__sub__ = Node.__sub__ = OpOverrider.__sub__
        Variable.__rsub__ = Node.__rsub__ = OpOverrider.__rsub__
        Variable.__mul__ = Node.__mul__ = OpOverrider.__mul__
        Variable.__rmul__ = Node.__rmul__ = OpOverrider.__rmul__
        Variable.__pow__ = Node.__pow__ = OpOverrider.__pow__
        Variable.__mod__ = Node.__mod__ = OpOverrider.__mod__
        Variable.__floordiv__ = Node.__floordiv__ = OpOverrider.__floordiv__
        Variable.__rfloordiv__ = Node.__rfloordiv__ = OpOverrider.__rfloordiv__

        ECtr.__and__ = EMetaCtr.__and__ = Variable.__and__ = Node.__and__ = OpOverrider.__and__
        ECtr.__or__ = EMetaCtr.__or__ = Variable.__or__ = Node.__or__ = OpOverrider.__or__
        ECtr.__invert__ = Node.__invert__ = OpOverrider.__invert__  # we keep __invert__ for Variable
        ECtr.__xor__ = EMetaCtr.__xor__ = Variable.__xor__ = Node.__xor__ = OpOverrider.__xor__

    @staticmethod
    def disable():
        OpOverrider.activated = False

        ListVar.__eq__ = list.__eq__
        ListVar.__ne__ = list.__ne__
        ListVar.__getitem__ = list.__getitem__
        ListInt.__getitem__ = list.__getitem__
        ListInt.__contains__ = list.__contains__

        EMetaCtr.__eq__ = Node.__eq__ = object.__eq__
        Variable.__eq__ = Variable.eq__save  # TODO are there other methods in the same situation?

        EMetaCtr.__ne__ = Variable.__ne__ = Node.__ne__ = object.__ne__
        Variable.__lt__ = Node.__lt__ = object.__lt__
        Variable.__le__ = Node.__le__ = object.__le__
        Variable.__ge__ = Node.__ge__ = object.__ge__
        Variable.__gt__ = Node.__gt__ = object.__gt__

        Variable.__neg__ = Node.__neg__ = None
        Variable.__add__ = Node.__add__ = None
        Variable.__radd__ = Node.__radd__ = None
        Variable.__sub__ = Node.__sub__ = None
        Variable.__rsub__ = Node.__rsub__ = None
        Variable.__mul__ = Node.__mul__ = None
        Variable.__rmul__ = Node.__rmul__ = None
        Variable.__pow__ = Node.__pow__ = None
        Variable.__mod__ = Node.__mod__ = None
        Variable.__floordiv__ = Node.__floordiv__ = None
        Variable.__rfloordiv__ = Node.__rfloordiv__ = None

        ECtr.__and__ = EMetaCtr.__and__ = Variable.__and__ = Node.__and__ = None
        ECtr.__or__ = EMetaCtr.__or__ = Variable.__or__ = Node.__or__ = None
        ECtr.__invert__ = Node.__invert__ = None  # we keep __invert__ for Variable
        ECtr.__xor__ = EMetaCtr.__xor__ = Variable.__xor__ = Node.__xor__ = None

        return OpOverrider

    @staticmethod
    def eq_protected(v1, v2):
        if isinstance(v1, list) and isinstance(v2, list):
            if len(v1) != len(v2):
                return False
            return all(OpOverrider.eq_protected(v1[i], v2[i]) for i in range(len(v1)))
        if isinstance(v1, Variable):
            return Variable.eq__save(v1, v2)
        return v1 == v2

    @staticmethod
    def execute(arg):
        OpOverrider.enable()
        return arg

    @staticmethod
    def project_recursive(t, indexes, dimension):
        index = slice(None, None, None) if indexes[dimension] == ANY else indexes[dimension]
        if isinstance(index, int):
            if isinstance(t, list):
                t = t[index]  # to keep the shape (dimensions), we need to do that
            else:
                return t
        elif isinstance(index, slice):
            t = list.__getitem__(t, index)
        else:
            raise TypeError()
        if isinstance(t, list) and dimension + 1 < len(indexes):
            if not isinstance(index, int):
                for i, element in enumerate(t):
                    t[i] = OpOverrider.project_recursive(element, indexes, dimension + 1)
            else:
                t = OpOverrider.project_recursive(t, indexes, dimension + 1)
        return t

    def __neg__(self):
        return Node.build(TypeNode.NEG, self)

    def __add__(self, other):
        if isinstance(other, PartialConstraint):
            if isinstance(other.constraint, ConstraintSum) and isinstance(self, Node) and all(s.type == TypeNode.VAR for s in self.sons):
                if self.type == TypeNode.ADD:
                    for s in self.sons:
                        other = other + s.sons
                    return other
                if self.type == TypeNode.SUB:
                    return other + self.sons[0].sons - self.sons[1].sons
            return PartialConstraint.combine_partial_objects(self, TypeNode.ADD, other) if isinstance(other.constraint, ConstraintSum) else other + self
        return Node.build(TypeNode.ADD, self, other)

    def __radd__(self, other):
        return Node.build(TypeNode.ADD, other, self)

    def __sub__(self, other):
        if isinstance(other, PartialConstraint):
            if isinstance(other.constraint, ConstraintSum) and isinstance(self, Node) and all(s.type == TypeNode.VAR for s in self.sons):
                if self.type == TypeNode.ADD:
                    for s in self.sons:
                        other = other - s.sons
                    other.constraint.revert_coeffs()
                    return other
                if self.type == TypeNode.SUB:
                    other = other - self.sons[0].sons + self.sons[1].sons
                    other.constraint.revert_coeffs()
                    return other
            return PartialConstraint.combine_partial_objects(self, TypeNode.SUB, other) if isinstance(other.constraint, ConstraintSum) else -(other - self)
        return Node.build(TypeNode.SUB, self, other)

    def __rsub__(self, other):
        return Node.build(TypeNode.SUB, other, self)

    def __mul__(self, other):
        return Node.build(TypeNode.MUL, self, other)

    def __rmul__(self, other):
        return Node.build(TypeNode.MUL, other, self)

    def __mod__(self, other):
        return Node.build(TypeNode.MOD, self, other)

    def __pow__(self, other):
        return Node.build(TypeNode.POW, self, other)

    def __floordiv__(self, other):
        return Node.build(TypeNode.DIV, self, other)

    def __rfloordiv__(self, other):
        return Node.build(TypeNode.DIV, other, self)

    def __lt__(self, other):
        if self is None or other is None:
            return object.__lt__(self, other)
        return other.__gt__(self) if isinstance(other, (PartialConstraint, ScalarProduct)) else Node.build(TypeNode.LT, self, other)

    def __le__(self, other):
        if self is None or other is None:
            return object.__le__(self, other)
        return other.__ge__(self) if isinstance(other, (PartialConstraint, ScalarProduct)) else Node.build(TypeNode.LE, self, other)

    def __ge__(self, other):
        if self is None or other is None:
            return object.__ge__(self, other)
        if isinstance(other, int) and other == 1 and isinstance(self, Node) and self.type == TypeNode.DIST:  # we simplify the expression
            return Node.build(TypeNode.NE, self.sons[0], self.sons[1])
        return other.__le__(self) if isinstance(other, (PartialConstraint, ScalarProduct)) else Node.build(TypeNode.GE, self, other)

    def __gt__(self, other):
        if self is None or other is None:
            return object.__gt__(self, other)
        if isinstance(other, int) and other == 0 and isinstance(self, Node) and self.type == TypeNode.DIST:  # we simplify the expression
            return Node.build(TypeNode.NE, self.sons[0], self.sons[1])
        return other.__lt__(self) if isinstance(other, (PartialConstraint, ScalarProduct)) else Node.build(TypeNode.GT, self, other)

    def __eq__(self, other):
        res = manage_global_indirection(self, other)
        if res is None:
            return functions.Iff(self, other)
        self, other = res
        if self is None or other is None:  # we must not write None in (self,other) because recursive behaviour
            return object.__eq__(self, other)
        if isinstance(other, int) and other == 0 and isinstance(self, Node) and self.type == TypeNode.DIST:  # we simplify the expression
            return Node.build(TypeNode.EQ, self.sons[0], self.sons[1])
        return other.__eq__(self) if isinstance(other, (PartialConstraint, ScalarProduct)) else Node.build(TypeNode.EQ, self, other)

    def __ne__(self, other):
        res = manage_global_indirection(self, other)
        if res is None:
            return functions.Xor(self, other)  # TODO: is it always appropriate?
        self, other = res
        if self is None or other is None:
            return object.__ne__(self, other)
        if isinstance(other, int) and other == 0 and isinstance(self, Node) and self.type == TypeNode.DIST:  # we simplify the expression
            return Node.build(TypeNode.NE, self.sons[0], self.sons[1])
        return other.__ne__(self) if isinstance(other, (PartialConstraint, ScalarProduct)) else Node.build(TypeNode.NE, self, other)

    def __or__(self, other):
        res = manage_global_indirection(self, other)
        if res is None:
            return functions.Or(self, other)
        self, other = res
        if self is None or other is None:
            return object.__or__(self, other)
        return Node.disjunction(self, other)

    def __and__(self, other):
        res = manage_global_indirection(self, other)
        if res is None:
            return functions.And(self, other)
        self, other = res
        if self is None or other is None:
            return object.__and__(self, other)
        return Node.conjunction(self, other)

    def __invert__(self):
        if isinstance(self, ECtr):
            gi = global_indirection(self.constraint)
            if gi is None:
                return functions.Not(self)
            self = gi
        return Variable.__invert__(self) if isinstance(self, VariableInteger) else Node.build(TypeNode.NOT, self)

    def __xor__(self, other):
        res = manage_global_indirection(self, other)
        if res is None:
            return functions.Xor(self, other)
        self, other = res
        if self is None or other is None:
            return object.__xor__(self, other)
        return Node.build(TypeNode.XOR, self, other)

    def __eq__lv(self, other):  # lv for ListVar
        def Instantiation(*, variables, values):
            variables = flatten(variables)
            values = flatten(values) if not isinstance(values, range) else list(values)
            checkType(variables, [Variable])
            checkType(values, (int, [int]))
            if len(variables) == 0:
                return None
            if len(values) == 1 and len(variables) > 1:
                values = [values[0]] * len(variables)
            return ConstraintInstantiation(variables, values)

        if isinstance(other, (list, tuple)) and any(isinstance(v, int) for v in other):
            return ECtr(Instantiation(variables=self, values=other))
        return list.__eq__(self, other)

    def __ne__lv(self, other):  # lv for ListVar
        if isinstance(other, (list, tuple)) and any(isinstance(v, int) for v in other):
            return self not in {tuple(other)}
        return list.__ne__(self, other)

    def __getitem__lv(self, indexes):
        if isinstance(indexes, PartialConstraint):
            indexes = auxiliary().replace_partial_constraint(indexes)
        elif isinstance(indexes, Node):
            indexes = auxiliary().replace_node(indexes)
        if isinstance(indexes, Variable):
            return PartialConstraint(ConstraintElement(self, indexes))
        if isinstance(indexes, tuple) and len(indexes) > 0:
            indexes = auxiliary().replace_nodes_and_partial_constraints(list(indexes), nodes_too=True)
            if any(isinstance(i, Variable) for i in indexes):  # this must be a constraint Element-Matrix
                assert is_matrix(self) and len(indexes) == 2, "A matrix is expected, with two indexes"
                if all(isinstance(i, Variable) for i in indexes):
                    return PartialConstraint(ConstraintElementMatrix(self, indexes[0], indexes[1]))
                else:
                    if isinstance(indexes[0], Variable) and isinstance(indexes[1], int):
                        return PartialConstraint(ConstraintElement(self[:, indexes[1]], indexes[0]))
                    elif isinstance(indexes[0], int) and isinstance(indexes[1], Variable):
                        return PartialConstraint(ConstraintElement(self[indexes[0]], indexes[1]))
                    else:
                        assert False
            result = OpOverrider.project_recursive(self, indexes, 0)
            try:
                return ListVar(result)  # TODO are sublists also guaranteed to be ListVar?
            except TypeError:
                return result
        result = list.__getitem__(self, indexes)
        try:
            return ListVar(result)
        except TypeError:
            return result

    def __getitem__li(self, indexes):  # li for ListInt
        if isinstance(indexes, PartialConstraint):
            indexes = auxiliary().replace_partial_constraint(indexes)
        if isinstance(indexes, Variable):
            return PartialConstraint(ConstraintElement(self, indexes))
        if isinstance(indexes, tuple) and len(indexes) > 0:
            indexes = auxiliary().replace_nodes_and_partial_constraints(list(indexes))
            if any(isinstance(i, Variable) for i in indexes):  # this must be a constraint Element-Matrix
                assert is_matrix(self) and len(indexes) == 2, "A matrix is expected, with two indexes"
                if all(isinstance(i, Variable) for i in indexes):
                    return PartialConstraint(ConstraintElementMatrix(self, indexes[0], indexes[1]))
                else:
                    if isinstance(indexes[0], Variable) and isinstance(indexes[1], int):
                        return PartialConstraint(ConstraintElement(self[:, indexes[1]], indexes[0]))
                    elif isinstance(indexes[0], int) and isinstance(indexes[1], Variable):
                        return PartialConstraint(ConstraintElement(self[indexes[0]], indexes[1]))
                    else:
                        assert False
            result = OpOverrider.project_recursive(self, indexes, 0)
            try:
                return ListVar(result)  # TODO is it ListVar or ListInt ?
            except TypeError:
                return result
        result = list.__getitem__(self, indexes)
        try:
            return ListInt(result)
        except TypeError:
            return result

    def __contains__li(self, other):
        if is_containing(other, Variable) and len(self) > 0 and isinstance(self[0], (tuple, int)):
            queue_in.append((self, other))
            return True
        return list.__contains__(self, other)


class ListInt(list):
    def __init__(self, integers):
        super().__init__(integers)  # self.extend(integers)

    def __getslice__(self, i, j):
        return ListInt(super().__getslice__(i, j))

    def __add__(self, other):
        return ListInt(super().__add__(other))

    def __mul__(self, other):
        if is_matrix(self):
            assert is_matrix(other) and len(self) == len(other) and len(self[0]) == len(other[0])
            t1, t2 = zip(
                *[(self[i][j], other[i][j]) for i in range(len(self)) for j in range(len(self[0])) if self[i][j] is not None and other[i][j] is not None])
            assert is_containing(t2, (Variable, Node))
            return ScalarProduct(list(t2), list(t1))
        if is_containing(flatten(other), (Variable, Node)):
            return ScalarProduct(other, self)
        assert is_containing(self, (Variable, Node))
        return ScalarProduct(self, other)

    def __rmul__(self, other):
        return ListInt.__mul__(other, self)


def columns(m):
    assert is_matrix(m), "columns() can only be called on matrices"
    return ListVar(ListVar(row[j] for row in m) for j in range(len(m[0])))


class ListVar(list):
    # def __new__(self, variables):  # if we subclass tuple instead of list (while removing __init__)
    #     return super().__new__(ListVar, variables)

    def __init__(self, variables):
        super().__init__(variables)

    def __getslice__(self, i, j):
        return ListVar(super().__getslice__(i, j))

    def __add__(self, other):
        return ListVar(super().__add__(other))

    def __mul__(self, other):
        if is_matrix(self):
            assert is_matrix(other) and len(self) == len(other) and len(self[0]) == len(other[0])
            t1, t2 = zip(
                *[(self[i][j], other[i][j]) for i in range(len(self)) for j in range(len(self[0])) if self[i][j] is not None and other[i][j] is not None])
            assert is_containing(t1, (Variable, Node))
            return ScalarProduct(list(t1), list(t2))
        assert is_containing(self, (Variable, Node))  # Node possible ?
        return ScalarProduct(self, list(other) if isinstance(other, (tuple, range)) else other)

    def __contains__(self, other):
        if isinstance(other, int) and (is_1d_list(self, Variable) or is_1d_tuple(self, Variable)):  # member constraint
            queue_in.append((self, other))
            return True
        return list.__contains__(self, other)

    # def __rmul__(self, other): return ListVar.__mul__(other, self)

    def columns(self):
        return columns(self)


def convert_to_namedtuples(obj):
    def with_only_alphanumeric_keys(obj):  # alphanum or '_'
        if isinstance(obj, dict):
            if any(not k.isidentifier() for k in obj.keys()):
                return False
            return all(with_only_alphanumeric_keys(v) for v in obj.values())
        if isinstance(obj, (int, str)):
            return True
        try:
            iter(obj)
        except TypeError:  # not iterable
            return True
        else:  # iterable
            return all(with_only_alphanumeric_keys(v) for v in obj)

    def recursive_convert_to_namedtuples(obj):
        if not hasattr(recursive_convert_to_namedtuples, "cnt"):
            recursive_convert_to_namedtuples.cnt = 0
        if isinstance(obj, tuple):
            obj = list(obj)  # because if data come from a text file (and not from a JSON file), we have different structures, which leads to problems
        if isinstance(obj, list):
            if len(obj) == 0:
                return obj
            if is_1d_list(obj, int):
                return ListInt(obj)
            if is_1d_list(obj, Variable):
                return ListVar(obj)
            if is_1d_list(obj, dict):
                nt = namedtuple("nt" + str(recursive_convert_to_namedtuples.cnt), obj[0].keys())
                recursive_convert_to_namedtuples.cnt += 1
                return [nt(*(recursive_convert_to_namedtuples(v) for (k, v) in d.items())) for d in obj]
            t = [recursive_convert_to_namedtuples(v) for v in obj]
            return ListInt(t) if isinstance(t[0], ListInt) else ListVar(t) if isinstance(t[0], ListVar) else t
        if isinstance(obj, dict):
            nt = namedtuple("nt" + str(recursive_convert_to_namedtuples.cnt), obj.keys())
            recursive_convert_to_namedtuples.cnt += 1
            return nt(*(recursive_convert_to_namedtuples(v) for (k, v) in obj.items()))
        return obj

    if not with_only_alphanumeric_keys(obj):
        warning("some key of some dictionary involved in the data is not alphanumeric, so no conversion to named tuples is performed\n")
        return obj  # not possible to make the conversion in that case
    return recursive_convert_to_namedtuples(obj)


def is_namedtuple(obj):  # imperfect way of checking, but must be enough for our use (when JSON dumping Compilation.data)
    t = type(obj)
    if len(t.__bases__) != 1 or t.__bases__[0] != tuple:
        return False
    fields = getattr(t, '_fields', None)
    return isinstance(fields, tuple) and all(type(field) == str for field in fields)

# def to_special_list(t):
#     assert is_1d_list(t)
#     if is_containing(t, (Variable, type(None))):
#         return ListVar(t)
#     if is_containing(t, (int, type(None))):
#         return ListInt(t)
#     return t
