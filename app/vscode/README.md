# Claude Usage for VS Code

Your Claude 5-hour and weekly quota without leaving the editor, read from the local Claude Usage Tracker
(the same storage as the widget: this extension collects nothing, never sees the Claude token and never calls Anthropic).

- **Status bar** (bottom right): `▰▰▱ 42 % · ▰▱▱ 18 %` for the 5-hour window and the week. Warning / error colour from
  80 % / 95 % (settings), dimmed when the latest reading is more than 30 minutes old. Hover: reset times, pace, age of the
  reading. Click: the side view.
- **Side view** (activity bar, “Claude Usage”): the widget's own gauges and charts, at the compactness level that fits
  the width of the view (narrow: two bars; wider: rings, then charts).

## Install (no Marketplace)

The tracker must be set up and its automatic readings running (`python run.py`, Quick setup).

- Simplest: link this folder into VS Code's extensions folder, then reload VS Code.
  - Linux / macOS: `ln -s "$PWD" ~/.vscode/extensions/local.claude-usage-0.1.0`
  - Windows (PowerShell): `New-Item -ItemType Junction -Path "$env:USERPROFILE\.vscode\extensions\local.claude-usage-0.1.0" -Target "$PWD"`
- Or build a `.vsix`: `npx @vscode/vsce package`, then *Extensions › … › Install from VSIX*. A copied `.vsix` does not
  sit inside the tracker any more: set `claudeUsage.appFolder` to the tracker's `app` folder.

## Settings

| Setting | Default | |
|---|---|---|
| `claudeUsage.appFolder` | the folder above this one | the tracker's `app` folder (with `run.py`) |
| `claudeUsage.source` | `file` | `file` = read `data/latest.json`; `api` = ask the server (`/api/v1/latest`), e.g. a hub on another machine |
| `claudeUsage.apiUrl` | `http://127.0.0.1:8765` | the tracker's server |
| `claudeUsage.template` | `{b5} {p5} · {b7} {p7}` | status bar text |
| `claudeUsage.warnAt` / `errorAt` | 80 / 95 | colour thresholds (%) |
| `claudeUsage.intervalSeconds` | 30 | how often to read again (the file is also watched) |
