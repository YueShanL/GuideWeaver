---
name: guideweaver-build
description: Build or refresh GuideWeaver project guides from git-tracked files, manifests, repository remotes, packaged dependency guides, and local dependency artifacts. Use when Codex needs to generate or update .codex/project-guides/PROJECT_GUIDE.md, GUIDE_INDEX.json, index.json, or version-aligned dependency guides before development work.
---

# GuideWeaver Build

Use this entry only to create or refresh guides. For guide-aware editing before code changes, use `guideweaver-start` instead.

## Workflow

1. Inspect the repo with git first:
   - Use `git -c safe.directory=<repo> -C <repo> ls-files`.
   - For focused updates, use `git -c safe.directory=<repo> -C <repo> diff --name-only <ref>`.
   - If the repo has no commits or git fails, fall back to a filesystem scan excluding `.git`, build outputs, and `.codex/project-guides`.
2. Prefer existing guides before reading implementation:
   - Project guide: `.codex/project-guides/PROJECT_GUIDE.md`.
   - Packaged guide index: `.codex/project-guides/GUIDE_INDEX.json`.
   - Dependency guides: dependency `GUIDE.md`, `SKILL.md`, or `.codex/project-guides/*.md`.
   - Local generated dependency guides: `.codex/project-guides/dependencies/*.md`.
3. Update only sections affected by changed files. Do not rewrite unrelated guide content unless it is stale.
4. Generate a local dependency guide only when no dependency-provided guide exists.

## Tool

When installed as the GuideWeaver plugin, call the MCP `build` tool.

Run the bundled script directly only when MCP tools are unavailable:

```bash
python scripts/update_guides.py build --repo <path>
python scripts/update_guides.py build --repo <path> --since <git-ref>
python scripts/update_guides.py build --repo <path> --dependency <name-or-path>
```

For compatibility, `python scripts/update_guides.py --repo <path>` behaves like `build`.

The script writes:

- `.codex/project-guides/PROJECT_GUIDE.md`
- `.codex/project-guides/GUIDE_INDEX.json`
- `.codex/project-guides/index.json`
- `.codex/project-guides/dependencies/<dependency-name>.md`

Versioned dependency guides use `<dependency-name>@<version>.md` when the manifest exposes a version.

Read `references/guide-conventions.md` before changing the guide format.

## Dependency Fallback

Use the smallest available source of truth:

1. Dependency-owned guide files.
2. Source jar or checked-out dependency source.
3. Guide files packaged inside a jar.
4. Jar/class public signatures with JDK tools when available.

`GUIDE_INDEX.json` records the dependency project's git remotes from `git remote -v`. If the local artifact only carries the remote URL and not the guide content, use that URL to fetch or inspect the upstream guide only when network access is explicitly available.

Do not add a decompiler dependency in v1. If bytecode signatures are not enough, write the limitation into the generated dependency guide and inspect only the source needed for the task.
