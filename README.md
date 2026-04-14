# sysml2py
[![PyPI version](https://badge.fury.io/py/sysml2py.svg)](https://badge.fury.io/py/sysml2py)[![PyPI status](https://img.shields.io/pypi/status/sysml2py.svg)](https://pypi.python.org/pypi/sysml2py/)[![MIT license](https://img.shields.io/badge/License-MIT-blue.svg)](https://lbesson.mit-license.org/)

## Description
sysml2py is an open source pure Python library for constructing python-based
classes consistent with the [SysML v2.0 standard](https://github.com/Systems-Modeling/SysML-v2-Release).

This is a fork of the original project by [Christopher Cox](https://github.com/chriscox-westfall),
maintained by [Jon Fox](mailto:jon.fox@drfox.com) at [mycr0ft/sysml2py](https://github.com/mycr0ft/sysml2py).

## Requirements
sysml2py requires the following Python packages:
- [textX](https://github.com/textX/textX)
- [pyyaml](https://github.com/yaml/pyyaml)
- [pint](https://github.com/hgrecco/pint)

## Installation

Multiple installation methods are supported by sysml2py, including:

|                             **Logo**                              | **Platform** |                                    **Command**                                    |
|:-----------------------------------------------------------------:|:------------:|:---------------------------------------------------------------------------------:|
|       ![PyPI logo](https://simpleicons.org/icons/pypi.svg)        |     PyPI     |                        ``python -m pip install sysml2py``                        |
|     ![GitHub logo](https://simpleicons.org/icons/github.svg)      |    GitHub    | ``python -m pip install https://github.com/mycr0ft/sysml2py/archive/refs/heads/main.zip`` |

## Documentation

Documentation can be found [here.](https://mycr0ft.github.io/sysml2py/)

### Basic Usage

The code below will create a part called Stage 1, with a shortname of <'3.1'>
referencing a specific requirement or document. It has a mass attribute of 100
kg. It has a thrust attribute of 1000 N. These attributes are created and placed
as a child of the part. Next, we recall the part value for thrust and add 199 N.
Finally, we can dump the output from this class.
```
  from sysml2py import Attribute, Part, ureg

  a = Attribute(name='mass')
  a.set_value(100 * ureg.kilogram)
  b = Attribute(name='thrust')
  b.set_value(1000 * ureg.newton)
  c = Part(name="Stage_1", shortname="'3.1'")
  c._set_child(a)
  c._set_child(b)
  v = "Stage_1.thrust"
  c._get_child(v).set_value(c._get_child(v).get_value() + 199 * ureg.newton)
  print(c.dump())
```

It will output the following:
```
  part <'3.1'> Stage_1 {
    attribute mass= 100 [kilogram];
    attribute thrust= 1199.0 [newton];
  }
```

The package is able to handle Items, Parts, and Attributes.

```
a = Part(name='camera')
b = Item(name='lens')
d = Attribute(name='mass')
c = Part(name='sensor')
c._set_child(a)
c._set_child(b)
a._set_child(d)
print(c.dump())
```

will return:
```
part sensor {
   part camera {
      attribute mass;
   }
   item lens;
}
```

Actions
-------

Actions (activities) can be defined with input and output parameters::

```
from sysml2py import Action

# Action definition with typed inputs/outputs
a = Action(definition=True, name='Focus')
a.add_input('scene', 'Scene')
a.add_output('image', 'Image')
print(a.dump())
# → action def Focus { in scene : Scene; out image : Image; }

# Action usage with references
b = Action(name='TakePicture')
b.add_input('scene')
b.add_output('picture')
print(b.dump())
# → action TakePicture { in scene; out picture; }
```

References
----------

References can reference other elements::

```
from sysml2py import Reference, Item

# Simple reference
r = Reference(name='driver')
print(r.dump())
# → ref driver;

# Reference with type
person = Item(name='Person')
r2 = Reference(name='driver')
r2.set_type(person)
print(r2.dump())
# → ref driver : Person;

# Reference redefinition
r3 = Reference(name='payload', redefines=True)
r3.set_type(person)
print(r3.dump())
# → ref :>> payload : Person;
```

## License
sysml2py is released under the MIT license, hence allowing commercial use of the library.
