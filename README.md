# Time Dashboard

Static time dashboard published with GitHub Pages.

- `inbox/time/`: captured Discord time-tracker messages and pull state.
- `life/worklog/data/`: generated sessions and daily aggregates.
- `life/worklog/site/index.html`: published website entry.

GitHub Actions refreshes Discord time captures, regenerates the dashboard, commits data changes, and deploys `life/worklog/site` to GitHub Pages every 5 minutes.
