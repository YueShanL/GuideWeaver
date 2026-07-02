---
name: guideweaver-start
description: Start GuideWeaver guide-aware editing mode by listing and reading the current project guide and version-aligned dependency guides before code changes. Use when Codex is about to modify a repository and needs missing project or dependency context from local guides, packaged guides, or subagent retrieval.
---

# GuideWeaver Start

Use this entry before editing code. It does not build guides and should not write project guide files.

## Workflow

1. Decide whether the target change needs project or dependency context not already in conversation.
2. If yes, read `.codex/project-guides/PROJECT_GUIDE.md` for the current repo.
3. Read `.codex/project-guides/index.json` to find version-aligned dependency guides.
4. For each dependency needed by the task, prefer the guide matching the manifest version.
5. If the matching guide is not local, start a subagent to get it. The subagent lookup order is:
   - download/read the guide packaged inside the dependency artifact;
   - inspect the dependency artifact/source and create a local guide;
   - use web search only when local/package sources fail and network access is available.
6. Do not decompile or guess in the main thread when a guide can be fetched by a subagent.

## Tool

When installed as the GuideWeaver plugin, call the MCP `start` tool.

Run the bundled script directly only when MCP tools are unavailable:

```bash
python ../guideweaver-build/scripts/update_guides.py start --repo <path>
```

`start` prints:

- the current project guide to read;
- the guide index to read;
- dependency guides already available locally;
- dependency guides missing locally and requiring subagent retrieval.
