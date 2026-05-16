"""
Pull Discord channel messages into core/inbox/discord/YYYY-MM.md.

This script intentionally uses only the Python standard library. It polls one
or more Discord channels through the REST API and appends unseen messages as
raw inbox captures. It does not classify, summarize, or route content.

Usage:
    python system/scripts/integrations/discord_inbox_pull.py --once
    python system/scripts/integrations/discord_inbox_pull.py --loop --interval 30
    python system/scripts/integrations/discord_inbox_pull.py --mark-seen
    python system/scripts/integrations/discord_inbox_pull.py --env-file D:\\workspace_v2\\secrets\\discord-inbox.env --once

Environment:
    DISCORD_BOT_TOKEN              required
    DISCORD_CHANNEL_IDS            required, comma-separated channel IDs
    DISCORD_ALLOWED_USER_IDS       optional comma-separated Discord user IDs
    DISCORD_INBOX_DIR              optional output directory
    DISCORD_STATE_FILE             optional state file path
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


CORE_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INBOX_DIR = CORE_ROOT / "inbox" / "discord"
DEFAULT_STATE_FILE = DEFAULT_INBOX_DIR / ".discord_pull_state.json"
LOCAL_TZ = ZoneInfo("Asia/Taipei")
API_BASE = "https://discord.com/api/v10"


def load_env_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"env file not found: {path}")

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def parse_id_list(value: str | None, *, required: bool = False) -> list[str]:
    if not value:
        if required:
            raise ValueError("required Discord ID list is empty")
        return []

    ids: list[str] = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        if not part.isdigit():
            raise ValueError(f"invalid Discord ID: {part}")
        ids.append(part)
    if required and not ids:
        raise ValueError("required Discord ID list is empty")
    return ids


def load_state(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"invalid state file: {path}")
    return {str(key): str(value) for key, value in data.items()}


def save_state(path: Path, state: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def discord_get(token: str, path: str, params: dict[str, str] | None = None):
    query = f"?{urllib.parse.urlencode(params)}" if params else ""
    request = urllib.request.Request(
        f"{API_BASE}{path}{query}",
        headers={
            "Authorization": f"Bot {token}",
            "User-Agent": "core-discord-inbox-pull/0.1",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Discord API error {exc.code}: {body}") from exc


def fetch_channel_messages(token: str, channel_id: str, after_id: str | None, limit: int):
    params = {"limit": str(limit)}
    if after_id:
        params["after"] = after_id
    return discord_get(token, f"/channels/{channel_id}/messages", params=params)


def fence_text(text: str) -> str:
    if not text:
        return "(empty message)"
    return text.replace("```", "`\u200b``")


def parse_discord_time(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized).astimezone(LOCAL_TZ)


def format_capture(message: dict, channel_id: str) -> str:
    created_at = parse_discord_time(message["timestamp"])
    stamp = created_at.strftime("%Y-%m-%d %H:%M")
    created_at_iso = created_at.isoformat(timespec="seconds")
    author = message.get("author", {})
    author_name = author.get("global_name") or author.get("username") or "unknown"
    author_id = author.get("id", "unknown")
    content = message.get("content", "")

    lines = [
        f"## {stamp}",
        "",
        "- source: discord",
        f"- created_at: {created_at_iso}",
        f"- author: {author_name} ({author_id})",
        f"- channel_id: {channel_id}",
        f"- message_id: {message.get('id', 'unknown')}",
        "- status: captured",
        "",
        "Raw:",
        "",
        "```text",
        fence_text(content.strip()),
        "```",
    ]

    attachments = message.get("attachments") or []
    if attachments:
        lines.extend(["", "Attachments:", ""])
        for attachment in attachments:
            lines.append(f"- filename: {attachment.get('filename', '')}")
            lines.append(f"  url: {attachment.get('url', '')}")
            if "size" in attachment:
                lines.append(f"  size: {attachment['size']}")

    lines.append("")
    return "\n".join(lines)


def append_capture(inbox_dir: Path, message: dict, channel_id: str) -> Path:
    created_at = parse_discord_time(message["timestamp"])
    monthly_file = inbox_dir / f"{created_at.strftime('%Y-%m')}.md"
    inbox_dir.mkdir(parents=True, exist_ok=True)

    capture = format_capture(message, channel_id)
    if monthly_file.exists() and monthly_file.read_text(encoding="utf-8").strip():
        prefix = "\n"
    else:
        prefix = f"# Discord Inbox {created_at.strftime('%Y-%m')}\n\n"

    with monthly_file.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(prefix)
        handle.write(capture)

    return monthly_file


def pull_once(
    token: str,
    channel_ids: list[str],
    allowed_user_ids: set[str],
    inbox_dir: Path,
    state_file: Path,
    limit: int,
    allow_bots: bool = False,
) -> int:
    state = load_state(state_file)
    captured = 0

    for channel_id in channel_ids:
        after_id = state.get(channel_id)
        messages = fetch_channel_messages(token, channel_id, after_id, limit)
        if not isinstance(messages, list):
            raise RuntimeError(f"unexpected Discord response for channel {channel_id}: {messages}")

        for message in sorted(messages, key=lambda item: int(item["id"])):
            author_id = str(message.get("author", {}).get("id", ""))
            is_bot = bool(message.get("author", {}).get("bot"))
            if is_bot and not allow_bots:
                state[channel_id] = str(message["id"])
                continue
            if allowed_user_ids and author_id not in allowed_user_ids and not (allow_bots and is_bot):
                state[channel_id] = str(message["id"])
                continue
            output = append_capture(inbox_dir, message, channel_id)
            print(f"captured {message['id']} -> {output}")
            state[channel_id] = str(message["id"])
            captured += 1

    save_state(state_file, state)
    return captured


def mark_seen(token: str, channel_ids: list[str], state_file: Path) -> int:
    state = load_state(state_file)
    updated = 0

    for channel_id in channel_ids:
        messages = fetch_channel_messages(token, channel_id, None, 1)
        if not messages:
            continue
        latest_id = str(messages[0]["id"])
        if state.get(channel_id) != latest_id:
            state[channel_id] = latest_id
            updated += 1

    save_state(state_file, state)
    return updated


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--once", action="store_true", help="Pull once and exit")
    mode.add_argument("--loop", action="store_true", help="Keep polling")
    mode.add_argument("--mark-seen", action="store_true", help="Record latest message IDs without capturing history")
    parser.add_argument("--interval", type=int, default=30, help="Polling interval in seconds for --loop")
    parser.add_argument("--limit", type=int, default=50, help="Max messages per channel per poll")
    parser.add_argument("--env-file", help="Optional env file containing Discord settings")
    parser.add_argument("--channel-ids", help="Override DISCORD_CHANNEL_IDS")
    parser.add_argument("--inbox-dir", help="Override DISCORD_INBOX_DIR")
    parser.add_argument("--state-file", help="Override DISCORD_STATE_FILE")
    parser.add_argument("--allow-bots", action="store_true", help="Capture bot/webhook messages")
    parser.add_argument("--dry-config", action="store_true", help="Validate configuration without calling Discord")
    args = parser.parse_args()

    if args.env_file:
        load_env_file(Path(args.env_file))

    token = os.environ.get("DISCORD_BOT_TOKEN")
    channel_ids = parse_id_list(args.channel_ids or os.environ.get("DISCORD_CHANNEL_IDS"), required=True)
    allowed_user_ids = set(parse_id_list(os.environ.get("DISCORD_ALLOWED_USER_IDS")))
    inbox_dir = Path(args.inbox_dir or os.environ.get("DISCORD_INBOX_DIR", str(DEFAULT_INBOX_DIR))).resolve()
    state_file = Path(args.state_file or os.environ.get("DISCORD_STATE_FILE", str(DEFAULT_STATE_FILE))).resolve()

    if not token:
        print("ERROR: DISCORD_BOT_TOKEN is required", file=sys.stderr)
        return 2
    if args.limit < 1 or args.limit > 100:
        print("ERROR: --limit must be between 1 and 100", file=sys.stderr)
        return 2
    if args.interval < 5:
        print("ERROR: --interval must be at least 5 seconds", file=sys.stderr)
        return 2

    if args.dry_config:
        print(f"inbox_dir={inbox_dir}")
        print(f"state_file={state_file}")
        print(f"channel_ids={channel_ids}")
        print(f"allowed_user_ids={sorted(allowed_user_ids) if allowed_user_ids else '(all users)'}")
        print(f"allow_bots={args.allow_bots}")
        return 0

    if args.mark_seen:
        updated = mark_seen(token, channel_ids, state_file)
        print(f"marked latest message as seen for {updated} channel(s)")
        return 0

    if not args.loop:
        captured = pull_once(token, channel_ids, allowed_user_ids, inbox_dir, state_file, args.limit, args.allow_bots)
        print(f"done: captured {captured} message(s)")
        return 0

    print(f"polling Discord every {args.interval}s; writing to {inbox_dir}")
    while True:
        try:
            captured = pull_once(token, channel_ids, allowed_user_ids, inbox_dir, state_file, args.limit, args.allow_bots)
            if captured:
                print(f"poll captured {captured} message(s)")
        except Exception as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
