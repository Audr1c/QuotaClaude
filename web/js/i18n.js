/* i18n.js: UI texts (English / French), language choice and number/date formatting.
   Order of precedence for the language: ?lang=xx in the URL > saved choice > browser language.
   Every key must exist in BOTH blocks below (a unit test checks it). One "key": "text", pair per line. */
window.CU = window.CU || {};

(function (CU) {
  const DICT = {
    // ==== en
    en: {
      "app.title": "Claude usage",
      "lang.label": "Language",
      "view.label": "View",
      "view.detail": "Detailed",
      "view.compact": "Compact",
      "refresh": "Refresh",
      "refresh.title": "Take a reading now",
      "refresh.disabled": "Open the widget from the launcher (run.py) to enable this button",
      "meta.updated": "Updated {ago} ago · {n} readings",
      "empty": "No data yet.<br>Click <b>Refresh</b>, or start <code>run.py</code> and choose “Take a reading now”.",
      "error.prefix": "Last reading failed: {msg}",
      "error.no_credentials": "Claude Code credentials not found. Open Claude Code and sign in with your Claude subscription.",
      "error.bad_credentials": "The Claude Code credentials file is unreadable or has no subscription token.",
      "error.auth": "Access refused: the token has probably expired. Open Claude Code once, it refreshes it by itself.",
      "error.http": "The server answered with an error.",
      "error.network": "Network unavailable.",
      "error.bad_json": "The response was not valid JSON.",
      "error.unexpected_response": "Unexpected response from the API (the endpoint may have changed).",
      "error.server": "Local server unreachable: {msg}",
      "error.scripts": "The page could not load all its scripts.",
      "card.five": "5-hour window",
      "card.seven": "Week (7 days)",
      "card.compact": "Usage",
      "gauge.used": "used",
      "gauge.aria.compact": "Week (outer ring) and 5-hour window (inner ring)",
      "reset.in": "resets in {left} · {when}",
      "reset.none": "no window in progress",
      "compact.five": "5 h",
      "compact.seven": "7 d",
      "legend.used": "Used",
      "legend.pace5": "5-hour pace (time elapsed)",
      "legend.limit5": "Limit at the weekly pace",
      "legend.max5": "Max possible until reset",
      "legend.advice5": "Advised to last the week",
      "legend.pace7": "Weekly pace (time elapsed)",
      "legend.perday": "Possible spend",
      "legend.sessions": "Full 5-hour windows left",
      "legend.remaining": "Remaining",
      "unit.perday": "/ day",
      "unit.perhour": "/h",
      "cap": "100% (cap)",
      "compact.legend.pace5": "5-hour pace",
      "compact.legend.limit5": "5-hour limit at weekly pace",
      "compact.legend.pace7": "Weekly pace",
      "compact.label.five": "5 HOURS",
      "compact.label.seven": "7 DAYS",
      "stat.rate": "/h advised (5 h)",
      "stat.day": "/day possible",
      "stat.windows": "5-hour windows",
      "status.ahead": "{n} pts ahead",
      "status.margin": "{n} pts of margin",
      "status.even": "On pace",
      "breakdown.title": "Weekly breakdown",
      "breakdown.count": "{n} products",
      "breakdown.count.one": "1 product",
      "breakdown.quota": "≈ {n} pts of quota",
      "breakdown.note": "Share of what you used this week ({pct} of your quota), by product.",
      "foot.ratio": "One full 5-hour window ≈ <b>{ratio}</b> of the week {source}",
      "foot.estimated": "(estimated from {pts} pts of 5-hour usage observed).",
      "foot.default": "(default assumption, refined once there is enough history).",
      "foot.limit": "The orange limit on the 5-hour window spreads the rest of your week over the hours you work per day (slider), not over the nights.",
      "hours.title": "Hours per day",
      "hours.aria": "Hours of Claude use per day",
      "hours.value": "{n} h",
      "hours.hint": "Hours you use Claude per working day. The rest of your week is spread over them.",
    },
    // ==== fr
    fr: {
      "app.title": "Quota Claude",
      "lang.label": "Langue",
      "view.label": "Présentation",
      "view.detail": "Détaillé",
      "view.compact": "Compact",
      "refresh": "Relever",
      "refresh.title": "Faire un relevé maintenant",
      "refresh.disabled": "Ouvre le widget depuis le lanceur (run.py) pour activer ce bouton",
      "meta.updated": "Relevé il y a {ago} · {n} relevés",
      "empty": "Pas encore de données.<br>Clique sur <b>Relever</b>, ou lance <code>run.py</code> et choisis « Faire un relevé maintenant ».",
      "error.prefix": "Dernier relevé en échec : {msg}",
      "error.no_credentials": "Identifiants Claude Code introuvables. Ouvre Claude Code et connecte-toi avec ton abonnement Claude.",
      "error.bad_credentials": "Le fichier d'identifiants de Claude Code est illisible ou sans jeton d'abonnement.",
      "error.auth": "Accès refusé : le jeton a sans doute expiré. Ouvre Claude Code une fois, il le rafraîchit tout seul.",
      "error.http": "Le serveur a répondu par une erreur.",
      "error.network": "Réseau indisponible.",
      "error.bad_json": "La réponse n'était pas du JSON valide.",
      "error.unexpected_response": "Réponse inattendue de l'API (l'endpoint a peut-être changé).",
      "error.server": "Serveur local injoignable : {msg}",
      "error.scripts": "La page n'a pas pu charger tous ses scripts.",
      "card.five": "Fenêtre 5 heures",
      "card.seven": "Semaine (7 jours)",
      "card.compact": "Quota",
      "gauge.used": "utilisés",
      "gauge.aria.compact": "Semaine (anneau extérieur) et fenêtre 5 heures (anneau intérieur)",
      "reset.in": "reset dans {left} · {when}",
      "reset.none": "pas de fenêtre en cours",
      "compact.five": "5 h",
      "compact.seven": "7 j",
      "legend.used": "Utilisé",
      "legend.pace5": "Rythme 5 h (temps écoulé)",
      "legend.limit5": "Limite au rythme de la semaine",
      "legend.max5": "Max possible d'ici le reset",
      "legend.advice5": "Conseillé pour tenir la semaine",
      "legend.pace7": "Rythme semaine (temps écoulé)",
      "legend.perday": "Dépense possible",
      "legend.sessions": "Fenêtres 5 h pleines restantes",
      "legend.remaining": "Reste",
      "unit.perday": "/ jour",
      "unit.perhour": "/h",
      "cap": "100 % (plafond)",
      "compact.legend.pace5": "Rythme 5 h",
      "compact.legend.limit5": "Limite 5 h au rythme semaine",
      "compact.legend.pace7": "Rythme semaine",
      "compact.label.five": "5 HEURES",
      "compact.label.seven": "7 JOURS",
      "stat.rate": "/h conseillé (5 h)",
      "stat.day": "/jour possible",
      "stat.windows": "fenêtres 5 h",
      "status.ahead": "En avance de {n} pts",
      "status.margin": "Marge de {n} pts",
      "status.even": "Dans le rythme",
      "breakdown.title": "Répartition de la semaine",
      "breakdown.count": "{n} produits",
      "breakdown.count.one": "1 produit",
      "breakdown.quota": "≈ {n} pts du quota",
      "breakdown.note": "Part de ce que tu as consommé cette semaine ({pct} du quota), par produit.",
      "foot.ratio": "Une fenêtre 5 h pleine ≈ <b>{ratio}</b> de la semaine {source}",
      "foot.estimated": "(estimé sur {pts} pts de 5 h observés).",
      "foot.default": "(hypothèse par défaut, affinée dès que l'historique suffit).",
      "foot.limit": "La limite orange de la fenêtre 5 h répartit le reste de ta semaine sur les heures que tu travailles par jour (curseur), pas sur les nuits.",
      "hours.title": "Heures par jour",
      "hours.aria": "Heures d'utilisation de Claude par jour",
      "hours.value": "{n} h",
      "hours.hint": "Heures où tu utilises Claude par jour travaillé. Le reste de ta semaine est réparti dessus.",
    },
  };

  const LANGS = ["en", "fr"];
  const KEY = "cu.lang";

  function detect() {
    try {
      const q = new URLSearchParams(location.search).get("lang");
      if (LANGS.includes(q)) { try { localStorage.setItem(KEY, q); } catch (e) { /* ignore */ } return q; }
    } catch (e) { /* ignore */ }
    try {
      const s = localStorage.getItem(KEY);
      if (LANGS.includes(s)) return s;
    } catch (e) { /* storage unavailable */ }
    return (navigator.language || "en").slice(0, 2).toLowerCase() === "fr" ? "fr" : "en";
  }

  CU.lang = detect();

  CU.setLang = function (lang) {
    if (!LANGS.includes(lang)) return;
    CU.lang = lang;
    try { localStorage.setItem(KEY, lang); } catch (e) { /* ignore */ }
  };

  /* t("key", {name: value}) -> text with {name} placeholders replaced; falls back to English, then to the key. */
  CU.t = function (key, vars) {
    let s = (DICT[CU.lang] && DICT[CU.lang][key]) || DICT.en[key] || key;
    if (vars) for (const k in vars) s = s.split("{" + k + "}").join(vars[k]);
    return s;
  };

  CU.hasText = key => !!(DICT[CU.lang] && DICT[CU.lang][key]) || !!DICT.en[key];

  /* number / duration / date formatting following the current language */
  CU.fmt = {
    num(v, d = 1) {
      if (v == null || !isFinite(v)) return "—";
      const s = v.toFixed(d);
      return CU.lang === "fr" ? s.replace(".", ",") : s;
    },
    pct(v, d = 0) {
      if (v == null || !isFinite(v)) return "—";
      return CU.fmt.num(v, d) + (CU.lang === "fr" ? " %" : "%");
    },
    left(ms) {
      const fr = CU.lang === "fr";
      if (ms <= 0) return fr ? "maintenant" : "now";
      const m = Math.round(ms / 60e3), d = Math.floor(m / 1440), h = Math.floor(m % 1440 / 60), mm = m % 60;
      const pad = String(mm).padStart(2, "0");
      if (d) return fr ? `${d} j ${h} h` : `${d}d ${h}h`;
      if (h) return fr ? `${h} h ${pad}` : `${h}h ${pad}m`;
      return `${mm} min`;
    },
    when(date) {
      return date.toLocaleString(CU.lang === "fr" ? "fr-FR" : "en-GB", { weekday: "short", hour: "2-digit", minute: "2-digit" });
    },
  };

  /* fill the static parts of index.html: data-i18n (text), data-i18n-title, data-i18n-aria */
  CU.applyStatic = function () {
    document.documentElement.lang = CU.lang;
    document.title = CU.t("app.title");
    document.querySelectorAll("[data-i18n]").forEach(el => { el.textContent = CU.t(el.dataset.i18n); });
    document.querySelectorAll("[data-i18n-title]").forEach(el => { el.title = CU.t(el.dataset.i18nTitle); });
    document.querySelectorAll("[data-i18n-aria]").forEach(el => { el.setAttribute("aria-label", CU.t(el.dataset.i18nAria)); });
  };
})(window.CU);
