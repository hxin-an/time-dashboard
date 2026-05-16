"""
Parse Discord time-tracker captures into worklog evidence.

The raw Discord captures stay in `inbox/time/` as provenance. This script
derives objective time-session data under `life/worklog/data/` and updates one
human-facing dashboard at `life/worklog/time_dashboard.md`.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo


CORE_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INBOX_DIR = CORE_ROOT / "inbox" / "time"
DEFAULT_WORKLOG_DIR = CORE_ROOT / "life" / "worklog"
REVIEW_OVERRIDES_FILENAME = "time_session_review_overrides.json"
LOCAL_TZ = ZoneInfo("Asia/Taipei")
NEEDS_REVIEW_MINUTES = 180
STUDY_TARGET_DAILY_MIN = 240
STUDY_TARGET_WEEKLY_MIN = 1500
STUDY_TARGET_MONTHLY_MIN = 6000
REST_WEEKLY_DAYS: list[int] = []
REST_DAYS_PER_WEEK = 1
REST_DECISION_WEEKDAY = 1
REST_DATES: list[str] = []

CATEGORIES = {
    "course",
    "research",
    "self_study",
    "language",
    "admin",
    "leetcode",
    "entertainment",
    "rest",
    "other",
}
WORK_CATEGORIES = CATEGORIES - {"rest", "entertainment"}
COUNTED_STATUSES = {"ok"}
WORK_CATEGORY_ORDER = ["course", "research", "self_study", "language", "leetcode", "admin", "other"]
CATEGORY_COLORS = {
    "course": "#3b82f6",
    "research": "#16a34a",
    "self_study": "#7c3aed",
    "language": "#db2777",
    "leetcode": "#d97706",
    "admin": "#6b7280",
    "other": "#475569",
}

CATEGORY_ALIASES = {
    "課程": "course",
    "課業": "course",
    "研究": "research",
    "lab": "research",
    "project": "research",
    "自學": "self_study",
    "語言學習": "language",
    "語言": "language",
    "雜事": "admin",
    "刷題": "leetcode",
    "行政": "admin",
    "休息": "rest",
    "娛樂": "entertainment",
    "其他": "other",
}

CATEGORY_LABELS = {
    "course": "課業",
    "research": "研究",
    "self_study": "自學",
    "language": "語言",
    "admin": "雜事",
    "leetcode": "刷題",
    "entertainment": "娛樂",
    "rest": "休息",
    "other": "其他",
}


@dataclass
class Event:
    at: datetime
    kind: str
    category: str
    label: str
    message_id: str
    source_file: str


@dataclass
class Session:
    start: datetime
    end: datetime | None
    duration_min: int | None
    category: str
    label: str
    status: str
    start_message_id: str
    end_message_id: str
    source_file: str
    notes: str


def parse_heading_time(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d %H:%M").replace(tzinfo=LOCAL_TZ)


def parse_event_time(block: str, heading_at: datetime) -> datetime:
    match = re.search(r"^- created_at:\s*(.+)$", block, flags=re.MULTILINE)
    if not match:
        return heading_at
    try:
        parsed = datetime.fromisoformat(match.group(1).strip())
    except ValueError:
        return heading_at
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=LOCAL_TZ)
    return parsed.astimezone(LOCAL_TZ)


def parse_raw_text(block: str) -> str:
    match = re.search(r"Raw:\s*\n\s*```text\n(.*?)\n```", block, flags=re.DOTALL)
    return match.group(1).strip() if match else ""


def parse_message_id(block: str) -> str:
    match = re.search(r"^- message_id:\s*(\S+)", block, flags=re.MULTILINE)
    return match.group(1).strip() if match else ""


def parse_time_command(raw: str) -> tuple[str, str, str] | None:
    words = raw.strip().split()
    if not words:
        return None
    command = words[0].lower()
    if command in {"stop", "end", "結束", "停"}:
        return "stop", "", " ".join(words[1:]).strip()
    if command in CATEGORIES or command in CATEGORY_ALIASES:
        category = CATEGORY_ALIASES.get(command, command)
        return "start", category, " ".join(words[1:]).strip()
    if command not in {"start", "開始"}:
        return None
    if len(words) == 1:
        return "start", "other", ""

    raw_category = words[1].lower()
    category = CATEGORY_ALIASES.get(raw_category, raw_category)
    label_words = words[2:]
    if category not in CATEGORIES:
        category = "other"
        label_words = words[1:]
    return "start", category, " ".join(label_words).strip()


def read_events(inbox_dir: Path) -> list[Event]:
    events: list[Event] = []
    heading_re = re.compile(r"^## (\d{4}-\d{2}-\d{2} \d{2}:\d{2})$", flags=re.MULTILINE)

    for path in sorted(inbox_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        matches = list(heading_re.finditer(text))
        for index, match in enumerate(matches):
            block_end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            block = text[match.start():block_end]
            parsed_command = parse_time_command(parse_raw_text(block))
            if not parsed_command:
                continue
            kind, category, label = parsed_command
            heading_at = parse_heading_time(match.group(1))
            events.append(Event(
                at=parse_event_time(block, heading_at),
                kind=kind,
                category=category,
                label=label,
                message_id=parse_message_id(block),
                source_file=str(path.relative_to(CORE_ROOT)),
            ))

    return sorted(events, key=lambda event: (event.at, event.message_id))


def minutes_between(start: datetime, end: datetime) -> int:
    return max(0, round((end - start).total_seconds() / 60))


def build_sessions(events: list[Event]) -> list[Session]:
    sessions: list[Session] = []
    open_event: Event | None = None

    for event in events:
        if event.kind == "start":
            if open_event:
                duration = minutes_between(open_event.at, event.at)
                sessions.append(Session(
                    open_event.at,
                    event.at,
                    duration,
                    open_event.category,
                    open_event.label,
                    "needs_review",
                    open_event.message_id,
                    "",
                    open_event.source_file,
                    "closed_by_next_start",
                ))
            open_event = event
            continue

        if not open_event:
            sessions.append(Session(
                event.at,
                event.at,
                0,
                "other",
                event.label,
                "needs_review",
                "",
                event.message_id,
                event.source_file,
                "stop_without_start",
            ))
            continue

        duration = minutes_between(open_event.at, event.at)
        status = "needs_review" if duration > NEEDS_REVIEW_MINUTES else "ok"
        sessions.append(Session(
            open_event.at,
            event.at,
            duration,
            open_event.category,
            event.label or open_event.label,
            status,
            open_event.message_id,
            event.message_id,
            open_event.source_file,
            "duration_over_3h" if status == "needs_review" else "",
        ))
        open_event = None

    if open_event:
        sessions.append(Session(
            open_event.at,
            None,
            None,
            open_event.category,
            open_event.label,
            "open",
            open_event.message_id,
            "",
            open_event.source_file,
            "open_session",
        ))

    return sessions


def session_review_key(session: Session) -> str:
    message_id = session.start_message_id or session.end_message_id or "no-message-id"
    return f"{fmt_dt(session.start)}|{message_id}"


def apply_review_overrides(sessions: list[Session], worklog_dir: Path) -> None:
    path = worklog_dir / "data" / REVIEW_OVERRIDES_FILENAME
    if not path.exists():
        return
    payload = json.loads(path.read_text(encoding="utf-8"))
    overrides = payload.get("sessions", {})
    for session in sessions:
        override = overrides.get(session_review_key(session))
        if not override:
            continue
        status = override.get("status")
        if status:
            session.status = status
        note = override.get("note")
        if note:
            session.notes = f"{session.notes}; {note}" if session.notes else note


def fmt_dt(dt: datetime | None) -> str:
    return dt.isoformat(timespec="seconds") if dt else ""


def fmt_time(dt: datetime | None) -> str:
    return dt.strftime("%H:%M") if dt else ""


def fmt_duration(minutes: int | None) -> str:
    if minutes is None:
        return "open"
    hours, mins = divmod(minutes, 60)
    if hours and mins:
        return f"{hours}h {mins}m"
    if hours:
        return f"{hours}h"
    return f"{mins}m"


def completed(sessions: list[Session]) -> list[Session]:
    return [session for session in sessions if session.duration_min is not None]


def counted(sessions: list[Session]) -> list[Session]:
    return [
        session
        for session in completed(sessions)
        if session.status in COUNTED_STATUSES
    ]


def month_key(dt: datetime) -> str:
    return dt.strftime("%Y-%m")


def write_sessions_csv(sessions: list[Session], worklog_dir: Path) -> None:
    data_dir = worklog_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    by_month: dict[str, list[Session]] = defaultdict(list)
    for session in sessions:
        by_month[month_key(session.start)].append(session)
    by_month.setdefault(datetime.now(LOCAL_TZ).strftime("%Y-%m"), [])

    fields = [
        "date",
        "start",
        "end",
        "duration_min",
        "category",
        "label",
        "status",
        "start_message_id",
        "end_message_id",
        "source_file",
        "notes",
    ]
    for month, items in by_month.items():
        with (data_dir / f"time_sessions_{month}.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for item in items:
                writer.writerow({
                    "date": item.start.date().isoformat(),
                    "start": fmt_dt(item.start),
                    "end": fmt_dt(item.end),
                    "duration_min": "" if item.duration_min is None else item.duration_min,
                    "category": item.category,
                    "label": item.label,
                    "status": item.status,
                    "start_message_id": item.start_message_id,
                    "end_message_id": item.end_message_id,
                    "source_file": item.source_file,
                    "notes": item.notes,
                })


def write_daily_stats_json(sessions: list[Session], worklog_dir: Path) -> None:
    data_dir = worklog_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    by_month_day: dict[str, dict[str, dict]] = defaultdict(dict)

    for session in counted(sessions):
        month = month_key(session.start)
        day = session.start.date().isoformat()
        day_data = by_month_day[month].setdefault(day, {
            "date": day,
            "total_min": 0,
            "session_count": 0,
            "work_session_count": 0,
            "first_start_min": None,
            "last_end_min": None,
            "longest_session_min": 0,
            "work_first_start_min": None,
            "work_last_end_min": None,
            "work_longest_session_min": 0,
            "by_category": {category: 0 for category in sorted(CATEGORIES)},
            "status": Counter(),
            "labels": Counter(),
        })
        minutes = session.duration_min or 0
        is_work = session.category in WORK_CATEGORIES
        day_data["total_min"] += minutes
        day_data["session_count"] += 1
        if is_work:
            day_data["work_session_count"] += 1
        start_min = session.start.hour * 60 + session.start.minute
        if day_data["first_start_min"] is None or start_min < day_data["first_start_min"]:
            day_data["first_start_min"] = start_min
        if is_work and (day_data["work_first_start_min"] is None or start_min < day_data["work_first_start_min"]):
            day_data["work_first_start_min"] = start_min
        if session.end:
            end_min = session.end.hour * 60 + session.end.minute
            if day_data["last_end_min"] is None or end_min > day_data["last_end_min"]:
                day_data["last_end_min"] = end_min
            if is_work and (day_data["work_last_end_min"] is None or end_min > day_data["work_last_end_min"]):
                day_data["work_last_end_min"] = end_min
        if minutes > day_data["longest_session_min"]:
            day_data["longest_session_min"] = minutes
        if is_work and minutes > day_data["work_longest_session_min"]:
            day_data["work_longest_session_min"] = minutes
        day_data["by_category"][session.category] = day_data["by_category"].get(session.category, 0) + minutes
        day_data["status"][session.status] += 1
        if session.label:
            day_data["labels"][session.label] += minutes

    now = datetime.now(LOCAL_TZ)
    current_month = now.strftime("%Y-%m")
    previous_month_date = (now.replace(day=1) - timedelta(days=1))
    previous_month = previous_month_date.strftime("%Y-%m")
    by_month_day.setdefault(current_month, {})
    by_month_day.setdefault(previous_month, {})

    for month, days in list(by_month_day.items()):
        year, month_num = [int(part) for part in month.split("-")]
        month_start = datetime(year, month_num, 1, tzinfo=LOCAL_TZ)
        if month_num == 12:
            month_end = datetime(year + 1, 1, 1, tzinfo=LOCAL_TZ)
        else:
            month_end = datetime(year, month_num + 1, 1, tzinfo=LOCAL_TZ)
        cursor = month_start
        while cursor < month_end:
            day = cursor.date().isoformat()
            days.setdefault(day, {
                "date": day,
                "total_min": 0,
                "session_count": 0,
                "work_session_count": 0,
                "first_start_min": None,
                "last_end_min": None,
                "longest_session_min": 0,
                "work_first_start_min": None,
                "work_last_end_min": None,
                "work_longest_session_min": 0,
                "by_category": {category: 0 for category in sorted(CATEGORIES)},
                "status": Counter(),
                "labels": Counter(),
            })
            cursor += timedelta(days=1)

    for month, days in by_month_day.items():
        normalized_days = []
        for day in sorted(days):
            day_data = days[day]
            by_category = day_data["by_category"]
            main_category = ""
            if day_data["total_min"]:
                main_category = max(by_category.items(), key=lambda item: item[1])[0]
            normalized_days.append({
                "date": day_data["date"],
                "total_min": day_data["total_min"],
                "session_count": day_data["session_count"],
                "work_session_count": day_data["work_session_count"],
                "first_start_min": day_data["first_start_min"],
                "last_end_min": day_data["last_end_min"],
                "longest_session_min": day_data["longest_session_min"],
                "work_first_start_min": day_data["work_first_start_min"],
                "work_last_end_min": day_data["work_last_end_min"],
                "work_longest_session_min": day_data["work_longest_session_min"],
                "main_category": main_category,
                "by_category": by_category,
                "status": dict(day_data["status"]),
                "labels": dict(day_data["labels"].most_common(8)),
            })

        payload = {
            "month": month,
            "categories": sorted(CATEGORIES),
            "category_labels": CATEGORY_LABELS,
            "days": normalized_days,
        }
        (data_dir / f"time_daily_stats_{month}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


def sessions_in_range(sessions: list[Session], start: datetime, end: datetime) -> list[Session]:
    return [session for session in sessions if start <= session.start < end]


def category_table(sessions: list[Session]) -> str:
    totals: Counter = Counter()
    for session in counted(sessions):
        if session.category not in WORK_CATEGORIES:
            continue
        totals[session.category] += session.duration_min or 0
    total = sum(totals.values())
    lines = ["| Category | Time | % |", "| --- | ---: | ---: |"]
    if total == 0:
        lines.append("| other | 0m | 0% |")
        return "\n".join(lines)
    for category, minutes in sorted(totals.items(), key=lambda item: (-item[1], item[0])):
        label = CATEGORY_LABELS.get(category, category)
        lines.append(f"| {label} | {fmt_duration(minutes)} | {round(minutes * 100 / total)}% |")
    return "\n".join(lines)


def session_table(sessions: list[Session], limit: int = 20) -> str:
    lines = [
        '<table class="worklog-review-table">',
        "<thead><tr><th>Date</th><th>Start</th><th>End</th><th>Duration</th><th>Category</th><th>Label</th><th>Status</th></tr></thead>",
        "<tbody>",
    ]
    for session in sorted(sessions, key=lambda item: item.start, reverse=True)[:limit]:
        category = CATEGORY_LABELS.get(session.category, session.category)
        lines.append(
            "<tr>"
            f"<td>{session.start.date().isoformat()}</td>"
            f"<td>{fmt_time(session.start)}</td>"
            f"<td>{fmt_time(session.end)}</td>"
            f"<td class=\"num\">{fmt_duration(session.duration_min)}</td>"
            f"<td>{category}</td>"
            f"<td>{session.label}</td>"
            f"<td>{session.status}</td>"
            "</tr>"
        )
    if len(lines) == 3:
        lines.append('<tr><td colspan="7" class="empty">None</td></tr>')
    lines.extend(["</tbody>", "</table>"])
    return "\n".join(lines)


def dataviewjs_block(month: str, view: str) -> str:
    json_path = f"life/worklog/data/time_daily_stats_{month}.json"
    year, month_num = [int(part) for part in month.split("-")]
    if month_num == 1:
        prev_month = f"{year - 1}-12"
    else:
        prev_month = f"{year}-{month_num - 1:02d}"
    prev_json_path = f"life/worklog/data/time_daily_stats_{prev_month}.json"
    script = """
```dataviewjs
const raw = await dv.io.load("__JSON_PATH__");
const data = JSON.parse(raw);
let prevData = {days: []};
try {
  const prevRaw = await dv.io.load("__PREV_JSON_PATH__");
  prevData = JSON.parse(prevRaw);
} catch (e) {}
const view = "__VIEW__";
const cats = ["course", "research", "self_study", "language", "leetcode", "admin", "other"];
const labels = data.category_labels || {};
const color = {course:"#4f83ff", research:"#2fbf71", self_study:"#8b6cff", language:"#e56ab3", leetcode:"#f59f00", admin:"#8a8f98", rest:"#41b6c4", entertainment:"#ff6b6b", other:"#6c757d"};
const fmt = (min) => { const h = Math.floor((min || 0) / 60); const m = (min || 0) % 60; return h ? `${h}h${m ? " " + m + "m" : ""}` : `${m}m`; };
const targets = {daily:__TARGET_DAILY__, weekly:__TARGET_WEEKLY__, monthly:__TARGET_MONTHLY__};
const targetText = (cur, goal) => `${fmt(cur)} / ${fmt(goal)} (${goal ? Math.round((cur / goal) * 100) : 0}%)`;
const restConfig = {
  weeklyRestDays: __REST_WEEKLY_DAYS__,
  restDaysPerWeek: __REST_DAYS_PER_WEEK__,
  decisionWeekday: __REST_DECISION_WEEKDAY__,
  restDates: __REST_DATES__
};
const weekday = (iso) => new Date(`${iso}T00:00:00+08:00`).getDay();
const weekStart = (iso) => { const dt = new Date(`${iso}T00:00:00+08:00`); dt.setDate(dt.getDate() - ((dt.getDay() + 6) % 7)); return dt.toISOString().slice(0,10); };
const currentWeekRestDates = (iso) => restConfig.restDates.filter(date => weekStart(date) === weekStart(iso));
const isPlannedRest = (d) => restConfig.restDates.includes(d.date) || restConfig.weeklyRestDays.includes(weekday(d.date));
const isDecisionDay = (d) => weekday(d.date) === restConfig.decisionWeekday;
const expectedWorkDays = (days) => { const selected=days.filter(isPlannedRest).length; if(selected) return days.length - selected; const weeks=new Set(days.map(d=>weekStart(d.date))).size; return Math.max(0, days.length - Math.min(days.length, weeks * restConfig.restDaysPerWeek)); };
const expectedRollingWorkDays = (days) => { const selected=days.filter(isPlannedRest).length; if(selected) return days.length - selected; return Math.max(0, days.length - Math.min(restConfig.restDaysPerWeek, days.length)); };
const completionText = (active, expected) => `${active} / ${expected} (${expected ? Math.round((active / expected) * 100) : 0}%)`;
const todayIso = new Date().toLocaleDateString("sv-SE", {timeZone: "Asia/Taipei"});
const allDays = [...(prevData.days || []), ...(data.days || [])].reduce((map,d)=>map.set(d.date,d),new Map());
const timeline = [...allDays.values()].sort((a,b)=>a.date.localeCompare(b.date));
let todayIndex = timeline.findIndex(d => d.date === todayIso); if (todayIndex < 0) todayIndex = timeline.length - 1;
const today = timeline.find(d => d.date === todayIso) || {total_min:0, by_category:{}, session_count:0, work_session_count:0, longest_session_min:0, work_longest_session_min:0};
const recent7 = timeline.slice(Math.max(0, todayIndex - 6), todayIndex + 1);
const recent14 = timeline.slice(Math.max(0, todayIndex - 13), todayIndex + 1);
const prev7 = timeline.slice(Math.max(0, todayIndex - 13), Math.max(0, todayIndex - 6));
const prev14 = timeline.slice(Math.max(0, todayIndex - 27), Math.max(0, todayIndex - 13));
const dayWorkMin = (d) => cats.reduce((sum,c)=>sum+(d.by_category?.[c]||0),0);
const categoryTotals = (days) => { const totals=Object.fromEntries(cats.map(c=>[c,0])); for (const day of days) for (const c of cats) totals[c] += day.by_category?.[c] || 0; return totals; };
const mainWorkCategory = (d) => cats.reduce((best,c)=>(d.by_category?.[c]||0)>(d.by_category?.[best]||0)?c:best,"other");
const monthTotal = data.days.reduce((sum,d)=>sum+dayWorkMin(d),0);
const activeDays = data.days.filter(d=>dayWorkMin(d)>0).length;
const expectedMonthDays = expectedWorkDays(data.days);
const dailyAvg = activeDays ? Math.round(monthTotal/activeDays) : 0;
const expectedAvg = expectedMonthDays ? Math.round(monthTotal/expectedMonthDays) : 0;
const best = data.days.reduce((a,b)=>dayWorkMin(b)>dayWorkMin(a)?b:a,{by_category:{},date:""});
const catTotals = categoryTotals(data.days);
const rankedDays = data.days.filter(d=>dayWorkMin(d)>0).sort((a,b)=>dayWorkMin(b)-dayWorkMin(a)).slice(0,5);
const rankedCats = cats.map(c=>({key:c,label:labels[c]||c,total:catTotals[c]||0})).filter(c=>c.total>0).sort((a,b)=>b.total-a.total).slice(0,5);
const sumDays = (days) => days.reduce((sum, d) => sum + dayWorkMin(d), 0);
const pct = (cur, prev) => prev ? `${cur >= prev ? "+" : ""}${Math.round(((cur - prev) / prev) * 100)}%` : (cur ? "new" : "0%");
const style = document.createElement("style");
style.textContent = `.time-summary{display:grid;grid-template-columns:repeat(4,minmax(120px,1fr));gap:10px;margin:10px 0 16px}.time-card{border:1px solid var(--background-modifier-border);border-radius:10px;padding:10px 12px;background:var(--background-secondary)}.time-card-k{color:var(--text-muted);font-size:12px}.time-card-v{font-size:22px;font-weight:750;margin-top:4px}.time-empty{border:1px dashed var(--background-modifier-border);border-radius:10px;padding:18px;color:var(--text-muted);background:var(--background-secondary);margin:10px 0}.time-legend{display:flex;flex-wrap:wrap;gap:8px 12px;margin:8px 0 12px;font-size:12px;color:var(--text-muted)}.time-dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:4px}.time-section-title{font-size:13px;font-weight:650;margin:14px 0 6px;color:var(--text-muted)}.time-month-grid{display:grid;grid-template-columns:repeat(7,minmax(48px,1fr));gap:6px;margin:8px 0 16px;max-width:780px}.time-day{border:1px solid var(--background-modifier-border);border-radius:8px;min-height:58px;padding:6px;background:var(--background-secondary);box-shadow:inset 0 1px 0 rgba(255,255,255,.04)}.time-day.rest{border-style:dashed}.time-date{font-size:11px;color:var(--text-muted)}.time-total{font-size:13px;font-weight:650;margin-top:4px}.time-cat{height:5px;border-radius:4px;margin-top:7px;opacity:.9}.time-chart{width:100%;max-width:780px;height:150px;border:1px solid var(--background-modifier-border);border-radius:10px;background:var(--background-secondary);margin:8px 0 16px;overflow:hidden}.time-chart.tall{height:190px}.time-stack{display:flex;height:24px;width:100%;max-width:780px;overflow:hidden;border-radius:999px;background:var(--background-secondary);border:1px solid var(--background-modifier-border)}.time-stack-part{height:100%;min-width:2px}.time-pie-wrap{display:grid;grid-template-columns:180px minmax(220px,1fr);gap:16px;align-items:center;max-width:780px;margin:8px 0 16px}.time-pie{width:160px;aspect-ratio:1;border-radius:50%;border:1px solid var(--background-modifier-border)}.time-pie-legend{border:1px solid var(--background-modifier-border);border-radius:8px;background:var(--background-secondary);overflow:hidden}.time-pie-row{display:grid;grid-template-columns:14px 1fr auto auto;gap:8px;align-items:center;padding:7px 10px;border-bottom:1px solid var(--background-modifier-border);font-size:13px}.time-pie-row:last-child{border-bottom:0}.time-pie-swatch{width:10px;height:10px;border-radius:50%}.time-pie-val,.time-pie-pct{font-variant-numeric:tabular-nums;font-weight:650}.time-pie-pct{color:var(--text-muted)}.time-rank-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;max-width:780px;margin:14px 0 16px}.time-rank-panel{min-width:0}.time-rank-title{font-size:13px;font-weight:650;margin:0 0 6px;color:var(--text-muted)}.time-rank{border:1px solid var(--background-modifier-border);border-radius:8px;background:var(--background-secondary);overflow:hidden}.time-rank-row{display:grid;grid-template-columns:34px minmax(0,1fr) auto;gap:10px;align-items:center;padding:8px 10px;border-bottom:1px solid var(--background-modifier-border)}.time-rank-row:last-child{border-bottom:0}.time-rank-no{font-weight:750;color:var(--text-accent)}.time-rank-name{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.time-rank-val{font-variant-numeric:tabular-nums;font-weight:650;white-space:nowrap}.time-bars{display:grid;gap:7px;max-width:780px;margin:8px 0 16px}.time-bar-row{display:grid;grid-template-columns:88px minmax(0,1fr) auto;gap:10px;align-items:center}.time-bar-name{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--text-muted);font-size:13px}.time-bar-track{height:10px;border-radius:999px;background:var(--background-secondary);border:1px solid var(--background-modifier-border);overflow:hidden}.time-bar-fill{height:100%;min-width:2px}.time-bar-val{font-variant-numeric:tabular-nums;font-weight:650;white-space:nowrap;font-size:13px}@media (max-width:650px){.time-summary{grid-template-columns:repeat(2,minmax(0,1fr))}.time-month-grid{grid-template-columns:repeat(4,minmax(0,1fr))}.time-pie-wrap,.time-rank-grid,.time-bars{grid-template-columns:1fr}.time-pie{justify-self:center}}.time-tip{position:fixed;z-index:9999;pointer-events:none;background:var(--background-primary);border:1px solid var(--background-modifier-border);box-shadow:0 8px 24px rgba(0,0,0,.18);border-radius:8px;padding:8px 10px;font-size:12px;color:var(--text-normal);max-width:240px;white-space:pre-line;opacity:0;transform:translate(10px,10px);transition:opacity .08s ease}`;
dv.container.appendChild(style);
const cards = (items) => { const el=dv.el("div","",{cls:"time-summary"}); el.innerHTML=items.map(([k,v])=>`<div class="time-card"><div class="time-card-k">${k}</div><div class="time-card-v">${v}</div></div>`).join(""); };
const empty = (msg) => dv.el("div", msg, {cls:"time-empty"});
const legend = () => { const el=dv.el("div","",{cls:"time-legend"}); el.innerHTML=cats.map(c=>`<span><i class="time-dot" style="background:${color[c]}"></i>${labels[c]||c}</span>`).join(""); };
const tip=dv.el("div","",{cls:"time-tip"});
const showTip=(text,ev)=>{tip.textContent=text||"";tip.style.left=ev.clientX+12+"px";tip.style.top=ev.clientY+12+"px";tip.style.opacity="1";};
const hideTip=()=>{tip.style.opacity="0";};
const bindTips=(root)=>{root.querySelectorAll("[data-tip]").forEach(el=>{el.addEventListener("mousemove",ev=>showTip(el.dataset.tip,ev));el.addEventListener("mouseleave",hideTip);});};
const stackBar = (totals) => { const total=Object.values(totals).reduce((a,b)=>a+b,0); const el=dv.el("div","",{cls:"time-stack"}); el.innerHTML=total?cats.filter(c=>(totals[c]||0)>0).map(c=>`<div class="time-stack-part" data-tip="${labels[c]||c}&#10;${fmt(totals[c])}&#10;${Math.round((totals[c]/total)*100)}%" style="width:${(totals[c]/total)*100}%;background:${color[c]}"></div>`).join(""):`<div class="time-stack-part" style="width:100%;background:var(--background-modifier-border)"></div>`; bindTips(el); };
const pieChart = (title, totals) => { const rows=cats.map(c=>({key:c,label:labels[c]||c,total:totals[c]||0})).filter(r=>r.total>0); const total=rows.reduce((s,r)=>s+r.total,0); dv.el("div",title,{cls:"time-section-title"}); const el=dv.el("div","",{cls:"time-pie-wrap"}); if(!total){el.innerHTML=`<div class="time-pie" style="background:var(--background-modifier-border)"></div><div class="time-pie-legend"><div class="time-pie-row">No data</div></div>`; return;} let acc=0; const gradient=rows.map(r=>{const start=(acc/total)*100; acc+=r.total; const end=(acc/total)*100; return `${color[r.key]} ${start}% ${end}%`;}).join(","); el.innerHTML=`<div class="time-pie" data-tip="${rows.map(r=>`${r.label} ${Math.round((r.total/total)*100)}%`).join("&#10;")}" style="background:conic-gradient(${gradient})"></div><div class="time-pie-legend">${rows.map(r=>`<div class="time-pie-row"><span class="time-pie-swatch" style="background:${color[r.key]}"></span><span>${r.label}</span><span class="time-pie-val">${fmt(r.total)}</span><span class="time-pie-pct">${Math.round((r.total/total)*100)}%</span></div>`).join("")}</div>`; bindTips(el); };
const categoryBars = (title, totals) => { const rows=cats.map(c=>({key:c,label:labels[c]||c,total:totals[c]||0})).filter(r=>r.total>0).sort((a,b)=>b.total-a.total); const max=Math.max(1,...rows.map(r=>r.total)); dv.el("div",title,{cls:"time-section-title"}); const el=dv.el("div","",{cls:"time-bars"}); el.innerHTML=rows.length?rows.map(r=>`<div class="time-bar-row"><div class="time-bar-name">${r.label}</div><div class="time-bar-track"><div class="time-bar-fill" style="width:${Math.max(2,(r.total/max)*100)}%;background:${color[r.key]}"></div></div><div class="time-bar-val">${fmt(r.total)}</div></div>`).join(""):`<div class="time-empty">No data</div>`; };
const rankRows = (title, rows) => `<div class="time-rank-panel"><div class="time-rank-title">${title}</div><div class="time-rank">${rows.length?rows.map((r,i)=>`<div class="time-rank-row"><div class="time-rank-no">#${i+1}</div><div class="time-rank-name">${r.name}</div><div class="time-rank-val">${fmt(r.total)}</div></div>`).join(""):`<div class="time-rank-row"><div class="time-rank-name">No data</div></div>`}</div></div>`;
const rankGrid = (groups) => { const grid=dv.el("div","",{cls:"time-rank-grid"}); grid.innerHTML=groups.map(g=>rankRows(g.title,g.rows)).join(""); };
const rankedCategoryRows = (totals) => cats.map(c=>({key:c,name:labels[c]||c,total:totals[c]||0})).filter(c=>c.total>0).sort((a,b)=>b.total-a.total).slice(0,5);
const dayRankRows = (days) => days.filter(d=>dayWorkMin(d)>0).sort((a,b)=>dayWorkMin(b)-dayWorkMin(a)).slice(0,5).map(d=>({name:d.date.slice(5),total:dayWorkMin(d)}));
const lineChart = (days, accessor, stroke="var(--text-accent)") => { const el=dv.el("div","",{cls:"time-chart"}); const w=780,h=150,pad=24; const max=Math.max(60,...days.map(accessor)); const points=days.map((d,i)=>{const x=pad+(days.length<=1?0:i*((w-pad*2)/(days.length-1))); const y=h-pad-(accessor(d)/max)*(h-pad*2); return [x,y,d,i];}); const poly=points.map(p=>`${p[0]},${p[1]}`).join(" "); const step=Math.max(1,Math.ceil(days.length/6)); const grid=[.25,.5,.75,1].map(r=>{const yy=h-pad-r*(h-pad*2); return `<line x1="${pad}" x2="${w-pad}" y1="${yy}" y2="${yy}" stroke="var(--background-modifier-border)" stroke-width="1" vector-effect="non-scaling-stroke"/><text x="4" y="${yy+4}" font-size="10" fill="var(--text-muted)">${fmt(Math.round(max*r))}</text>`;}).join(""); el.innerHTML=`<svg viewBox="0 0 ${w} ${h}" width="100%" height="150" preserveAspectRatio="none">${grid}<polyline points="${poly}" fill="none" stroke="${stroke}" stroke-width="3" vector-effect="non-scaling-stroke"/>${points.map(p=>`<circle cx="${p[0]}" cy="${p[1]}" r="5" fill="${stroke}" data-tip="${p[2].date}&#10;${fmt(accessor(p[2]))}"></circle>`).join("")}${points.filter(p=>p[3]===0||p[3]===points.length-1||p[3]%step===0).map(p=>`<text x="${p[0]}" y="${h-5}" font-size="10" text-anchor="middle" fill="var(--text-muted)">${p[2].date.slice(5)}</text>`).join("")}</svg>`; bindTips(el); };
if(view==="daily"){ const todayWork=dayWorkMin(today); const plannedRest=isPlannedRest(today); const weekRest=currentWeekRestDates(today.date); const restStatus=weekRest.length?weekRest.map(d=>d.slice(5)).join(", "):(isDecisionDay(today)?"Pick today":"Unset"); const plan=plannedRest?"Rest":(isDecisionDay(today)?"Decide":"Work"); cards([["Today",fmt(todayWork)],["Target",targetText(todayWork,targets.daily)],["Plan",plan],["Rest Rule",`${restConfig.restDaysPerWeek} / week`],["This Week Rest",restStatus],["Sessions",String(today.work_session_count||0)],["Longest",fmt(today.work_longest_session_min||0)],["Active",todayWork?"Yes":(plannedRest?"Rest":"No")]]); if(!todayWork) empty(plannedRest ? "今天是設定休息日，沒有正式做事時間紀錄。" : (isDecisionDay(today) ? "今天是本週休息日決策日，目前還沒有正式做事時間紀錄。" : "今天還沒有正式做事時間紀錄。")); else { legend(); const t=categoryTotals([today]); stackBar(t); rankGrid([{title:"今日類別排名",rows:rankedCategoryRows(t)}]); } }
if(view==="weekly"){ const total=sumDays(recent7); const active=recent7.filter(d=>dayWorkMin(d)>0).length; const expected=expectedRollingWorkDays(recent7); const t=categoryTotals(recent7); cards([["7 Days",fmt(total)],["Target",targetText(total,targets.weekly)],["Daily Avg",fmt(active?Math.round(total/active):0)],["Expected Avg",fmt(expected?Math.round(total/expected):0)],["Active Days",String(active)],["Expected",String(expected)],["Completion",completionText(active,expected)],["Best",fmt(Math.max(0,...recent7.map(d=>dayWorkMin(d))))]]); if(!total) empty("最近一週還沒有正式做事時間紀錄。"); else { lineChart(recent7,d=>dayWorkMin(d)); categoryBars("近 7 天類別長條", t); rankGrid([{title:"近 7 天日排名",rows:dayRankRows(recent7)},{title:"近 7 天類別排名",rows:rankedCategoryRows(t)}]); } }
if(view==="monthly"){ cards([["Month",fmt(monthTotal)],["Target",targetText(monthTotal,targets.monthly)],["Daily Avg",fmt(dailyAvg)],["Expected Avg",fmt(expectedAvg)],["Active Days",String(activeDays)],["Expected",String(expectedMonthDays)],["Completion",completionText(activeDays,expectedMonthDays)],["Best Day",best.date?best.date.slice(5):"-"]]); if(!monthTotal){empty("本月還沒有正式做事時間紀錄。"); return;} legend(); const max=Math.max(60,...data.days.map(d=>dayWorkMin(d))); const grid=dv.el("div","",{cls:"time-month-grid"}); for(const day of data.days){ const work=dayWorkMin(day); const main=mainWorkCategory(day); const intensity=Math.max(.12,work/max); const plannedRest=isPlannedRest(day); const cell=document.createElement("div"); cell.className=plannedRest?"time-day rest":"time-day"; cell.style.boxShadow=`inset 0 -3px 0 ${color[main]||color.other}`; cell.style.opacity=work?String(.55+intensity*.45):".45"; cell.dataset.tip=`${day.date}\\n${plannedRest?"planned rest":"planned work"}\\n${fmt(work)}\\n${labels[main]||main}\\n${day.session_count||0} sessions`; cell.innerHTML=`<div class="time-date">${day.date.slice(5)}</div><div class="time-total">${fmt(work)}</div><div class="time-cat" style="background:${color[main]||color.other}"></div>`; grid.appendChild(cell);} bindTips(grid); stackBar(catTotals); pieChart("本月類別占比", catTotals); categoryBars("本月類別長條", catTotals); rankGrid([{title:"本月日排名",rows:rankedDays.map(d=>({name:d.date.slice(5),total:dayWorkMin(d)}))},{title:"本月類別排名",rows:rankedCats.map(c=>({name:c.label,total:c.total}))}]); }
if(view==="trend"){
  if(!monthTotal){empty("有時間紀錄後，這裡會顯示週期比較、近 14 天、累積曲線、開始/結束時間。"); return;}
  const cur7 = sumDays(recent7), old7 = sumDays(prev7);
  const cur14 = sumDays(recent14), old14 = sumDays(prev14);
  const dayOfMonth = Number(todayIso.slice(8));
  const prevSamePeriod = prevData.days.slice(0, dayOfMonth);
  const prevMonthToDate = sumDays(prevSamePeriod);
  cards([
    ["7d vs prev", `${fmt(cur7)} / ${pct(cur7, old7)}`],
    ["14d vs prev", `${fmt(cur14)} / ${pct(cur14, old14)}`],
    ["MTD vs last", `${fmt(monthTotal)} / ${pct(monthTotal, prevMonthToDate)}`],
    ["Last MTD", fmt(prevMonthToDate)]
  ]);
  dv.el("div","近 14 天",{cls:"time-section-title"});
  lineChart(recent14,d=>dayWorkMin(d));
  rankGrid([{title:"近 14 天日排名",rows:dayRankRows(recent14)},{title:"近 14 天類別排名",rows:rankedCategoryRows(categoryTotals(recent14))}]);
  dv.el("div","本月累積",{cls:"time-section-title"});
  let running=0;
  const cumulative=data.days.map(d=>({date:d.date,total_min:running+=dayWorkMin(d),by_category:d.by_category}));
  lineChart(cumulative,d=>d.total_min,"#ff7a1a");
  dv.el("div","開始 / 結束時間",{cls:"time-section-title"});
  const rhythmDays=data.days.filter(d=>d.work_first_start_min!==null||d.work_last_end_min!==null);
  const el=dv.el("div","",{cls:"time-chart tall"});
  const w=780,h=190,pad=26,minClock=6*60,maxClock=26*60;
  const y=m=>pad+((m-minClock)/(maxClock-minClock))*(h-pad*2);
  const x=(i,n)=>pad+(n<=1?0:i*((w-pad*2)/(n-1)));
  const ticks=[8,12,16,20,24];
  el.innerHTML=`<svg viewBox="0 0 ${w} ${h}" width="100%" height="190" preserveAspectRatio="none">${ticks.map(hr=>`<line x1="${pad}" x2="${w-pad}" y1="${y(hr*60)}" y2="${y(hr*60)}" stroke="var(--background-modifier-border)" stroke-dasharray="4 5"/><text x="4" y="${y(hr*60)+4}" font-size="10" fill="var(--text-muted)">${hr}</text>`).join("")}${rhythmDays.map((d,i)=>{const xx=x(i,Math.max(1,rhythmDays.length)); const s=d.work_first_start_min??d.work_last_end_min; const e=d.work_last_end_min??d.work_first_start_min; const step=Math.max(1,Math.ceil(rhythmDays.length/6)); const label=(i===0||i===rhythmDays.length-1||i%step===0)?`<text x="${xx}" y="${h-5}" font-size="10" text-anchor="middle" fill="var(--text-muted)">${d.date.slice(8)}</text>`:""; return `<line x1="${xx}" x2="${xx}" y1="${y(s)}" y2="${y(e)}" stroke="#adb5bd" stroke-width="2"/><circle cx="${xx}" cy="${y(s)}" r="5" fill="#ff7a1a" data-tip="${d.date}&#10;start ${Math.floor(s/60)}:${String(s%60).padStart(2,'0')}"></circle><circle cx="${xx}" cy="${y(e)}" r="5" fill="#e9ecef" data-tip="${d.date}&#10;end ${Math.floor(e/60)}:${String(e%60).padStart(2,'0')}"></circle>${label}`;}).join("")}</svg>`; bindTips(el);
}
```
"""
    return (
        script
        .replace("__JSON_PATH__", json_path)
        .replace("__PREV_JSON_PATH__", prev_json_path)
        .replace("__VIEW__", view)
        .replace("__TARGET_DAILY__", str(STUDY_TARGET_DAILY_MIN))
        .replace("__TARGET_WEEKLY__", str(STUDY_TARGET_WEEKLY_MIN))
        .replace("__TARGET_MONTHLY__", str(STUDY_TARGET_MONTHLY_MIN))
        .replace("__REST_WEEKLY_DAYS__", json.dumps(REST_WEEKLY_DAYS))
        .replace("__REST_DAYS_PER_WEEK__", str(REST_DAYS_PER_WEEK))
        .replace("__REST_DECISION_WEEKDAY__", str(REST_DECISION_WEEKDAY))
        .replace("__REST_DATES__", json.dumps(REST_DATES, ensure_ascii=False))
    )


def dataviewjs_rollup_block(months: list[str], view: str, year: int) -> str:
    month_list = ", ".join(f'"{month}"' for month in months)
    script = """
```dataviewjs
const months = [__MONTHS__];
const view = "__VIEW__";
const targetYear = "__YEAR__";
const cats = ["course", "research", "self_study", "language", "leetcode", "admin", "other"];
const color = {course:"#4f83ff", research:"#2fbf71", self_study:"#8b6cff", language:"#e56ab3", leetcode:"#f59f00", admin:"#8a8f98", other:"#6c757d"};
const fmt = (min) => { const h = Math.floor((min || 0) / 60); const m = (min || 0) % 60; return h ? `${h}h${m ? " " + m + "m" : ""}` : `${m}m`; };
const restConfig = {
  weeklyRestDays: __REST_WEEKLY_DAYS__,
  restDaysPerWeek: __REST_DAYS_PER_WEEK__,
  decisionWeekday: __REST_DECISION_WEEKDAY__,
  restDates: __REST_DATES__
};
const weekday = (iso) => new Date(`${iso}T00:00:00+08:00`).getDay();
const weekStart = (iso) => { const dt = new Date(`${iso}T00:00:00+08:00`); dt.setDate(dt.getDate() - ((dt.getDay() + 6) % 7)); return dt.toISOString().slice(0,10); };
const isPlannedRest = (d) => restConfig.restDates.includes(d.date) || restConfig.weeklyRestDays.includes(weekday(d.date));
const expectedWorkDays = (items) => { const selected=items.filter(isPlannedRest).length; if(selected) return items.length - selected; const weeks=new Set(items.map(d=>weekStart(d.date))).size; return Math.max(0, items.length - Math.min(items.length, weeks * restConfig.restDaysPerWeek)); };
const completionText = (active, expected) => `${active} / ${expected} (${expected ? Math.round((active / expected) * 100) : 0}%)`;
const loaded = [];
for (const month of months) {
  try {
    const raw = await dv.io.load(`life/worklog/data/time_daily_stats_${month}.json`);
    loaded.push(JSON.parse(raw));
  } catch (e) {}
}
const labels = loaded[0]?.category_labels || {};
const allDays = loaded.flatMap(m => m.days || []);
const days = view === "year" ? allDays.filter(d => d.date.startsWith(targetYear + "-")) : allDays;
const dayWorkMin = (d) => cats.reduce((sum,c)=>sum+(d.by_category?.[c]||0),0);
const categoryTotals = (items) => { const totals=Object.fromEntries(cats.map(c=>[c,0])); for (const day of items) for (const c of cats) totals[c] += day.by_category?.[c] || 0; return totals; };
const byMonth = (items) => {
  const map = new Map();
  for (const day of items) map.set(day.date.slice(0,7), (map.get(day.date.slice(0,7)) || 0) + dayWorkMin(day));
  return [...map.entries()].sort((a,b)=>a[0].localeCompare(b[0])).map(([name,total])=>({name,total}));
};
const total = days.reduce((sum,d)=>sum+dayWorkMin(d),0);
const activeDays = days.filter(d=>dayWorkMin(d)>0).length;
const expectedDays = expectedWorkDays(days);
const expectedAvg = expectedDays ? Math.round(total / expectedDays) : 0;
const bestDay = days.reduce((a,b)=>dayWorkMin(b)>dayWorkMin(a)?b:a,{date:"-",by_category:{}});
const totals = categoryTotals(days);
const pieCats = cats.map(c=>({name:labels[c]||c,total:totals[c]||0,key:c})).filter(r=>r.total>0).sort((a,b)=>b.total-a.total);
const rankedCats = pieCats.slice(0,6);
const rankedDays = days.filter(d=>dayWorkMin(d)>0).sort((a,b)=>dayWorkMin(b)-dayWorkMin(a)).slice(0,6).map(d=>({name:d.date,total:dayWorkMin(d)}));
const rankedMonths = byMonth(days).filter(r=>r.total>0).sort((a,b)=>b.total-a.total).slice(0,6);
const style = document.createElement("style");
style.textContent = `.time-summary{display:grid;grid-template-columns:repeat(4,minmax(120px,1fr));gap:10px;margin:10px 0 16px}.time-card{border:1px solid var(--background-modifier-border);border-radius:10px;padding:10px 12px;background:var(--background-secondary)}.time-card-k{color:var(--text-muted);font-size:12px}.time-card-v{font-size:22px;font-weight:750;margin-top:4px}.time-section-title{font-size:13px;font-weight:650;margin:14px 0 6px;color:var(--text-muted)}.time-empty{border:1px dashed var(--background-modifier-border);border-radius:10px;padding:18px;color:var(--text-muted);background:var(--background-secondary);margin:10px 0}.time-pie-wrap{display:grid;grid-template-columns:180px minmax(220px,1fr);gap:16px;align-items:center;max-width:780px;margin:8px 0 16px}.time-pie{width:160px;aspect-ratio:1;border-radius:50%;border:1px solid var(--background-modifier-border)}.time-pie-legend,.time-rank{border:1px solid var(--background-modifier-border);border-radius:8px;background:var(--background-secondary);overflow:hidden}.time-pie-row{display:grid;grid-template-columns:14px 1fr auto auto;gap:8px;align-items:center;padding:7px 10px;border-bottom:1px solid var(--background-modifier-border);font-size:13px}.time-pie-row:last-child{border-bottom:0}.time-pie-swatch{width:10px;height:10px;border-radius:50%}.time-pie-val,.time-pie-pct,.time-rank-val{font-variant-numeric:tabular-nums;font-weight:650;white-space:nowrap}.time-pie-pct{color:var(--text-muted)}.time-rank-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;max-width:980px;margin:14px 0 16px}.time-rank-title{font-size:13px;font-weight:650;margin:0 0 6px;color:var(--text-muted)}.time-rank-row{display:grid;grid-template-columns:34px minmax(0,1fr) auto;gap:10px;align-items:center;padding:8px 10px;border-bottom:1px solid var(--background-modifier-border)}.time-rank-row:last-child{border-bottom:0}.time-rank-no{font-weight:750;color:var(--text-accent)}.time-rank-name{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}@media (max-width:760px){.time-summary{grid-template-columns:repeat(2,minmax(0,1fr))}.time-pie-wrap,.time-rank-grid,.time-bars{grid-template-columns:1fr}.time-pie{justify-self:center}}`;
dv.container.appendChild(style);
const cards = (items) => { const el=dv.el("div","",{cls:"time-summary"}); el.innerHTML=items.map(([k,v])=>`<div class="time-card"><div class="time-card-k">${k}</div><div class="time-card-v">${v}</div></div>`).join(""); };
const rankRows = (title, rows) => `<div><div class="time-rank-title">${title}</div><div class="time-rank">${rows.length?rows.map((r,i)=>`<div class="time-rank-row"><div class="time-rank-no">#${i+1}</div><div class="time-rank-name">${r.name}</div><div class="time-rank-val">${fmt(r.total)}</div></div>`).join(""):`<div class="time-rank-row"><div class="time-rank-name">No data</div></div>`}</div></div>`;
const rankGrid = (groups) => { const grid=dv.el("div","",{cls:"time-rank-grid"}); grid.innerHTML=groups.map(g=>rankRows(g.title,g.rows)).join(""); };
const pieChart = (title) => { const rows=pieCats; dv.el("div",title,{cls:"time-section-title"}); const el=dv.el("div","",{cls:"time-pie-wrap"}); if(!total){el.innerHTML=`<div class="time-pie" style="background:var(--background-modifier-border)"></div><div class="time-pie-legend"><div class="time-pie-row">No data</div></div>`; return;} let acc=0; const gradient=rows.map(r=>{const start=(acc/total)*100; acc+=r.total; const end=(acc/total)*100; return `${color[r.key]} ${start}% ${end}%`;}).join(","); el.innerHTML=`<div class="time-pie" style="background:conic-gradient(${gradient})"></div><div class="time-pie-legend">${rows.map(r=>`<div class="time-pie-row"><span class="time-pie-swatch" style="background:${color[r.key]}"></span><span>${r.name}</span><span class="time-pie-val">${fmt(r.total)}</span><span class="time-pie-pct">${Math.round((r.total/total)*100)}%</span></div>`).join("")}</div>`; };
cards([
  [view === "year" ? "Year" : "All Time", fmt(total)],
  ["Daily Avg", fmt(activeDays ? Math.round(total / activeDays) : 0)],
  ["Expected Avg", fmt(expectedAvg)],
  ["Active Days", String(activeDays)],
  ["Expected", String(expectedDays)],
  ["Completion", completionText(activeDays, expectedDays)],
  ["Best Day", bestDay.date === "-" ? "-" : bestDay.date.slice(5)]
]);
if(!total){ dv.el("div", view === "year" ? "今年還沒有正式做事時間紀錄。" : "目前還沒有正式做事時間紀錄。", {cls:"time-empty"}); return; }
pieChart(view === "year" ? "今年類別占比" : "總累積類別占比");
rankGrid([
  {title: view === "year" ? "今年月份排名" : "總月份排名", rows: rankedMonths},
  {title: view === "year" ? "今年日排名" : "總日排名", rows: rankedDays},
  {title: view === "year" ? "今年類別排名" : "總類別排名", rows: rankedCats}
]);
```
"""
    return (
        script
        .replace("__MONTHS__", month_list)
        .replace("__VIEW__", view)
        .replace("__YEAR__", str(year))
        .replace("__REST_WEEKLY_DAYS__", json.dumps(REST_WEEKLY_DAYS))
        .replace("__REST_DAYS_PER_WEEK__", str(REST_DAYS_PER_WEEK))
        .replace("__REST_DECISION_WEEKDAY__", str(REST_DECISION_WEEKDAY))
        .replace("__REST_DATES__", json.dumps(REST_DATES, ensure_ascii=False))
    )


def html_escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def day_work_min(day: dict) -> int:
    by_category = day.get("by_category") or {}
    return sum(int(by_category.get(category) or 0) for category in WORK_CATEGORY_ORDER)


def load_month_stats(worklog_dir: Path) -> list[dict]:
    stats: list[dict] = []
    data_dir = worklog_dir / "data"
    for path in sorted(data_dir.glob("time_daily_stats_*.json")):
        try:
            stats.append(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
    return stats


def category_totals(days: list[dict]) -> dict[str, int]:
    totals = {category: 0 for category in WORK_CATEGORY_ORDER}
    for day in days:
        by_category = day.get("by_category") or {}
        for category in WORK_CATEGORY_ORDER:
            totals[category] += int(by_category.get(category) or 0)
    return totals


def expected_work_days(days: list[dict]) -> int:
    selected = [
        day for day in days
        if day["date"] in REST_DATES
        or (datetime.fromisoformat(f"{day['date']}T00:00:00+08:00").weekday() + 1) % 7 in REST_WEEKLY_DAYS
    ]
    if selected:
        return len(days) - len(selected)
    weeks = {datetime.fromisoformat(f"{day['date']}T00:00:00+08:00").isocalendar().week for day in days}
    return max(0, len(days) - min(len(days), len(weeks) * REST_DAYS_PER_WEEK))


def expected_rolling_work_days(days: list[dict]) -> int:
    selected = [
        day for day in days
        if day["date"] in REST_DATES
        or (datetime.fromisoformat(f"{day['date']}T00:00:00+08:00").weekday() + 1) % 7 in REST_WEEKLY_DAYS
    ]
    if selected:
        return len(days) - len(selected)
    return max(0, len(days) - min(REST_DAYS_PER_WEEK, len(days)))


def render_cards(items: list[tuple[str, str]]) -> str:
    return "<div class=\"site-cards\">" + "".join(
        f"<section class=\"site-card\"><div class=\"site-card-label\">{html_escape(label)}</div>"
        f"<div class=\"site-card-value\">{html_escape(value)}</div></section>"
        for label, value in items
    ) + "</div>"


def render_rank(title: str, rows: list[tuple[str, int]]) -> str:
    body = "".join(
        f"<tr><td>#{index}</td><td>{html_escape(name)}</td><td>{fmt_duration(total)}</td></tr>"
        for index, (name, total) in enumerate(rows, start=1)
    )
    if not body:
        body = "<tr><td colspan=\"3\">No data</td></tr>"
    return (
        f"<section><h3>{html_escape(title)}</h3><table class=\"site-table\">"
        "<thead><tr><th></th><th>Name</th><th>Time</th></tr></thead>"
        f"<tbody>{body}</tbody></table></section>"
    )


def render_bars(title: str, totals: dict[str, int], labels: dict[str, str]) -> str:
    rows = sorted(
        [(category, total) for category, total in totals.items() if total > 0],
        key=lambda item: item[1],
        reverse=True,
    )
    max_total = max([total for _, total in rows] or [1])
    bars = "".join(
        "<div class=\"bar-row\">"
        f"<span>{html_escape(labels.get(category, category))}</span>"
        "<div class=\"bar-track\">"
        f"<i style=\"width:{max(3, round(total * 100 / max_total))}%;background:{CATEGORY_COLORS[category]}\"></i>"
        "</div>"
        f"<strong>{fmt_duration(total)}</strong>"
        "</div>"
        for category, total in rows
    )
    if not bars:
        bars = "<p class=\"empty\">No data</p>"
    return f"<section><h3>{html_escape(title)}</h3><div class=\"bars\">{bars}</div></section>"


def render_line_chart(title: str, points: list[tuple[str, int]], color: str = "#2563eb") -> str:
    if not points:
        return f"<section><h3>{html_escape(title)}</h3><p class=\"empty\">No data</p></section>"
    width, height, pad_left, pad_right, pad_y = 760, 184, 58, 18, 28
    max_value = max(60, *(value for _, value in points))
    coords = []
    for index, (label, value) in enumerate(points):
        x = pad_left if len(points) == 1 else pad_left + index * ((width - pad_left - pad_right) / (len(points) - 1))
        y = height - pad_y - (value / max_value) * (height - pad_y * 2)
        coords.append((x, y, label, value))
    polyline = " ".join(f"{x:.1f},{y:.1f}" for x, y, _, _ in coords)
    labels = "".join(
        f"<text x=\"{x:.1f}\" y=\"{height - 5}\" text-anchor=\"middle\">{html_escape(label[-5:])}</text>"
        for index, (x, _, label, _) in enumerate(coords)
        if index == 0 or index == len(coords) - 1 or index % max(1, len(coords) // 5) == 0
    )
    dots = "".join(
        f"<circle cx=\"{x:.1f}\" cy=\"{y:.1f}\" r=\"4\"><title>{html_escape(label)} {fmt_duration(value)}</title></circle>"
        for x, y, label, value in coords
    )
    grid = "".join(
        f"<line x1=\"{pad_left}\" x2=\"{width - pad_right}\" y1=\"{height - pad_y - ratio * (height - pad_y * 2):.1f}\" "
        f"y2=\"{height - pad_y - ratio * (height - pad_y * 2):.1f}\" />"
        f"<text x=\"8\" y=\"{height - pad_y - ratio * (height - pad_y * 2) + 4:.1f}\">{fmt_duration(round(max_value * ratio))}</text>"
        for ratio in (0.25, 0.5, 0.75, 1)
    )
    return (
        f"<section><h3>{html_escape(title)}</h3><div class=\"chart\">"
        f"<svg viewBox=\"0 0 {width} {height}\" role=\"img\" aria-label=\"{html_escape(title)}\">"
        f"<g class=\"grid\">{grid}</g><polyline points=\"{polyline}\" style=\"stroke:{color}\" />"
        f"<g class=\"dots\" style=\"fill:{color}\">{dots}</g><g class=\"axis\">{labels}</g></svg></div></section>"
    )


def render_day_24h(title: str, sessions: list[Session], day: datetime, now: datetime) -> str:
    day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)
    rows = []
    total_by_hour = [0 for _ in range(24)]
    items = []
    for session in sessions:
        if session.category not in WORK_CATEGORY_ORDER:
            continue
        if session.status not in {"ok", "open"}:
            continue
        start = max(session.start, day_start)
        end_source = session.end or now
        end = min(end_source, day_end)
        if end <= day_start or start >= day_end or end <= start:
            continue
        start_min = int((start - day_start).total_seconds() // 60)
        end_min = int((end - day_start).total_seconds() // 60)
        items.append((start_min, end_min, session))
        for hour in range(start_min // 60, min(23, (max(end_min - 1, 0)) // 60) + 1):
            hour_start = hour * 60
            hour_end = hour_start + 60
            total_by_hour[hour] += max(0, min(end_min, hour_end) - max(start_min, hour_start))

    for hour in range(24):
        hour_start = hour * 60
        parts = []
        for start_min, end_min, session in items:
            overlap_start = max(start_min, hour_start)
            overlap_end = min(end_min, hour_start + 60)
            if overlap_end <= overlap_start:
                continue
            left = (overlap_start - hour_start) / 60 * 100
            width = max(1.5, (overlap_end - overlap_start) / 60 * 100)
            color = CATEGORY_COLORS.get(session.category, CATEGORY_COLORS["other"])
            label = CATEGORY_LABELS.get(session.category, session.category)
            status_class = " open" if session.status == "open" else ""
            tip = (
                f"{fmt_duration(overlap_end - overlap_start)} · {label}"
                f"{' · ' + session.label if session.label else ''}"
                f"{' · open' if session.status == 'open' else ''}"
            )
            parts.append(
                f"<i class=\"day24-segment{status_class}\" title=\"{html_escape(tip)}\" "
                f"style=\"left:{left:.2f}%;width:{width:.2f}%;background:{color}\"></i>"
            )
        rows.append(
            "<div class=\"day24-row\">"
            f"<span>{hour:02d}:00</span>"
            f"<div class=\"day24-track\">{''.join(parts)}</div>"
            f"<strong>{fmt_duration(total_by_hour[hour])}</strong>"
            "</div>"
        )

    total = sum(total_by_hour)
    subtitle = f"{day_start.date().isoformat()} · {fmt_duration(total)}"
    return (
        f"<section><h3>{html_escape(title)}</h3>"
        f"<div class=\"day24\"><div class=\"day24-head\"><span>{html_escape(subtitle)}</span>"
        "<span>00-24</span></div>"
        f"{''.join(rows)}</div></section>"
    )


def render_pie(title: str, totals: dict[str, int], labels: dict[str, str]) -> str:
    rows = [(category, total) for category, total in totals.items() if total > 0]
    total = sum(value for _, value in rows)
    if not total:
        return f"<section><h3>{html_escape(title)}</h3><p class=\"empty\">No data</p></section>"
    start = 0
    gradient_parts = []
    legend = []
    for category, value in rows:
        end = start + (value / total) * 100
        gradient_parts.append(f"{CATEGORY_COLORS[category]} {start:.2f}% {end:.2f}%")
        legend.append(
            "<tr>"
            f"<td><i style=\"background:{CATEGORY_COLORS[category]}\"></i>{html_escape(labels.get(category, category))}</td>"
            f"<td>{fmt_duration(value)}</td><td>{round(value * 100 / total)}%</td>"
            "</tr>"
        )
        start = end
    return (
        f"<section><h3>{html_escape(title)}</h3><div class=\"pie-wrap\">"
        f"<div class=\"pie\" style=\"background:conic-gradient({','.join(gradient_parts)})\"></div>"
        f"<table class=\"site-table pie-table\"><tbody>{''.join(legend)}</tbody></table>"
        "</div></section>"
    )


def render_month_grid(days: list[dict], labels: dict[str, str]) -> str:
    max_minutes = max([day_work_min(day) for day in days] or [60], default=60)
    cells = []
    for day in days:
        minutes = day_work_min(day)
        by_category = day.get("by_category") or {}
        main_category = max(WORK_CATEGORY_ORDER, key=lambda category: by_category.get(category) or 0)
        opacity = 0.34 + (0.66 * (minutes / max_minutes if max_minutes else 0))
        cells.append(
            f"<div class=\"month-cell\" title=\"{html_escape(day['date'])} {fmt_duration(minutes)}\" "
            f"style=\"border-bottom-color:{CATEGORY_COLORS[main_category]};opacity:{opacity:.2f}\">"
            f"<span>{html_escape(day['date'][5:])}</span><strong>{fmt_duration(minutes)}</strong>"
            f"<small>{html_escape(labels.get(main_category, main_category))}</small></div>"
        )
    return "<section><h3>本月月曆</h3><div class=\"month-grid\">" + "".join(cells) + "</div></section>"


def render_site_session_table(title: str, sessions: list[Session], limit: int) -> str:
    body = "".join(
        "<tr>"
        f"<td>{html_escape(session.start.date().isoformat())}</td>"
        f"<td>{html_escape(fmt_time(session.start))}</td>"
        f"<td>{html_escape(fmt_duration(session.duration_min))}</td>"
        f"<td>{html_escape(CATEGORY_LABELS.get(session.category, session.category))}</td>"
        f"<td>{html_escape(session.label)}</td>"
        f"<td>{html_escape(session.status)}</td>"
        "</tr>"
        for session in sorted(sessions, key=lambda item: item.start, reverse=True)[:limit]
    )
    if not body:
        body = "<tr><td colspan=\"6\">None</td></tr>"
    return (
        f"<section><h3>{html_escape(title)}</h3><div class=\"table-scroll\"><table class=\"site-table\">"
        "<thead><tr><th>Date</th><th>Start</th><th>Duration</th><th>Category</th><th>Label</th><th>Status</th></tr></thead>"
        f"<tbody>{body}</tbody></table></div></section>"
    )


def render_period_explorer(payload: dict) -> str:
    payload_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    return f"""
  <section id="explorer">
    <h2>Explorer</h2>
    <div class="period-controls" aria-label="Dashboard period controls">
      <div class="mode-tabs" role="group" aria-label="Period mode">
        <button type="button" data-mode="week">Week</button>
        <button type="button" data-mode="month">Month</button>
        <button type="button" data-mode="year">Year</button>
        <button type="button" data-mode="all">All</button>
      </div>
      <label class="period-field" id="year-field">Year<select id="year-select" aria-label="Select year"></select></label>
      <label class="period-field" id="month-field">Month<select id="month-select" aria-label="Select month"></select></label>
      <label class="period-field" id="period-field">Period<select id="period-select" aria-label="Select period"></select></label>
    </div>
    <div id="period-view"></div>
  </section>
  <script type="application/json" id="time-dashboard-data">{payload_json}</script>
  <script>
(() => {{
  const payload = JSON.parse(document.getElementById("time-dashboard-data").textContent);
  const days = payload.days || [];
  const cats = payload.categories || [];
  const labels = payload.labels || {{}};
  const colors = payload.colors || {{}};
  const today = payload.today;
  const targets = payload.targets || {{}};
  let mode = "month";

  const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, ch => ({{"&":"&amp;","<":"&lt;",">":"&gt;","\\\"":"&quot;","'":"&#39;"}}[ch]));
  const fmt = (min) => {{
    min = Math.round(Number(min) || 0);
    const h = Math.floor(min / 60);
    const m = min % 60;
    return h ? `${{h}}h${{m ? " " + m + "m" : ""}}` : `${{m}}m`;
  }};
  const dayWorkMin = (day) => cats.reduce((sum, cat) => sum + Number(day.by_category?.[cat] || 0), 0);
  const activeDays = (items) => items.filter(day => dayWorkMin(day) > 0).length;
  const categoryTotals = (items) => {{
    const totals = Object.fromEntries(cats.map(cat => [cat, 0]));
    for (const day of items) for (const cat of cats) totals[cat] += Number(day.by_category?.[cat] || 0);
    return totals;
  }};
  const dateObj = (iso) => new Date(`${{iso}}T00:00:00+08:00`);
  const dateIso = (date) => date.toLocaleDateString("sv-SE", {{timeZone:"Asia/Taipei"}});
  const addDays = (iso, count) => {{
    const d = dateObj(iso);
    d.setDate(d.getDate() + count);
    return dateIso(d);
  }};
  const weekStart = (iso) => {{
    const d = dateObj(iso);
    d.setDate(d.getDate() - ((d.getDay() + 6) % 7));
    return dateIso(d);
  }};
  const currentYear = today.slice(0, 4);
  const currentMonth = today.slice(5, 7);
  const yearOptions = () => {{
    const years = new Set(days.map(day => day.date.slice(0, 4)));
    years.add(currentYear);
    years.add(String(Number(currentYear) - 1));
    return [...years].sort().reverse();
  }};
  const monthOptions = () => Array.from({{length: 12}}, (_, index) => String(index + 1).padStart(2, "0"));
  const weekOptions = () => [...new Set(days.map(day => weekStart(day.date)))].sort().reverse().map(start => ({{key:start, label:`${{start}} to ${{addDays(start, 6)}}`}}));
  const selectedKey = () => {{
    if (mode === "all") return "all";
    if (mode === "year") return document.getElementById("year-select").value || currentYear;
    if (mode === "month") return `${{document.getElementById("year-select").value || currentYear}}-${{document.getElementById("month-select").value || currentMonth}}`;
    return document.getElementById("period-select").value || weekStart(today);
  }};
  const selectedLabel = (key) => {{
    if (mode === "all") return "All Time";
    if (mode === "year") return key;
    if (mode === "month") return key;
    return key.includes(" to ") ? key : `${{key}} to ${{addDays(key, 6)}}`;
  }};
  const selectedDays = (key) => {{
    if (mode === "all") return days;
    if (mode === "year") return days.filter(day => day.date.startsWith(key + "-"));
    if (mode === "month") return days.filter(day => day.date.startsWith(key));
    return days.filter(day => weekStart(day.date) === key);
  }};
  const cards = (items) => `<div class="site-cards">${{items.map(([k,v]) => `<section class="site-card"><div class="site-card-label">${{escapeHtml(k)}}</div><div class="site-card-value">${{escapeHtml(v)}}</div></section>`).join("")}}</div>`;
  const bars = (title, totals) => {{
    const rows = cats.map(cat => [cat, totals[cat] || 0]).filter(([,total]) => total > 0).sort((a,b) => b[1] - a[1]);
    const max = Math.max(1, ...rows.map(([,total]) => total));
    const body = rows.length ? rows.map(([cat,total]) => `<div class="bar-row"><span>${{escapeHtml(labels[cat] || cat)}}</span><div class="bar-track"><i style="width:${{Math.max(3, Math.round(total * 100 / max))}}%;background:${{colors[cat] || "#64748b"}}"></i></div><strong>${{fmt(total)}}</strong></div>`).join("") : `<p class="empty">No data</p>`;
    return `<section><h3>${{escapeHtml(title)}}</h3><div class="bars">${{body}}</div></section>`;
  }};
  const rank = (title, rows) => {{
    const body = rows.length ? rows.map(([name,total], index) => `<tr><td>#${{index + 1}}</td><td>${{escapeHtml(name)}}</td><td>${{fmt(total)}}</td></tr>`).join("") : `<tr><td colspan="3">No data</td></tr>`;
    return `<section><h3>${{escapeHtml(title)}}</h3><table class="site-table"><thead><tr><th></th><th>Name</th><th>Time</th></tr></thead><tbody>${{body}}</tbody></table></section>`;
  }};
  const line = (title, items, color = "#2563eb") => {{
    if (!items.length) return `<section><h3>${{escapeHtml(title)}}</h3><p class="empty">No data</p></section>`;
    const w = 760, h = 184, padLeft = 58, padRight = 18, padY = 28;
    const max = Math.max(60, ...items.map(dayWorkMin));
    const pts = items.map((day, index) => {{
      const x = items.length === 1 ? padLeft : padLeft + index * ((w - padLeft - padRight) / (items.length - 1));
      const y = h - padY - (dayWorkMin(day) / max) * (h - padY * 2);
      return [x, y, day.date, dayWorkMin(day), index];
    }});
    const step = Math.max(1, Math.floor(items.length / 5));
    const grid = [0.25,0.5,0.75,1].map(r => {{
      const y = h - padY - r * (h - padY * 2);
      return `<line x1="${{padLeft}}" x2="${{w-padRight}}" y1="${{y}}" y2="${{y}}" /><text x="8" y="${{y + 4}}">${{fmt(max * r)}}</text>`;
    }}).join("");
    const poly = pts.map(([x,y]) => `${{x.toFixed(1)}},${{y.toFixed(1)}}`).join(" ");
    const dots = pts.map(([x,y,date,total]) => `<circle cx="${{x.toFixed(1)}}" cy="${{y.toFixed(1)}}" r="4"><title>${{escapeHtml(date)}} ${{fmt(total)}}</title></circle>`).join("");
    const labelsHtml = pts.filter((p) => p[4] === 0 || p[4] === pts.length - 1 || p[4] % step === 0).map(([x,,date]) => `<text x="${{x.toFixed(1)}}" y="${{h-5}}" text-anchor="middle">${{escapeHtml(mode === "year" || mode === "all" ? date.slice(5) : date.slice(5))}}</text>`).join("");
    return `<section><h3>${{escapeHtml(title)}}</h3><div class="chart"><svg viewBox="0 0 ${{w}} ${{h}}"><g class="grid">${{grid}}</g><polyline points="${{poly}}" style="stroke:${{color}}" /><g class="dots" style="fill:${{color}}">${{dots}}</g><g class="axis">${{labelsHtml}}</g></svg></div></section>`;
  }};
  const monthGrid = (items) => {{
    if (mode !== "month") return "";
    if (!items.length) return `<section><h3>Month Grid</h3><p class="empty">No synced data for this month.</p></section>`;
    const max = Math.max(60, ...items.map(dayWorkMin));
    return `<section><h3>Month Grid</h3><div class="month-grid">${{items.map(day => {{
      const total = dayWorkMin(day);
      const main = cats.reduce((best, cat) => Number(day.by_category?.[cat] || 0) > Number(day.by_category?.[best] || 0) ? cat : best, cats[0]);
      const opacity = (0.34 + 0.66 * (total / max)).toFixed(2);
      return `<div class="month-cell" style="border-bottom-color:${{colors[main] || "#64748b"}};opacity:${{opacity}}"><span>${{escapeHtml(day.date.slice(5))}}</span><strong>${{fmt(total)}}</strong><small>${{escapeHtml(labels[main] || main)}}</small></div>`;
    }}).join("")}}</div></section>`;
  }};
  const render = () => {{
    const key = selectedKey();
    const items = selectedDays(key);
    const total = items.reduce((sum, day) => sum + dayWorkMin(day), 0);
    const active = activeDays(items);
    const totals = categoryTotals(items);
    const best = items.reduce((a,b) => dayWorkMin(b) > dayWorkMin(a) ? b : a, {{date:"-", by_category:{{}}}});
    const target = mode === "week" ? targets.weekly : mode === "month" ? targets.monthly : 0;
    const catRows = cats.map(cat => [labels[cat] || cat, totals[cat] || 0]).filter(([,v]) => v > 0).sort((a,b) => b[1] - a[1]).slice(0, 6);
    const dayRows = items.filter(day => dayWorkMin(day) > 0).sort((a,b) => dayWorkMin(b) - dayWorkMin(a)).slice(0, 6).map(day => [day.date, dayWorkMin(day)]);
    const cumulative = [];
    let running = 0;
    for (const day of items) {{ running += dayWorkMin(day); cumulative.push({{...day, by_category: {{other: running}} }}); }}
    document.getElementById("period-view").innerHTML = [
      cards([
        [selectedLabel(key), fmt(total)],
        ["Target", target ? `${{fmt(total)}} / ${{fmt(target)}}` : "-"],
        ["Daily Avg", fmt(active ? Math.round(total / active) : 0)],
        ["Active Days", `${{active}} / ${{items.length}}`],
        ["Best Day", best.date === "-" ? "-" : best.date],
      ]),
      line("Period Trend", items),
      mode === "month" || mode === "year" || mode === "all" ? line("Cumulative", cumulative, "#d97706") : "",
      monthGrid(items),
      `<div class="grid-2">${{bars("Categories", totals)}}${{rank("Category Rank", catRows)}}</div>`,
      rank("Day Rank", dayRows),
    ].join("");
  }};
  const fillSelect = (select, options, selected) => {{
    select.innerHTML = options.map(item => typeof item === "string" ? `<option value="${{escapeHtml(item)}}">${{escapeHtml(item)}}</option>` : `<option value="${{escapeHtml(item.key)}}">${{escapeHtml(item.label)}}</option>`).join("");
    select.value = selected;
  }};
  const refreshControls = () => {{
    document.querySelectorAll(".mode-tabs button").forEach(btn => btn.classList.toggle("active", btn.dataset.mode === mode));
    const yearField = document.getElementById("year-field");
    const monthField = document.getElementById("month-field");
    const periodField = document.getElementById("period-field");
    yearField.hidden = !(mode === "month" || mode === "year");
    monthField.hidden = mode !== "month";
    periodField.hidden = !(mode === "week" || mode === "all");
    if (mode === "month" || mode === "year") {{
      const previousYear = document.getElementById("year-select").value;
      fillSelect(document.getElementById("year-select"), yearOptions(), previousYear || currentYear);
    }}
    if (mode === "month") {{
      const previousMonth = document.getElementById("month-select").value;
      fillSelect(document.getElementById("month-select"), monthOptions().map(month => ({{key:month, label:`${{month}} 月`}})), previousMonth || currentMonth);
    }}
    if (mode === "week") {{
      const options = weekOptions();
      fillSelect(document.getElementById("period-select"), options, options[0]?.key || "");
    }} else if (mode === "all") {{
      fillSelect(document.getElementById("period-select"), [{{key:"all", label:"All synced time"}}], "all");
    }}
    render();
  }};
  document.querySelectorAll(".mode-tabs button").forEach(btn => btn.addEventListener("click", () => {{ mode = btn.dataset.mode; refreshControls(); }}));
  document.getElementById("year-select").addEventListener("change", render);
  document.getElementById("month-select").addEventListener("change", render);
  document.getElementById("period-select").addEventListener("change", render);
  refreshControls();
}})();
  </script>
"""


def generate_dashboard_site(sessions: list[Session], worklog_dir: Path) -> None:
    now = datetime.now(LOCAL_TZ)
    stats = load_month_stats(worklog_dir)
    all_days = sorted([day for month in stats for day in month.get("days", [])], key=lambda day: day["date"])
    current_month = now.strftime("%Y-%m")
    current_data = next((month for month in stats if month.get("month") == current_month), {"days": [], "category_labels": CATEGORY_LABELS})
    labels = current_data.get("category_labels") or CATEGORY_LABELS
    month_days = current_data.get("days", [])
    today_iso = now.date().isoformat()
    today_index = next((index for index, day in enumerate(all_days) if day["date"] == today_iso), len(all_days) - 1)
    today = next((day for day in all_days if day["date"] == today_iso), None)
    recent7 = all_days[max(0, today_index - 6):today_index + 1] if all_days else []
    recent14 = all_days[max(0, today_index - 13):today_index + 1] if all_days else []
    open_sessions = [session for session in sessions if session.status == "open"]
    needs_review = [session for session in sessions if session.status == "needs_review"]
    current = "None"
    if open_sessions:
        session = sorted(open_sessions, key=lambda item: item.start)[-1]
        current = (
            f"{CATEGORY_LABELS.get(session.category, session.category)}"
            f"{' / ' + session.label if session.label else ''}"
            f" · {fmt_duration(minutes_between(session.start, now))}"
        )

    today_minutes = day_work_min(today) if today else 0
    week_total = sum(day_work_min(day) for day in recent7)
    month_total = sum(day_work_min(day) for day in month_days)
    all_total = sum(day_work_min(day) for day in all_days)
    month_active = len([day for day in month_days if day_work_min(day) > 0])
    week_active = len([day for day in recent7 if day_work_min(day) > 0])
    best_day = max(month_days or [{"date": "-", "by_category": {}}], key=day_work_min)

    month_totals = category_totals(month_days)
    week_totals = category_totals(recent7)
    all_totals = category_totals(all_days)
    day_rank = [
        (day["date"], day_work_min(day))
        for day in sorted(month_days, key=day_work_min, reverse=True)
        if day_work_min(day) > 0
    ][:5]
    cat_rank = [
        (labels.get(category, category), total)
        for category, total in sorted(month_totals.items(), key=lambda item: item[1], reverse=True)
        if total > 0
    ][:5]
    explorer_payload = {
        "days": all_days,
        "categories": WORK_CATEGORY_ORDER,
        "labels": labels,
        "colors": CATEGORY_COLORS,
        "today": today_iso,
        "targets": {
            "weekly": STUDY_TARGET_WEEKLY_MIN,
            "monthly": STUDY_TARGET_MONTHLY_MIN,
        },
    }

    site = worklog_dir / "site"
    site.mkdir(parents=True, exist_ok=True)
    html_text = f"""<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light dark">
  <title>Time Dashboard</title>
  <style>
    :root {{ --bg:#f8fafc; --panel:#ffffff; --text:#111827; --muted:#64748b; --line:#dbe3ee; --accent:#2563eb; }}
    @media (prefers-color-scheme: dark) {{ :root {{ --bg:#0f172a; --panel:#111c2e; --text:#e5edf7; --muted:#9ba9bb; --line:#27364a; --accent:#60a5fa; }} }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; background:var(--bg); color:var(--text); font:15px/1.5 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }}
    header {{ position:sticky; top:0; z-index:1; background:color-mix(in srgb, var(--bg) 88%, transparent); backdrop-filter:blur(12px); border-bottom:1px solid var(--line); }}
    .wrap {{ width:min(1100px, 100%); margin:0 auto; padding:18px clamp(14px, 4vw, 30px); }}
    h1 {{ margin:0; font-size:clamp(25px, 7vw, 42px); line-height:1.05; letter-spacing:0; }}
    h2 {{ margin:28px 0 12px; font-size:22px; }}
    h3 {{ margin:18px 0 8px; font-size:15px; color:var(--muted); }}
    .meta {{ margin-top:8px; color:var(--muted); }}
    nav {{ display:flex; gap:8px; overflow-x:auto; padding-top:14px; }}
    nav a {{ color:var(--text); text-decoration:none; border:1px solid var(--line); border-radius:8px; padding:7px 10px; white-space:nowrap; background:var(--panel); }}
    .period-controls {{ display:flex; flex-wrap:wrap; gap:10px; align-items:center; margin:0 0 14px; }}
    .mode-tabs {{ display:flex; gap:6px; padding:4px; border:1px solid var(--line); border-radius:8px; background:var(--panel); }}
    .mode-tabs button {{ appearance:none; border:0; border-radius:6px; padding:8px 11px; color:var(--muted); background:transparent; font:inherit; font-weight:700; cursor:pointer; }}
    .mode-tabs button.active {{ color:#fff; background:var(--accent); }}
    .period-field {{ display:grid; gap:4px; color:var(--muted); font-size:12px; font-weight:700; }}
    .period-field[hidden] {{ display:none; }}
    .period-field select {{ min-width:min(180px, 100%); min-height:40px; border:1px solid var(--line); border-radius:8px; padding:0 10px; background:var(--panel); color:var(--text); font:inherit; font-size:15px; font-weight:500; }}
    .site-cards {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:10px; }}
    .site-card {{ min-width:0; background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:12px; }}
    .site-card-label {{ color:var(--muted); font-size:12px; }}
    .site-card-value {{ margin-top:4px; font-size:21px; font-weight:750; overflow-wrap:anywhere; }}
    .grid-2 {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:16px; }}
    .site-table {{ width:100%; border-collapse:collapse; background:var(--panel); border:1px solid var(--line); border-radius:8px; overflow:hidden; }}
    .site-table th,.site-table td {{ padding:9px 10px; border-bottom:1px solid var(--line); text-align:left; }}
    .site-table th {{ color:var(--muted); font-size:12px; font-weight:700; }}
    .site-table td:last-child,.site-table th:last-child {{ text-align:right; }}
    .table-scroll {{ overflow-x:auto; }}
    .bars {{ display:grid; gap:8px; }}
    .bar-row {{ display:grid; grid-template-columns:76px minmax(0,1fr) auto; gap:10px; align-items:center; }}
    .bar-row span {{ min-width:0; color:var(--muted); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
    .bar-row strong {{ font-variant-numeric:tabular-nums; white-space:nowrap; }}
    .bar-track {{ height:11px; background:var(--panel); border:1px solid var(--line); border-radius:999px; overflow:hidden; }}
    .bar-track i {{ display:block; height:100%; border-radius:999px; }}
    .chart {{ background:var(--panel); border:1px solid var(--line); border-radius:8px; overflow:hidden; }}
    svg {{ display:block; width:100%; height:170px; }}
    svg polyline {{ fill:none; stroke-width:3; vector-effect:non-scaling-stroke; }}
    svg .grid line {{ stroke:var(--line); stroke-width:1; vector-effect:non-scaling-stroke; }}
    svg text {{ fill:var(--muted); font-size:11px; }}
    .pie-wrap {{ display:grid; grid-template-columns:170px minmax(0,1fr); gap:16px; align-items:center; }}
    .pie {{ width:150px; aspect-ratio:1; border-radius:50%; border:1px solid var(--line); justify-self:center; }}
    .pie-table i {{ display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:8px; }}
    .month-grid {{ display:grid; grid-template-columns:repeat(7,minmax(0,1fr)); gap:7px; }}
    .month-cell {{ min-height:66px; padding:7px; background:var(--panel); border:1px solid var(--line); border-bottom:4px solid; border-radius:8px; }}
    .month-cell span,.month-cell small {{ display:block; color:var(--muted); font-size:11px; }}
    .month-cell strong {{ display:block; margin:4px 0 2px; font-size:14px; }}
    .day24 {{ display:grid; gap:4px; background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:10px; }}
    .day24-head,.day24-row {{ display:grid; grid-template-columns:48px minmax(0,1fr) 54px; gap:8px; align-items:center; }}
    .day24-head {{ color:var(--muted); font-size:12px; font-weight:700; }}
    .day24-head span:first-child {{ grid-column:1 / 3; }}
    .day24-row span {{ color:var(--muted); font-size:12px; font-variant-numeric:tabular-nums; }}
    .day24-row strong {{ text-align:right; font-size:12px; font-variant-numeric:tabular-nums; }}
    .day24-track {{ position:relative; height:14px; border:1px solid var(--line); border-radius:999px; background:color-mix(in srgb, var(--panel) 72%, var(--line)); overflow:hidden; }}
    .day24-segment {{ position:absolute; top:0; bottom:0; border-radius:999px; min-width:2px; }}
    .day24-segment.open {{ background-image:repeating-linear-gradient(45deg, rgba(255,255,255,.28) 0 5px, transparent 5px 10px); }}
    .empty {{ color:var(--muted); background:var(--panel); border:1px dashed var(--line); border-radius:8px; padding:14px; }}
    footer {{ color:var(--muted); border-top:1px solid var(--line); margin-top:32px; }}
    @media (max-width:760px) {{
      .site-cards {{ grid-template-columns:repeat(2,minmax(0,1fr)); }}
      .grid-2,.pie-wrap {{ grid-template-columns:1fr; }}
      .month-grid {{ grid-template-columns:repeat(4,minmax(0,1fr)); }}
      .site-card-value {{ font-size:18px; }}
    }}
  </style>
</head>
<body>
<header><div class="wrap">
  <h1>Time Dashboard</h1>
  <div class="meta">Updated {html_escape(fmt_dt(now))} · Current session: {html_escape(current)}</div>
  <nav>
    <a href="#explorer">Explorer</a><a href="#daily">Daily</a><a href="#weekly">Weekly</a><a href="#monthly">Monthly</a><a href="#trend">Trend</a><a href="#all-time">All Time</a><a href="#review">Review</a>
  </nav>
</div></header>
<main class="wrap">
{render_period_explorer(explorer_payload)}
  <section id="daily"><h2>Daily</h2>{render_cards([
      ("Today", fmt_duration(today_minutes)),
      ("Target", f"{fmt_duration(today_minutes)} / {fmt_duration(STUDY_TARGET_DAILY_MIN)}"),
      ("Sessions", str((today or {}).get("work_session_count") or 0)),
      ("Longest", fmt_duration((today or {}).get("work_longest_session_min") or 0)),
  ])}{render_day_24h("Today 24h", sessions, now, now)}</section>
  <section id="weekly"><h2>Weekly</h2>{render_cards([
      ("7 Days", fmt_duration(week_total)),
      ("Target", f"{fmt_duration(week_total)} / {fmt_duration(STUDY_TARGET_WEEKLY_MIN)}"),
      ("Daily Avg", fmt_duration(round(week_total / week_active) if week_active else 0)),
      ("Active Days", f"{week_active} / {expected_rolling_work_days(recent7)}"),
  ])}{render_line_chart("近 7 天", [(day["date"], day_work_min(day)) for day in recent7])}{render_bars("近 7 天類別", week_totals, labels)}</section>
  <section id="monthly"><h2>Monthly</h2>{render_cards([
      ("Month", fmt_duration(month_total)),
      ("Target", f"{fmt_duration(month_total)} / {fmt_duration(STUDY_TARGET_MONTHLY_MIN)}"),
      ("Daily Avg", fmt_duration(round(month_total / month_active) if month_active else 0)),
      ("Best Day", best_day["date"] if best_day["date"] != "-" else "-"),
      ("Active Days", f"{month_active} / {expected_work_days(month_days)}"),
  ])}{render_month_grid(month_days, labels)}<div class="grid-2">{render_pie("本月類別占比", month_totals, labels)}{render_bars("本月類別長條", month_totals, labels)}</div><div class="grid-2">{render_rank("本月日排名", day_rank)}{render_rank("本月類別排名", cat_rank)}</div></section>
  <section id="trend"><h2>Trend</h2>{render_line_chart("近 14 天", [(day["date"], day_work_min(day)) for day in recent14])}{render_line_chart("本月累積", [(day["date"], sum(day_work_min(item) for item in month_days[:index + 1])) for index, day in enumerate(month_days)], "#d97706")}</section>
  <section id="all-time"><h2>All Time</h2>{render_cards([
      ("All Time", fmt_duration(all_total)),
      ("Active Days", str(len([day for day in all_days if day_work_min(day) > 0]))),
      ("Months", str(len(stats))),
      ("Expected Avg", fmt_duration(round(all_total / expected_work_days(all_days)) if expected_work_days(all_days) else 0)),
  ])}{render_pie("總累積類別占比", all_totals, labels)}</section>
  <section id="review"><h2>Review Flags</h2>{render_site_session_table("Open Sessions", open_sessions, 20)}{render_site_session_table("Needs Review", needs_review, 30)}</section>
</main>
<footer><div class="wrap">Generated from life/worklog/data by system/scripts/integrations/time_tracker_sync.py.</div></footer>
</body>
</html>
"""
    (site / "index.html").write_text(html_text, encoding="utf-8")



def generate_dashboard(sessions: list[Session], worklog_dir: Path) -> None:
    now = datetime.now(LOCAL_TZ)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today_start + timedelta(days=1)
    week_start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = week_start + timedelta(days=7)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_end = (
        month_start.replace(year=month_start.year + 1, month=1)
        if month_start.month == 12
        else month_start.replace(month=month_start.month + 1)
    )

    today = sessions_in_range(sessions, today_start, tomorrow)
    week = sessions_in_range(sessions, week_start, week_end)
    month = sessions_in_range(sessions, month_start, month_end)
    open_sessions = [session for session in sessions if session.status == "open"]
    needs_review = [session for session in sessions if session.status == "needs_review"]

    def total(items: list[Session]) -> int:
        return sum(session.duration_min or 0 for session in counted(items))

    current = "None"
    if open_sessions:
        session = sorted(open_sessions, key=lambda item: item.start)[-1]
        current = (
            f"- category: {CATEGORY_LABELS.get(session.category, session.category)}\n"
            f"- label: {session.label}\n"
            f"- started: {fmt_dt(session.start)}\n"
            f"- duration_so_far: {fmt_duration(minutes_between(session.start, now))}"
        )

    worklog_dir.mkdir(parents=True, exist_ok=True)
    month = now.strftime("%Y-%m")
    data_dir = worklog_dir / "data"
    available_months = sorted(
        path.stem.replace("time_daily_stats_", "")
        for path in data_dir.glob("time_daily_stats_*.json")
    )
    if month not in available_months:
        available_months.append(month)
        available_months.sort()
    (worklog_dir / "time_dashboard.md").write_text(f"""# Time Dashboard

Updated: {fmt_dt(now)}

This dashboard is evidence for weekly journal review. It describes work time allocation; rest, entertainment, open sessions, and sessions needing review are excluded from totals, charts, and rankings.

<style>
.worklog-review-table {{
  width: 100%;
  border-collapse: collapse;
  margin: 0.75rem 0 1rem;
}}
.worklog-review-table th,
.worklog-review-table td {{
  border-bottom: 1px solid var(--background-modifier-border);
  padding: 0.45rem 0.6rem;
  text-align: left;
}}
.worklog-review-table th {{
  border-top: 1px solid var(--background-modifier-border);
  color: var(--text-muted);
  font-size: 0.85em;
  font-weight: 650;
}}
.worklog-review-table .num {{
  text-align: right;
  font-variant-numeric: tabular-nums;
}}
.worklog-review-table .empty {{
  color: var(--text-muted);
  text-align: center;
}}
</style>

## Outline

- [Current Session](#current-session)
- [Daily Overview](#daily-overview)
- [Weekly Overview](#weekly-overview)
- [Monthly Overview](#monthly-overview)
- [Trend Overview](#trend-overview)
- [Year Overview](#year-overview)
- [All-Time Overview](#all-time-overview)
- [Review Flags](#review-flags)

## Current Session

{current}

## Daily Overview

今日做事總量、目前 session、今日是否有正式做事紀錄。

{dataviewjs_block(month, "daily")}

## Weekly Overview

最近一週的做事總量、活躍天數、類別占比與短期節奏。

{dataviewjs_block(month, "weekly")}

## Monthly Overview

月曆熱度、本月類別占比與排名。

{dataviewjs_block(month, "monthly")}

## Trend Overview

近 14 天、本月累積曲線、排名、開始 / 結束時間。

Month: {month}  
Week: {week_start.date().isoformat()} to {(week_end - timedelta(days=1)).date().isoformat()}

{dataviewjs_block(month, "trend")}

## Year Overview

今年做事時間總覽、類別占比與排名。

{dataviewjs_rollup_block(available_months, "year", now.year)}

## All-Time Overview

所有已同步月份的做事時間總覽、類別占比與排名。

{dataviewjs_rollup_block(available_months, "total", now.year)}

## Review Flags

### Open Sessions

{session_table(open_sessions, 20)}

### Needs Review

{session_table(needs_review, 30)}
""", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inbox-dir", default=str(DEFAULT_INBOX_DIR))
    parser.add_argument("--time-dir", default=str(DEFAULT_WORKLOG_DIR), help="Worklog output directory")
    parser.add_argument("--sync", action="store_true", help="Write sessions and dashboard")
    parser.add_argument("--dry-run", action="store_true", help="Parse and report without writing")
    args = parser.parse_args()

    worklog_dir = Path(args.time_dir).resolve()
    sessions = build_sessions(read_events(Path(args.inbox_dir).resolve()))
    apply_review_overrides(sessions, worklog_dir)
    print(f"sessions={len(sessions)}")
    if args.dry_run:
        for session in sessions[-10:]:
            print(f"{fmt_dt(session.start)} {fmt_time(session.end)} {fmt_duration(session.duration_min)} {session.category} {session.label} {session.status}")
        return 0
    if not args.sync:
        print("nothing written; pass --sync to update sessions and dashboard")
        return 0

    write_sessions_csv(sessions, worklog_dir)
    write_daily_stats_json(sessions, worklog_dir)
    generate_dashboard(sessions, worklog_dir)
    generate_dashboard_site(sessions, worklog_dir)
    print(f"wrote {worklog_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
