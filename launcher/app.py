# -*- coding: utf-8 -*-
"""Launcher logic: the interactive menu, its actions, and the matching command-line interface.

The menu only dispatches. "Take a reading" and "open the widget" are done in Python (same on every
OS); only installing/removing the background job is OS specific, so that part calls the right
script: windows/*.ps1 (Task Scheduler) or linux/*.sh (systemd timer, or cron).
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import claude_usage as cu
from server import DEFAULT_PORT, ping

from . import banner, tui
from .strings import LANG_NAMES, LANGS, STRINGS

ROOT = Path(__file__).resolve().parent.parent
DATA = cu.DATA_DIR
CONFIG_FILE = DATA / "config.json"
DEFAULT_MINUTES = 10
MAX_MINUTES = 1439
TASK_NAME = "Claude Usage Tracker"
CRON_MARKER = "# claude-usage-tracker"
IS_WINDOWS = os.name == "nt"
IS_LINUX = sys.platform.startswith("linux")


# --------------------------------------------------------------------------- settings

def load_config() -> dict:
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_config(cfg: dict) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(cfg, indent=1), encoding="utf-8")
    os.replace(tmp, CONFIG_FILE)


class Ui:
    """Holds the menu language and formats messages."""

    def __init__(self, lang: str):
        self.lang = lang if lang in LANGS else "en"

    def t(self, key: str, **kw) -> str:
        text = STRINGS[self.lang].get(key) or STRINGS["en"][key]
        return text.format(**kw) if kw else text

    def say(self, key: str, **kw) -> None:
        print(self.t(key, **kw))

    def error_text(self, code: str | None, raw: str | None) -> str:
        key = f"error.{code}"
        return self.t(key) if code and key in STRINGS["en"] else (raw or "?")

    # --- formatting that depends on the language
    def pct(self, v) -> str:
        if v is None:
            return "—"
        s = f"{v:g}"
        return s.replace(".", ",") + " %" if self.lang == "fr" else s + "%"

    def duration(self, seconds: float) -> str:
        m = max(0, int(round(seconds / 60)))
        d, rest = divmod(m, 1440)
        h, mm = divmod(rest, 60)
        if self.lang == "fr":
            return f"{d} j {h} h" if d else f"{h} h {mm:02d}" if h else f"{mm} min"
        return f"{d}d {h}h" if d else f"{h}h {mm:02d}m" if h else f"{mm} min"

    def when(self, dt: datetime) -> str:
        local = dt.astimezone()
        names = self.t("weekdays").split(",")
        return f"{names[local.weekday()]} {local:%H:%M}"


def ago(iso_text: str | None) -> float | None:
    """Seconds since an ISO timestamp, or None."""
    dt = cu.parse_dt(iso_text)
    return (cu.now_utc() - dt).total_seconds() if dt else None


# --------------------------------------------------------------------------- actions

def read_now(ui: Ui) -> bool:
    ui.say("read.running")
    row, error, state = cu.run()
    if error:
        print(ui.t("read.fail", msg=ui.error_text(state.get("error_code"), error)))
        return False
    ui.say("read.ok")
    for key, label in (("five_hour", "read.five"), ("seven_day", "read.seven")):
        window = state.get(key) or {}
        reset = cu.parse_dt(window.get("resets_at"))
        if reset and reset > cu.now_utc():
            left = ui.duration((reset - cu.now_utc()).total_seconds())
            print("  " + ui.t("read.line", label=ui.t(label), pct=ui.pct(window.get("pct")), left=left, when=ui.when(reset)))
        else:
            print("  " + ui.t("read.line.none", label=ui.t(label), pct=ui.pct(window.get("pct"))))
    return True


def background_python() -> str:
    """The interpreter for background processes: pythonw.exe on Windows (no console window)."""
    if IS_WINDOWS:
        candidate = Path(sys.executable).with_name("pythonw.exe")
        if candidate.exists():
            return str(candidate)
    return sys.executable


def open_widget(ui: Ui, browser: bool = True) -> bool:
    """Start the widget server if it is not running; open the browser too unless browser=False."""
    if not browser and ping(DEFAULT_PORT):
        ui.say("server.already", url=f"http://127.0.0.1:{DEFAULT_PORT}/")
        return True
    ui.say("open.starting" if browser else "server.starting")
    DATA.mkdir(parents=True, exist_ok=True)
    cmd = [background_python(), str(ROOT / "server.py"), "--lang", ui.lang] + (["--open"] if browser else [])
    opts: dict = {"stdin": subprocess.DEVNULL, "cwd": str(ROOT)}
    log = None
    if IS_WINDOWS:
        # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW: survives this window, shows no console
        opts.update(creationflags=0x00000008 | 0x00000200 | 0x08000000,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        log = open(DATA / "server.log", "ab")
        opts.update(stdout=log, stderr=log, start_new_session=True)
    try:
        subprocess.Popen(cmd, **opts)
    finally:
        if log:
            log.close()
    for _ in range(24):                                   # up to ~6 s for the server to answer
        if ping(DEFAULT_PORT):
            ui.say("open.ok" if browser else "server.ok", url=f"http://127.0.0.1:{DEFAULT_PORT}/")
            return True
        time.sleep(0.25)
    ui.say("open.fail")
    return False


def stop_server(ui: Ui) -> bool:
    info = ping(DEFAULT_PORT)
    if not info:
        ui.say("stop.none")
        return True
    pid = info.get("pid")
    if not pid:
        ui.say("stop.nopid")
        return False
    try:
        os.kill(int(pid), signal.SIGTERM)                 # the pid comes from our own verified server
    except OSError as e:
        print(ui.t("stop.fail", msg=str(e)))
        return False
    for _ in range(20):
        if not ping(DEFAULT_PORT):
            break
        time.sleep(0.15)
    ui.say("stop.ok")
    return True


def scheduler_kind() -> str | None:
    """Which mechanism runs the periodic reading right now: 'task' | 'systemd' | 'cron' | None."""
    try:
        if IS_WINDOWS:
            r = subprocess.run(["schtasks", "/Query", "/TN", TASK_NAME], capture_output=True, timeout=20)
            return "task" if r.returncode == 0 else None
        if IS_LINUX:
            r = subprocess.run(["systemctl", "--user", "is-enabled", "claude-usage-tracker.timer"],
                               capture_output=True, timeout=10)
            if r.returncode == 0:
                return "systemd"
            r = subprocess.run(["crontab", "-l"], capture_output=True, text=True, timeout=10)
            if r.returncode == 0 and CRON_MARKER in r.stdout:
                return "cron"
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def status(ui: Ui) -> bool:
    state = load_state()
    label = {"reading": ui.t("status.reading"), "samples": ui.t("status.samples"),
             "server": ui.t("status.server"), "auto": ui.t("status.auto")}
    width = max(len(v) for v in label.values())
    cfg = load_config()

    def line(key: str, value: str) -> None:
        print(f"  {label[key]:<{width}} : {value}")

    age = ago(state.get("fetched_at")) if state else None
    if state and age is not None:
        five = (state.get("five_hour") or {}).get("pct")
        seven = (state.get("seven_day") or {}).get("pct")
        line("reading", ui.t("status.reading.value", ago=ui.duration(age), h5=ui.pct(five), d7=ui.pct(seven)))
    else:
        line("reading", ui.t("status.reading.none"))
    if state and state.get("error"):
        print(f"  ! {ui.t('status.error')}: {ui.error_text(state.get('error_code'), state.get('error'))}")
    line("samples", str(state.get("samples", 0)) if state else "0")

    info = ping(DEFAULT_PORT)
    line("server", ui.t("status.server.on", url=f"http://127.0.0.1:{DEFAULT_PORT}/") if info else ui.t("status.server.off"))

    kind = scheduler_kind()
    if kind:
        minutes = cfg.get("interval_minutes")
        name = ui.t(f"kind.{kind}")
        line("auto", ui.t("status.auto.on.interval", kind=name, n=minutes) if minutes else ui.t("status.auto.on", kind=name))
        if age is not None and minutes and age > 3 * 60 * int(minutes) + 120:
            print(f"  ! {ui.t('status.stale', ago=ui.duration(age))}")
    else:
        line("auto", ui.t("status.auto.off"))
    return True


def load_state() -> dict | None:
    try:
        return json.loads((DATA / "latest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def install_task(ui: Ui, minutes: int, with_server: bool) -> bool:
    if IS_WINDOWS:
        cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ROOT / "windows" / "install_task.ps1"),
               "-Minutes", str(minutes), "-PythonW", background_python()]
        if with_server:
            cmd.append("-WithServer")
        env = None
    elif IS_LINUX:
        cmd = ["bash", str(ROOT / "linux" / "install_task.sh"), str(minutes)] + (["--with-server"] if with_server else [])
        env = dict(os.environ, PYTHON=sys.executable)
    else:
        ui.say("install.unsupported")
        return False
    ui.say("install.running")
    code = subprocess.run(cmd, cwd=str(ROOT), env=env).returncode
    if code != 0:
        ui.say("install.fail", code=code)
        return False
    cfg = load_config()
    cfg.update(interval_minutes=minutes, server_at_login=with_server)
    save_config(cfg)
    ui.say("install.ok", n=minutes)
    ui.say("install.first")
    read_now(ui)
    return True


def remove_task(ui: Ui) -> bool:
    if IS_WINDOWS:
        cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ROOT / "windows" / "uninstall_task.ps1")]
    elif IS_LINUX:
        cmd = ["bash", str(ROOT / "linux" / "uninstall_task.sh")]
    else:
        ui.say("install.unsupported")
        return False
    code = subprocess.run(cmd, cwd=str(ROOT)).returncode
    if code != 0:
        ui.say("remove.fail", code=code)
        return False
    cfg = load_config()
    cfg.pop("interval_minutes", None)
    cfg.pop("server_at_login", None)
    save_config(cfg)
    ui.say("remove.ok")
    return True


def run_tests(ui: Ui) -> bool:
    ui.say("tests.running")
    code = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", str(ROOT), "-p", "test_*.py"],
                          cwd=str(ROOT)).returncode
    ui.say("tests.ok" if code == 0 else "tests.fail", code=code)
    return code == 0


def parse_minutes(text: str) -> int | None:
    """'' -> default; a whole number within range -> that number; anything else -> None."""
    text = text.strip()
    if not text:
        return DEFAULT_MINUTES
    if text.isdigit() and 1 <= int(text) <= MAX_MINUTES:
        return int(text)
    return None


# --------------------------------------------------------------------------- menus

def pick_language(current: str | None = None) -> str | None:
    options = [(LANG_NAMES[code], STRINGS[code][f"lang.{code}.desc"]) for code in LANGS]
    selected = 1 if current == "fr" else 0
    choice = tui.choose("Language / Langue", options, hint=STRINGS["en"]["menu.hint"],
                        plain_hint=", ".join(f"{i} = {LANG_NAMES[c]}" for i, c in enumerate(LANGS, 1)), selected=selected)
    return None if choice is None else LANGS[choice]


def ask_yes_no(ui: Ui, title: str, yes: tuple[str, str], no: tuple[str, str]) -> bool | None:
    choice = tui.choose(title, [yes, no], hint=ui.t("menu.hint.back"), plain_hint=ui.t("plain.hint"))
    return None if choice is None else choice == 0


def install_flow(ui: Ui) -> None:
    if not (IS_WINDOWS or IS_LINUX):
        ui.say("install.unsupported")
        return
    print()
    print(ui.t("install.intro.windows" if IS_WINDOWS else "install.intro.linux"))
    print(ui.t("install.interval.tip", default=DEFAULT_MINUTES))
    previous = load_config().get("interval_minutes")
    default = previous or DEFAULT_MINUTES
    while True:
        raw = tui.ask(ui.t("install.interval.ask", default=default), str(default))
        minutes = parse_minutes(raw)
        if minutes is not None:
            break
        ui.say("install.interval.bad")
    with_server = ask_yes_no(ui, ui.t("install.server.title"),
                             (ui.t("install.server.yes"), ui.t("install.server.yes.desc")),
                             (ui.t("install.server.no"), ui.t("install.server.no.desc")))
    if with_server is None:
        return
    install_task(ui, minutes, with_server)


def auto_menu(ui: Ui) -> None:
    options = [(ui.t("auto.install"), ui.t("auto.install.desc", default=DEFAULT_MINUTES)),
               (ui.t("auto.remove"), ui.t("auto.remove.desc")),
               (ui.t("auto.back"), ui.t("auto.back.desc"))]
    choice = tui.choose(ui.t("auto.title"), options, hint=ui.t("menu.hint.back"), plain_hint=ui.t("plain.hint"))
    if choice == 0:
        install_flow(ui)
        tui.pause(ui.t("press_enter"))
    elif choice == 1:
        confirm = ask_yes_no(ui, ui.t("remove.confirm"), (ui.t("remove.yes"), ""), (ui.t("remove.no"), ""))
        if confirm:
            remove_task(ui)
        if confirm is not None:
            tui.pause(ui.t("press_enter"))


def summary_line(ui: Ui) -> str:
    state = load_state()
    age = ago(state.get("fetched_at")) if state else None
    if state is None or age is None:
        return ui.t("main.summary.none")
    return ui.t("main.summary", ago=ui.duration(age),
                h5=ui.pct((state.get("five_hour") or {}).get("pct")),
                d7=ui.pct((state.get("seven_day") or {}).get("pct")))


def main_menu(ui: Ui) -> Ui:
    banner.show(ui.t("banner.title"), ui.t("banner.tagline"))
    keys = ["read", "open", "server", "auto", "status", "lang", "tests", "quit"]
    while True:
        # the server entry follows the real state: offers "start" when it is off, "stop" when it is on
        server_key = "main.server.stop" if ping(DEFAULT_PORT) else "main.server.start"
        options = [(ui.t(server_key if k == "server" else f"main.{k}"),
                    ui.t((server_key if k == "server" else f"main.{k}") + ".desc")) for k in keys]
        choice = tui.choose(ui.t("main.title"), options, hint=ui.t("menu.hint"), plain_hint=ui.t("plain.hint"),
                            intro=summary_line(ui))
        if choice is None or keys[choice] == "quit":
            ui.say("bye")
            return ui
        action = keys[choice]
        print()
        if action == "read":
            read_now(ui)
        elif action == "open":
            open_widget(ui)
        elif action == "server":
            if server_key == "main.server.stop":
                stop_server(ui)
            else:
                open_widget(ui, browser=False)
        elif action == "auto":
            auto_menu(ui)
            print()
            continue
        elif action == "status":
            status(ui)
        elif action == "tests":
            run_tests(ui)
        elif action == "lang":
            lang = pick_language(ui.lang)
            if lang:
                ui = Ui(lang)
                cfg = load_config()
                cfg["lang"] = lang
                save_config(cfg)
            continue
        print()
        tui.pause(ui.t("press_enter"))
        print()


# --------------------------------------------------------------------------- command line

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="run.py",
        description="Claude Usage Tracker launcher. Without a command, an interactive menu opens.")
    p.add_argument("--lang", choices=LANGS, help="menu language (remembered for next time)")
    sub = p.add_subparsers(dest="cmd", metavar="command")
    sub.add_parser("read", help="take a reading now")
    sub.add_parser("open", help="start the widget server (if needed) and open the widget in the browser")
    sub.add_parser("start", help="start the widget server in the background (no browser)")
    sub.add_parser("stop", help="stop the widget server")
    sub.add_parser("status", help="show the latest reading and what is set up")
    sub.add_parser("tests", help="run the project's tests")
    inst = sub.add_parser("install", help="set up automatic readings in the background")
    inst.add_argument("--minutes", type=int, default=DEFAULT_MINUTES, help=f"minutes between readings (default {DEFAULT_MINUTES})")
    inst.add_argument("--with-server", action="store_true", help="also start the widget server at login")
    sub.add_parser("uninstall", help="remove automatic readings (your data is kept)")
    return p


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    args = build_parser().parse_args(argv)
    cfg = load_config()
    lang = args.lang or cfg.get("lang")
    if args.lang and cfg.get("lang") != args.lang:
        cfg["lang"] = args.lang
        save_config(cfg)

    try:
        if args.cmd is None:
            if lang not in LANGS:                          # first run: ask once
                lang = pick_language() or "en"
                cfg["lang"] = lang
                save_config(cfg)
            main_menu(Ui(lang))
            return 0
        ui = Ui(lang or "en")
        if args.cmd == "read":
            return 0 if read_now(ui) else 1
        if args.cmd == "open":
            return 0 if open_widget(ui) else 1
        if args.cmd == "start":
            return 0 if open_widget(ui, browser=False) else 1
        if args.cmd == "stop":
            return 0 if stop_server(ui) else 1
        if args.cmd == "status":
            return 0 if status(ui) else 1
        if args.cmd == "tests":
            return 0 if run_tests(ui) else 1
        if args.cmd == "install":
            minutes = parse_minutes(str(args.minutes))
            if minutes is None:
                ui.say("install.interval.bad")
                return 2
            return 0 if install_task(ui, minutes, args.with_server) else 1
        if args.cmd == "uninstall":
            return 0 if remove_task(ui) else 1
    except KeyboardInterrupt:
        print()
        return 130
    return 0
