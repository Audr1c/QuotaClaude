# Claude Usage Tracker

[Français](README.fr.md)

Logs your Claude **5-hour** and **7-day** quota (% used + reset times) to a CSV file and shows it as gauges, with pacing indicators, in Claude's colours. Everything runs locally on your machine.

![Level 9, wide window](app/docs/screenshot-detail.png)

| Narrow window (level 4) | Dark |
|---|---|
| ![Level 4, narrow window](app/docs/screenshot-compact.png) | ![Dark theme](app/docs/screenshot-detail-dark.png) |

> **Unofficial.** It uses an undocumented Anthropic endpoint (`/api/oauth/usage`) that may change or disappear without notice.

## Quick start

You do not need to build anything: the launchers are already in the repository.

1. Have **Python 3.8+** (standard library only, nothing to install) and **Claude Code signed in** with your Claude subscription on the same machine.
2. Download the project (**Releases** page, or *Code → Download ZIP*, or `git clone`) and unpack it **as a whole folder**.
3. Start it:

| OS | Start |
|---|---|
| Windows | double-click **`claude-usage-tracker.exe`** (or `app\run.bat`) |
| Linux | **`claude-usage-tracker`** (or `app/run.sh`; after a ZIP download run `chmod +x claude-usage-tracker app/run.sh` once) |
| Any | `python app/run.py` |

> The `.exe` / Linux program is only a launcher: it starts `run.bat` / `run.sh` from the `app/` folder next to it, so it does not work alone. Copy the whole folder, not just the binary.

Your readings are stored in the `app/data/` folder next to the code (see [Where your data goes](#where-your-data-goes)).

The first launch runs a **Quick setup**: language, a check that Claude Code is signed in (it tells you to type `/login` in Claude Code if not), a first reading, automatic readings, the widget server at login, a desktop shortcut, opening the widget. Each step is a yes/no question with the recommended answer on **Enter**; nothing is installed without an answer, and the final summary says what was set up, where your data is and how to remove everything. It can be replayed from the menu or with `run.py --setup` (`--yes` takes every recommended answer without asking).

Then comes an arrow-key menu, grouped (See · Readings · Settings · Maintenance), with a state line on top (automatic readings, server, latest reading) and a short explanation under each entry:

- **Take a reading now** – one manual reading, saved to the CSV.
- **Open the widget** – starts the local server and opens the gauges in your browser.
- **Start / Stop the widget server** – the entry follows the real state: it offers "Start" when the server is off and "Stop" when it is running.
- **Automatic readings** – install or remove the background poller, which takes readings by itself, faster while your quota is moving and slower when it is not (see [How it works](#how-it-works)). No interval to choose. Optionally also start the widget server at login/boot. Or skip it entirely and refresh by hand (button in the widget, or the menu).
- **Status** – last reading, poller state (with the time of the next reading), server state.
- **Quick setup**, **Run tests**, **Language**, **Quit**.

### The widget

Gauges for the 5-hour window and the week, with time marks outside the rings (every 15 minutes, hours labelled, for the 5-hour window; local midnights and day initials for the week) and % marks inside. A per-product **Weekly breakdown** (each bar is split by day, see below), and on the side a **Pace by my working hours** switch (off by default: the weekly pace follows calendar time); switched on, an **hours-per-day slider** appears (1–24 h): the weekly pace then counts those working hours (from your first request of the day, 08:00 by default) and the advised hourly pace is computed over them. The **?** button (top right) opens every equation with your values in a side panel. The header shows when the next automatic reading is due ("next in …").

- **Detail slider** (header): nine levels, from two thin bars (1) to everything (9), each level keeping what the level below shows: 1 bars, 2 + % and pace marker, 3 + reset times, 4 the two rings in one gauge, 5 two gauges with key figures, 6 + a small hourly chart, 7 + the ratio chart and the tokens summary, 8 full charts, 9 breakdown, per-day tokens and settings. **Auto** (default) picks the level from the width of the window. **Explanations** is a tenth notch apart from the slider: level 9 plus a short note under each panel; each panel's **?** shows or hides its own note.
- **Layout**: one column on a narrow screen, the charts side by side from 900 px, two columns from 1300 px, three from 1750 px. On a touch screen: 44 px targets, a tap shows the value of a bar or a dot, drag and pinch on the charts.
- **Theme** (header): presets (Claude, high contrast, colour-blind, monochrome), your own colours for the two rings and the inside / over-budget zones, light and dark separately, a system font, export / import as text.
- **Installable**: Chrome / Edge offer "Install app" (own window and icon); it also opens at `http://claude.localhost:8765/`.
- Settings (level, explanations, working hours, language, theme) are stored in `app/data/config.json` through the server, so every browser and client sees the same ones.

In the breakdown, each product's bar has one segment per local day, all in the same colour with thin separators, and the day name written inside (full name, then shorter abbreviations, then one letter, then nothing, depending on the room). Hover a segment for its date and points. Each product is measured on its own: a day's segment is how much **that** product rose that day (from the per-product shares recorded in `breakdown.csv` at each change), so a Code-only day only shows up in the Code bar. Usage from before the per-product tracking started this week forms a single "Earlier" segment (exact in total, not split by day).

Three collapsed history panels sit below the breakdown:

- **Usage per hour**: bars of the 5-hour window you consumed each hour (1 h, 3 h, 6 h or 1 day per bar depending on the range), against the dashed hourly pace that keeps you on your daily budget.
- **5 h → week ratio over time**: how many % of the week one full 5-hour window costs, day by day (dots) and as the all-time estimate the widget uses (line).
- **Tokens and cache**: the four token types (fresh input, cache write, cache read, output) with their number, their share of the tokens, their relative price and their share of the cost, plus the saving brought by the cache and a per-day view. Cost is in plain-input-token equivalents (cache read × 0.1, cache write × 1.25 or × 2, output × 5), not dollars; how the quota weights each type is not published.

The first two have a range selector and a small overview below, like a market chart: drag the window to move it, drag its edges to zoom, click outside to jump. The range is remembered in the browser. The tokens panel has its own 7 d / 14 d / 30 d / All buttons.

The token figures come from Claude Code's own transcripts (`~/.claude/projects/**/*.jsonl`, or `CLAUDE_PROJECTS_DIR`), read incrementally by `transcripts.py`: only the usage numbers, model, time and message id are read from each line, never the conversation text. Chats and Cowork use your quota too but leave no transcript, so token counts cover Claude Code only.

### Command-line shortcuts

```
python app/run.py read                      one reading
python app/run.py start                     start the widget server (background, no browser)
python app/run.py open                      start the server if needed and open the widget
python app/run.py stop                      stop the server
python app/run.py status
python app/run.py install [--with-server]   start the background poller at logon (and now)
python app/run.py uninstall                 remove it (also stops a running poller)
python app/run.py tests
python app/run.py shortcut [--remove]       desktop / menu shortcut that opens the widget directly
python app/run.py hub --url URL --token T   also send every reading to a hub (see below); --off to stop
python app/run.py --setup [--yes]           quick setup again (--yes: recommended answers, no questions)
python app/run.py --lang fr <command>       force the language
```

### Read API, VS Code, other devices

- **API** (same data for every client, never the Claude token): `GET /api/v1/latest`, `/api/v1/history?since=ISO`, `/api/v1/tokens?since=YYYY-MM-DD`, `/api/v1/model[?hours=N]` (gauge values, limits and paces computed by the server, ready to draw), `GET`/`POST /api/v1/config` (shared settings, validated). `latest.json` carries `"schema": 1`; `app/schema/latest.v1.json` is the reference sample.
- **VS Code**: `app/vscode/` is an extension with a status bar indicator (`▰▰▱ 42 % · ▰▱▱ 18 %`, tooltip, colours by threshold) and a side view drawn with the widget's own components at the level that fits its width. See [app/vscode/README.md](app/vscode/README.md).
- **Hub** (an always-on machine: NAS, small server): run `server.py --bind 0.0.0.0 --token-file data/api_token` there (or the `app/Dockerfile`); on the PC, `run.py hub --url http://hub:8765 --token <the hub's token>`. The PC keeps doing the readings and pushes each one: the Claude token never leaves it. On the hub every request needs the API token (`Authorization: Bearer`, or open `/?token=…` once in a browser). Reach it through Tailscale / WireGuard (`tailscale serve` gives HTTPS, needed to install the app on a phone) rather than from the Internet; extra host names go in `allowed_hosts` of `config.json` or `--allow-host`.

## Launchers and icon

Besides `app/run.bat` / `app/run.sh`, the project root holds two tiny prebuilt programs that do nothing but start those scripts in a terminal (same menu, same arguments):

| OS | Program | Icon |
|---|---|---|
| Windows | `claude-usage-tracker.exe` (double-click, or pin it to the taskbar) | embedded in the .exe |
| Linux | `claude-usage-tracker` (static binary) + a menu entry with `make desktop` | from the menu entry |

The widget also has a browser-tab icon (`app/web/favicon.svg`). Logo: two rings, orange = week, blue = 5-hour window. The terminal menu shows a pixel-art version of it.

### Building them yourself (make)

You only need this to rebuild or change them. Run it from the `app/` folder (`cd app`). Requirements: Python 3 and `pip install ziglang` (the Zig compiler packaged for pip; it cross-compiles both programs from any OS, nothing else to install). Icons also need `pip install pillow`.

```
make            only explains the targets (nothing is built)
make all        build both programs (next to the README)
make windows    claude-usage-tracker.exe (with the icon, via assets/app.rc)
make linux      claude-usage-tracker
make desktop    add "Claude Usage Tracker" to the Linux applications menu
make icons      regenerate assets/ and web/favicon.* from tools/make_icons.py
make clean      delete the two built programs
python tools/build.py [windows|linux|icons|desktop|clean]    same thing without make (e.g. on Windows)
```

How it works: `app/tools/launcher.c` finds `run.bat` (Windows) or `run.sh` (Linux) in the `app/` folder next to itself and starts it. `app/tools/make_icons.py` draws the logo once and writes the SVG, PNG and ICO files. The prebuilt binaries are unsigned, so Windows SmartScreen may warn you the first time; rebuild them from source if you prefer.

## Where your data goes

Everything stays in the `app/data/` folder next to the code (git-ignored, created automatically by the first reading; nothing is written anywhere else):

| File | What |
|---|---|
| `usage.csv` | one line per reading: time, 5-hour %, week %, reset times |
| `latest.json` / `latest.js` | latest state + recent history (only readings where values changed, plus the last one), read by the widget |
| `breakdown.csv` | per-product weekly shares, one line per product each time they change; used to split the breakdown bars by day |
| `tokens.csv` | token counters per hour, model and agent kind (main / sub-agent), read from Claude Code's transcripts (numbers only) |
| `transcripts_state.json` | where the transcript reader stopped in each file (files are identified by a hash, never by name), the message ids already counted, and its hourly counters |
| `poller.json` | poller state: time of the next reading, current step |
| `poller.lock` | lock so that only one poller runs at a time |
| `last_response.json` | raw API answer of the last reading (debugging) |
| `tracker.log` | log of the background readings (status, Retry-After, failures in a row) |
| `errors.json` | the last 30 failed readings with full detail; the widget's red banner opens it (**Details**) |
| `config.json` | menu language, setup done, widget settings (level, explanations, working hours, theme), hub address |
| `hub_token` / `api_token` | only with a hub: the API token of the tracker (rights 0600; not the Claude token) |
| `server.log` | widget server output (Linux) |

Outside `app/data/`: the "Claude Usage" shortcut if you created one (`run.py shortcut --remove`), the scheduled task if you set one up (Windows Task Scheduler, or a systemd user service / crontab line on Linux; the menu removes it), and Python's `__pycache__` folders. The Claude Code credentials file is only **read**, never copied. A reading needs Claude Code signed in; otherwise the menu tells you the credentials were not found.

## How it works

- `claude_usage.py` reads your Claude Code OAuth token from `~/.claude/.credentials.json` (Windows: `%USERPROFILE%\.claude\.credentials.json`; honours `CLAUDE_CONFIG_DIR`, or set `CLAUDE_USAGE_TOKEN`), calls the usage endpoint, and appends a row to `data/usage.csv`. It also writes `data/latest.json` / `latest.js` for the widget.
- The access token lasts about 8 hours and only Claude Code renews it: run `claude` once in a terminal (the Claude desktop app does not seem to rewrite this file). Once its `expiresAt` is past, no request is sent (it would only get HTTP 401); the poller watches the file and reads again as soon as it changes.
- `server.py` serves the widget on `http://127.0.0.1:8765` (local only; Host/Origin checks against DNS rebinding) and lets the **Refresh** button trigger a reading.
- `poller.py` is the adaptive poller behind the automatic readings: a long-running loop, not a fixed interval. After a reading where the 5-hour or weekly % changed, the next one comes 30 s later; each reading without change climbs one step (1 min, 3 min, 5 min, 7 min, then 10 min, where it stays). After an HTTP 429 (rate limited) it waits 2 min, or the API's `Retry-After` if longer, without moving on the ladder. Other errors count as "no change". Only one poller runs at a time.
- Background start: on Windows the "Claude Usage Tracker" scheduled task starts the poller at logon (and right at install) and restarts it if it crashes; on Linux it is the systemd user service `claude-usage-tracker.service` (`Restart=on-failure`), or an `@reboot` crontab line without systemd (the poller is then started immediately).
- The widget also works opened as a plain file (`app/web/index.html`) but then cannot refresh by itself.

The weekly-vs-5-hour ratio shown in the widget is estimated from your own consecutive readings (10 % until enough data exists).

## How the numbers are computed

The widget's **?** button opens the **How it is computed** panel, which shows each equation with your current values. Same content here. Notation: *u5* / *u7* = % used in the 5-hour window / the week (as reported), *h* = the hours-per-day slider.

| What | Equation |
|---|---|
| 5-hour pace (blue marker) | `(5 h − time left) / 5 h × 100` – real elapsed time |
| Start of your work day | first reading of the day where usage rose (your first request), else 08:00 |
| Weekly pace (orange marker, week ring) | `working hours elapsed this week / working hours in the week × 100` – a day is *h* hours from the start time; at 24 h it is plain calendar time |
| Cost of a 5-hour window, *r* | % of the week consumed per 100 % of a 5-hour window, estimated from your consecutive readings (default 10 %) |
| Week used at start of today, *u0* | weekly % at the last reading before local midnight (oldest reading if none; 0 if the week reset since) |
| Days until reset, *D* | `(weekly reset − today 00:00) / 24 h` |
| **Daily budget** *B* ("possible spend / day") | `(100 − u0) / D` |
| Weekly limit now, *L7* (green/red boundary of the week ring) | `u0 + B` |
| Left in today's budget | `max(0, L7 − u7)` |
| 5-hour limit, *L5* (orange marker and green/red boundary of the 5-hour ring) | `u5 + (L7 − u7) × 100 / r` (may exceed 100 % when today's budget covers more than one 5-hour window) |
| **Advised per hour** (5-hour %/h) | `B / h × 100 / r` |
| Max possible until reset | `(100 − u5) / hours left in the window` |
| Full 5-hour windows left | `(100 − u7) / r` |
| Per-product breakdown | `product share × u7 / 100` points of the weekly quota, split per day from the shares recorded in `breakdown.csv` and the week's % over time |
| "Ahead / margin" pill | `used − pace`; beyond ±5 points it reads ahead / margin |

**What the slider changes:** the weekly pace (working hours instead of calendar time) and the advised hourly pace. The 5-hour pace is real time, and the green/red zones come from the daily budget, which does not depend on the slider.

## Project layout

```
README.md  README.fr.md  LICENSE
claude-usage-tracker.exe    Windows launcher (double-click)
claude-usage-tracker        Linux launcher
app/                        everything else
  run.py  run.bat  run.sh   entry point (menu)
  launcher/                 menu code and translations (strings.py)
  claude_usage.py           reads the quota, writes data/
  poller.py                 adaptive poller (background readings)
  transcripts.py            local token counters from Claude Code's transcripts
  server.py                 local widget server and read API (/api/v1)
  model.py  settings.py     the pace model computed on the server, shared settings
  hub.py  Dockerfile        hub: readings pushed by a PC, API token
  schema/                   sample of latest.json (data contract)
  vscode/                   VS Code extension
  web/                      the widget (HTML, CSS, JS; EN/FR)
  windows/  linux/          scheduler install/uninstall scripts
  tools/  assets/  Makefile launchers' C source, build scripts, icons
  docs/                     README screenshots
  data/                     your readings (git-ignored, never committed)
```

## Privacy

- No data leaves your machine except the request to Anthropic's API with your own token.
- The token is read at run time and never copied or logged. `app/data/` and credentials are in `.gitignore`.
- The server only listens on `127.0.0.1`, unless you start a hub with `--bind`, which requires an API token for every request.
- Claude Code's transcripts contain your conversations. `transcripts.py` reads only token numbers, the model, the time, the message id and the sub-agent flag from them, and writes only counters and message ids (random strings from the API); never the text, and no project or folder name (transcript files are identified by a hash). Each message is counted once, even when a resumed session or a sub-agent file repeats it.

## Notes

- macOS: the scripts are plain Python/shell and may work, but the scheduler setup is untested (use cron manually).
- If you set up automatic readings with an older layout (before the `app/` folder existed), open the menu and redo **Automatic readings** once: the old task points to the old location.
- If you installed automatic readings with v1.0.0 (fixed interval), open the menu and redo **Automatic readings** once to switch to the poller.
- Not affiliated with Anthropic.

## Licence

MIT – see [LICENSE](LICENSE).
