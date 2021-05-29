import re

from pycsp3.classes.auxiliary.ptypes import TypeVar
from pycsp3.classes.main.domains import Domain


class Variable:
    name2obj = dict()  # Dictionary (keys: names of variables - values: variable objects)

    @staticmethod
    def build_names_array(name, sizes, mins, indexes=[]):
        if sizes:
            t = []
            for i in range(sizes[0]):
                indexes.append(i + mins[len(indexes)])
                t.append(Variable.build_names_array(name, sizes[1:], mins, indexes))
                indexes.pop()
            return t
        return name + "[" + "][".join(str(i) for i in indexes) + "]"

    @staticmethod
    def build_domain(name, domain, indexes):
        if domain is None:
            return None
        if isinstance(domain, Domain):
            return domain
        if isinstance(domain, type(lambda: 0)):
            domain = domain(*indexes)
            if domain is None:
                return None
        if isinstance(domain, (tuple, list)):
            if all(isinstance(v, int) for v in domain) or all(isinstance(v, str) for v in domain):  # possible, even if using a set is recommended
                return Domain(set(domain))
            # at this point, it means that a specific domain for each variable is given in a list
            for i in indexes:
                assert i < len(domain), "The number of domains is less than the specified index " + name + " - " + str(domain)
                domain = domain[i]
        if isinstance(domain, Domain):
            return domain
        if isinstance(domain, list) and (all(isinstance(v, int) for v in domain) or all(isinstance(v, str) for v in domain)):
            return Domain(set(domain))
        assert isinstance(domain, (range, set)), str(type(domain)) + " " + str(domain)
        return Domain(domain)

    @staticmethod
    def build_variable(name, domain, indexes):
        dom = Variable.build_domain(name, domain, indexes)
        if dom is None:
            return None
        var = VariableInteger(name, dom) if dom.get_type() == TypeVar.INTEGER else VariableSymbolic(name, dom)
        Variable.name2obj[name] = var
        return var

    @staticmethod
    def build_variables_array(name, sizes, domain, indexes=[]):
        if isinstance(name, list):
            # it means that several variables are declared with a single line
            assert len(sizes) == 1, "When using several declarations, only one-dimensional arrays are allowed."
            return [Variable.build_variable(var_name.strip(), domain, indexes) for var_name in name]
        if sizes:
            t = []
            for i in range(sizes[0]):
                indexes.append(i)
                t.append(Variable.build_variables_array(name, sizes[1:], domain, indexes))
                indexes.pop()
            return t
        var_name = name + "[" + "][".join(str(i) for i in indexes) + "]"
        return Variable.build_variable(var_name, domain, indexes)

    def __init__(self, name, dom, *, inverse=False, negation=False):
        self.id = name
        self.dom = dom
        pos = self.id.find("[")
        if pos == -1:
            self.indexes = None
        else:
            self.prefix, self.suffix = self.id[:pos], self.id[pos:]
            self.indexes = [int(v) for v in re.split("\]\[", self.suffix[1:-1])]
        self.inverse = inverse  # arithmetic inverse
        self.negation = negation  # logical negation

    def eq__safe(self, other):
        return isinstance(other, Variable) and self.id == other.id

    def __eq__(self, other):
        return self.eq__safe(other)  #isinstance(other, Variable) and self.id == other.id

    def __invert__(self):
        return Variable(self.id, self.dom, negation=not self.negation)

    def __neg__(self):
        return Variable(self.id, self.dom, inverse=not self.inverse)

    def __hash__(self, *args, **kwargs):
        return object.__hash__(self, *args, **kwargs)

    def __repr__(self):
        return self.id


class VariableInteger(Variable):
    def __init__(self, name, dom):
        super().__init__(name, dom)


class VariableSymbolic(Variable):
    def __init__(self, name, dom):
        super().__init__(name, dom)
