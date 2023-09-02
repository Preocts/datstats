[![Python 3.8 | 3.9 | 3.10 | 3.11 | 3.12](https://img.shields.io/badge/Python-3.8%20%7C%203.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue)](https://www.python.org/downloads)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)

[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/Preocts/daystats/main.svg)](https://results.pre-commit.ci/latest/github/Preocts/daystats/main)
[![Python tests](https://github.com/Preocts/daystats/actions/workflows/python-tests.yml/badge.svg?branch=main)](https://github.com/Preocts/daystats/actions/workflows/python-tests.yml)

# daystats

Pull your GitHub stats for a given 24 hour period and display them in the
terminal. Optionally, output them as a markdown ready table.

### Installation:

From repo:

```bash
python -m pip install .
```

From GitHub:

```bash
pip install git+https://github.com/Preocts/daystats@main
```

From curl:

```
curl https://raw.githubusercontent.com/Preocts/daystats/main/src/daystats/daystats.py -O
```

**Note**: "`/main/`" in the path can be replaced with desired tag/branch. The module
is completely stand-alone and can be invoked directly.

---

### CLI Usage:

A personal access token to your GitHub account is needed to generate day stats.
The token only needs read-only access to repos. The token can be provided via
the CLI or as an environment variable: `DAYSTATS_TOKEN`.

From Python:

```console
$ python -m daystats --help
```

From entry script:

```console
$ daystats --help
```

```console
$ daystats --help
usage: daystats [-h] [--markdown] [--year YEAR] [--month MONTH] [--day DAY] [--url URL] [--token TOKEN] [--debug] loginname

Pull daily stats from GitHub.

positional arguments:
  loginname      Login name to GitHub (author name).

optional arguments:
  -h, --help     show this help message and exit
  --markdown     Changes the text output to Markdown table for copy/paste.
  --year YEAR    Year to query. (default: today)
  --month MONTH  Month of the year to query. (default: today)
  --day DAY      Day of the month to query. (default: today)
  --url URL      Override default GitHub GraphQL API url. (default: https://api.github.com/graphql)
  --token TOKEN  GitHub Personal Access Token with read-only access for publis repos. Defaults to $DAYSTATS_TOKEN environ variable.
  --debug        Turn debug logging output on. Use with care, will expose token!
```

---

### Example console output:

```console
$ daystats preocts --month 8 --day 18

Daily GitHub Summary:
|    Contribution    | Count |    Metric     | Total |
------------------------------------------------------
| Reviews            |   0   | Files Changed |  38   |
| Issue              |   0   | Additions     |  300  |
| Commits            |  13   | Deletions     |  388  |
| Pull Requests      |   6   |               |       |

Pull Request Breakdown:

| Addition | Deletion | Files | Number | Url
----------------------------------------
|   102    |   266    |  14   |   35   | https://github.com/Preocts/walk-watcher/pull/35
|    82    |    39    |   9   |   80   | https://github.com/Preocts/pd-utils/pull/80
|    0     |    20    |   1   |   54   | https://github.com/Preocts/braghook/pull/54
|    14    |    9     |   1   |   53   | https://github.com/Preocts/braghook/pull/53
|    17    |    11    |   4   |  122   | https://github.com/Preocts/python-src-template/pull/122
|    85    |    43    |   9   |  145   | https://github.com/Preocts/secretbox/pull/145
```

### Example markdown output:

**Daily GitHub Summary**:

| Contribution  | Count | Metric        | Total |
| ------------- | ----- | ------------- | ----- |
| Reviews       | 0     | Files Changed | 38    |
| Issues        | 0     | Additions     | 300   |
| Commits       | 13    | Deletions     | 388   |
| Pull Requests | 6     |               |       |

**Pull Request Breakdown**:

| Repo                | Addition | Deletion | Files | Number                                                               |
| ------------------- | -------- | -------- | ----- | -------------------------------------------------------------------- |
| secretbox           | 85       | 43       | 9     | [see: #145](https://github.com/Preocts/secretbox/pull/145)           |
| python-src-template | 17       | 11       | 4     | [see: #122](https://github.com/Preocts/python-src-template/pull/122) |
| braghook            | 0        | 20       | 1     | [see: #54](https://github.com/Preocts/braghook/pull/54)              |
| braghook            | 14       | 9        | 1     | [see: #53](https://github.com/Preocts/braghook/pull/53)              |
| walk-watcher        | 102      | 266      | 14    | [see: #35](https://github.com/Preocts/walk-watcher/pull/35)          |
| pd-utils            | 82       | 39       | 9     | [see: #80](https://github.com/Preocts/pd-utils/pull/80)              |

---
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

Clone this repo and enter root directory of repo:

```console
git clone https://github.com/Preocts/daystats
cd daystats
```

Create the `venv`:

```console
python -m venv venv
```

Activate the `venv`:

```console
# Linux/Mac
. venv/bin/activate

# Windows
venv\Scripts\activate
```

The command prompt should now have a `(venv)` prefix on it. `python` will now
call the version of the interpreter used to create the `venv`

Install editable library and development requirements:

```console
python -m pip install --editable .[dev,test]
```

Install pre-commit [(see below for details)](#pre-commit):

```console
pre-commit install
```

---

## Misc Steps

Run pre-commit on all files:

```console
pre-commit run --all-files
```

Run tests (quick):

```console
pytest
```

Run tests:

```console
nox
```

Build dist:

```console
python -m pip install --upgrade build
python -m build
```

To deactivate (exit) the `venv`:

```console
deactivate
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
