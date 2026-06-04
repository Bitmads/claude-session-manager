#!/usr/bin/env python3
"""
Generate a curated FAKE ~/.claude dataset for the demo video.

Writes transcripts + task notes into demo/home/.claude so the picker shows
a clean, story-driven session list instead of real (private) sessions.
Reuses cc-sessions' own helpers so the data always matches the tool's logic.

Run from the demo/ folder:  python3 make_demo_data.py
"""

import os, json, shutil, pathlib, importlib.util, importlib.machinery
from datetime import datetime, timezone, timedelta

DEMO = pathlib.Path(__file__).resolve().parent
HOME = DEMO / "home"
CLAUDE = HOME / ".claude"

# Redirect Path.home() to the demo home BEFORE importing cc-sessions, so its
# CLAUDE_DIR / NOTES_DIR point at demo/home/.claude (never the real ~/.claude).
os.environ["HOME"] = str(HOME)

_src = DEMO.parent / "cc-sessions"
_loader = importlib.machinery.SourceFileLoader("ccs", str(_src))
_spec = importlib.util.spec_from_loader("ccs", _loader)
ccs = importlib.util.module_from_spec(_spec)
_loader.exec_module(ccs)

NOW = datetime.now(timezone.utc)


def iso(dt):
    return dt.isoformat().replace("+00:00", "Z")


# tier: 'custom' (★ user-renamed), 'ai' (○ auto), 'snippet' (· first message)
SESSIONS = [
    # ── payments ────────────────────────────────────────────────────
    dict(project="-payments", cwd="/home/dev/payments", branch="PAY-204/1",
         sid="7bdc4f85-aa10-4c21-9e33-1f0a2b3c4d5e", tier="custom",
         title="PAY-204/1.001: Refactor checkout flow",
         first_msg="Refactor the checkout flow to support split payments and idempotent retries.",
         ctx_pct=17, age=timedelta(days=3), msgs=42, status="wip"),
    dict(project="-payments", cwd="/home/dev/payments", branch="PAY-204/1",
         sid="eacf293b-7c44-4b8a-bb21-9d8e7f6a5b4c", tier="custom",
         title="PAY-204/1.002: Refactor checkout flow",
         first_msg="Continue the checkout refactor — wire up the new idempotency-key store.",
         ctx_pct=58, age=timedelta(hours=2), msgs=88,
         status="wip", note="Left off at idempotency-key collision handling.\nTODO: backfill keys for in-flight orders before deploy."),
    dict(project="-payments", cwd="/home/dev/payments", branch="PAY-204/2",
         sid="cd3c2712-3e90-4d1f-8a77-2b4c6d8e0a1f", tier="custom",
         title="PAY-204/2.001: Refactor checkout flow",
         first_msg="Phase 2: migrate the legacy checkout endpoints behind a feature flag.",
         ctx_pct=6, age=timedelta(minutes=18), msgs=9, status="open"),
    dict(project="-payments", cwd="/home/dev/payments", branch="PAY-198/1",
         sid="5f3dbaea-6b22-4c9d-9f01-3c5d7e9f1b2a", tier="custom",
         title="PAY-198/1.001: Fix Stripe webhook retries",
         first_msg="Webhooks are being retried forever when our handler 500s. Add a dead-letter path.",
         ctx_pct=34, age=timedelta(days=1), msgs=51, status="done"),
    # ── auth ────────────────────────────────────────────────────────
    dict(project="-auth", cwd="/home/dev/auth", branch="AUTH-88/1",
         sid="bd7adddd-9a11-4e22-8c44-4d6e8f0a2b3c", tier="custom",
         title="AUTH-88/1.001: OAuth token migration",
         first_msg="Migrate our OAuth tokens from the legacy table to the new encrypted store.",
         ctx_pct=18, age=timedelta(days=6), msgs=37, status="done"),
    dict(project="-auth", cwd="/home/dev/auth", branch="AUTH-88/1",
         sid="d8f5adbb-1c33-4f55-9b66-5e7f9a1b3c4d", tier="custom",
         title="AUTH-88/1.002: OAuth token migration",
         first_msg="Finish the OAuth migration — add the dual-read shim and a rollback switch.",
         ctx_pct=45, age=timedelta(hours=5), msgs=64,
         status="wip", note="Dual-read shim works. Need a metric on legacy-store hits before we cut over."),
    dict(project="-auth", cwd="/home/dev/auth", branch="AUTH-90/1",
         sid="c27ab9c8-2d44-4a66-8c77-6f8a0b2c4d5e", tier="custom",
         title="AUTH-90/1.001: Add passkey login",
         first_msg="Add WebAuthn passkey login as an alternative to passwords.",
         ctx_pct=37, age=timedelta(days=12), msgs=29, status="blocked",
         note="Blocked on the platform team enabling the passkey relying-party domain."),
    dict(project="-auth", cwd="/home/dev/auth", branch="main",
         sid="6820fd92-3e55-4b77-9d88-7a9b1c3d5e6f", tier="ai",
         title="Investigate intermittent 401s after token refresh",
         first_msg="Users are getting random 401s right after a token refresh. Can you dig in?",
         ctx_pct=22, age=timedelta(hours=9), msgs=40),
    # ── platform ────────────────────────────────────────────────────
    dict(project="-platform", cwd="/home/dev/platform", branch="INFRA-12/1",
         sid="f0bd12bb-4f66-4c88-8e99-8b0c2d4e6f70", tier="custom",
         title="INFRA-12/1.001: Upgrade Postgres to 16",
         first_msg="Plan and execute the Postgres 15 → 16 upgrade with zero downtime.",
         ctx_pct=11, age=timedelta(days=1, hours=4), msgs=23, status="wip"),
    dict(project="-platform", cwd="/home/dev/platform", branch="main",
         sid="03f40c8f-5a77-4d99-9f00-9c1d3e5f7081", tier="snippet",
         title=None,
         first_msg="can you help me write a migration to add a created_at index on the events table",
         ctx_pct=4, age=timedelta(hours=14), msgs=6),
]


def main():
    if CLAUDE.exists():
        shutil.rmtree(CLAUDE)
    (CLAUDE / "projects").mkdir(parents=True, exist_ok=True)
    (CLAUDE / "task-notes").mkdir(parents=True, exist_ok=True)

    # default config (naming scheme), copy disabled (no clipboard in container)
    (CLAUDE / "csm.json").write_text(json.dumps(ccs.DEFAULT_CONFIG, indent=2) + "\n")

    for s in SESSIONS:
        pdir = CLAUDE / "projects" / s["project"]
        pdir.mkdir(parents=True, exist_ok=True)
        # `age` anchors the LAST activity; spread earlier messages before it.
        end = NOW - s["age"]
        records = []

        if s["tier"] == "custom":
            records.append({"type": "custom-title", "customTitle": s["title"],
                            "sessionId": s["sid"]})
        elif s["tier"] == "ai":
            records.append({"type": "ai-title", "aiTitle": s["title"],
                            "sessionId": s["sid"]})

        n = max(s.get("msgs", 4), 2)
        pairs = max(n // 2, 1)
        tokens = int(s["ctx_pct"] / 100 * 1_000_000)
        gap = timedelta(minutes=5)
        for i in range(pairs):
            t = end - gap * (pairs - 1 - i)   # i=pairs-1 lands exactly at `end`
            records.append({"type": "user",
                            "message": {"content": s["first_msg"] if i == 0 else "..."},
                            "timestamp": iso(t - timedelta(seconds=30)),
                            "cwd": s["cwd"], "gitBranch": s["branch"]})
            usage = tokens if i == pairs - 1 else int(tokens * 0.6)
            records.append({"type": "assistant",
                            "message": {"usage": {"input_tokens": usage,
                                                  "cache_read_input_tokens": 0,
                                                  "cache_creation_input_tokens": 0}},
                            "timestamp": iso(t),
                            "cwd": s["cwd"], "gitBranch": s["branch"]})

        (pdir / f"{s['sid']}.jsonl").write_text(
            "".join(json.dumps(r) + "\n" for r in records))

        # status + note keyed the same way the picker groups
        key = ccs.extract_task_key(s["title"] or s["first_msg"])
        if s.get("note"):
            note_file = CLAUDE / "task-notes" / f"{ccs.sanitize(key)}.md"
            note_file.write_text(s["note"].rstrip() + "\n")
        if s.get("status"):
            ccs._set_task_status(key, s["status"])

    print(f"Wrote {len(SESSIONS)} demo sessions to {CLAUDE}")


if __name__ == "__main__":
    main()
