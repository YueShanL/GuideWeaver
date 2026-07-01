#!/usr/bin/env python3
"""Refresh .codex/project-guides from a repository git tree."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path


SKIP_DIRS = {".git", ".gradle", ".idea", ".codex/project-guides", "build", "dist", "node_modules", "target", "__pycache__"}
GUIDE_SKIP_DIRS = SKIP_DIRS - {".codex/project-guides", "node_modules", "target"}
MANIFESTS = {
    "build.gradle",
    "build.gradle.kts",
    "settings.gradle",
    "settings.gradle.kts",
    "pom.xml",
    "package.json",
    "pyproject.toml",
    "Cargo.toml",
    "CMakeLists.txt",
    "vcpkg.json",
    "conanfile.py",
    "conanfile.txt",
}
GUIDE_NAMES = {"GUIDE.md", "SKILL.md"}
JAR_GUIDE_RE = re.compile(r"(^|/)(GUIDE|SKILL)\.md$|(^|/)\.codex/project-guides/.+\.md$")
JAR_INDEX_RE = re.compile(r"(^|/)\.codex/project-guides/GUIDE_INDEX\.json$")


def run(cmd: list[str], cwd: Path | None = None) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False)
        return p.returncode, p.stdout
    except OSError:
        return 127, ""


def git(repo: Path, *args: str) -> tuple[int, str]:
    return run(["git", "-c", f"safe.directory={repo}", "-C", str(repo), *args])


def rel_files(repo: Path) -> list[str]:
    code, out = git(repo, "ls-files")
    files = [x.strip().replace("\\", "/") for x in out.splitlines() if x.strip()]
    if code == 0 and files:
        return files
    found: list[str] = []
    for path in repo.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(repo).as_posix()
        if any(rel == d or rel.startswith(d + "/") for d in SKIP_DIRS):
            continue
        found.append(rel)
    return sorted(found)


def changed_files(repo: Path, since: str | None, all_files: list[str]) -> list[str]:
    if not since:
        return all_files
    code, out = git(repo, "diff", "--name-only", since)
    files = [x.strip().replace("\\", "/") for x in out.splitlines() if x.strip()]
    return files if code == 0 and files else all_files


def remote_urls(repo: Path) -> list[str]:
    code, out = git(repo, "remote", "-v")
    if code != 0:
        return []
    urls = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1] not in urls:
            urls.append(parts[1])
    return urls


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def toml_section(text: str, name: str) -> str:
    match = re.search(rf"(?ms)^\[{re.escape(name)}]\s*(.*?)(?=^\[|\Z)", text)
    return match.group(1) if match else ""


def find_guides(root: Path) -> list[Path]:
    guides: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if any(rel == d or rel.startswith(d + "/") for d in GUIDE_SKIP_DIRS):
            continue
        if path.name in GUIDE_NAMES or re.fullmatch(r"\.codex/project-guides/.+\.md", rel):
            guides.append(path)
    return sorted(guides)


def dependency_name(dep: str) -> str:
    dep, _version = split_dep(dep)
    name = dep.replace("/", "-") if dep.startswith("@") else Path(dep).stem if any(sep in dep for sep in ("/", "\\")) else dep
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", name).strip("-") or "dependency"


def split_dep(dep: str) -> tuple[str, str | None]:
    if Path(dep).exists():
        return dep, None
    if dep.startswith("@"):
        pos = dep.rfind("@")
        return (dep[:pos], dep[pos + 1 :]) if pos > 0 else (dep, None)
    return tuple(dep.rsplit("@", 1)) if "@" in dep else (dep, None)


def dependency_slug(dep: str) -> str:
    name, version = split_dep(dep)
    slug = dependency_name(name)
    if version:
        slug += "@" + re.sub(r"[^A-Za-z0-9_.+-]+", "-", version).strip("-")
    return slug


def parse_dependencies(repo: Path, manifests: list[str]) -> list[str]:
    deps: set[str] = set()
    for rel in manifests:
        text = (repo / rel).read_text(encoding="utf-8", errors="ignore")
        if rel.endswith("package.json"):
            data = json.loads(text)
            for key in ("dependencies", "devDependencies", "peerDependencies"):
                deps.update(f"{name}@{version}" for name, version in data.get(key, {}).items())
        elif rel.endswith("pyproject.toml"):
            deps.update(re.findall(r'["\']([A-Za-z0-9_.-]+)(?:\[[^]]+\])?[<>=~! ;"\']', text))
        elif rel.endswith("pom.xml"):
            for block in re.findall(r"(?s)<dependency>(.*?)</dependency>", text):
                group = re.search(r"<groupId>([^<]+)</groupId>", block)
                artifact = re.search(r"<artifactId>([^<]+)</artifactId>", block)
                version = re.search(r"<version>([^<]+)</version>", block)
                if artifact:
                    name = f"{group.group(1)}:{artifact.group(1)}" if group else artifact.group(1)
                    deps.add(f"{name}@{version.group(1)}" if version else name)
        elif "gradle" in rel:
            deps.update(f"{g}:{a}@{v}" for g, a, v in re.findall(r"['\"]([A-Za-z0-9_.-]+):([A-Za-z0-9_.-]+):([^'\"]+)['\"]", text))
        elif rel.endswith("Cargo.toml"):
            for section in ("dependencies", "dev-dependencies", "build-dependencies"):
                deps.update(f"{name}@{version}" for name, version in re.findall(r"(?m)^([A-Za-z0-9_-]+)\s*=\s*['\"]([^'\"]+)['\"]", toml_section(text, section)))
                deps.update(re.findall(r"(?m)^([A-Za-z0-9_-]+)\s*=\s*\{", toml_section(text, section)))
        elif rel.endswith("vcpkg.json"):
            data = json.loads(text)
            for dep in data.get("dependencies", []):
                deps.add(dep if isinstance(dep, str) else dep.get("name", ""))
        elif rel.endswith("conanfile.txt") or rel.endswith("conanfile.py"):
            deps.update(f"{name}@{version}" for name, version in re.findall(r"([A-Za-z0-9_.+-]+)/([A-Za-z0-9_.+-]+)", text))
        elif rel.endswith("CMakeLists.txt"):
            deps.update(re.findall(r"FetchContent_Declare\s*\(\s*([A-Za-z0-9_.+-]+)", text, re.I))
    return sorted(d for d in deps if d)


def resolve_dependency_path(repo: Path, dep: str) -> Path | None:
    dep, version = split_dep(dep)
    dep_path = Path(dep)
    if dep_path.exists():
        return dep_path

    candidates = [
        repo / "node_modules" / dep,
        repo / ".venv" / "Lib" / "site-packages" / dep.replace("-", "_"),
        repo / ".venv" / "lib" / "python3" / "site-packages" / dep.replace("-", "_"),
        repo / "target" / "package" / dep,
        repo / "vcpkg_installed" / dep,
        repo / "build" / "_deps" / f"{dep}-src",
        repo / "_deps" / f"{dep}-src",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate

    home = Path.home()
    scoped = dep.replace(":", "/")
    if ":" in dep:
        for root in (home / ".m2" / "repository" / scoped, home / ".gradle" / "caches" / "modules-2" / "files-2.1" / scoped):
            if root.exists():
                pattern = f"**/*{version}*.jar" if version else "**/*.jar"
                jars = sorted(root.glob(pattern))
                if jars:
                    return jars[-1]

    external_roots = [home / ".cargo" / "registry" / "src", home / ".conan2" / "p"]
    for root in external_roots:
        if not root.exists():
            continue
        pattern = f"**/{dep}-{version}*" if version and root.name == "src" else f"**/{dep}-*" if root.name == "src" else "**/*"
        matches = sorted(root.glob(pattern))
        for match in matches[:200]:
            if match.exists() and dependency_name(match.name).startswith(dependency_name(dep)):
                return match
    return None


def inspect_dependency(repo: Path, dep: str) -> dict:
    dep_ref, version = split_dep(dep)
    name = dependency_name(dep_ref)
    out = repo / ".codex" / "project-guides" / "dependencies" / f"{dependency_slug(dep)}.md"
    if out.exists():
        return {"name": name, "version": version, "path": out.relative_to(repo).as_posix(), "source": "local-project-guide"}

    dep_path = resolve_dependency_path(repo, dep)
    if dep_path and dep_path.exists():
        if dep_path.is_file() and dep_path.suffix == ".jar":
            jar_guide = read_jar_guide(dep_path)
            if jar_guide:
                return {"name": name, "version": version, "path": jar_guide["source"], "source": "packaged-guide"}
        guides = find_guides(dep_path if dep_path.is_dir() else dep_path.parent)
        if guides:
            return {"name": name, "version": version, "path": str(guides[0]), "source": "dependency-guide"}
        return {"name": name, "version": version, "path": str(dep_path), "source": "local-artifact", "needs_subagent": True}

    return {"name": name, "version": version, "path": out.relative_to(repo).as_posix(), "source": "missing", "needs_subagent": True}


def copy_or_generate_dependency(repo: Path, dep: str) -> dict:
    out_dir = repo / ".codex" / "project-guides" / "dependencies"
    out_dir.mkdir(parents=True, exist_ok=True)
    dep_ref, version = split_dep(dep)
    name = dependency_name(dep_ref)
    out = out_dir / f"{dependency_slug(dep)}.md"
    dep_path = resolve_dependency_path(repo, dep)

    if out.exists():
        return {"name": name, "version": version, "path": out.relative_to(repo).as_posix(), "source": "local-project-guide"}

    if dep_path and dep_path.exists():
        if dep_path.is_file() and dep_path.suffix == ".jar":
            jar_guide = read_jar_guide(dep_path)
            if jar_guide:
                out.write_text(jar_guide["text"], encoding="utf-8")
                return {"name": name, "version": version, "path": out.relative_to(repo).as_posix(), "source": jar_guide["source"]}
        root = dep_path if dep_path.is_dir() else dep_path.parent
        guides = find_guides(root)
        if guides:
            src = guides[0]
            out.write_text(src.read_text(encoding="utf-8", errors="ignore"), encoding="utf-8")
            return {"name": name, "version": version, "path": out.relative_to(repo).as_posix(), "source": str(src)}
        out.write_text(render_dependency_fallback(name, dep_path), encoding="utf-8")
        return {"name": name, "version": version, "path": out.relative_to(repo).as_posix(), "source": str(dep_path), "fallback": "local-artifact"}

    return {"name": name, "version": version, "path": out.relative_to(repo).as_posix(), "source": "missing", "needs_subagent": True}


def read_jar_guide(path: Path) -> dict | None:
    if not zipfile.is_zipfile(path):
        return None
    with zipfile.ZipFile(path) as zf:
        names = sorted(n for n in zf.namelist() if JAR_GUIDE_RE.search(n))
        if names:
            source = names[0]
            return {"source": f"{path}!/{source}", "text": zf.read(source).decode("utf-8", errors="ignore")}
        indexes = sorted(n for n in zf.namelist() if JAR_INDEX_RE.search(n))
        if indexes:
            source = indexes[0]
            return {"source": f"{path}!/{source}", "text": render_index_hint(path.stem, zf.read(source).decode("utf-8", errors="ignore"))}
    return None


def render_index_hint(name: str, text: str) -> str:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = {}
    remotes = data.get("repository_remotes") or []
    guide = data.get("project_guide") or ".codex/project-guides/PROJECT_GUIDE.md"
    lines = [f"# {name} Guide", "", "Packaged guide index found, but the package did not include the markdown guide.", "", f"- Guide path: `{guide}`"]
    lines += [f"- Repository remote: `{url}`" for url in remotes] or ["- Repository remote: none recorded"]
    return "\n".join(lines) + "\n"


def render_dependency_fallback(name: str, path: Path) -> str:
    lines = [f"# {name} Guide", "", "Generated fallback guide. Prefer an upstream GUIDE.md/SKILL.md when available.", ""]
    if path.exists() and path.is_dir():
        sources = sorted(p for p in path.rglob("*") if p.suffix in {".c", ".cc", ".cpp", ".h", ".hpp", ".java", ".kt", ".py", ".rs", ".ts", ".js"})
        lines += ["## Public Surface", ""]
        for src in sources[:80]:
            text = src.read_text(encoding="utf-8", errors="ignore")
            for m in re.finditer(r"\b(public\s+)?(class|interface|enum|struct|trait|fn|fun|def|function)\s+([A-Za-z_][A-Za-z0-9_]*)", text):
                lines.append(f"- `{m.group(3)}` in `{src.name}`")
    elif path.exists() and path.suffix == ".jar":
        lines += jar_summary(path)
    else:
        lines += ["## Status", "", "- No local guide or artifact was found for this dependency."]
    return "\n".join(lines).rstrip() + "\n"


def jar_summary(path: Path) -> list[str]:
    lines = ["## Public Surface", ""]
    if not zipfile.is_zipfile(path):
        return lines + ["- Artifact is not a readable jar."]
    with zipfile.ZipFile(path) as zf:
        classes = sorted(n[:-6].replace("/", ".") for n in zf.namelist() if n.endswith(".class") and "$" not in n)
    for cls in classes[:120]:
        lines.append(f"- `{cls}`")
    if shutil.which("javap") and classes:
        lines += ["", "## Sample Signatures", ""]
        for cls in classes[:20]:
            code, out = run(["javap", "-classpath", str(path), "-public", cls])
            if code == 0:
                sigs = [x.strip() for x in out.splitlines() if x.strip().startswith("public ")]
                lines.extend(f"- `{x}`" for x in sigs[:8])
    return lines


def render_project_guide(repo: Path, files: list[str], changed: list[str], manifests: list[str], deps: list[dict], remotes: list[str]) -> str:
    exts: dict[str, int] = {}
    for rel in files:
        ext = Path(rel).suffix or "(none)"
        exts[ext] = exts.get(ext, 0) + 1
    roots = sorted({f.split("/", 1)[0] for f in files if "/" in f})[:40]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    lines = [
        "# Project Guide",
        "",
        f"Generated: {now}",
        "",
        "<!-- guideweaver:start -->",
        "",
        "## Repo Shape",
        "",
        f"- Files indexed: {len(files)}",
        f"- Files changed in this refresh: {len(changed)}",
        f"- Git remotes: {', '.join(remotes) if remotes else 'none detected'}",
        f"- Manifests: {', '.join(manifests) if manifests else 'none detected'}",
        f"- Top-level source roots: {', '.join(roots) if roots else 'none detected'}",
        "",
        "## File Types",
        "",
    ]
    lines += [f"- `{k}`: {v}" for k, v in sorted(exts.items(), key=lambda x: (-x[1], x[0]))[:30]]
    lines += ["", "## Changed Files", ""]
    lines += [f"- `{x}`" for x in changed[:80]] or ["- none"]
    lines += ["", "## Dependency Guides", ""]
    lines += [f"- `{d['name']}`{('@' + d['version']) if d.get('version') else ''}: `{d['path']}`" for d in deps] or ["- none"]
    lines += ["", "<!-- guideweaver:end -->", ""]
    return "\n".join(lines)


def print_start(repo: Path, deps: list[dict]) -> None:
    guide_dir = repo / ".codex" / "project-guides"
    project_guide = guide_dir / "PROJECT_GUIDE.md"
    index = guide_dir / "index.json"
    print("# GuideWeaver start")
    print()
    if project_guide.exists():
        print(f"- Read current project guide: `{project_guide}`")
    else:
        print("- Current project guide missing: run `build` before editing if project context matters.")
    if index.exists():
        print(f"- Read guide index: `{index}`")
    print()
    print("## Dependency guides")
    for dep in deps:
        label = f"{dep['name']}@{dep['version']}" if dep.get("version") else dep["name"]
        if dep.get("needs_subagent"):
            print(f"- `{label}`: missing local guide; open a subagent to fetch packaged guide, then fallback to artifact inspection or web search.")
        else:
            print(f"- `{label}`: read `{dep['path']}`")


def main(argv: list[str]) -> int:
    mode = "build"
    if argv and argv[0] in {"build", "start"}:
        mode = argv.pop(0)
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--since")
    ap.add_argument("--dependency", action="append", default=[])
    args = ap.parse_args(argv)

    repo = Path(args.repo).resolve()

    files = rel_files(repo)
    changed = changed_files(repo, args.since, files)
    manifests = sorted(f for f in files if Path(f).name in MANIFESTS)
    remotes = remote_urls(repo)
    dep_inputs = sorted(set(parse_dependencies(repo, manifests) + list(args.dependency)))
    if mode == "start":
        print_start(repo, [inspect_dependency(repo, dep) for dep in dep_inputs])
        return 0

    guide_dir = repo / ".codex" / "project-guides"
    guide_dir.mkdir(parents=True, exist_ok=True)
    deps = [copy_or_generate_dependency(repo, dep) for dep in dep_inputs]

    guide_index = {
        "schema": "guideweaver.v1",
        "repository_remotes": remotes,
        "project_guide": ".codex/project-guides/PROJECT_GUIDE.md",
        "dependency_guides": [d["path"] for d in deps],
        "missing_dependency_guides": [d for d in deps if d.get("needs_subagent")],
    }
    index = {
        "repo": str(repo),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "repository_remotes": remotes,
        "files": {rel: sha256(repo / rel) for rel in files if (repo / rel).is_file()},
        "manifests": manifests,
        "dependency_guides": deps,
    }
    (guide_dir / "GUIDE_INDEX.json").write_text(json.dumps(guide_index, indent=2, sort_keys=True), encoding="utf-8")
    (guide_dir / "index.json").write_text(json.dumps(index, indent=2, sort_keys=True), encoding="utf-8")
    (guide_dir / "PROJECT_GUIDE.md").write_text(render_project_guide(repo, files, changed, manifests, deps, remotes), encoding="utf-8")
    print(f"updated {guide_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
