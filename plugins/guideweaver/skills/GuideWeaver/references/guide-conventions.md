# Guide Conventions

Generated guides live under `.codex/project-guides/` in the target repo.

Keep guides short and operational:

- Record where important code lives, not every file.
- Link dependency guides instead of copying them.
- Prefer public APIs and extension points over private implementation notes.
- Mark generated fallback dependency guides as incomplete when they come from bytecode only.
- Package `.codex/project-guides/GUIDE_INDEX.json` with libraries when possible; it points consumers to the main guide and repository remotes.

`GUIDE_INDEX.json` is the stable descriptor for other projects. `index.json` is script-owned and may be overwritten. `PROJECT_GUIDE.md` is safe to edit by hand, but keep the generated section markers so future refreshes can replace the summary.

There is no universal language package path. Keep the guide files at the same relative paths inside any source package, wheel, npm package, crate source, or jar when the ecosystem allows extra files.

Dependency guide filenames should include the resolved version when known: `name@version.md`. If a manifest version changes, treat the old guide as stale unless its `GUIDE_INDEX.json` says it covers the new version.
