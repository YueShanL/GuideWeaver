---
name: project-guide-synth
description: Build and refresh repository project guides from git-tracked files and dependency guides. Use when Codex needs to understand a codebase, update .codex/project-guides docs, inspect changed files since a git ref, reuse dependency-provided guides, or create a local dependency guide before resorting to decompilation or trial-and-error.
---

# Project Guide Synth

Use this skill in two modes:

- `build`: create or update guides.
- `start`: enter guide-aware editing mode before changing code.

## Workflow

### build

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

### start

Before each editing turn, decide whether the target change needs project or dependency context not already in conversation. If yes:

1. Read `.codex/project-guides/PROJECT_GUIDE.md` for the current repo.
2. Read `.codex/project-guides/index.json` to find version-aligned dependency guides.
3. For each dependency needed by the task, prefer the guide matching the manifest version.
4. If the matching guide is not local, start a subagent to get it. The subagent lookup order is:
   - download/read the guide packaged inside the dependency artifact;
   - inspect the dependency artifact/source and create a local guide;
   - use web search only when local/package sources fail and network access is available.
5. Do not decompile or guess in the main thread when a guide can be fetched by a subagent.

## Script

Run the bundled script when a deterministic refresh is enough:

```bash
python scripts/update_guides.py build --repo <path>
python scripts/update_guides.py build --repo <path> --since <git-ref>
python scripts/update_guides.py build --repo <path> --dependency <name-or-path>
python scripts/update_guides.py start --repo <path>
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

Package locations are ecosystem-specific. The script checks common local locations only:

- Java/JVM: jar contents, Maven local cache, Gradle module cache.
- Node: `node_modules/<package>`.
- Python: `.venv` `site-packages`.
- Rust: Cargo registry source cache.
- C/C++: `vcpkg_installed`, Conan 2 cache, and CMake FetchContent `_deps`.

If a dependency uses a different layout, pass it explicitly with `--dependency <path>`.

Do not add a decompiler dependency in v1. If bytecode signatures are not enough, write the limitation into the generated dependency guide and inspect only the source needed for the task.
