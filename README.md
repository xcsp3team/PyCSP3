<h1 align="center"> PyCSP3 v1.1.x </h1>

This is the version 1.1.0 of PyCSP3, a library in Python 3 (version 3.5 or later) for modeling constrained combinatorial problems.
PyCSP3 is inspired from both [JvCSP3](http://www.xcsp.org/modeling) (a Java-based API) and [Numberjack](https://github.com/eomahony/Numberjack); it is also related to [CPpy](https://github.com/tias/cppy).

With PyCSP3, it is possible to generate instances of:
1. CSPs (Constraint Satisfaction Problems)
1. COPs (Constraint Optimization Problems)

in format XCSP3; see [www.xcsp.org](www.xcsp.org).

Note that:
* the code is available on [Github](https://github.com/xcsp3team/pycsp3)
* a [well-documented guide](https://github.com/xcsp3team/pycsp3/blob/master/guidePyCSP3.pdf) is available
* PyCSP3 is available as a PyPi package [here](https://pypi.org/project/pycsp3/)

**Important**: another version, 1.2.0, is planned to be published within a few weeks/months.
Currently, our main goal is :
* to fix a few problems encountered with python 3.8 (with python 3.5, 3.6 and 3.7, things look good)
* to give more helpful messages when the user (modeler) writes something incorrect

At this stage, one can run:
* the constraint solver 'AbsCon', with the option -solve or the option -solver=abscon
* the constraint solver 'Choco, with the option -solver=choco

Of course, it is possible to launch on generated XCSP3 instances (files) any solver that recognizes the XCSP3 format.
In the medium/long term, we also plan to develop an interface that will allow users to pilot solvers with Python.

# Installation


Installation instructions are currently given for Linux and Windows (instructions for Mac will be inserted soon)

## Installing PyCSP3 (Linux)


For installing PyCSP3, you need to execute:

```console
sudo apt install python3-pip
sudo pip3 install pycsp3
```

For using the -solve or -solver options, you need to install (at least) Java version 8:

```console
sudo apt-get install openjdk-8-jdk
```

## Installing PyCSP3 (Windows)

For installing Python, you need to install the version 3.7:

https://www.python.org/downloads/release/python-377/

Do not forget to tick the box 'Add Python 3.7 to PATH' during the installation.

Next, you have to open the console and upgrade pip:

```console
python -m pip install --upgrade pip
```

And for installing pycsp3:

```console
python -m pip install pycsp3
```

For using the -solve or -solver options, you need to install (at least) Java version 8:

https://www.oracle.com/java/technologies/javase-downloads.html

And add in the PATH the java command, for example, temporally, with the command:

```console
set path=%path%;C:/Program Files/Java/jdk-14.0.1/bin/
```

You can check the java command by typing in your console:

```console
java --version
```

## Updating PyCSP3

For updating your version of PyCSP3, simply execute:

For linux:

```console
sudo pip3 install --upgrade pycsp3
```

For Windows:

```console
python -m pip install --upgrade pycsp3
```

## Copying a pool of models

PyCSP3 is accompanied by more than 100 models.
To get them in a subdirectory `problems` of your current directory, execute:

```console
python3 -m pycsp3 (For linux)
python -m pycsp3 (For Windows)
```

And you can test the compilation of one of the models, for example:

```console
python3 problems/g0_school/Pic.py (For Linux)
python problems\g0_school\Pic.py (For Windows)
```

## Compiling PyCSP3 Models

For generating an XCSP3 file from a PyCSP3 model, you have to execute:

```console
python3 <file> [options]
```

with:

*  &lt;file&gt;: a Python file to be executed, describing a model in PyCSP3
*  [options]: possible options to be used when compiling

Among the options, we find:

* ```-data=<data_value>```: allows us to specify the data to be used by the model. It can be:
    + elementary: -data=5
    + a simple list: -data=[9,0,0,3,9]
    + a JSON file: -data=Bibd-3-4-6.json

    Data can then be directly used in the PyCSP3 model by means of a predefined variable `data`.


* ```-dataparser=<file>```: a Python file for reading/parsing data given under any arbitrary form (e.g., by a text file).
     See Example Nonogram below, for an illustration.

* ```-dataexport```: exports (saves) the data in JSON format.
     See Example Nonogram below, for an illustration.

* ```-variant=<variant_name>```: the name of a variant, to be used with function `variant()`.
      See Example AllInterval below, for an illustration.

* ```-solve```: attempts to solve the instance with the embedded solver 'AbsCon'. It requires that Java version 8 (at least) is installed.

* ```-solver=<solver_name>```: attempts to solve the instance with the solver whose name is given. Currently, it can be 'abscon' or 'choco'. Important: it requires that Java version 8 (at least) is installed.


# Some Examples

We succinctly introduce a few PyCSP3 models, showing how to compile them with different options.


## Example 1: in console mode

Our first example shows how you can build basic models in console mode.
In this example, we just post two variable and two simple binary constraints.

```console
$ python3
Python 3.5.2
>>> from pycsp3 import *
>>> x = Var(range(10))
>>> y = Var(range(10))
>>> satisfy(
       x < y,
       x + y > 15
    )
>>> compile()
```
Note that to get an XCSP3 file, we call `compile()`.


## Example 2: Send+More=Money

This example shows how you can define a model when no data is required from the user.
This is the classical crypto-arithmetic puzzle 'Send+More=Money'.

#### File **`SendMore.py`**

```python
from pycsp3 import *

# letters[i] is the digit of the ith letter involved in the equation
s, e, n, d, m, o, r, y = letters = VarArray(size=8, dom=range(10))

satisfy(
    # letters are given different values
    AllDifferent(letters),

    # words cannot start with 0
    [s > 0, m > 0],

    # respecting the mathematical equation
    [s, e, n, d] * [1000, 100, 10, 1]
    + [m, o, r, e] * [1000, 100, 10, 1]
    == [m, o, n, e, y] * [10000, 1000, 100, 10, 1]
)
```

To generate the XCSP3 instance (file), the command is:

```console
python3 SendMore.py
```

To generate and solve (with AbsCon) the XCSP3 instance, the command is:

```console
python3 SendMore.py -solve
```

To generate and solve with Choco the XCSP3 instance, the command is:

```console
python3 SendMore.py -solver=choco
```


## Example 3: All-Interval Series

This example shows how you can simply specify an integer (as unique data) for a model.
For our illustration, we consider the problem [All-Interval Series](http://www.csplib.org/Problems/prob007/).

A classical model is:

#### File **`AllInterval.py`** (version 1)

```python
from pycsp3 import *

n = data

# x[i] is the ith note of the series
x = VarArray(size=n, dom=range(n))

satisfy(
    # notes must occur once, and so form a permutation
    AllDifferent(x),

    # intervals between neighbouring notes must form a permutation
    AllDifferent(abs(x[i] - x[i + 1]) for i in range(n - 1)),

    # tag(symmetry-breaking)
    x[0] < x[n - 1]
)
```

Note the presence of a tag `symmetry-breaking` that will be directly integrated into the XCSP3 file generated by the following command:

```console
python3 AllInterval.py -data=5
```

Suppose that you would prefer to declare a second array of variables for representing successive distances.
This would give:


#### File **`AllInterval.py`** (version 2)

```python
from pycsp3 import *

n = data

# x[i] is the ith note of the series
x = VarArray(size=n, dom=range(n))

# y[i] is the distance between x[i] and x[i+1]
y = VarArray(size=n - 1, dom=range(1, n))

satisfy(
    # notes must occur once, and so form a permutation
    AllDifferent(x),

    # intervals between neighbouring notes must form a permutation
    AllDifferent(y),

    # computing distances
    [y[i] == abs(x[i] - x[i + 1]) for i in range(n - 1)],

    # tag(symmetry-breaking)
    [x[0] < x[n - 1], y[0] < y[1]]
)
```

However, sometimes, it may be relevant to combine different variants of a model in the same file.
In our example, this would give:

#### File **`AllInterval.py`** (version 3)

```python
from pycsp3 import *

n = data

# x[i] is the ith note of the series
x = VarArray(size=n, dom=range(n))

if not variant():

    satisfy(
        # notes must occur once, and so form a permutation
        AllDifferent(x),

        # intervals between neighbouring notes must form a permutation
        AllDifferent(abs(x[i] - x[i + 1]) for i in range(n - 1)),

        # tag(symmetry-breaking)
        x[0] < x[n - 1]
    )

elif variant("aux"):

    # y[i] is the distance between x[i] and x[i+1]
    y = VarArray(size=n - 1, dom=range(1, n))

    satisfy(
        # notes must occur once, and so form a permutation
        AllDifferent(x),

        # intervals between neighbouring notes must form a permutation
        AllDifferent(y),

        # computing distances
        [y[i] == abs(x[i] - x[i + 1]) for i in range(n - 1)],

        # tag(symmetry-breaking)
        [x[0] < x[n - 1], y[0] < y[1]]
    )
```

For compiling the main model (variant), the command is:

```console
python3 AllInterval.py -data=5
```

For compiling the second model variant, using the option `-variant`, the command is:

```console
python3 AllInterval.py -data=5 -variant=aux
```

To generate and solve (with AbsCon) the instance of order 10 and variant 'aux', the command is:

```console
python3 AllInterval.py -data=10 -variant=aux -solve
```


## Example 4: BIBD

This example shows how you can specify a list of integers to be used as data for a model.
For our illustration, we consider the problem [BIBD](http://www.csplib.org/Problems/prob028/).
We need five integers `v, b, r, k, l` for specifying a unique instance (possibly, `b` and `r` can be set to 0, so that these values are automatically computed according to a template for this problem).
The model is:

#### File **`Bibd.py`**

```python
from pycsp3 import *

v, b, r, k, l = data
b = (l * v * (v - 1)) // (k * (k - 1)) if b == 0 else b
r = (l * (v - 1)) // (k - 1) if r == 0 else r

# x[i][j] is the value of the matrix at row i and column j
x = VarArray(size=[v, b], dom={0, 1})

satisfy(
    # constraints on rows
    [Sum(row) == r for row in x],

    # constraints on columns
    [Sum(col) == k for col in columns(x)],

    # scalar constraints with respect to lambda
    [row1 * row2 == l for (row1, row2) in combinations(x, 2)]
)
```

To generate an XCSP3 instance (file), we can for example execute a command like:

```console
python3 Bibd.py -data=[9,0,0,3,9]
```

With some command interpreters (shells), you may have to escape the characters '[' and ']', which gives:

```console
python3 Bibd.py -data=\[9,0,0,3,9\]
```


## Example 5: Rack Configuration

This example shows how you can specify a JSON file to be used as data for a model.
For our illustration, we consider the problem [Rack Configuration](http://www.csplib.org/Problems/prob031/).
The data (for a specific instance) are then initially given in a JSON file, as for example:

#### File **`Rack_r2.json`**

```json
{
    "nRacks": 10,
    "models": [[150,8,150],[200,16,200]],
    "cardTypes": [[20,20],[40,8],[50,4],[75,2]]
}
```

In the following model, we directly unpack the components of the variable `data` (because it is automatically given under the form of a named tuple) whose fields are exactly those of the main object in the JSON file.

#### File **`Rack.py`**

```python
from pycsp3 import *

nRacks, models, cardTypes = data
models.append([0, 0, 0])  # we add first a dummy model (0,0,0)
powers, sizes, costs = zip(*models)
cardPowers, cardDemands = zip(*cardTypes)
nModels, nTypes = len(models), len(cardTypes)

table = {(i, powers[i], sizes[i], costs[i]) for i in range(nModels)}

# m[i] is the model used for the ith rack
m = VarArray(size=nRacks, dom=range(nModels))

# p[i] is the power of the model used for the ith rack
p = VarArray(size=nRacks, dom=powers)

# s[i] is the size (number of connectors) of the model used for the ith rack
s = VarArray(size=nRacks, dom=sizes)

# c[i] is the cost (price) of the model used for the ith rack
c = VarArray(size=nRacks, dom=costs)

# nc[i][j] is the number of cards of type j put in the ith rack
nc = VarArray(size=[nRacks, nTypes], dom=lambda i, j: range(min(max(sizes), cardDemands[j]) + 1))

satisfy(
    # linking rack models with powers, sizes and costs
    [(m[i], p[i], s[i], c[i]) in table for i in range(nRacks)],

    # connector-capacity constraints
    [Sum(nc[i]) <= s[i] for i in range(nRacks)],

    # power-capacity constraints
    [nc[i] * cardPowers <= p[i] for i in range(nRacks)],

    # demand constraints
    [Sum(nc[:, j]) == cardDemands[j] for j in range(nTypes)],

    # tag(symmetry-breaking)
    [Decreasing(m), imply(m[0] == m[1], nc[0][0] >= nc[1][0])]
)

minimize(
    # minimizing the total cost being paid for all racks
    Sum(c)
)
```

To generate an XCSP3 instance (file), we execute the command:

```console
python3 Rack.py -data=Rack_r2.json
```

One might want to have the data in the JSON file with another structure, as for example:


#### File **`Rack_r2b.json`**

```json
{
    "nRacks": 10,
    "rackModels": [
	{"power":150,"nConnectors":8,"price":150},
	{"power":200,"nConnectors":16,"price":200}
    ],
    "cardTypes": [
	{"power":20,"demand":20},
	{"power":40,"demand":8},
	{"power":50,"demand":4},
	{"power":75,"demand":2}
    ]
}
  ```

We only need to modify one line from the previous model:


#### File **`Rack2.py`**

```python
models.append(models[0].__class__(0, 0, 0))  # we add first a dummy model (0,0,0) ; we get the class of the used named tuples to build a new one
```

To generate an XCSP3 instance (file), we execute the command:

```console
python3 Rack2.py -data=Rack_r2b.json
```


## Example 6: Nonogram

This example shows how you can use an auxiliary Python file for parsing data that are not initially given under JSON format.
For our illustration, we consider the problem [Nonogram](http://www.csplib.org/Problems/prob012/).
The data (for a specific Nonogram puzzle) are initially given in a text file as follows:
1. a line stating the numbers of rows and columns,
1. then, for each row a line stating the number of blocks followed by the sizes of all these blocks (on the same line),
1. then, for each column a line stating the number of blocks followed by the sizes of all these blocks (on the same line).

Below, here is an example of such a text file.

#### File **`Nonogram_example.txt`**
```
24 24
0
1	5
2	3 3
2	1 2
2	2 1
2	1 1
2	3 3
3	1 5 1
3	1 1 1
3	2 1 1
3	1 1 2
3	3 1 3
3	1 3 1
3	1 1 1
3	2 1 2
3	1 1 1
1	5
3	1 1 1
3	1 1 1
3	1 1 1
3	5 1 1
2	1 2
3	2 2 4
2	4 9

0
0
0
1	1
1	2
1	2
2	6 1
3	3 1 3
3	1 1 4
4	2 1 1 7
5	1 1 1 1 1
3	1 12 1
5	1 1 1 1 1
4	2 1 1 7
4	1 1 4 1
4	2 1 2 2
2	8 3
2	1 1
2	1 2
1	4
1	3
1	2
1	1
0
```

First, we need to write a piece of code in Python for building a dictionary `data` that will be then used in our model (after having been automatically converted to a named tuple).
We have first to import everything (*) from `pycsp3.problems.data.parsing`.
We can then add any new arbitrary item to the dictionary `data` (which is initially empty).
This is what we do below with two items whose keys are called `rowPatterns` and `colPatterns`.
The values associated with these two keys are defined as two-dimensional arrays (lists) of integers, defining the sizes of blocks.
The function `next_int()` can be called for reading the next integer in a text file, which will be specified on the command line (see later).

#### File **`Nonogram_Parser.py`**
```python
from pycsp3.problems.data.parsing import *

nRows, nCols = next_int(), next_int()
data["rowPatterns"] = [[next_int() for _ in range(next_int())] for _ in range(nRows)]
data["colPatterns"] = [[next_int() for _ in range(next_int())] for _ in range(nRows)]
```

Then, we just write the model by getting data from the variable `data`.
The model is totally independent of the way data were initially given (from a text file or a JSON file, for example).
In the code below, note how an object `Automaton` is defined from a specified pattern (list of blocks).
 Also, for a `regular` constraint, we just write something like `scope in automaton`.
 Finally, `x[:, j]` denotes the jth column of `x`.

#### File **`Nonogram.py`**
```python
from pycsp3 import *

rows, cols = data  # patterns for row and columns 
nRows, nCols = len(rows), len(cols)

def automaton(pattern):
    q = Automaton.q  # for building state names
    transitions = []
    if len(pattern) == 0:
        n_states = 1
        transitions.append((q(0), 0, q(0)))
    else:
        n_states = sum(pattern) + len(pattern)
        num = 0
        for i in range(len(pattern)):
            transitions.append((q(num), 0, q(num)))
            for j in range(pattern[i]):
                transitions.append((q(num), 1, q(num + 1)))
                num += 1
            if i < len(pattern) - 1:
                transitions.append((q(num), 0, q(num + 1)))
                num += 1
        transitions.append((q(num), 0, q(num)))
    return Automaton(start=q(0), final=q(n_states - 1), transitions=transitions)

#  x[i][j] is 1 iff the cell at row i and col j is colored in black
x = VarArray(size=[nRows, nCols], dom={0, 1})

satisfy(
    [x[i] in automaton(rows[i]) for i in range(nRows)],

    [x[:, j] in automaton(cols[j]) for j in range(nCols)]
)
```

To generate the XCSP3 instance (file), we just need to specify the name of the text file (option `-data`) and the name of the Python parser (option `-dataparser`).

```console
python3 Nonogram.py -data=Nonogram_example.txt -dataparser=Nonogram_Parser.py
```

Maybe, you think that it would be simpler to have directly the data in JSON file.
You can generate such a file with the option `-dataexport`.
The command is as follows:

```console
python3 Nonogram.py -data=Nonogram_example.txt -dataparser=Nonogram_Parser.py -dataexport
```

A file `Nonogram_example.json` is generated, whose content is:

```json
{
 "colPatterns":[[],[],[],[1],[2],[2],[6,1],[3,1,3],[1,1,4],[2,1,1,7],[1,1,1,1,1],[1,12,1],[1,1,1,1,1],[2,1,1,7],[1,1,4,1],[2,1,2,2],[8,3],[1,1],[1,2],[4],[3],[2],[1],[]],
 "rowPatterns":[[],[5],[3,3],[1,2],[2,1],[1,1],[3,3],[1,5,1],[1,1,1],[2,1,1],[1,1,2],[3,1,3],[1,3,1],[1,1,1],[2,1,2],[1,1,1],[5],[1,1,1],[1,1,1],[1,1,1],[5,1,1],[1,2],[2,2,4],[4,9]]
}
```

With this new file, you can directly generate the XCSP3 file with:
 ```console
python3 Nonogram.py -data=Nonogram_example.json
```
