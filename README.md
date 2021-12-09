[![Build Status](https://github.com/ladybug-tools/honeybee-ies/workflows/CI/badge.svg)](https://github.com/ladybug-tools/honeybee-ies/actions)

[![Python 3.7](https://img.shields.io/badge/python-3.7-blue.svg)](https://www.python.org/downloads/release/python-370/) [![Python 2.7](https://img.shields.io/badge/python-2.7-green.svg)](https://www.python.org/downloads/release/python-270/) [![IronPython](https://img.shields.io/badge/ironpython-2.7-red.svg)](https://github.com/IronLanguages/ironpython2/releases/tag/ipy-2.7.8/)

# honeybee-ies

Honeybee extension for import and export to/from IES-VE

## Installation
```console
pip install honeybee-ies
```

## QuickStart
```python
import honeybee_ies

```

## [API Documentation](http://ladybug-tools.github.io/honeybee-ies/docs)

## Local Development
1. Clone this repo locally
```console
git clone git@github.com:ladybug-tools/honeybee-ies

# or

git clone https://github.com/ladybug-tools/honeybee-ies
```
2. Install dependencies:
```console
cd honeybee-ies
pip install -r dev-requirements.txt
pip install -r requirements.txt
```

3. Run Tests:
```console
python -m pytest tests/
```

4. Generate Documentation:
```console
sphinx-apidoc -f -e -d 4 -o ./docs ./honeybee_ies
sphinx-build -b html ./docs ./docs/_build/docs
```
