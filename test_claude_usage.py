# -*- coding: utf-8 -*-
"""
Tests du tracker.   python test_claude_usage.py

- Tests hors ligne : reponse API simulee, verifie CSV / latest.js / estimation du ratio.
- Test reel (test_live_fetch) : interroge vraiment l'API si les identifiants Claude Code
  sont presents sur la machine, et affiche tes valeurs. Ignore sinon.
"""
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import claude_usage as cu

T0 = datetime(2026, 10, 22, 9, 0, tzinfo=timezone.utc)
R5 = "2026-10-22T12:00:00+00:00"
R7 = "2026-10-27T18:00:00.123456+00:00"


def payload(h5, d7, r5=R5, r7=R7):
    return {
        "five_hour": {"utilization": h5, "resets_at": r5},
        "seven_day": {"utilization": d7, "resets_at": r7},
        "seven_day_opus": None,
        "extra_usage": {"is_enabled": False},
    }


class OfflineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def read_js_state(self):
        js = (self.dir / "latest.js").read_text(encoding="utf-8")
        self.assertTrue(js.startswith("window.CLAUDE_USAGE = "))
        return json.loads(js[len("window.CLAUDE_USAGE = "):].rstrip().rstrip(";"))

    def test_releve_ecrit_csv_et_js(self):
        cu.run(self.dir, payload(12.0, 34.0), T0)
        row, err, _ = cu.run(self.dir, payload(15.0, 34.5), T0 + timedelta(minutes=10))
        self.assertIsNone(err)
        lines = (self.dir / "usage.csv").read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(lines[0].split(","), cu.CSV_FIELDS)
        self.assertEqual(len(lines), 3)
        st = self.read_js_state()
        self.assertEqual(st["five_hour"]["pct"], 15.0)
        self.assertEqual(st["seven_day"]["pct"], 34.5)
        self.assertEqual(st["seven_day"]["resets_at"], "2026-10-27T18:00:00+00:00")
        self.assertEqual(len(st["history"]), 2)

    def test_ratio_estime_dans_une_meme_fenetre(self):
        # 5 h : 0 -> 40 % ; 7 j : 20 -> 24 %  => une fenetre pleine = 10 % de la semaine
        for i in range(5):
            cu.run(self.dir, payload(10.0 * i, 20.0 + i), T0 + timedelta(minutes=10 * i))
        st = self.read_js_state()
        self.assertAlmostEqual(st["ratio_estimate"], 10.0)

    def test_ratio_ignore_les_resets(self):
        cu.run(self.dir, payload(80.0, 20.0), T0)
        # nouvelle fenetre 5 h : la chute 80 -> 5 ne doit pas compter
        cu.run(self.dir, payload(5.0, 30.0, r5="2026-10-22T17:00:00+00:00"), T0 + timedelta(hours=5))
        st = self.read_js_state()
        self.assertIsNone(st["ratio_estimate"])
        self.assertEqual(st["ratio_default"], cu.DEFAULT_RATIO)

    def test_erreur_garde_le_dernier_etat(self):
        cu.run(self.dir, payload(42.0, 50.0), T0)
        row, err, _ = cu.run(self.dir, {"autre": 1}, T0 + timedelta(minutes=10))
        self.assertIsNone(row)
        self.assertIn("Reponse inattendue", err)
        st = self.read_js_state()
        self.assertEqual(st["five_hour"]["pct"], 42.0)
        self.assertIn("Reponse inattendue", st["error"])

    def test_repartition_par_produit(self):
        p = payload(10.0, 20.0)
        p["seven_day_breakdown"] = {"as_of": R5, "rows": [
            {"key": "claude_code", "display_name": "Claude Code", "percent": 28},
            {"key": "chat", "display_name": "Chats", "percent": 72}]}
        cu.run(self.dir, p, T0)
        cu.run(self.dir, {"autre": 1}, T0 + timedelta(minutes=10))   # echec : on garde la repartition
        st = self.read_js_state()
        self.assertEqual([r["pct"] for r in st["breakdown"]["rows"]], [28.0, 72.0])
        self.assertEqual(st["breakdown"]["rows"][0]["name"], "Claude Code")

    def test_fenetre_sans_reset(self):
        row, err, _ = cu.run(self.dir, {"five_hour": {"utilization": 0, "resets_at": None},
                                         "seven_day": {"utilization": 3, "resets_at": R7}}, T0)
        self.assertIsNone(err)
        self.assertEqual(row["five_hour_resets_at"], "")


class ServerTests(unittest.TestCase):
    """Le serveur du widget repond, sert les fichiers et refuse les autres origines."""

    @classmethod
    def setUpClass(cls):
        import threading
        import urllib.request
        import server
        cls.srv = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        cls.base = f"http://127.0.0.1:{cls.srv.server_address[1]}"
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def get(self, path):
        import urllib.error
        try:
            with self.opener.open(self.base + path, timeout=5) as r:
                return r.status, r.headers.get("Content-Type", ""), r.read()
        except urllib.error.HTTPError as e:
            return e.code, "", b""

    def test_ping_et_fichiers(self):
        self.assertEqual(self.get("/api/ping")[0], 200)
        code, ctype, _ = self.get("/web/js/app.js")
        self.assertEqual(code, 200)
        self.assertIn("javascript", ctype)
        self.assertEqual(self.get("/web/index.html")[0], 200)

    def test_pas_de_sortie_du_dossier_web(self):
        self.assertEqual(self.get("/web/../claude_usage.py")[0], 404)
        self.assertEqual(self.get("/claude_usage.py")[0], 404)

    def test_refuse_un_nom_de_domaine_detourne(self):
        import http.client
        c = http.client.HTTPConnection("127.0.0.1", self.srv.server_address[1], timeout=5)
        c.request("GET", "/data/latest.json", headers={"Host": "evil.example"})
        self.assertEqual(c.getresponse().status, 403)
        c.close()

    def test_refresh_refuse_autre_origine(self):
        import urllib.error
        import urllib.request
        req = urllib.request.Request(self.base + "/api/refresh", method="POST", headers={"Origin": "http://exemple.com"})
        with self.assertRaises(urllib.error.HTTPError) as cm:
            self.opener.open(req, timeout=5)
        self.assertEqual(cm.exception.code, 403)


class LiveTest(unittest.TestCase):
    def test_live_fetch(self):
        try:
            token = cu.read_token()
        except cu.TrackerError as e:
            self.skipTest(str(e))
        data = cu.fetch_usage(token)
        row = cu.build_row(data, cu.now_utc())
        print("\n--- Valeurs reelles ---")
        print(" 5 heures :", row["five_hour_pct"], "%  reset", row["five_hour_resets_at"] or "-")
        print(" 7 jours  :", row["seven_day_pct"], "%  reset", row["seven_day_resets_at"] or "-")
        print(" cles de la reponse :", sorted(data))
        self.assertTrue(row["seven_day_pct"] != "" or row["five_hour_pct"] != "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
