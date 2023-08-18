[![Python 3.8 | 3.9 | 3.10 | 3.11](https://img.shields.io/badge/Python-3.8%20%7C%203.9%20%7C%203.10%20%7C%203.11-blue)](https://www.python.org/downloads)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)

[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/Preocts/braghook/main.svg)](https://results.pre-commit.ci/latest/github/Preocts/braghook/main)
[![Python tests](https://github.com/Preocts/braghook/actions/workflows/python-tests.yml/badge.svg?branch=main)](https://github.com/Preocts/braghook/actions/workflows/python-tests.yml)

# braghook

Recording daily achievements and posting them places. Running `braghook` will
open a file in the editor of choice for the current day. Once completed you will
be prompted to send the brag to the configuration file defined targets.

Supports:

- Discord (embed or code-block)
- Microsoft Teams
- GitHub Gist (appends new file to secret gist)

### Installation:

From repo:

```bash
python -m pip install .
```

From GitHub:

```bash
pip install git+https://github.com/Preocts/braghook@main
```

From curl:

```
curl https://raw.githubusercontent.com/Preocts/braghook/main/src/braghook/braghook.py -O
```

**Note**: "`/main/`" in the path can be replaced with desired tag/branch. The module
is completely stand-alone and can be invoked directly.

### Usage:

```console
usage: braghook [-h] [--bragfile BRAGFILE] [--create-config] [--auto-send] [--config CONFIG]

optional arguments:
  -h, --help            show this help message and exit
  --bragfile BRAGFILE, -b BRAGFILE
                        The brag file to use
  --create-config, -C   Create the config file
  --auto-send, -a       Automatically send the brag
  --config CONFIG, -c CONFIG
                        The config file to use
  ```

### Config file:

```ini
[DEFAULT]
workdir = .
editor = vim
editor_args =
author = yourname
author_icon =
discord_webhook =
discord_webhook_plain =
msteams_webhook =
github_url = https://api.github.com
github_user =
github_pat =
gist_id =
openweathermap_url =
```

| field                 | value                                                        | required |
| --------------------- | ------------------------------------------------------------ | -------- |
| workdir               | Target path for new brag files                               | yes      |
| editor                | Which editor to open                                         | yes      |
| editor_args           | Multiline of optional editor arguments                       | no       |
| author                | Your name, used in webhook posts, where applicable           | no       |
| authorh_icon          | URL to icon for webhook, where applicable                    | no       |
| discord_webhook       | URL of discord webhook - formatted as embed                  | no       |
| discord_webhook_plain | URL of discord webhook - posted as code-block                | no       |
| msteams_webhook       | URL of msteams webhook connector                             | no       |
| github_url            | URL to GitHub API (default: https://api.github.com)          | no       |
| github_user           | GitHub user name                                             | no       |
| github_pat            | GitHub personal access token with Gist read/write permission | no       |
| gist_id               | Gist ID to add brag file to                                  | no       |
| openweathermap_url    | OpenWeatherMap url with api key to pull current weather      | no       |

**note:** `github_user`, `github_pat`, and `gist_id` are all jointly required if used

---

### OpenWeatherMap

When provided, braghook will poll OpenWeatherMap on each edit of the brag file.
The current weather information will be appended to the bottom of the current
file. This happens when the file is closed, ensures a newline between the last
line enter and after.

This feature expects an [OpenWeatherMap current weather endpoint](https://openweathermap.org/current#zip) such as:

```
https://api.openweathermap.org/data/2.5/weather?zip=[your_zipcode],us&appid=[your_api_here]
```

The output line looks like this:

```
min: -9.0°C, max: -7.3°C, feels like: -12.8°C, humidity: 87%, pressure: 1022hPa
```

You will need to provide an API key. They are free with a registered account and allow 60 pulls per hour.

---

# Local developer installation

It is **strongly** recommended to use a virtual environment
([`venv`](https://docs.python.org/3/library/venv.html)) when working with python
projects. Leveraging a `venv` will ensure the installed dependency files will
not impact other python projects or any system dependencies.

The following steps outline how to install this repo for local development. See
the [CONTRIBUTING.md](CONTRIBUTING.md) file in the repo root for information on
contributing to the repo.

**Windows users**: Depending on your python install you will use `py` in place
of `python` to create the `venv`.

**Linux/Mac users**: Replace `python`, if needed, with the appropriate call to
the desired version while creating the `venv`. (e.g. `python3` or `python3.8`)

**All users**: Once inside an active `venv` all systems should allow the use of
`python` for command line instructions. This will ensure you are using the
`venv`'s python and not the system level python.

---

## Installation steps

### Makefile

This repo has a Makefile with some quality of life scripts if the system
supports `make`.  Please note there are no checks for an active `venv` in the
Makefile.  If you are on Windows you can install make using scoop or chocolatey.

| PHONY         | Description                                                           |
| ------------- | --------------------------------------------------------------------- |
| `install-dev` | install development/test requirements and project as editable install |
| `coverage`    | Run tests with coverage, generate console report                      |
| `build-dist`  | Build source distribution and wheel distribution                      |
| `clean`       | Deletes build, nox, coverage, pytest, mypy, cache, and pyc artifacts  |


Clone this repo and enter root directory of repo:

```console
$ git clone https://github.com/Preocts/braghook
$ cd braghook
```


Create the `venv`:

```console
$ python -m venv venv
```

Activate the `venv`:

```console
# Linux/Mac
$ . venv/bin/activate

# Windows
$ venv\Scripts\activate
```

The command prompt should now have a `(venv)` prefix on it. `python` will now
call the version of the interpreter used to create the `venv`

Install editable library and development requirements:

### With Makefile:

```console
make install-dev
```

### Without Makefile:

```console
$ python -m pip install --editable .[dev,test]
```

Install pre-commit [(see below for details)](#pre-commit):

```console
$ pre-commit install
```

---

## Misc Steps

Run pre-commit on all files:

```console
$ pre-commit run --all-files
```

Run tests (quick):

```console
$ pytest
```

Run tests (slow):

```console
$ nox
```

Build dist:

```console
$ python -m pip install --upgrade build

$ python -m build
```

To deactivate (exit) the `venv`:

```console
$ deactivate
```

---

## [pre-commit](https://pre-commit.com)

> A framework for managing and maintaining multi-language pre-commit hooks.

This repo is setup with a `.pre-commit-config.yaml` with the expectation that
any code submitted for review already passes all selected pre-commit checks.
`pre-commit` is installed with the development requirements and runs seemlessly
with `git` hooks.

---

## Error: File "setup.py" not found.

If you recieve this error while installing an editible version of this project you have two choices:

1. Update your `pip` to *at least* version 22.3.1
2. Add the following empty `setup.py` to the project if upgrading pip is not an option

```py
from setuptools import setup

setup()
```
