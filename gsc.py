"""Google Search Console 客户端（零依赖，OAuth via ADC）。

凭据（由磁帧鱼 Deploy 统一管理，禁止写进代码）：
  1. CIZHENYU_AUTH_DIR / SEOGEO_AUTH_DIR 下 google/gsc.json、google/gsc_adc.json、gsc_adc.json
  2. 环境变量 GOOGLE_APPLICATION_CREDENTIALS（仅由 Deploy 注入进程 env）
  3. 最后回退 %APPDATA%\\gcloud\\application_default_credentials.json
"""

from __future__ import annotations

import datetime as dt
import json
import os
import ssl
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import cizhenyu_auth

API = "https://searchconsole.googleapis.com"
TOKEN_URL = "https://oauth2.googleapis.com/token"
ADC_FALLBACK = Path(os.environ.get("APPDATA", "")) / "gcloud" / "application_default_credentials.json"

_cache = {"token": None, "exp": 0}


class GscError(RuntimeError):
    pass


def adc_path() -> Path:
    env_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    if env_path and Path(env_path).is_file():
        return Path(env_path)

    try:
        base = cizhenyu_auth.auth_dir()
    except cizhenyu_auth.AuthError as exc:
        if ADC_FALLBACK.is_file():
            return ADC_FALLBACK
        raise GscError(str(exc)) from exc

    for rel in ("google/gsc_adc.json", "gsc_adc.json"):
        candidate = base / rel
        if candidate.is_file():
            return candidate

    meta = base / "google" / "gsc.json"
    if meta.is_file():
        try:
            data = json.loads(meta.read_text(encoding="utf-8-sig"))
            pointed = cizhenyu_auth.first_str(data, "credentialsPath", "credentials_path", "path")
            if pointed and Path(pointed).is_file():
                return Path(pointed)
        except (OSError, ValueError, TypeError):
            pass

    if ADC_FALLBACK.is_file():
        return ADC_FALLBACK
    raise GscError(
        f"找不到 GSC ADC。请在 Deploy 凭证中配置 gsc.credentialsPath，"
        f"或将 ADC 放到 {base / 'google' / 'gsc_adc.json'}"
    )


def access_token() -> str:
    import time
    if _cache["token"] and _cache["exp"] > time.time() + 60:
        return _cache["token"]
    path = adc_path()
    if not path.exists():
        raise GscError(f"找不到 ADC：{path}")
    adc = json.loads(path.read_text(encoding="utf-8-sig"))
    if adc.get("type") != "authorized_user" or not adc.get("refresh_token"):
        raise GscError("ADC 不是 authorized_user 类型，或缺少 refresh_token")
    payload = urllib.parse.urlencode({
        "client_id": adc["client_id"], "client_secret": adc["client_secret"],
        "refresh_token": adc["refresh_token"], "grant_type": "refresh_token",
    }).encode()
    req = urllib.request.Request(TOKEN_URL, data=payload,
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=30, context=ssl.create_default_context()) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:200]
        raise GscError(f"刷新令牌失败 HTTP {exc.code}: {detail}") from exc
    _cache["token"] = data["access_token"]
    _cache["exp"] = time.time() + int(data.get("expires_in", 3600))
    return _cache["token"]


def _request(method: str, path: str, body: dict | None = None, timeout: int = 60) -> dict:
    url = f"{API}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"Bearer {access_token()}",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ssl.create_default_context()) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:300]
        if exc.code == 403 and "insufficient" in detail.lower():
            raise GscError(
                "403 insufficient scope：当前 ADC 没有 webmasters.readonly 权限。"
                "请用 scripts/google_ads_auth.py --scope https://www.googleapis.com/auth/webmasters.readonly 重新授权"
            ) from exc
        raise GscError(f"HTTP {exc.code}: {detail}") from exc


def _enc(site_url: str) -> str:
    return urllib.parse.quote(site_url, safe="")


def sites() -> dict:
    data = _request("GET", "/webmasters/v3/sites")
    return {"sites": [{"site": s.get("siteUrl"), "level": s.get("permissionLevel")}
                      for s in data.get("siteEntry", [])]}


def date_range(days: int = 28, lag: int = 3) -> tuple[str, str]:
    end = dt.date.today() - dt.timedelta(days=lag)
    start = end - dt.timedelta(days=days - 1)
    return start.isoformat(), end.isoformat()


def query(site_url: str, start_date: str = "", end_date: str = "",
          dimensions: list[str] | None = None, row_limit: int = 500,
          page_url: str = "", query_contains: str = "", device: str = "") -> dict:
    if not start_date or not end_date:
        start_date, end_date = date_range()
    body = {
        "startDate": start_date, "endDate": end_date,
        "dimensions": dimensions or ["query"],
        "rowLimit": min(row_limit, 25000),
        "dataState": "final",
    }
    filters = []
    if page_url:
        filters.append({"dimension": "page", "operator": "equals", "expression": page_url})
    if query_contains:
        filters.append({"dimension": "query", "operator": "contains", "expression": query_contains})
    if device:
        filters.append({"dimension": "device", "operator": "equals", "expression": device})
    if filters:
        body["dimensionFilterGroups"] = [{"filters": filters}]
    data = _request("POST", f"/webmasters/v3/sites/{_enc(site_url)}/searchAnalytics/query", body)
    rows = [{
        "keys": r.get("keys"),
        "clicks": r.get("clicks"), "impressions": r.get("impressions"),
        "ctr": round((r.get("ctr") or 0) * 100, 2), "position": round(r.get("position") or 0, 1),
    } for r in data.get("rows", [])]
    return {"site": site_url, "start": start_date, "end": end_date,
            "dimensions": body["dimensions"], "rows": rows, "row_count": len(rows)}


def top_queries(site_url: str, days: int = 28, row_limit: int = 200) -> dict:
    start, end = date_range(days)
    return query(site_url, start, end, ["query"], row_limit)


def top_pages(site_url: str, days: int = 28, row_limit: int = 200) -> dict:
    start, end = date_range(days)
    return query(site_url, start, end, ["page"], row_limit)


def page_queries(site_url: str, page_url: str, days: int = 90, row_limit: int = 200) -> dict:
    start, end = date_range(days)
    return query(site_url, start, end, ["query"], row_limit, page_url=page_url)


def country_device_breakdown(site_url: str, days: int = 28) -> dict:
    start, end = date_range(days)
    by_country = query(site_url, start, end, ["country"], 100)
    by_device = query(site_url, start, end, ["device"], 10)
    return {"country": by_country, "device": by_device}


def sitemaps(site_url: str) -> dict:
    data = _request("GET", f"/webmasters/v3/sites/{_enc(site_url)}/sitemaps")
    return {"sitemaps": [{"path": s.get("path"), "last_submitted": s.get("lastSubmitted"),
                          "errors": s.get("errors"), "warnings": s.get("warnings")}
                         for s in data.get("sitemap", [])]}
