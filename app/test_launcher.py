# -*- coding: utf-8 -*-
"""
Tests of the launcher, of the French/English texts and of the "code is English" rule.   python test_launcher.py
"""
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from launcher import app, strings  # noqa: E402


def placeholders(text: str) -> set:
    return set(re.findall(r"\{(\w+)\}", text))


class LauncherTextTests(unittest.TestCase):
    def test_both_languages_have_the_same_keys_and_placeholders(self):
        en, fr = strings.EN, strings.FR
        self.assertEqual(sorted(set(en) ^ set(fr)), [], "keys present in only one language")
        for key in en:
            self.assertEqual(placeholders(en[key]), placeholders(fr[key]), f"placeholders differ for {key}")

    def test_every_key_used_by_the_code_exists(self):
        source = (ROOT / "launcher" / "app.py").read_text(encoding="utf-8")
        used = set(re.findall(r"""\bt\(\s*["']([\w.]+)["']""", source)) | set(re.findall(r"""say\(\s*["']([\w.]+)["']""", source))
        used = {k for k in used if not k.endswith(".")}     # prefixes of dynamic keys, checked explicitly below
        entries = ("read", "open", "server.start", "server.stop", "auto", "status", "setup", "lang", "tests", "quit")
        used |= {f"main.{k}" for k in entries}
        used |= {f"main.{k}.desc" for k in entries}
        used |= {f"kind.{k}" for k in ("task", "systemd", "cron", "manual")}
        used |= {f"group.{g}" for g, _ in app.MENU}
        used |= {f"error.{k}" for k in ("no_credentials", "bad_credentials", "auth", "token_expired", "file_locked", "http", "network", "bad_json", "unexpected_response")}
        self.assertEqual(sorted(k for k in used if k not in strings.EN), [])

    def test_weekday_tables_have_seven_days(self):
        for lang in strings.LANGS:
            self.assertEqual(len(strings.STRINGS[lang]["weekdays"].split(",")), 7)


class WebTextTests(unittest.TestCase):
    @staticmethod
    def blocks():
        text = (ROOT / "web" / "js" / "i18n.js").read_text(encoding="utf-8")
        en = text.split("// ==== en")[1].split("// ==== fr")[0]
        fr = text.split("// ==== fr")[1]
        pair = re.compile(r'^\s*"([^"]+)":\s*"(.*)",\s*$', re.M)
        return dict(pair.findall(en)), dict(pair.findall(fr))

    def test_both_languages_have_the_same_keys_and_placeholders(self):
        en, fr = self.blocks()
        self.assertGreater(len(en), 50)
        self.assertEqual(sorted(set(en) ^ set(fr)), [], "keys present in only one language")
        for key in en:
            self.assertEqual(placeholders(en[key]), placeholders(fr[key]), f"placeholders differ for {key}")

    def test_every_key_used_by_the_page_exists(self):
        en, _ = self.blocks()
        used = set()
        for path in list((ROOT / "web" / "js").glob("*.js")) + [ROOT / "web" / "index.html"]:
            if path.name == "i18n.js":
                continue                               # defines t(); its comments contain examples
            text = path.read_text(encoding="utf-8")
            used |= set(re.findall(r"""\bt\(\s*["']([a-z0-9._]+)["']""", text))
            used |= set(re.findall(r"""data-i18n(?:-title|-aria)?="([^"]+)\"""", text))
        used = {k for k in used if not k.endswith(".")}     # prefixes of dynamic keys, checked explicitly below
        used |= {"status.ahead", "status.margin", "status.even"}
        used |= {f"error.{k}" for k in ("no_credentials", "bad_credentials", "auth", "token_expired", "file_locked", "http", "network", "bad_json", "unexpected_response")}
        self.assertEqual(sorted(k for k in used if k not in en), [])


class CodeIsEnglishTests(unittest.TestCase):
    """Code, comments and messages are English. Only the translation files (and the tests that check them) may contain French."""

    ALLOWED = {Path("launcher/strings.py"), Path("web/js/i18n.js"), Path("test_launcher.py"), Path("test_vscode.py")}
    ACCENTS = re.compile("[àâäçéèêëîïôöùûüœÀÂÄÇÉÈÊËÎÏÔÖÙÛÜŒ]")

    def test_no_french_outside_the_translation_files(self):
        offenders = []
        for ext in ("*.py", "*.sh", "*.ps1", "*.bat", "*.js", "*.html", "*.css"):
            for path in ROOT.rglob(ext):
                rel = path.relative_to(ROOT)
                if rel in self.ALLOWED or {"data", ".git", "__pycache__"} & set(rel.parts):
                    continue
                if self.ACCENTS.search(path.read_text(encoding="utf-8", errors="replace")):
                    offenders.append(str(rel))
        self.assertEqual(offenders, [])


class WizardTests(unittest.TestCase):
    """The quick setup with --yes takes every recommended answer, and never installs twice."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = Path(self.tmp.name)
        self.calls = []
        self.patches = [mock.patch.object(app, "DATA", d), mock.patch.object(app, "CONFIG_FILE", d / "config.json"),
                        mock.patch.object(app, "IS_LINUX", True), mock.patch.object(app, "IS_WINDOWS", False),
                        mock.patch.object(app, "token_problem", lambda: None),
                        mock.patch.object(app, "read_now", lambda ui: self.calls.append("read") or True),
                        mock.patch.object(app, "open_widget", lambda ui, browser=True: self.calls.append("open") or True),
                        mock.patch.object(app, "install_task", lambda ui, s: self.calls.append(("install", s)) or True),
                        mock.patch.object(app, "shortcut_paths", lambda: [d / "never-written.desktop"]),
                        mock.patch.object(app, "make_shortcut", lambda ui, remove=False: self.calls.append("shortcut") or True)]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def run_quiet(self, kind):
        with mock.patch.object(app, "scheduler_kind", lambda: kind), mock.patch("sys.stdout", io.StringIO()) as out:
            app.setup_wizard(app.Ui("en"), yes=True)
        return out.getvalue()

    def test_yes_takes_the_recommended_answers(self):
        out = self.run_quiet(None)
        self.assertEqual(self.calls, ["read", ("install", True), "shortcut"])      # --yes does not open a browser
        self.assertTrue(app.load_config().get("setup_done"))
        self.assertIn("run.py uninstall", out)

    def test_replay_does_not_install_again(self):
        app.save_config({"server_at_login": True})
        out = self.run_quiet("systemd")
        self.assertEqual(self.calls, ["read", "shortcut"])
        self.assertIn("already set up", out)

    def test_missing_token_skips_the_reading(self):
        err = app.cu.TrackerError("no_credentials", "nope")
        with mock.patch.object(app, "token_problem", lambda: err):
            out = self.run_quiet(None)
        self.assertNotIn("read", self.calls)
        self.assertIn("/login", out)


class ShortcutTests(unittest.TestCase):
    def test_desktop_entry_opens_the_widget_and_quotes_paths(self):
        text = app.desktop_entry('/opt/my "py"/python3')
        self.assertIn('Exec="/opt/my \\"py\\"/python3" ', text)
        self.assertIn('run.py" open', text)
        self.assertIn("Terminal=false", text)

    def test_linux_shortcut_is_written_and_removed(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(app, "IS_LINUX", True), \
                mock.patch.object(app, "IS_WINDOWS", False), mock.patch.object(app, "shortcut_paths", lambda: [Path(d) / "a" / "x.desktop"]), \
                mock.patch("sys.stdout", io.StringIO()):
            self.assertTrue(app.make_shortcut(app.Ui("en")))
            f = Path(d) / "a" / "x.desktop"
            self.assertTrue(f.is_file() and os.access(f, os.X_OK))
            self.assertTrue(app.make_shortcut(app.Ui("en"), remove=True))
            self.assertFalse(f.exists())


class LauncherLogicTests(unittest.TestCase):
    def test_duration_and_percent_formatting(self):
        en, fr = app.Ui("en"), app.Ui("fr")
        self.assertEqual(en.duration(35 * 60), "35 min")
        self.assertEqual(en.duration(2 * 3600 + 9 * 60), "2h 09m")
        self.assertEqual(en.duration(3 * 86400 + 4 * 3600), "3d 4h")
        self.assertEqual(fr.duration(2 * 3600 + 9 * 60), "2 h 09")
        self.assertEqual(fr.duration(3 * 86400 + 4 * 3600), "3 j 4 h")
        self.assertEqual(en.pct(36.5), "36.5%")
        self.assertEqual(fr.pct(36.5), "36,5 %")
        self.assertEqual(en.pct(None), "—")

    def test_unknown_error_code_falls_back_to_the_raw_message(self):
        ui = app.Ui("fr")
        self.assertIn("Identifiants", ui.error_text("no_credentials", "raw"))
        self.assertEqual(ui.error_text("something_new", "raw message"), "raw message")


@unittest.skipIf(os.name == "nt", "pty-based smoke test (POSIX only)")
class MenuSmokeTest(unittest.TestCase):
    """Drives the real menu through a pseudo-terminal: language prompt, main menu, Status, quit."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name) / "tracker"
        shutil.copytree(ROOT, self.dir, ignore=shutil.ignore_patterns("data", ".git", "__pycache__", "docs"))

    def tearDown(self):
        self.tmp.cleanup()

    def drive(self, steps, timeout=15):
        import fcntl
        import pty
        import select
        import struct
        import termios
        import time
        env = dict(os.environ, TERM="xterm", CLAUDE_CONFIG_DIR=str(self.dir / "no-claude"))
        env.pop("CLAUDE_USAGE_TOKEN", None)
        env.pop("NO_COLOR", None)
        pid, fd = pty.fork()
        if pid == 0:
            os.chdir(self.dir)
            os.execve(sys.executable, [sys.executable, "run.py"], env)
        fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", 40, 100, 0, 0))
        seen = ""

        def read_until(text):
            nonlocal seen
            end = time.time() + timeout
            while text not in seen:
                if time.time() > end:
                    self.fail(f"timeout waiting for {text!r}; screen so far:\n{seen[-800:]}")
                if select.select([fd], [], [], 0.2)[0]:
                    try:
                        seen += os.read(fd, 4096).decode("utf-8", "replace")
                    except OSError:
                        break

        for expected, keys in steps:
            read_until(expected)
            if keys:
                os.write(fd, keys.encode())
            seen = ""                                  # the next step must wait for FRESH output
        _, status = os.waitpid(pid, 0)
        os.close(fd)
        return seen, os.waitstatus_to_exitcode(status) if hasattr(os, "waitstatus_to_exitcode") else status

    def test_first_run_language_then_quick_setup_then_status_then_quit(self):
        seen, code = self.drive([
            ("Language / Langue", "\x1b[B"),              # arrow down: Francais
            ("Français", "\r"),                            # Enter: choose it
            ("Vérifier à nouveau", "2"),                   # no Claude Code token here: go on without it
            ("Faire les relevés automatiquement", "2"),    # do not install anything from a test
            ("Ajouter un raccourci", "2"),
            ("Ouvrir le widget maintenant", "2"),
            ("Appuie sur Entrée pour aller au menu", "\r"),
            ("Que veux-tu faire", "3"),                    # direct jump to "État" (group "Voir")
            ("Dernier relevé", "\r"),                      # status shown, Enter to go back
            ("relevé auto", "q"),                          # the state line is on top of the menu; quit
            ("À bientôt", ""),
        ])
        self.assertEqual(code, 0)
        cfg = json.loads((self.dir / "data" / "config.json").read_text(encoding="utf-8"))
        self.assertEqual(cfg.get("lang"), "fr")
        self.assertTrue(cfg.get("setup_done"))

    def test_read_without_credentials_reports_a_clear_error(self):
        env = dict(os.environ, CLAUDE_CONFIG_DIR=str(self.dir / "no-claude"))
        env.pop("CLAUDE_USAGE_TOKEN", None)
        import subprocess
        r = subprocess.run([sys.executable, "run.py", "--lang", "en", "read"], cwd=self.dir, env=env,
                           capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 1)
        self.assertIn("Reading failed", r.stdout)
        self.assertIn("credentials not found", r.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
