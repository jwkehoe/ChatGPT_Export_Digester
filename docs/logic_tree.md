# ChatGPT Export Digester Logic Tree

```
                           +---------------------------+
                           | parse_args(...)           |
                           | (chatgpt_export_digester.py:1043-1116) |
                           +-------------+-------------+
                                         |
          +------------------------------+------------------------------+
          |                                                             |
  --merge-overlaps?                                             No --merge-overlaps
          |                                                             |
+---------v---------+                                       +-----------v---------------+
| process_archives_ |                                       | loop over zip archives    |
| merge(...)        |                                       | -> process_archive(...):  |
| (global merge)    |                                       |    - load conversations   |
| (lines 725-983)   |                                       |    - dedupe unless        |
|                   |                                       |      --no-dedupe          |
+---------+---------+                                       |      (registry logic:     |
          |                                                 |      chatgpt_export...:   |
          |                                                 |      999-1039)            |
          |                                                 |    - include_all_branches |
          |                                                 |      flag affects node    |
          |                                                 |      selection (line 535) |
          +-- asset-strategy copy_per_conversation          | 
             -> builds consolidated conversations           |
             -> stats/index/unresolved reports              |
                                                            |
                             (Branch detail)                |
                                                            |
               +------------------------+-------------------+
               |                        |
     --include-all-branches?        (default) Active path only
               |                        |
       linearize_all_nodes(...)    linearize_active_path(...)
       (records every node)       (only current branch; fallback to all
                                  if nothing) (see lines 421-566)
```

- Every run uses `--asset-strategy copy_per_conversation` (default and only allowed choice), so assets copy into each `assets/` folder and are recorded in `assets_manifest.json` (`chatgpt_export_digester.py:452-666`).  
- The non-merge path respects `--dedupe` (default) vs `--no-dedupe` by scoping registry keys, controlling whether multiple archives yield separate folders or overwrite per-ID output (`chatgpt_export_digester.py:999-1036`).  
- Stats written to `index.json` and the unresolved asset reports track archives, conversations, assets, unresolved assets, deduped entries, merged messages, and bad archives, letting you validate success after any option combination (`chatgpt_export_digester.py:1114-1154`).

Let me know if you’d like an annotated version of this tree that includes the asset-copy helpers (`copy_assets_local` vs `copy_assets_global`) or the rename step afterward.

© 2026 John Kehoe, Exotic Problems.
