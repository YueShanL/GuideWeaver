# GuideWeaver

![GuideWeaver icon](assets/guideweaver-icon.png)

GuideWeaver is a Codex skill for turning a project and its dependencies into compact, version-aligned guides. It has two modes:

- `build`: create or refresh guide files from the current git tree and dependency metadata.
- `start`: enter guide-aware editing mode by listing which project and dependency guides must be read before changing code.

The skill id remains `project-guide-synth` so it can be invoked as `$project-guide-synth`.

## What It Creates

GuideWeaver writes guide files into the target project:

```text
.codex/project-guides/
  PROJECT_GUIDE.md
  GUIDE_INDEX.json
  index.json
  dependencies/
    <dependency-name>@<version>.md
```

- `PROJECT_GUIDE.md`: human-readable summary of the current project.
- `GUIDE_INDEX.json`: stable descriptor intended to be packaged with libraries.
- `index.json`: script-owned index with file hashes, manifests, remotes, dependency guides, and missing guide entries.
- `dependencies/*.md`: local copies or generated fallback guides for dependencies.

## Install

### Use From This Repository

Run the script directly:

```powershell
C:\Users\User\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe C:\Users\User\Documents\skiller\project-guide-synth\scripts\update_guides.py build --repo C:\path\to\repo
```

Any Python 3.10+ should work; the script uses only the Python standard library plus existing local tools such as `git`, `jar`, and `javap` when available.

### Install As A Codex Skill

Copy the folder to your Codex skills directory:

```text
project-guide-synth/
```

Typical destination:

```text
%CODEX_HOME%\skills\project-guide-synth
```

Then invoke it in Codex:

```text
Use $project-guide-synth to refresh this repository's project guide from the git tree and dependency guides.
```

## Build Mode

Build or update guides:

```powershell
python project-guide-synth\scripts\update_guides.py build --repo C:\path\to\repo
```

Focus on changes since a git ref:

```powershell
python project-guide-synth\scripts\update_guides.py build --repo C:\path\to\repo --since HEAD~1
```

Add an explicit dependency path or artifact:

```powershell
python project-guide-synth\scripts\update_guides.py build --repo C:\path\to\repo --dependency C:\path\to\dependency.jar
```

Compatibility shortcut:

```powershell
python project-guide-synth\scripts\update_guides.py --repo C:\path\to\repo
```

This behaves like `build`.

## Start Mode

Before editing a project, run:

```powershell
python project-guide-synth\scripts\update_guides.py start --repo C:\path\to\repo
```

`start` does not write files. It prints:

- the current project guide to read;
- the guide index to read;
- dependency guides that are already available locally;
- dependency guides that are missing and must be fetched by a subagent.

Expected workflow:

1. Read the current project guide if the task needs project context.
2. Read matching dependency guides by version.
3. For any missing dependency guide, open a subagent instead of guessing in the main thread.
4. Only fall back to artifact inspection, decompilation, or web search after local guide lookup fails.

## Dependency Lookup Order

GuideWeaver uses this order:

1. Existing local dependency guide matching the manifest version.
2. Guide packaged inside the dependency artifact.
3. Dependency source or artifact inspection.
4. Web search, only when network is available and local/package sources fail.

Non-local retrieval should be done by a subagent so the main coding thread stays focused.

## Version Alignment

When a manifest exposes a version, dependency guide filenames include it:

```text
left-pad@1.2.3.md
serde@1.md
org.example-lib@2.4.0.md
```

If a dependency version changes, treat the old guide as stale unless the dependency's own `GUIDE_INDEX.json` says it covers the new version.

## Supported Ecosystems

GuideWeaver has a shared guide protocol across languages:

```text
GUIDE.md
SKILL.md
.codex/project-guides/GUIDE_INDEX.json
.codex/project-guides/PROJECT_GUIDE.md
```

It also checks common local package locations:

- Java/JVM: jar contents, Maven local cache, Gradle module cache.
- Node: `node_modules/<package>`.
- Python: `.venv` `site-packages`.
- Rust: Cargo registry source cache.
- C/C++: `vcpkg_installed`, Conan 2 cache, and CMake FetchContent `_deps`.

If a dependency uses a custom layout, pass it explicitly:

```powershell
python project-guide-synth\scripts\update_guides.py build --repo C:\path\to\repo --dependency C:\path\to\dependency
```

## Packaging Guides With Libraries

For libraries that want downstream projects to discover their guide, package these files when possible:

```text
.codex/project-guides/GUIDE_INDEX.json
.codex/project-guides/PROJECT_GUIDE.md
```

`GUIDE_INDEX.json` records:

- schema name;
- git remotes inferred from `git remote -v`;
- main project guide path;
- dependency guide paths;
- missing dependency guide entries.

If an artifact contains only `GUIDE_INDEX.json`, GuideWeaver can still tell a subagent which repository remote and guide path to inspect.

## Fallback Behavior

When no guide is available:

- local source directories produce a small public-surface summary;
- jars produce public class/signature summaries when possible;
- missing dependencies are marked with `needs_subagent`;
- no new decompiler dependency is installed by default.

## Files In This Skill

```text
project-guide-synth/
  SKILL.md
  README.md
  agents/openai.yaml
  assets/guideweaver-icon.png
  references/guide-conventions.md
  scripts/update_guides.py
```

## Name And Image

Recommended display name: **GuideWeaver**.

Reason: it describes the tool's job without overpromising. It weaves repository structure, dependency metadata, packaged guides, and fallback summaries into one guide layer for Codex.

Icon prompt used:

```text
Create a clean square app icon for a developer tool named GuideWeaver. Main subject: a friendly focused octopus at a developer desk, using several tentacles to arrange files, type in a command-line terminal, and hold a branching git tree diagram. Modern flat/vector-like raster illustration, crisp edges, professional developer tooling aesthetic, balanced composition, no text, no logos, no watermark. Use deep charcoal, teal, warm yellow, white, and a small coral accent. Centered subject on a plain light background with generous padding, suitable as a README and marketplace icon.
```
