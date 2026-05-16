# Worklog

`life/worklog/` records what actually happened.

It is evidence for planning and journal review, not the task source of truth.

## Roles

- `2026-春.md`: human-readable output log for the semester.
- `time_dashboard.md`: generated factual dashboard for time allocation.
- `site/index.html`: generated mobile-friendly static website for the same dashboard.
- `data/time_sessions_YYYY-MM.csv`: structured time sessions parsed from `inbox/time/`.
- `data/time_daily_stats_YYYY-MM.json`: daily aggregates used by the Obsidian DataviewJS dashboard. Normal totals count clean `ok` sessions; `open` / `needs_review` sessions remain review evidence.
- `data/time_session_review_overrides.json`: explicit reviewed-session overrides applied after parsing raw captures.

## Boundaries

- Do not create a separate `life/time/` area.
- Raw mobile capture stays in `../../inbox/time/`.
- Time sessions describe allocation; they do not by themselves define efficiency.
- Weekly journal is where schedule, worklog, and time evidence are interpreted.

## Mobile Website

Run the normal sync command to update both Obsidian and website outputs:

```bash
python3 system/scripts/integrations/time_tracker_sync.py --sync
```

The website entry is `life/worklog/site/index.html`. For phone viewing on the same Wi-Fi, serve that folder from the workstation:

The top `Explorer` section supports adjustable views from all synced daily JSON files:

- `Month`: choose a year and month, such as `2026` + `05 月` or `2026` + `04 月`.
- `Year`: choose a year, such as `2026` or `2025`.
- `Week`: choose a synced week range.
- `All`: show all synced data.

Years or months without synced data are selectable and show `No data`. The lower sections remain fixed current-period snapshots.

```bash
cd life/worklog/site
python3 -m http.server 8787 --bind 0.0.0.0
```

Then open `http://<workstation-lan-ip>:8787/` on the phone.

For phone viewing from any network, start a temporary HTTPS tunnel:

```bash
system/scripts/integrations/serve_time_dashboard_mobile.sh
```

The script prints a public `https://...lhr.life` URL. Keep the terminal/session running on the workstation while using it; stop the background services with:

```bash
kill $(cat /tmp/time_dashboard_tunnel.pid) $(cat /tmp/time_dashboard_http.pid)
```

For live mobile viewing, keep a lightweight polling service running:

```bash
system/scripts/integrations/serve_time_dashboard_mobile_live.sh
```

This service:

- starts or reuses the mobile HTTPS tunnel;
- every 60 seconds pulls the Discord time channel into `inbox/time/`;
- regenerates `time_dashboard.md` and `site/index.html` when `inbox/time/` changes.

Useful knobs:

```bash
TIME_DASHBOARD_POLL_INTERVAL=30 system/scripts/integrations/serve_time_dashboard_mobile_live.sh
TIME_DASHBOARD_PULL_LIMIT=50 system/scripts/integrations/serve_time_dashboard_mobile_live.sh
```

Stop the live service:

```bash
kill $(cat /tmp/time_dashboard_mobile_live.pid)
```

## Review Flow

```text
schedule weekly plan
+ worklog outputs
+ time dashboard / sessions
-> journal weekly review
```
