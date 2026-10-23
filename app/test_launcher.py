# -*- coding: utf-8 -*-
"""
Tests of the launcher, of the French/English texts and of the "code is English" rule.   python test_launcher.py
"""
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
        entries = ("read", "open", "server.start", "server.stop", "auto", "status", "lang", "tests", "quit")
        used |= {f"main.{k}" for k in entries}
        used |= {f"main.{k}.desc" for k in entries}
        used |= {f"kind.{k}" for k in ("task", "systemd", "cron")}
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

    ALLOWED = {Path("launcher/strings.py"), Path("web/js/i18n.js"), Path("test_launcher.py")}
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

    def test_first_run_language_then_status_then_quit(self):
        seen, code = self.drive([
            ("Language / Langue", "\x1b[B"),              # arrow down: Francais
            ("Français", "\r"),                            # Enter: choose it
            ("Que veux-tu faire", "5"),                    # direct jump to "État"
            ("Dernier relevé", "\r"),                      # status shown, Enter to go back
            ("Que veux-tu faire", "q"),                    # quit
            ("À bientôt", ""),
        ])
        self.assertEqual(code, 0)
        self.assertIn('"lang": "fr"', (self.dir / "data" / "config.json").read_text(encoding="utf-8"))

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
