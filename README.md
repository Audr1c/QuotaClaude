# Claude Usage Tracker

[Français](README.fr.md)

Logs your Claude **5-hour** and **7-day** quota (% used + reset times) to a CSV file and shows it as gauges, with pacing indicators, in Claude's colours. Everything runs locally on your machine.

![Detailed view](docs/screenshot-detail.png)

| Compact | Dark |
|---|---|
| ![Compact view](docs/screenshot-compact.png) | ![Dark theme](docs/screenshot-detail-dark.png) |

> **Unofficial.** It uses an undocumented Anthropic endpoint (`/api/oauth/usage`) that may change or disappear without notice.

## Quick start

Requirements: Python 3.8+ (standard library only, nothing to install) and Claude Code signed in on the same machine.

| OS | Start |
|---|---|
| Windows | double-click `run.bat` (or `run.bat` in a terminal) |
| Linux | `./run.sh` (first time: `chmod +x run.sh`) |
| Any | `python run.py` |

The first launch asks for a language (English / Français), then shows an arrow-key menu with a short explanation under each entry:

- **Take a reading now** – one manual reading, saved to the CSV.
- **Open the widget** – starts the local server and opens the gauges in your browser.
- **Start / Stop the widget server** – the entry follows the real state: it offers "Start" when the server is off and "Stop" when it is running.
- **Automatic readings** – install, change or remove the background task. Default: every **10 minutes**; pick a preset or type any number of minutes. Optionally also start the widget server at login/boot. Or skip it entirely and refresh by hand (button in the widget, or the menu).
- **Status** – last reading, scheduler state, server state.
- **Run tests**, **Language**, **Quit**.

### The widget

Gauges for the 5-hour window and the week, a compact/detailed switch, a collapsed per-product breakdown, and an **hours-per-day slider** on the side (1–24 h, long marks every 5 h): tell it how many hours a day you really use Claude and the weekly pace counts those working hours (from your first request of the day, 08:00 by default) and the advised hourly pace is computed over them. A collapsed panel lists every equation (see below).

### Command-line shortcuts

```
python run.py read                      one reading
python run.py start                     start the widget server (background, no browser)
python run.py open                      start the server if needed and open the widget
python run.py stop                      stop the server
python run.py status
python run.py install --minutes 10 [--with-server]
python run.py uninstall
python run.py tests
python run.py --lang fr <command>       force the language
```

## Launchers and icon

Besides `run.bat` / `run.sh`, `bin/` holds two tiny prebuilt programs that do nothing but start those scripts in a terminal (same menu, same arguments):

| OS | Program | Icon |
|---|---|---|
| Windows | `bin/claude-usage-tracker.exe` (double-click, or pin it to the taskbar) | embedded in the .exe |
| Linux | `bin/claude-usage-tracker` (static binary) + a menu entry with `make desktop` | from the menu entry |

The widget also has a browser-tab icon (`web/favicon.svg`). Logo: two rings, orange = week, blue = 5-hour window. The terminal menu shows a pixel-art version of it.

### Building them yourself (make)

You only need this to rebuild or change them. Requirements: Python 3 and `pip install ziglang` (the Zig compiler packaged for pip; it cross-compiles both programs from any OS, nothing else to install). Icons also need `pip install pillow`.

```
make            build both programs into bin/
make windows    bin/claude-usage-tracker.exe (with the icon, via assets/app.rc)
make linux      bin/claude-usage-tracker
make desktop    add "Claude Usage Tracker" to the Linux applications menu
make icons      regenerate assets/ and web/favicon.* from tools/make_icons.py
make clean      remove bin/
python tools/build.py [windows|linux|all]    same thing without make (e.g. on Windows)
```

How it works: `tools/launcher.c` finds `run.bat` (Windows) or `run.sh` (Linux) next to itself (or one folder up) and starts it. `tools/make_icons.py` draws the logo once and writes the SVG, PNG and ICO files. The prebuilt binaries are unsigned, so Windows SmartScreen may warn you the first time; rebuild them from source if you prefer.

## How it works

- `claude_usage.py` reads your Claude Code OAuth token from `~/.claude/.credentials.json` (Windows: `%USERPROFILE%\.claude\.credentials.json`; honours `CLAUDE_CONFIG_DIR`, or set `CLAUDE_USAGE_TOKEN`), calls the usage endpoint, and appends a row to `data/usage.csv`. It also writes `data/latest.json` / `latest.js` for the widget.
- `server.py` serves the widget on `http://127.0.0.1:8765` (local only; Host/Origin checks against DNS rebinding) and lets the **Refresh** button trigger a reading.
- Scheduling: Windows Task Scheduler, or a systemd user timer on Linux (cron fallback).
- The widget also works opened as a plain file (`web/index.html`) but then cannot refresh by itself.

The weekly-vs-5-hour ratio shown in the widget is estimated from your own consecutive readings (10 % until enough data exists).

## How the numbers are computed

The widget has a collapsed **How it is computed** panel that shows each equation with your current values. Same content here. Notation: *u5* / *u7* = % used in the 5-hour window / the week (as reported), *h* = the hours-per-day slider.

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
| 5-hour limit, *L5* (orange marker and green/red boundary of the 5-hour ring) | `u5 + (L7 − u7) × 100 / r`, capped at 100 |
| **Advised per hour** (5-hour %/h) | `B / h × 100 / r` |
| Max possible until reset | `(100 − u5) / hours left in the window` |
| Full 5-hour windows left | `(100 − u7) / r` |
| Per-product breakdown | `product share × u7 / 100` points of the weekly quota |
| "Ahead / margin" pill | `used − pace`; beyond ±5 points it reads ahead / margin |

**What the slider changes:** the weekly pace (working hours instead of calendar time) and the advised hourly pace. The 5-hour pace is real time, and the green/red zones come from the daily budget, which does not depend on the slider.

## Project layout

```
run.py / run.bat / run.sh   entry point (menu)
bin/  tools/  assets/       launchers (.exe / Linux), their C source and build scripts, icons
Makefile                    make all | windows | linux | desktop | icons
launcher/                   menu code and translations (strings.py)
claude_usage.py             reads the quota, writes data/
server.py                   local widget server
web/                        the widget (HTML, CSS, JS; EN/FR)
windows/  linux/            scheduler install/uninstall scripts
data/                       your readings (git-ignored, never committed)
```

## Privacy

- No data leaves your machine except the request to Anthropic's API with your own token.
- The token is read at run time and never copied or logged. `data/` and credentials are in `.gitignore`.
- The server only listens on `127.0.0.1`.

## Notes

- macOS: the scripts are plain Python/shell and may work, but the scheduler setup is untested (use cron manually).
- Existing scheduled tasks created by earlier versions keep working.
- Not affiliated with Anthropic.

## Licence

MIT – see [LICENSE](LICENSE).
