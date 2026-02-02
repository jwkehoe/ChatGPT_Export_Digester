# Python Context & Scaffold

## Overview
This repository stages everything needed to pull ChatGPT conversations off the platform, normalize them into human-friendly transcripts, and keep each referenced asset together with the messages that touch it.
- `chatgpt_export_digester.py` ingests one or more export zips, merges overlaps, deduplicates messages, copies referenced assets into per-conversation `assets/` folders, and writes `conversation.md`, `messages.jsonl`, plus index/unresolved-asset reports.
- `rename_conversation_dirs.py` slugifies conversation titles (optionally appending the original ID), renames the folders, and emits rename/id-title mapping JSON so downstream consumers know who said what.
- Automation, schema documentation, and supporting docs (logic tree, October article, shared context guide) live under `docs/`, while `requirements.txt` declares that Python ≥3.10 with only the standard library is enough.

## Reconciled Scaffold Reference
The universal Python scaffold prompt (originally in `ContextPython.md`) defined how to structure a project:

1. **Directory layout**: `src/`, `tests/`, `scripts/`, `configs/`, `docs/`, top-level tooling files (`Makefile`, `requirements*.in`, `CHANGELOG.md`, optional `pyproject.toml`).
2. **Headers**: Every generated `.py` gets the standard MIT-style header (project name, author, date, version, changelog), and shell helpers share a similar annotated header plus safety flags.
3. **Config files**: `configs/project.yaml` should describe project metadata + tasks, with a companion JSON Schema; `Makefile` defines tasks for venv bootstrap, lint/test/format, and version bumps.
4. **Requirements**: Runtime/dev dependencies are declared via `requirements.in`/`dev-requirements.in`, pinned via generated `.txt` files.
5. **CI readiness**: Always initialize `.github/workflows/ci.yml`, include `LICENSE`, and ensure docs are present before the first commit.

In this specific repository the scaffold plays out as:
- `ChatGPT_Exports/` contains the zipped exports; `ChatGPT_Digested/` holds the processed conversations, asset manifests, renamer outputs, and unresolved reports.
- `README.md` explains the digester/renamer workflow, no-arg help printing, and automation.
- `docs/logic_tree.md` and `docs/october-archive-article.md` expand on the pipeline and the motivation; `docs/python_context_standard.md` interprets the scaffold for this repo’s conventions.
- `.github/workflows/ci.yml` installs (empty) requirements and runs both CLIs’ `--help` across multiple Python versions so the repo is CI-ready out of the box.
- The repo-level `requirements.txt` reiterates “Python ≥3.10, standard library only” for lightweight portability.

## Repository-Specific Rules
1. **Metadata + headers** – Every Python file carries the MIT/Exotic Problems header. Update the changelog section when bumping versions.
2. **CLI help & transparency** – Both scripts print their extended epilog whenever invoked without options, so users instantly see each flag’s purpose, examples, and the reason the tool exists.
3. **Documentation pointers** – Always reference `docs/python_context_standard.md`, `docs/logic_tree.md`, and `docs/october-archive-article.md` when describing how to extend or integrate the pipeline.
4. **Assets + reports** – The digester writes `assets_manifest.json`, and the global unresolved reports highlight missing files across conversations. Include these with any commit that touches asset-handling logic.
5. **Environment** – The tooling relies only on the standard library (per `requirements.txt`) and targets Python 3.10+. Mention this when onboarding new contributors or scripting automation.

## Appendix: Original Scaffold Prompt
```
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
```
