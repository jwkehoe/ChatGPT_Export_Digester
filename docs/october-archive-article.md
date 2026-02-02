# Guard Your October Conversations

With the “October gatekeeping” tightening access and retention on AI chat platforms, protecting your histories and assets means moving them off the platform and into your own tooling. This project gives you a full pipeline to do exactly that.

## What it is

This repository is a self-contained **ChatGPT Archive Digester** that ingests the export zip files the chat UI gives you and emits tidy, human-readable folders you control. It normalizes conversation graphs into `conversation.md` transcripts, `messages.jsonl`, per-conversation `assets/`, and manifests that mark resolved/unresolved references. A companion renamer script converts the numeric IDs into slugified titles and emits traceable rename/id maps. Everything is tied together with a README, schema (`chatgpt_conversations.schema.json`), and analysis notes so you can inspect how exports are structured.

## Why it was written

The October gatekeeping push increased the risk of losing access to old chats, especially assets (images, code, files) stored only on the provider’s side. This tool is a countermeasure:

1. **You own the data.** It downloads every referenced asset into `ChatGPT_Digested/conversations/.../assets`, and writes metadata/manifest files so nothing gets forgotten.
2. **No provider limitations.** The digester can merge overlapping exports (`--merge-overlaps`, dedupe logic) or preserve per-archive copies (`--no-dedupe`), so you never rely on a single snapshot.
3. **Reusable outputs.** The normalized JSONL + markdown transcripts are ready to feed Codex or any other AI/analysis stack because they strip out graph noise and focus on timestamps, roles, content, and asset refs.

## What you can do with it

- **Archive aggressively.** Download every export zip, throw them in `ChatGPT_Exports/`, run `python3 chatgpt_export_digester.py --input-dir ChatGPT_Exports --output-dir ChatGPT_Digested --merge-overlaps`, and walk away knowing every conversation, message, and asset has a stable home.
- **Inspect unresolved assets.** The pipeline always emits `unresolved_assets_report.jsonl` and a summary, highlighting any asset the export referenced but didn’t contain (expired links, provider pruning, etc.).
- **Rename for clarity.** Run `python3 rename_conversation_dirs.py --root ChatGPT_Digested/conversations` (with optional `--include-id` or `--dry-run`) to replace ID folders with slugified titles while keeping a JSON map for auditing.
- **Feed other systems.** The normalized transcripts are plain Markdown plus metadata, so you can feed your search, summarization, or Codex prompts without re-parsing the export graph yourself.
- **Document for teams.** The README, schema, `logic_tree.md`, and shared Python context guide (`../TOOLS/python_context_standard.md`) explain the workflow so collaborators know where to look and how to extend it.

## Final thought

October’s gatekeeping reminds us that relying on the provider’s memory is risky. This project keeps your chat history and assets local, documented, and programmable. Run the digester, rename the outputs, and plug those transcripts into whatever AI stack you prefer—Codex, GPT, or something else—with confidence that you still own every byte.
