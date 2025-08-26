[![Build Status](https://github.com/ladybug-tools/honeybee-ies/workflows/CI/badge.svg)](https://github.com/ladybug-tools/honeybee-ies/actions)

[![Python 3.10](https://img.shields.io/badge/python-3.10-orange.svg)](https://www.python.org/downloads/release/python-3100/)
[![Python 3.7](https://img.shields.io/badge/python-3.7-blue.svg)](https://www.python.org/downloads/release/python-370/)

# honeybee-ies

Honeybee extension for translating an HBJSON file to IES-VE GEM file format and vice versa.

## Sydney Opera House

![image(52)](https://github.com/ladybug-tools/honeybee-ies/assets/2915573/d57be713-0cef-41ef-b365-7611ebc704f6)

<img width="958" alt="image(53)" src="https://github.com/ladybug-tools/honeybee-ies/assets/2915573/34ad782b-f177-4b11-8fc4-84d7bc9c34aa">

## Revit sample model

![image](https://user-images.githubusercontent.com/2915573/145484209-ca484536-2d86-4f3f-9113-f4c998aa304f.png)

## Installation
```console
pip install honeybee-ies
```

## QuickStart

```python
import pathlib
from honeybee.model import Model

path_to_hbjson = './tests/assets/sample_model_45.hbjson'
path_to_out_folder = pathlib.Path('./tests/assets/temp')
path_to_out_folder.mkdir(parents=True, exist_ok=True) 
model = Model.from_hbjson(path_to_hbjson)
# the to_gem method is added to model by honeybee-ies library
gem_file = model.to_gem(path_to_out_folder.as_posix(), name='sample_model_45')

```

You can also run the command from CLI

```honeybee-ies translate model-to-gem ./tests/assets/revit_sample_model.hbjson --name revit-sample-model```


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
