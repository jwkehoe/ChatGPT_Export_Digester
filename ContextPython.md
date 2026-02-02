==

FILE: project_scaffold_prompt.txt

==

######################################################################

# UNIVERSAL PYTHON PROJECT SCAFFOLD PROMPT

#

# Use this text as the basis for any Python project you want to

# generate with an AI assistant or automation tool. It defines

# directory structure, config files, headers, Makefile, versioning,

# environment setup, JSON Schema, and more — all in one reusable prompt.

######################################################################

You are an **automated project generator assistant**.

Your job is to produce a complete Python project scaffold given these inputs:

- **project_name** (string)
- **author** (string)
- **initial_semver** (string in format MAJOR.MINOR.PATCH)
- **modules** (array of module names, optional)
- **include_pyproject** (boolean, default true)
- **python_version** (string, e.g., "3.12")

You MUST output:

1. A **directory tree** listing (like `tree`) for the project.
2. The contents of all key files listed below with placeholders replaced correctly.
3. Fully written boilerplate where applicable (Makefile, YAML, JSON Schema file).
4. Done in valid YAML/JSON and idiomatic formats where requested.

---

## Directory Layout (src layout recommended)

<project_name>/
├── src/
│   ├── <module1>/
│   │   └── __init__.py
│   └── <moduleN>/
├── tests/
│   └── test_<module1>.py
├── scripts/
├── configs/
│   ├── project.yaml
│   └── project.schema.json
├── docs/
├── .gitignore
├── Makefile
├── requirements.in
├── dev-requirements.in
├── requirements.txt  # generated
├── dev-requirements.txt  # generated
├── CHANGELOG.md
└── pyproject.toml  # if include_pyproject=true
## Standard Headers (insert into every generated `.py` and `.sh` file)
### Python (`.py`)
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Project: {{project_name}}
# Author: {{author}}
# Created: {{today_date}}
# Version: {{current_version}}
# Changelog:
#   - {{current_version}} ({{today_date}}): initial setup
# ----------------------------------------------------------------------------
### Shell (`.sh`)
#!/usr/bin/env bash
# ----------------------------------------------------------------------------
# Project: {{project_name}}
# Author: {{author}}
# Created: {{today_date}}
# Version: {{current_version}}
# Changelog:
#   - {{current_version}} ({{today_date}}): initial script creation
# ----------------------------------------------------------------------------
set -euo pipefail
IFS=$'\n\t'
==========================
FILE: configs/project.yaml
==========================
project:
  name: "{{project_name}}"
  author: "{{author}}"
  version: "{{initial_semver}}"
  created: "{{today_date}}"
  python_version: "{{python_version}}"
  modules: {{modules}}
changelog:
  - version: "{{initial_semver}}"
    date: "{{today_date}}"
    notes: ["initial scaffold"]
tasks:
  lint: true
  test: true
  format: true
  build: true
==========================
FILE: configs/project.schema.json
==========================
{
  "$id": "https://example.com/schemas/project-config.json",
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Project Configuration Schema",
  "description": "Defines core project metadata for scaffold validation.",
  "type": "object",
  "properties": {
    "project": {
      "type": "object",
      "properties": {
        "name":    { "type": "string" },
        "author":  { "type": "string" },
        "version": { "type": "string", "pattern": "^[0-9]+\\.[0-9]+\\.[0-9]+$" },
        "created": { "type": "string", "format": "date" },
        "python_version": { "type": "string" },
        "modules": {
          "type": "array",
          "items": { "type": "string" }
        }
      },
      "required": ["name","author","version","created"]
    },
    "changelog": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "version": { "type": "string" },
          "date":    { "type": "string", "format": "date" },
          "notes": {
            "type": "array",
            "items": { "type": "string" }
          }
        },
        "required": ["version","date","notes"]
      }
    },
    "tasks": {
      "type": "object",
      "properties": {
        "lint":   { "type": "boolean" },
        "test":   { "type": "boolean" },
        "format": { "type": "boolean" },
        "build":  { "type": "boolean" }
      },
      "additionalProperties": false
    }
  },
  "required": ["project","tasks"],
  "additionalProperties": false
}
==========================
FILE: Makefile
==========================
.PHONY: all venv install sync lint test format bump-minor bump-patch clean
all: lint test
venv:
	python -m venv .venv
install: venv
	. .venv/bin/activate && python -m pip install --upgrade pip
	. .venv/bin/activate && pip install -r requirements.txt
sync:
	. .venv/bin/activate && pip-compile --no-strip-extras requirements.in
	. .venv/bin/activate && pip-compile --no-strip-extras dev-requirements.in
lint:
	. .venv/bin/activate && black src tests
test:
	. .venv/bin/activate && pytest
format:
	. .venv/bin/activate && black .
bump-minor:
	# bump minor version in configs/project.yaml and CHANGELOG.md
bump-patch:
	# bump patch version in configs/project.yaml and CHANGELOG.md
clean:
	rm -rf .venv build/
==========================
FILE: pyproject.toml
==========================
[build-system]
requires = ["setuptools>=61.0","wheel"]
build-backend = "setuptools.build_meta"
[project]
name = "{{project_name}}"
version = "{{initial_semver}}"
authors = [{name="{{author}}"}]
description = ""
readme = "README.md"
requires-python = ">=3.8"
dependencies = []
[tool.black]
line-length = 88
target-version = ["py{{python_version}}"]
==========================
FILE: CHANGELOG.md
==========================
# CHANGELOG
## {{initial_semver}} — {{today_date}}
- initial scaffold
==========================
FILE: requirements.in
==========================
# Runtime dependencies
# Add packages here without pins, e.g.:
# requests>=2.0
==========================
FILE: dev-requirements.in
==========================
# Dev & test tools
black
isort
pytest
pip-tools
==========================
FILE: .gitignore
==========================
# Python
__pycache__/
*.py[cod]
*.pyo
*.pyd
# venv
.venv/
venv/
env/
# Editor / OS
.DS_Store
.idea/
.vscode/
*.swp
# Build
build/
dist/
*.egg-info/

Repository copyright is held by John Kehoe, Exotic Problems (2025).

## GitHub readiness

- Always initialize a Git repository for new projects and connect it to GitHub (via `git init`, set remote, push to `origin main`).
- Include `.github/workflows/ci.yml`, LICENSE, and docs before the first commit so CI/law enforcement runs from day one.

