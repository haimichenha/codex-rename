#!/usr/bin/env python3
"""Codex VS Code thread hot-reload helper.

Purpose
-------
When cc-switch changes ``~/.codex/config.toml`` / ``auth.json`` while VS Code is
still running, the Codex VS Code extension can keep stale in-memory state.  A
common symptom is that ``/load`` cannot find a thread until VS Code is restarted.

This helper does not patch the VS Code extension.  It performs the low-risk
local-state repair that is usually enough for ``/load <thread-id>`` to work:

* list/find recent Codex threads from ``~/.codex/state_5.sqlite``;
* mark a target thread as non-archived and bump its updated_at timestamps;
* append/update ``~/.codex/session_index.jsonl`` with the target id/title;
* create ring-buffer backups before any write.

No API keys are printed.  Config diagnostics redact tokens by design.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import shutil
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def now_s() -> int:
    return int(time.time())


def now_ms() -> int:
    return int(time.time() * 1000)


def now_iso_z() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def default_codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME") or (Path.home() / ".codex"))


EXPECTED_PROVIDER_URLS: dict[str, str] = {
    "boh": "https://x666.me/v1",
    "default": "https://x666.me/v1",
    "muyuan": "https://muyuan.do/v1",
}


def provider_baseline_path(codex_home: Path) -> Path:
    return codex_home / "provider-guard-baselines.json"


def load_provider_baselines(codex_home: Path) -> dict[str, Any]:
    path = provider_baseline_path(codex_home)
    if not path.exists():
        return {"version": 1, "providers": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"provider baseline file is invalid JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"provider baseline file is not an object: {path}")
    providers = data.setdefault("providers", {})
    if not isinstance(providers, dict):
        raise SystemExit(f"provider baseline providers field is invalid: {path}")
    data.setdefault("version", 1)
    return data


def save_provider_baselines(codex_home: Path, data: dict[str, Any]) -> Path:
    path = provider_baseline_path(codex_home)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return path


def find_provider_baseline(
    baselines: dict[str, Any] | None,
    provider_id: str | None,
    provider_name: str | None,
) -> dict[str, Any] | None:
    if not baselines:
        return None
    providers = baselines.get("providers")
    if not isinstance(providers, dict):
        return None
    keys = {k.lower() for k in (provider_id or "", provider_name or "") if k}
    for item in providers.values():
        if not isinstance(item, dict):
            continue
        item_keys = {str(item.get("id", "")).lower(), str(item.get("name", "")).lower()}
        if keys & item_keys:
            return item
    return None


def config_base_url(config_text: str) -> str | None:
    base = re.search(r'base_url\s*=\s*"([^"]+)"', config_text)
    return base.group(1) if base else None


def replace_config_base_url(config_text: str, base_url: str) -> str:
    """Replace the first Codex provider base_url in TOML-like config text."""
    if re.search(r'base_url\s*=\s*"[^"]*"', config_text):
        return re.sub(r'base_url\s*=\s*"[^"]*"', f'base_url = "{base_url}"', config_text, count=1)
    marker = "[model_providers.custom]"
    if marker in config_text:
        return config_text.replace(marker, f'{marker}\nbase_url = "{base_url}"', 1)
    suffix = "" if config_text.endswith("\n") else "\n"
    return config_text + suffix + f'\n[model_providers.custom]\nbase_url = "{base_url}"\n'


def config_model(config_text: str) -> str | None:
    model = re.search(r'^model\s*=\s*"([^"]+)"', config_text, re.M)
    if not model:
        model = re.search(r'model\s*=\s*"([^"]+)"', config_text)
    return model.group(1) if model else None


def redact(s: str) -> str:
    if not s:
        return s
    s = re.sub(r"(sk-[A-Za-z0-9_\-]{6})[A-Za-z0-9_\-]+", r"\1…REDACTED", s)
    s = re.sub(r'("OPENAI_API_KEY"\s*:\s*")[^"]+', r"\1…REDACTED", s)
    s = re.sub(r"""(api_key\s*=\s*["'])[^\s"']+""", r"\1…REDACTED", s, flags=re.I)
    return s


def connect_state(codex_home: Path) -> sqlite3.Connection:
    db = codex_home / "state_5.sqlite"
    if not db.exists():
        raise SystemExit(f"state sqlite not found: {db}")
    con = sqlite3.connect(str(db))
    con.row_factory = sqlite3.Row
    return con


def backup_file(path: Path, backup_dir: Path) -> Path | None:
    if not path.exists():
        return None
    backup_dir.mkdir(parents=True, exist_ok=True)
    dst = backup_dir / f"{path.name}.bak"
    shutil.copy2(path, dst)
    return dst


def ring_backup_dir(base: Path, name: str, slots: int = 3) -> Path:
    root = base / "backups" / f"{name}-ring"
    root.mkdir(parents=True, exist_ok=True)
    counter_path = root / ".counter"
    try:
        counter = int(counter_path.read_text(encoding="utf-8").strip())
    except Exception:
        counter = 0
    slot = counter % max(1, slots)
    counter_path.write_text(str(counter + 1), encoding="utf-8")
    backup_dir = root / f"slot-{slot}"
    if backup_dir.exists():
        shutil.rmtree(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    (backup_dir / "metadata.json").write_text(
        json.dumps(
            {
                "created_at": now_iso_z(),
                "slot": slot,
                "slots": slots,
                "counter": counter,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return backup_dir


def backup_codex_state(codex_home: Path) -> list[Path]:
    backup_dir = ring_backup_dir(codex_home, "codex-hot-reload")
    made: list[Path] = []
    for rel in ("state_5.sqlite", "state_5.sqlite-wal", "state_5.sqlite-shm", "session_index.jsonl"):
        b = backup_file(codex_home / rel, backup_dir)
        if b:
            made.append(b)
    return made


def row_to_thread(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "title": row["title"],
        "updated_at": row["updated_at"],
        "model_provider": row["model_provider"],
        "model": row["model"],
        "cwd": row["cwd"],
        "archived": row["archived"],
        "rollout_path": row["rollout_path"],
    }


def list_threads(codex_home: Path, limit: int, cwd_filter: str | None = None) -> list[dict[str, Any]]:
    con = connect_state(codex_home)
    try:
        if cwd_filter:
            rows = con.execute(
                """
                select id,title,updated_at,model_provider,model,cwd,archived,rollout_path
                from threads
                where cwd like ?
                order by updated_at desc
                limit ?
                """,
                (f"%{cwd_filter}%", limit),
            ).fetchall()
        else:
            rows = con.execute(
                """
                select id,title,updated_at,model_provider,model,cwd,archived,rollout_path
                from threads
                order by updated_at desc
                limit ?
                """,
                (limit,),
            ).fetchall()
        return [row_to_thread(r) for r in rows]
    finally:
        con.close()


def find_thread(codex_home: Path, ident: str) -> dict[str, Any]:
    con = connect_state(codex_home)
    try:
        row = con.execute(
            """
            select id,title,updated_at,model_provider,model,cwd,archived,rollout_path
            from threads
            where id = ? or id like ?
            order by updated_at desc
            limit 1
            """,
            (ident, f"{ident}%"),
        ).fetchone()
        if not row:
            row = con.execute(
                """
                select id,title,updated_at,model_provider,model,cwd,archived,rollout_path
                from threads
                where title like ?
                order by updated_at desc
                limit 1
                """,
                (f"%{ident}%",),
            ).fetchone()
        if not row:
            raise SystemExit(f"thread not found by id/title: {ident}")
        return row_to_thread(row)
    finally:
        con.close()


def append_session_index(codex_home: Path, thread: dict[str, Any]) -> None:
    idx = codex_home / "session_index.jsonl"
    item = {
        "id": thread["id"],
        "thread_name": thread.get("title") or "",
        "updated_at": now_iso_z(),
    }
    with idx.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")


def refresh_thread(codex_home: Path, ident: str, dry_run: bool) -> dict[str, Any]:
    thread = find_thread(codex_home, ident)
    if dry_run:
        return thread

    backups = backup_codex_state(codex_home)
    con = connect_state(codex_home)
    try:
        con.execute(
            """
            update threads
            set updated_at = ?,
                updated_at_ms = ?,
                archived = 0,
                archived_at = null
            where id = ?
            """,
            (now_s(), now_ms(), thread["id"]),
        )
        con.commit()
    finally:
        con.close()

    refreshed = find_thread(codex_home, thread["id"])
    append_session_index(codex_home, refreshed)
    refreshed["backups"] = [str(p) for p in backups]
    return refreshed


def read_config_diag(codex_home: Path, cc_switch_home: Path | None) -> dict[str, Any]:
    diag: dict[str, Any] = {}
    cfg = codex_home / "config.toml"
    auth = codex_home / "auth.json"
    if cfg.exists():
        txt = cfg.read_text(encoding="utf-8", errors="replace")
        base = re.search(r'base_url\s*=\s*"([^"]+)"', txt)
        model = re.search(r'model\s*=\s*"([^"]+)"', txt)
        provider = re.search(r'model_provider\s*=\s*"([^"]+)"', txt)
        diag["codex_config"] = {
            "path": str(cfg),
            "model": model.group(1) if model else None,
            "model_provider": provider.group(1) if provider else None,
            "base_url": base.group(1) if base else None,
        }
    if auth.exists():
        raw = auth.read_text(encoding="utf-8", errors="replace")
        diag["codex_auth"] = {"path": str(auth), "preview": redact(raw[:240])}

    if cc_switch_home:
        db = cc_switch_home / "cc-switch.db"
        if db.exists():
            try:
                con = sqlite3.connect(str(db))
                con.row_factory = sqlite3.Row
                rows = con.execute(
                    """
                    select id,name,website_url,is_current,settings_config
                    from providers
                    where app_type = 'codex'
                    order by is_current desc, sort_index asc, name asc
                    limit 8
                    """
                ).fetchall()
                diag["cc_switch_codex_providers"] = [
                    {
                        "id": r["id"],
                        "name": r["name"],
                        "website_url": r["website_url"],
                        "is_current": r["is_current"],
                        "settings_preview": redact((r["settings_config"] or "")[:260]),
                    }
                    for r in rows
                ]
            except Exception as exc:  # pragma: no cover - diagnostic path
                diag["cc_switch_error"] = str(exc)
            finally:
                try:
                    con.close()
                except Exception:
                    pass
    return diag


def cc_switch_db(cc_switch_home: Path) -> Path:
    db = cc_switch_home / "cc-switch.db"
    if not db.exists():
        raise SystemExit(f"cc-switch db not found: {db}")
    return db


def list_cc_switch_codex_providers(cc_switch_home: Path, codex_home: Path | None = None) -> list[dict[str, Any]]:
    baselines = load_provider_baselines(codex_home) if codex_home else None
    con = sqlite3.connect(str(cc_switch_db(cc_switch_home)))
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(
            """
            select id,name,website_url,is_current,sort_index,settings_config
            from providers
            where app_type = 'codex'
            order by is_current desc, sort_index asc, name asc
            """
        ).fetchall()
        out: list[dict[str, Any]] = []
        for r in rows:
            cfg = json.loads(r["settings_config"] or "{}")
            config_text = cfg.get("config") or ""
            base_url = config_base_url(config_text)
            model = config_model(config_text)
            effective_url = base_url or r["website_url"]
            baseline = find_provider_baseline(baselines, r["id"], r["name"])
            expected_url = (baseline or {}).get("base_url") or expected_provider_url(r["id"], r["name"])
            out.append(
                {
                    "id": r["id"],
                    "name": r["name"],
                    "website_url": r["website_url"],
                    "is_current": bool(r["is_current"]),
                    "sort_index": r["sort_index"],
                    "model": model,
                    "base_url": base_url,
                    "effective_url": effective_url,
                    "expected_url": expected_url,
                    "baseline": bool(baseline),
                    "url_mismatch": bool(base_url and r["website_url"] and base_url != r["website_url"]),
                    "guard_mismatch": bool(expected_url and effective_url != expected_url),
                    "has_auth": bool(cfg.get("auth")),
                    "has_config": bool(cfg.get("config")),
                }
            )
        return out
    finally:
        con.close()


def find_cc_switch_codex_provider(cc_switch_home: Path, query: str | None) -> dict[str, Any]:
    con = sqlite3.connect(str(cc_switch_db(cc_switch_home)))
    con.row_factory = sqlite3.Row
    try:
        if not query or query.lower() in {"current", "@current"}:
            row = con.execute(
                """
                select id,name,website_url,is_current,settings_config
                from providers
                where app_type = 'codex' and is_current = 1
                order by sort_index asc
                limit 1
                """
            ).fetchone()
            if not row:
                raise SystemExit("no current codex provider in cc-switch db")
        else:
            row = con.execute(
                """
                select id,name,website_url,is_current,settings_config
                from providers
                where app_type = 'codex'
                  and (id = ? or name = ? or name like ?)
                order by case when name = ? then 0 else 1 end, sort_index asc
                limit 1
                """,
                (query, query, f"%{query}%", query),
            ).fetchone()
            if not row:
                raise SystemExit(f"codex provider not found in cc-switch db: {query}")
        data = dict(row)
        data["settings"] = json.loads(data.pop("settings_config") or "{}")
        return data
    finally:
        con.close()


def expected_provider_url(
    provider_id: str | None,
    provider_name: str | None,
    baselines: dict[str, Any] | None = None,
    website_url: str | None = None,
) -> str | None:
    baseline = find_provider_baseline(baselines, provider_id, provider_name)
    if baseline and baseline.get("base_url"):
        return str(baseline["base_url"])
    keys = [provider_name or "", provider_id or ""]
    for key in keys:
        expected = EXPECTED_PROVIDER_URLS.get(key.lower())
        if expected:
            return expected
    return website_url


def validate_provider_guard(
    provider: dict[str, Any],
    config_text: str,
    baselines: dict[str, Any] | None = None,
    use_website_default: bool = False,
    raise_on_mismatch: bool = True,
) -> dict[str, Any]:
    actual = config_base_url(config_text) or provider.get("website_url")
    expected = expected_provider_url(
        provider.get("id"),
        provider.get("name"),
        baselines,
        provider.get("website_url") if use_website_default else None,
    )
    result = {
        "provider": provider.get("name"),
        "id": provider.get("id"),
        "expected_url": expected,
        "actual_url": actual,
        "ok": not expected or actual == expected,
    }
    if not result["ok"] and raise_on_mismatch:
        raise SystemExit(
            "provider settings guard failed: "
            f"{provider.get('name')} expected {expected}, got {actual}. "
            "This usually means cc-switch saved another provider into this provider. "
            "Repair the provider settings from backup before switching."
        )
    return result


def validate_all_provider_guards(cc_switch_home: Path, codex_home: Path | None = None) -> dict[str, Any]:
    providers = list_cc_switch_codex_providers(cc_switch_home, codex_home)
    checks = []
    ok = True
    for pvd in providers:
        if not pvd.get("expected_url"):
            continue
        check = {
            "provider": pvd["name"],
            "id": pvd["id"],
            "expected_url": pvd["expected_url"],
            "actual_url": pvd["effective_url"],
            "ok": not pvd.get("guard_mismatch"),
        }
        checks.append(check)
        ok = ok and check["ok"]
    return {"ok": ok, "checks": checks}


def validate_provider_pair_guards(
    cc_switch_home: Path,
    codex_home: Path,
    target_query: str,
) -> dict[str, Any]:
    baselines = load_provider_baselines(codex_home)
    selected: dict[str, dict[str, Any]] = {}
    for query in ("current", target_query):
        provider = find_cc_switch_codex_provider(cc_switch_home, query)
        selected[provider["id"]] = provider

    checks = []
    ok = True
    for provider in selected.values():
        config_text = provider["settings"].get("config") or ""
        guard = validate_provider_guard(
            provider,
            config_text,
            baselines=baselines,
            use_website_default=True,
            raise_on_mismatch=False,
        )
        checks.append(guard)
        ok = ok and guard["ok"]
    return {"ok": ok, "checks": checks}


def capture_provider_baseline(
    codex_home: Path,
    cc_switch_home: Path,
    query: str,
    dry_run: bool,
    force: bool = False,
) -> dict[str, Any]:
    provider = find_cc_switch_codex_provider(cc_switch_home, query)
    settings = provider["settings"]
    config_text = settings.get("config")
    auth_obj = settings.get("auth")
    if not isinstance(config_text, str) or not config_text.strip():
        raise SystemExit(f"provider has no codex config text: {provider['name']}")
    if not isinstance(auth_obj, dict) or not auth_obj:
        raise SystemExit(f"provider has no codex auth object: {provider['name']}")
    base_url = config_base_url(config_text) or provider.get("website_url")
    model = config_model(config_text)
    if not base_url:
        raise SystemExit(f"provider has no base_url/website_url to guard: {provider['name']}")

    data = load_provider_baselines(codex_home)
    providers = data.setdefault("providers", {})
    key = provider["id"] or provider["name"]
    if key in providers and not force:
        existing = providers[key]
        return {
            "provider": provider["name"],
            "id": provider["id"],
            "base_url": existing.get("base_url"),
            "model": existing.get("model"),
            "baseline_path": str(provider_baseline_path(codex_home)),
            "dry_run": dry_run,
            "written": False,
            "reason": "baseline already exists; pass --force to overwrite",
        }

    item = {
        "id": provider["id"],
        "name": provider["name"],
        "website_url": provider.get("website_url"),
        "base_url": base_url,
        "model": model,
        "captured_at": now_iso_z(),
        "settings": {
            "auth": auth_obj,
            "config": config_text,
        },
    }
    result = {
        "provider": provider["name"],
        "id": provider["id"],
        "base_url": base_url,
        "model": model,
        "baseline_path": str(provider_baseline_path(codex_home)),
        "dry_run": dry_run,
    }
    if dry_run:
        return result
    providers[key] = item
    path = save_provider_baselines(codex_home, data)
    result["written"] = True
    result["baseline_path"] = str(path)
    return result


def find_codex_backup_pair(codex_home: Path, expected_url: str) -> tuple[Path, Path, str | None]:
    candidates: list[Path] = []
    for root in (codex_home / "backups", codex_home):
        if root.exists():
            candidates.extend(sorted(root.rglob("config.toml*"), key=lambda p: p.stat().st_mtime, reverse=True))

    for cfg_path in candidates:
        if not cfg_path.is_file():
            continue
        config_text = cfg_path.read_text(encoding="utf-8", errors="replace")
        base = re.search(r'base_url\s*=\s*"([^"]+)"', config_text)
        if not base or base.group(1) != expected_url:
            continue
        auth_path = None
        for name in ("auth.json.bak", "auth.json"):
            candidate = cfg_path.parent / name
            if candidate.exists():
                auth_path = candidate
                break
        if not auth_path:
            continue
        try:
            auth_obj = json.loads(auth_path.read_text(encoding="utf-8", errors="replace"))
        except json.JSONDecodeError:
            continue
        if not isinstance(auth_obj, dict) or not auth_obj:
            continue
        model = re.search(r'^model\s*=\s*"([^"]+)"', config_text, re.M)
        return cfg_path, auth_path, model.group(1) if model else None
    raise SystemExit(f"no usable Codex config/auth backup found for base_url: {expected_url}")


def repair_provider_settings(
    codex_home: Path,
    cc_switch_home: Path,
    query: str,
    dry_run: bool,
    use_website_default: bool = False,
) -> dict[str, Any]:
    provider = find_cc_switch_codex_provider(cc_switch_home, query)
    baselines = load_provider_baselines(codex_home)
    expected = expected_provider_url(
        provider.get("id"),
        provider.get("name"),
        baselines,
        provider.get("website_url") if use_website_default else None,
    )
    if not expected:
        raise SystemExit(f"provider is not guarded and has no expected URL: {provider['name']}")

    baseline = find_provider_baseline(baselines, provider.get("id"), provider.get("name"))
    if baseline and isinstance(baseline.get("settings"), dict):
        settings = baseline["settings"]
        config_text = settings.get("config")
        auth_obj = settings.get("auth")
        if not isinstance(config_text, str) or not isinstance(auth_obj, dict) or not auth_obj:
            raise SystemExit(f"provider baseline is incomplete: {provider['name']}")
        model = config_model(config_text)
        config_source = str(provider_baseline_path(codex_home))
        auth_source = str(provider_baseline_path(codex_home))
    else:
        cfg_path, auth_path, model = find_codex_backup_pair(codex_home, expected)
        config_text = cfg_path.read_text(encoding="utf-8", errors="replace")
        auth_obj = json.loads(auth_path.read_text(encoding="utf-8", errors="replace"))
        config_source = str(cfg_path)
        auth_source = str(auth_path)

    result = {
        "provider": provider["name"],
        "id": provider["id"],
        "expected_url": expected,
        "model": model,
        "config_source": config_source,
        "auth_source": auth_source,
        "dry_run": dry_run,
    }
    if dry_run:
        return result

    backup_dir = ring_backup_dir(cc_switch_home, f"{provider['name']}-provider-repair")
    backups = []
    for rel in ("cc-switch.db", "settings.json"):
        b = backup_file(cc_switch_home / rel, backup_dir)
        if b:
            backups.append(b)

    settings = {"auth": auth_obj, "config": config_text}
    con = sqlite3.connect(str(cc_switch_db(cc_switch_home)))
    try:
        cur = con.execute(
            """
            update providers
            set website_url = ?,
                settings_config = ?
            where app_type = 'codex' and id = ?
            """,
            (expected, json.dumps(settings, ensure_ascii=False), provider["id"]),
        )
        if cur.rowcount != 1:
            raise SystemExit(f"provider repair updated unexpected row count: {cur.rowcount}")
        con.commit()
    finally:
        con.close()

    result["backups"] = [str(p) for p in backups]
    result["written"] = True
    return result


def ensure_provider_guards(
    codex_home: Path,
    cc_switch_home: Path,
    target_query: str,
    dry_run: bool,
) -> dict[str, Any]:
    before = validate_provider_pair_guards(cc_switch_home, codex_home, target_query)
    repairs = []
    if before["ok"]:
        return {"ok": True, "before": before, "repairs": repairs, "dry_run": dry_run}

    for check in before["checks"]:
        if check["ok"]:
            continue
        repairs.append(
            repair_provider_settings(
                codex_home,
                cc_switch_home,
                check["provider"],
                dry_run=dry_run,
                use_website_default=True,
            )
        )

    after = before if dry_run else validate_provider_pair_guards(cc_switch_home, codex_home, target_query)
    return {
        "ok": after["ok"],
        "before": before,
        "repairs": repairs,
        "after": after,
        "dry_run": dry_run,
    }


def backup_codex_config(codex_home: Path) -> list[Path]:
    backup_dir = ring_backup_dir(codex_home, "cc-switch-provider-apply")
    made: list[Path] = []
    for rel in ("config.toml", "auth.json"):
        b = backup_file(codex_home / rel, backup_dir)
        if b:
            made.append(b)
    return made


def backup_cc_switch_state(cc_switch_home: Path) -> list[Path]:
    backup_dir = ring_backup_dir(cc_switch_home, "codex-provider-current")
    made: list[Path] = []
    for rel in ("cc-switch.db", "settings.json"):
        b = backup_file(cc_switch_home / rel, backup_dir)
        if b:
            made.append(b)
    return made


def set_cc_switch_current_provider(cc_switch_home: Path, provider_id: str, dry_run: bool) -> list[Path]:
    if dry_run:
        return []
    backups = backup_cc_switch_state(cc_switch_home)
    con = sqlite3.connect(str(cc_switch_db(cc_switch_home)))
    try:
        con.execute(
            """
            update providers
            set is_current = case when id = ? then 1 else 0 end
            where app_type = 'codex'
            """,
            (provider_id,),
        )
        # Some cc-switch versions also mirror simple settings in this table.
        try:
            con.execute(
                """
                insert into settings(key, value)
                values('currentProviderCodex', ?)
                on conflict(key) do update set value = excluded.value
                """,
                (provider_id,),
            )
        except sqlite3.Error:
            pass
        con.commit()
    finally:
        con.close()

    settings_json = cc_switch_home / "settings.json"
    if settings_json.exists():
        try:
            data = json.loads(settings_json.read_text(encoding="utf-8"))
            data["currentProviderCodex"] = provider_id
            settings_json.write_text(
                json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
                newline="\n",
            )
        except Exception as exc:
            print(f"WARNING: failed to update cc-switch settings.json: {exc}", file=sys.stderr)
    return backups


def update_provider_endpoint(
    codex_home: Path,
    cc_switch_home: Path,
    query: str,
    base_url: str | None,
    api_key: str | None,
    dry_run: bool,
    update_baseline: bool = True,
) -> dict[str, Any]:
    """Patch one cc-switch Codex provider's stored base_url/key.

    This intentionally updates the provider record before switching, so a bad
    URL/key in cc-switch does not get copied back into ~/.codex.
    """
    if not base_url and not api_key:
        raise SystemExit("nothing to update: pass --base-url and/or --api-key/--api-key-env")

    provider = find_cc_switch_codex_provider(cc_switch_home, query)
    settings = provider["settings"]
    config_text = settings.get("config")
    auth_obj = settings.get("auth")
    if not isinstance(config_text, str) or not config_text.strip():
        raise SystemExit(f"provider has no codex config text: {provider['name']}")
    if not isinstance(auth_obj, dict):
        auth_obj = {"auth_mode": "apikey"}

    old_base_url = config_base_url(config_text) or provider.get("website_url")
    old_has_key = bool(auth_obj.get("OPENAI_API_KEY"))

    new_config_text = replace_config_base_url(config_text, base_url) if base_url else config_text
    new_auth_obj = dict(auth_obj)
    if api_key:
        new_auth_obj["auth_mode"] = new_auth_obj.get("auth_mode") or "apikey"
        new_auth_obj["OPENAI_API_KEY"] = api_key

    new_settings = dict(settings)
    new_settings["config"] = new_config_text
    new_settings["auth"] = new_auth_obj

    result: dict[str, Any] = {
        "provider": {
            "id": provider["id"],
            "name": provider["name"],
            "website_url": provider.get("website_url"),
            "old_base_url": old_base_url,
            "new_base_url": config_base_url(new_config_text) or provider.get("website_url"),
            "old_has_key": old_has_key,
            "new_has_key": bool(new_auth_obj.get("OPENAI_API_KEY")),
        },
        "cc_switch_db": str(cc_switch_db(cc_switch_home)),
        "baseline_path": str(provider_baseline_path(codex_home)),
        "dry_run": dry_run,
    }
    if dry_run:
        return result

    cc_backups = backup_cc_switch_state(cc_switch_home)
    con = sqlite3.connect(str(cc_switch_db(cc_switch_home)))
    try:
        con.execute(
            "update providers set settings_config = ? where id = ? and app_type = 'codex'",
            (json.dumps(new_settings, ensure_ascii=False, separators=(",", ":")), provider["id"]),
        )
        con.commit()
    finally:
        con.close()

    result["cc_switch_backups"] = [str(p) for p in cc_backups]

    if update_baseline:
        data = load_provider_baselines(codex_home)
        providers = data.setdefault("providers", {})
        providers[provider["id"]] = {
            "id": provider["id"],
            "name": provider["name"],
            "website_url": provider.get("website_url"),
            "base_url": config_base_url(new_config_text) or provider.get("website_url"),
            "model": config_model(new_config_text),
            "captured_at": now_iso_z(),
            "settings": {"auth": new_auth_obj, "config": new_config_text},
        }
        path = provider_baseline_path(codex_home)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        result["baseline_written"] = True

    result["written"] = True
    return result


def apply_cc_switch_codex_provider(
    codex_home: Path,
    cc_switch_home: Path,
    query: str | None,
    dry_run: bool,
    sync_current: bool = False,
) -> dict[str, Any]:
    provider = find_cc_switch_codex_provider(cc_switch_home, query)
    settings = provider["settings"]
    config_text = settings.get("config")
    auth_obj = settings.get("auth")
    if not isinstance(config_text, str) or not config_text.strip():
        raise SystemExit(f"provider has no codex config text: {provider['name']}")
    if not isinstance(auth_obj, dict):
        raise SystemExit(f"provider has no codex auth object: {provider['name']}")

    base_url = config_base_url(config_text)
    model = config_model(config_text)
    guard = validate_provider_guard(
        provider,
        config_text,
        baselines=load_provider_baselines(codex_home),
        use_website_default=True,
    )
    result = {
        "provider": {
            "id": provider["id"],
            "name": provider["name"],
            "website_url": provider["website_url"],
            "is_current": bool(provider["is_current"]),
            "model": model,
            "base_url": base_url,
        },
        "provider_guard": guard,
        "codex_config": str(codex_home / "config.toml"),
        "codex_auth": str(codex_home / "auth.json"),
        "dry_run": dry_run,
    }
    if dry_run:
        result["sync_current"] = sync_current
        return result

    backups = backup_codex_config(codex_home)
    cc_switch_backups = set_cc_switch_current_provider(
        cc_switch_home,
        provider["id"],
        dry_run=False,
    ) if sync_current else []
    codex_home.mkdir(parents=True, exist_ok=True)
    (codex_home / "config.toml").write_text(config_text, encoding="utf-8", newline="\n")
    (codex_home / "auth.json").write_text(
        json.dumps(auth_obj, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    result["backups"] = [str(p) for p in backups]
    result["cc_switch_backups"] = [str(p) for p in cc_switch_backups]
    result["sync_current"] = sync_current
    result["written"] = True
    return result


def smart_switch(
    codex_home: Path,
    cc_switch_home: Path,
    provider_query: str,
    thread_query: str | None,
    cwd_contains: str | None,
    dry_run: bool,
    sync_current: bool,
    base_url: str | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    endpoint_update = None
    if base_url or api_key:
        endpoint_update = update_provider_endpoint(
            codex_home,
            cc_switch_home,
            provider_query,
            base_url=base_url,
            api_key=api_key,
            dry_run=dry_run,
            update_baseline=True,
        )

    ensure_result = ensure_provider_guards(codex_home, cc_switch_home, provider_query, dry_run=dry_run)
    if not ensure_result["ok"] and not dry_run:
        raise SystemExit("provider guard auto-repair failed; refusing to switch")

    result = apply_cc_switch_codex_provider(
        codex_home,
        cc_switch_home,
        provider_query,
        dry_run=dry_run,
        sync_current=sync_current,
    )
    if endpoint_update:
        result["endpoint_update"] = endpoint_update
    result["provider_guard_ensure"] = ensure_result
    if thread_query:
        result["thread"] = refresh_thread(codex_home, thread_query, dry_run=dry_run)
    elif cwd_contains:
        threads = list_threads(codex_home, 1, cwd_contains)
        if threads:
            result["thread"] = refresh_thread(codex_home, threads[0]["id"], dry_run=dry_run)
    if result.get("thread"):
        result["load_command"] = f"/load {result['thread']['id']}"
    return result


def print_thread(thread: dict[str, Any]) -> None:
    title = (thread.get("title") or "").replace("\r", " ").replace("\n", " ")
    if len(title) > 120:
        title = title[:117] + "..."
    print(json.dumps({**thread, "title": title}, ensure_ascii=False, indent=2))
    print(f"/load {thread['id']}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Codex VS Code thread hot-reload helper")
    ap.add_argument("--codex-home", default=str(default_codex_home()))
    ap.add_argument("--cc-switch-home", default=str(Path.home() / ".cc-switch"))
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("list", help="list recent threads")
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--cwd-contains")

    p = sub.add_parser("find", help="find thread by id prefix or title substring")
    p.add_argument("query")

    p = sub.add_parser("refresh", help="bump a thread in Codex local state for /load")
    p.add_argument("query")
    p.add_argument("--write", action="store_true", help="actually modify local Codex state; default is dry-run")

    sub.add_parser("diag", help="print redacted Codex/cc-switch config diagnostics")

    sub.add_parser("providers", help="list Codex providers stored in cc-switch")

    sub.add_parser("validate-providers", help="validate guarded provider settings are not cross-contaminated")

    p = sub.add_parser("capture-provider-baseline", help="capture a provider's current cc-switch settings as a guard baseline")
    p.add_argument("provider", help="provider name/id to capture")
    p.add_argument("--write", action="store_true", help="actually write provider-guard-baselines.json; default is dry-run")
    p.add_argument("--force", action="store_true", help="overwrite an existing baseline for this provider")

    p = sub.add_parser("repair-provider", help="repair a guarded provider from local Codex config/auth backups")
    p.add_argument("provider", help="guarded provider name/id, for example boh or muyuan")
    p.add_argument("--write", action="store_true", help="actually update cc-switch provider settings; default is dry-run")

    p = sub.add_parser("update-provider", help="patch a provider's stored base_url/API key, then optionally apply it")
    p.add_argument("provider", help="provider name/id to patch")
    p.add_argument("--base-url", help="new Codex API base_url for this provider")
    p.add_argument("--api-key", help="new OPENAI_API_KEY for this provider; not printed, but may remain in shell history")
    p.add_argument("--api-key-env", help="read new OPENAI_API_KEY from this environment variable")
    p.add_argument("--apply", action="store_true", help="after patching, write the provider to ~/.codex config/auth")
    p.add_argument("--sync-current", action="store_true", help="with --apply, also mark provider current in cc-switch")
    p.add_argument("--write", action="store_true", help="actually update cc-switch/provider config; default is dry-run")

    p = sub.add_parser("apply-provider", help="apply a cc-switch Codex provider to ~/.codex config/auth")
    p.add_argument("query", nargs="?", default="current", help="provider name/id, or 'current'")
    p.add_argument("--write", action="store_true", help="actually write ~/.codex/config.toml and auth.json")
    p.add_argument("--sync-current", action="store_true", help="also mark the provider as current in cc-switch db/settings")

    p = sub.add_parser("switch", help="smart provider switch: sync cc-switch, write Codex config, optionally refresh a thread")
    p.add_argument("provider", help="cc-switch Codex provider name/id, for example muyuan")
    p.add_argument("--thread", help="thread id/title to refresh and print /load for")
    p.add_argument("--cwd-contains", help="if --thread is omitted, refresh latest thread matching this cwd substring")
    p.add_argument("--no-sync-current", action="store_true", help="do not update cc-switch current provider markers")
    p.add_argument("--base-url", help="patch target provider base_url before switching")
    p.add_argument("--api-key", help="patch target provider OPENAI_API_KEY before switching; not printed, but may remain in shell history")
    p.add_argument("--api-key-env", help="read target provider OPENAI_API_KEY from this environment variable")
    p.add_argument("--write", action="store_true", help="actually write config/db; default is dry-run")

    ns = ap.parse_args(argv)
    codex_home = Path(ns.codex_home).expanduser()
    cc_switch_home = Path(ns.cc_switch_home).expanduser() if ns.cc_switch_home else None

    if ns.cmd == "list":
        for t in list_threads(codex_home, ns.limit, ns.cwd_contains):
            print_thread(t)
        return 0
    if ns.cmd == "find":
        print_thread(find_thread(codex_home, ns.query))
        return 0
    if ns.cmd == "refresh":
        thread = refresh_thread(codex_home, ns.query, dry_run=not ns.write)
        print_thread(thread)
        if not ns.write:
            print("DRY_RUN: add --write to update state_5.sqlite and session_index.jsonl")
        else:
            print("UPDATED: backups were created before write")
        return 0
    if ns.cmd == "diag":
        print(json.dumps(read_config_diag(codex_home, cc_switch_home), ensure_ascii=False, indent=2))
        return 0
    if ns.cmd == "providers":
        for pvd in list_cc_switch_codex_providers(cc_switch_home, codex_home):
            mark = "*" if pvd["is_current"] else " "
            mismatch = "  website_url differs" if pvd.get("url_mismatch") else ""
            guard = "  GUARD_MISMATCH" if pvd.get("guard_mismatch") else ""
            baseline = "  baseline" if pvd.get("baseline") else ""
            print(
                f"{mark} {pvd['name']}  id={pvd['id']}  "
                f"model={pvd['model']}  effective={pvd['effective_url']}{mismatch}{guard}{baseline}"
            )
        return 0
    if ns.cmd == "validate-providers":
        result = validate_all_provider_guards(cc_switch_home, codex_home)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["ok"] else 2
    if ns.cmd == "capture-provider-baseline":
        result = capture_provider_baseline(
            codex_home,
            cc_switch_home,
            ns.provider,
            dry_run=not ns.write,
            force=ns.force,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if not ns.write:
            print("DRY_RUN: add --write to save baseline")
        return 0
    if ns.cmd == "repair-provider":
        result = repair_provider_settings(
            codex_home,
            cc_switch_home,
            ns.provider,
            dry_run=not ns.write,
            use_website_default=True,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if not ns.write:
            print("DRY_RUN: add --write to repair cc-switch provider settings")
        else:
            print("UPDATED: provider settings repaired from local Codex backup")
        return 0
    if ns.cmd == "update-provider":
        api_key = ns.api_key
        if ns.api_key_env:
            api_key = os.environ.get(ns.api_key_env)
            if not api_key:
                raise SystemExit(f"environment variable not set or empty: {ns.api_key_env}")
        result = update_provider_endpoint(
            codex_home,
            cc_switch_home,
            ns.provider,
            base_url=ns.base_url,
            api_key=api_key,
            dry_run=not ns.write,
            update_baseline=True,
        )
        if ns.apply:
            result["apply_provider"] = apply_cc_switch_codex_provider(
                codex_home,
                cc_switch_home,
                ns.provider,
                dry_run=not ns.write,
                sync_current=ns.sync_current,
            )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if not ns.write:
            print("DRY_RUN: add --write to patch provider URL/key")
        else:
            print("UPDATED: provider URL/key patched; API key was not printed.")
        return 0
    if ns.cmd == "apply-provider":
        result = apply_cc_switch_codex_provider(
            codex_home,
            cc_switch_home,
            ns.query,
            dry_run=not ns.write,
            sync_current=ns.sync_current,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if not ns.write:
            print("DRY_RUN: add --write to update ~/.codex/config.toml and auth.json")
        else:
            print("UPDATED: open a new Codex panel/thread, or restart only the codex child process if the current panel still uses old config.")
        return 0
    if ns.cmd == "switch":
        api_key = ns.api_key
        if ns.api_key_env:
            api_key = os.environ.get(ns.api_key_env)
            if not api_key:
                raise SystemExit(f"environment variable not set or empty: {ns.api_key_env}")
        result = smart_switch(
            codex_home,
            cc_switch_home,
            ns.provider,
            ns.thread,
            ns.cwd_contains,
            dry_run=not ns.write,
            sync_current=not ns.no_sync_current,
            base_url=ns.base_url,
            api_key=api_key,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if not ns.write:
            print("DRY_RUN: add --write to apply provider/config/thread refresh")
        else:
            print("UPDATED: provider/config synced.")
            if result.get("load_command"):
                print(result["load_command"])
        return 0
    raise AssertionError(ns.cmd)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        raise SystemExit(1)
