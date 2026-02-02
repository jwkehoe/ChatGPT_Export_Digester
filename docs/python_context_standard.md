# Python Context Standard

This repository now keeps a **formal context document** that captures how to think about Python work here. It is derived from the existing `ContextPython.md`/`ContextPython.txt` scaffold prompt plus the actual structure of `chatgpt_export_digester.py` and `rename_conversation_dirs.py`. Use it whenever you need to build or extend a Python module inside this project so you stay consistent.

## Why this exists

- `ContextPython.*` defines a universal scaffold prompt (project layout, headers, config files, etc.). The new document distills that information into a practical checklist that fits this repo’s simpler structure.
- The two scripts already exist; their layout and metadata show how we prefer CLI help, documentation, and license notices to look.

## What belongs in the Python context

1. **Project metadata** – project name, author (John Kehoe / Exotic Problems), creation dates, version info, MIT license, and README/CHANGELOG references just like the headers in the scripts.
2. **CLI expectations** – every script should use `argparse` with helpful descriptions plus an extended epilog describing flags, their reasons, and examples; printing that epilog when no args are supplied is encouraged.
3. **Directory layout** – keep the repository scoped: root-level scripts (`chatgpt_export_digester.py`, `rename_conversation_dirs.py`), `ChatGPT_Exports/` for inputs, `ChatGPT_Digested/` for outputs, and supplemental docs/schemas (`README.md`, `chatgpt_conversations.schema.json`, `ChatGPT_Export_Schema_Analysis.md`).
4. **Documentation links** – mention the schema + export analysis, `README.md`, newly added `logic_tree.md`, and this doc in any context you provide.
5. **Environment note** – Python 3.10+ standard library only (`requirements.txt` reflects this), so call out this minimal dependency model whenever you describe how to run or extend the project.

## Standard context template

Use the following structure when summarizing context for future Python work here:

1. **Overview** - one paragraph describing the project’s goal and artifacts (transactions from zipped ChatGPT exports to chat transcripts).
2. **Key scripts & CLI** - mention `chatgpt_export_digester.py` and `rename_conversation_dirs.py`, highlight their flag behavior, merge/dedupe defaults, and the no-arg epilog printing.
3. **Assets & reports** - note that assets are copied per conversation, manifests are written, and unresolved reports are always generated.
4. **Documentation pointers** - link to `README.md`, `docs/python_context_standard.md`, `logic_tree.md`, `chatgpt_conversations.schema.json`, `ChatGPT_Export_Schema_Analysis.md`, and `docs` folder contents.
5. **Environment** - remind the reader of the Python ≥3.10 requirement and that only the standard library is used.

Whenever someone asks for more context, start by pointing them to this file plus the README, schema, and analysis docs before repeating details inline.
