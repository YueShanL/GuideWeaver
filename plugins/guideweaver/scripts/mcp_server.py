#!/usr/bin/env python3
"""Tiny stdio MCP server for GuideWeaver."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GUIDE_SCRIPT = ROOT / "skills" / "guideweaver-build" / "scripts" / "update_guides.py"


TOOLS = [
    {
        "name": "build",
        "description": "Build or refresh GuideWeaver project guides for a repository.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo": {"type": "string", "description": "Repository path."},
                "since": {"type": "string", "description": "Optional git ref to focus changed files."},
                "dependency": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional dependency names, source paths, or artifacts.",
                },
            },
            "required": ["repo"],
        },
    },
    {
        "name": "start",
        "description": "List project and dependency guides to read before editing.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo": {"type": "string", "description": "Repository path."},
                "dependency": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional dependency names, source paths, or artifacts.",
                },
            },
            "required": ["repo"],
        },
    },
]


def read_message() -> dict | None:
    headers: dict[str, str] = {}
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            return None
        line = line.decode("ascii", errors="ignore").strip()
        if not line:
            break
        key, _, value = line.partition(":")
        headers[key.lower()] = value.strip()
    length = int(headers.get("content-length", "0"))
    if length <= 0:
        return None
    return json.loads(sys.stdin.buffer.read(length).decode("utf-8"))


def write_message(message: dict) -> None:
    body = json.dumps(message, separators=(",", ":")).encode("utf-8")
    sys.stdout.buffer.write(f"Content-Length: {len(body)}\r\n\r\n".encode("ascii") + body)
    sys.stdout.buffer.flush()


def text_result(text: str) -> dict:
    return {"content": [{"type": "text", "text": text}]}


def run_guide(mode: str, args: dict) -> dict:
    cmd = [sys.executable, str(GUIDE_SCRIPT), mode, "--repo", args["repo"]]
    if mode == "build" and args.get("since"):
        cmd += ["--since", args["since"]]
    for dep in args.get("dependency") or []:
        cmd += ["--dependency", dep]
    p = subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    out = p.stdout.rstrip()
    if p.stderr.strip():
        out += ("\n\nstderr:\n" if out else "stderr:\n") + p.stderr.strip()
    if p.returncode:
        return {"content": [{"type": "text", "text": out or f"{mode} failed"}], "isError": True}
    return text_result(out)


def handle(message: dict) -> dict | None:
    method = message.get("method")
    msg_id = message.get("id")
    if msg_id is None:
        return None
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "guideweaver", "version": "0.1.1"},
            },
        }
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": TOOLS}}
    if method == "tools/call":
        params = message.get("params") or {}
        name = params.get("name")
        args = params.get("arguments") or {}
        if name in {"build", "start"}:
            return {"jsonrpc": "2.0", "id": msg_id, "result": run_guide(name, args)}
        return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32601, "message": f"Unknown tool: {name}"}}
    return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32601, "message": f"Unknown method: {method}"}}


def main() -> int:
    while True:
        message = read_message()
        if message is None:
            return 0
        response = handle(message)
        if response:
            write_message(response)


if __name__ == "__main__":
    raise SystemExit(main())
