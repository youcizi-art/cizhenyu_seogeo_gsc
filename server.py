#!/usr/bin/env python3
"""Google Search Console MCP 服务器 + CLI（零依赖，stdio JSON-RPC）。

MCP 挂载：
  command: <python.exe>
  args:    ["C:/scripts/seogeo-gsc/server.py"]
  cwd:     C:/scripts/seogeo-gsc

CLI：
  python server.py list
  python server.py gsc_sites
  python server.py gsc_top_queries --json "{\"site_url\":\"sc-domain:example.com\"}"

前置：ADC 需含 webmasters.readonly scope（403 时会提示重新授权命令）。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import gsc  # noqa: E402

SERVER_NAME = "seogeo-gsc"
SERVER_VERSION = "1.0.0"

_ROW = {"type": "integer", "default": 200}
_DAYS = {"type": "integer", "default": 28}

TOOLS = {
    "gsc_sites": {
        "fn": gsc.sites,
        "desc": "列出当前授权可访问的 Search Console 站点（含权限级别）。",
        "schema": {"type": "object", "properties": {}, "required": []},
    },
    "gsc_top_queries": {
        "fn": gsc.top_queries,
        "desc": "站点 Top 查询词（点击/展现/CTR/平均排名）。默认最近 28 天。",
        "schema": {"type": "object", "properties": {
            "site_url": {"type": "string"}, "days": _DAYS, "row_limit": _ROW},
            "required": ["site_url"]},
    },
    "gsc_top_pages": {
        "fn": gsc.top_pages,
        "desc": "站点 Top 页面（点击/展现/CTR/平均排名）。",
        "schema": {"type": "object", "properties": {
            "site_url": {"type": "string"}, "days": _DAYS, "row_limit": _ROW},
            "required": ["site_url"]},
    },
    "gsc_query": {
        "fn": gsc.query,
        "desc": "通用 Search Analytics 查询：自定义维度（query/page/country/device）、日期区间、页面或查询过滤。",
        "schema": {"type": "object", "properties": {
            "site_url": {"type": "string"},
            "start_date": {"type": "string", "description": "YYYY-MM-DD，留空取默认区间"},
            "end_date": {"type": "string"},
            "dimensions": {"type": "array", "items": {"type": "string"}},
            "row_limit": _ROW,
            "page_url": {"type": "string"},
            "query_contains": {"type": "string"},
            "device": {"type": "string", "enum": ["", "DESKTOP", "MOBILE", "TABLET"]}},
            "required": ["site_url"]},
    },
    "gsc_page_queries": {
        "fn": gsc.page_queries,
        "desc": "某个页面的查询词明细（用于页面级关键词与 cannibalization 排查）。",
        "schema": {"type": "object", "properties": {
            "site_url": {"type": "string"}, "page_url": {"type": "string"},
            "days": {"type": "integer", "default": 90}, "row_limit": _ROW},
            "required": ["site_url", "page_url"]},
    },
    "gsc_breakdown": {
        "fn": gsc.country_device_breakdown,
        "desc": "按国家与设备拆分的表现（判断目标市场真实流量来源）。",
        "schema": {"type": "object", "properties": {
            "site_url": {"type": "string"}, "days": _DAYS},
            "required": ["site_url"]},
    },
    "gsc_sitemaps": {
        "fn": gsc.sitemaps,
        "desc": "站点已提交的 sitemap 与错误/警告数（上线验收与收录诊断用）。",
        "schema": {"type": "object", "properties": {"site_url": {"type": "string"}},
                   "required": ["site_url"]},
    },
}


def call_tool(name: str, args: dict) -> dict:
    spec = TOOLS.get(name)
    if not spec:
        return {"ok": False, "error": f"unknown tool: {name}"}
    try:
        return {"ok": True, "tool": name, "result": spec["fn"](**args)}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "tool": name, "error": f"{type(exc).__name__}: {exc}"}


def _reply(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def serve() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        method, msg_id, params = msg.get("method"), msg.get("id"), (msg.get("params") or {})
        if method == "initialize":
            _reply({"jsonrpc": "2.0", "id": msg_id, "result": {
                "protocolVersion": params.get("protocolVersion", "2025-06-18"),
                "capabilities": {"tools": {}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION}}})
        elif method in ("notifications/initialized", "initialized"):
            continue
        elif method == "tools/list":
            _reply({"jsonrpc": "2.0", "id": msg_id, "result": {"tools": [
                {"name": n, "description": s["desc"], "inputSchema": s["schema"]}
                for n, s in TOOLS.items()]}})
        elif method == "tools/call":
            result = call_tool(params.get("name", ""), params.get("arguments") or {})
            _reply({"jsonrpc": "2.0", "id": msg_id, "result": {
                "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}})
        elif method == "ping":
            _reply({"jsonrpc": "2.0", "id": msg_id, "result": {}})
        elif msg_id is not None:
            _reply({"jsonrpc": "2.0", "id": msg_id,
                    "error": {"code": -32601, "message": f"method not found: {method}"}})


def cli(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    if argv[0] == "list":
        for name, spec in TOOLS.items():
            print(f"{name:22} {spec['desc']}")
        return 0
    args = {}
    if "--args-file" in argv:
        args = json.loads(Path(argv[argv.index("--args-file") + 1]).read_text(encoding="utf-8-sig"))
    elif "--json" in argv:
        args = json.loads(argv[argv.index("--json") + 1])
    print(json.dumps(call_tool(argv[0], args), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1:
        raise SystemExit(cli(sys.argv[1:]))
    serve()
