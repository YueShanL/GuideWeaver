# GuideWeaver

![GuideWeaver icon](plugins/guideweaver/skills/guideweaver-build/assets/GuideWeaver-icon.png)

GuideWeaver is a Codex plugin and bundled skill for turning a project and its dependencies into compact, version-aligned guides. It has two modes:

- `build`: create or refresh guide files from the current git tree and dependency metadata.
- `start`: enter guide-aware editing mode by listing which project and dependency guides must be read before changing code.

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

### Install As A Codex Plugin

Add this repository as a Codex marketplace, then install the plugin:

```bash
codex plugin marketplace add /path/to/GuideWeaver
codex plugin add guideweaver@guideweaver
```

If your Codex CLI supports GitHub marketplace sources, use the repository URL instead of the local path:

```bash
codex plugin marketplace add https://github.com/YueShanL/GuideWeaver
codex plugin add guideweaver@guideweaver
```

The plugin includes:

- bundled skills: `guideweaver-build` and `guideweaver-start`;
- MCP server: `plugins/guideweaver/scripts/mcp_server.py`;
- MCP tools: `build` and `start`.

The marketplace and plugin manifest live at:

```text
.agents/plugins/marketplace.json
.claude-plugin/marketplace.json
plugins/guideweaver/.codex-plugin/plugin.json
plugins/guideweaver/.claude-plugin/plugin.json
```

After installing/reloading the plugin in Codex, use the MCP tools directly:

```text
Use GuideWeaver build for this repo.
Use GuideWeaver start before editing this repo.
```

### Install As A Claude Plugin Marketplace

Add this repository as a Claude plugin marketplace. Claude looks for this manifest:

```text
.claude-plugin/marketplace.json
```

Use the repository URL in Claude's plugin marketplace import flow:

```text
https://github.com/YueShanL/GuideWeaver
```

In Claude Code, the official marketplace command form is:

```text
/plugin marketplace add YueShanL/GuideWeaver
/plugin install guideweaver@guideweaver
```

If you are installing from a local checkout, point Claude at the repository root, not at `plugins/guideweaver/`.

The Claude marketplace manifest points at the same plugin body:

```text
plugins/guideweaver/
```

The plugin body includes Claude-specific metadata and MCP config:

```text
plugins/guideweaver/.claude-plugin/plugin.json
plugins/guideweaver/.claude-plugin/mcp.json
```

If Claude marketplace import is unavailable, configure the MCP server manually:

```json
{
  "mcpServers": {
    "guideweaver": {
      "command": "python",
      "args": ["/path/to/GuideWeaver/plugins/guideweaver/scripts/mcp_server.py"]
    }
  }
}
```

Then install the bundled skills for Claude Code if your Claude setup uses local skills:

```bash
mkdir -p ~/.claude/skills
cp -R /path/to/GuideWeaver/plugins/guideweaver/skills/guideweaver-build ~/.claude/skills/guideweaver-build
cp -R /path/to/GuideWeaver/plugins/guideweaver/skills/guideweaver-start ~/.claude/skills/guideweaver-start
```

On Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.claude\skills"
Copy-Item -Recurse -Force C:\path\to\GuideWeaver\plugins\guideweaver\skills\guideweaver-build "$env:USERPROFILE\.claude\skills\guideweaver-build"
Copy-Item -Recurse -Force C:\path\to\GuideWeaver\plugins\guideweaver\skills\guideweaver-start "$env:USERPROFILE\.claude\skills\guideweaver-start"
```

Restart Claude, then ask:

```text
Use GuideWeaver build for this repo.
Use GuideWeaver start before editing this repo.
```

### Use From This Repository

Run the script directly:

```bash
python plugins/guideweaver/skills/guideweaver-build/scripts/update_guides.py build --repo /path/to/repo
```

Any Python 3.10+ should work; the script uses only the Python standard library plus existing local tools such as `git`, `jar`, and `javap` when available.

### Install As A Standalone Codex Skill

Copy the folder to your Codex skills directory:

```text
plugins/guideweaver/skills/guideweaver-build/
plugins/guideweaver/skills/guideweaver-start/
```

Typical destination:

```text
%CODEX_HOME%\skills\guideweaver-build
%CODEX_HOME%\skills\guideweaver-start
```

Then invoke it in Codex:

```text
Use $guideweaver-build to refresh this repository's guides.
Use $guideweaver-start before editing this repository.
```

### Install For Claude

GuideWeaver is also usable as Claude skills because each skill folder contains a standard `SKILL.md`.

For Claude Code, copy the skill folder into Claude's user skills directory:

```bash
mkdir -p ~/.claude/skills
cp -R plugins/guideweaver/skills/guideweaver-build ~/.claude/skills/guideweaver-build
cp -R plugins/guideweaver/skills/guideweaver-start ~/.claude/skills/guideweaver-start
```

On Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.claude\skills"
Copy-Item -Recurse -Force plugins\guideweaver\skills\guideweaver-build "$env:USERPROFILE\.claude\skills\guideweaver-build"
Copy-Item -Recurse -Force plugins\guideweaver\skills\guideweaver-start "$env:USERPROFILE\.claude\skills\guideweaver-start"
```

Restart or reload Claude Code, then ask:

```text
Use $guideweaver-build to build this repository's guide.
Use $guideweaver-start before editing this repository.
```

For Claude web or team workspaces that support uploaded skills, upload separate zips for `plugins/guideweaver/skills/guideweaver-build/` and `plugins/guideweaver/skills/guideweaver-start/`, each with `SKILL.md` at the archive root.

## Build Mode

Build or update guides:

```bash
python plugins/guideweaver/skills/guideweaver-build/scripts/update_guides.py build --repo /path/to/repo
```

Focus on changes since a git ref:

```bash
python plugins/guideweaver/skills/guideweaver-build/scripts/update_guides.py build --repo /path/to/repo --since HEAD~1
```

Add an explicit dependency path or artifact:

```bash
python plugins/guideweaver/skills/guideweaver-build/scripts/update_guides.py build --repo /path/to/repo --dependency /path/to/dependency.jar
```

Compatibility shortcut:

```bash
python plugins/guideweaver/skills/guideweaver-build/scripts/update_guides.py --repo /path/to/repo
```

This behaves like `build`.

## Start Mode

Before editing a project, run:

```bash
python plugins/guideweaver/skills/guideweaver-build/scripts/update_guides.py start --repo /path/to/repo
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

```bash
python plugins/guideweaver/skills/guideweaver-build/scripts/update_guides.py build --repo /path/to/repo --dependency /path/to/dependency
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
.agents/plugins/marketplace.json
.claude-plugin/marketplace.json
README.md
plugins/guideweaver/
  .codex-plugin/plugin.json
  .claude-plugin/plugin.json
  .claude-plugin/mcp.json
  .mcp.json
  scripts/mcp_server.py
  skills/guideweaver-build/
    SKILL.md
    agents/openai.yaml
    assets/GuideWeaver-icon.png
    references/guide-conventions.md
    scripts/update_guides.py
  skills/guideweaver-start/
    SKILL.md
    agents/openai.yaml
    assets/GuideWeaver-icon.png
```
