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
      "legend.limit5": "Limit for today's budget",
      "legend.today": "Left in today's budget",
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
      "compact.legend.limit5": "5-hour limit for today's budget",
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
      "foot.limit": "Daily budget = what was left of your week this morning, split over the days until the reset. While the ring's pale zone ahead of the bar is green, you are still inside today's budget; the red zone is overspending. The 5-hour limit is today's remaining budget converted to a 5-hour window; the hourly pace spreads the daily budget over the hours you work (slider).",
      "formulas.title": "How it is computed",
      "formulas.hint": "every number, with your values",
      "formulas.slider": "The hours-per-day slider only changes the row marked “slider” (the hourly pace). The two pace markers (5-hour and weekly) are pure elapsed time, so they never move with the slider; the green/red zones and the limits come from the daily budget, which does not depend on it either.",
      "formulas.badge": "slider",
      "f.used.name": "Used (5 h / week)",
      "f.used.eq": "utilization % reported by Claude, for each window",
      "f.pace5.name": "5-hour pace",
      "f.pace5.eq": "(5 h − time left) / 5 h × 100",
      "f.pace7.name": "Weekly pace",
      "f.pace7.eq": "(7 d − time left) / 7 d × 100",
      "f.ratio.name": "Cost of a 5-hour window",
      "f.ratio.eq": "r = % of the week used per 100 % of a 5-hour window",
      "f.ratio.est": "estimated from your readings",
      "f.ratio.def": "default assumption",
      "f.u0.name": "Week used at the start of today",
      "f.u0.eq": "u0 = weekly % at the last reading before midnight (oldest reading if none)",
      "f.days.name": "Days until the reset",
      "f.days.eq": "D = (weekly reset − today 00:00) / 24 h",
      "f.days.calc": "→",
      "f.budget.name": "Daily budget (possible spend / day)",
      "f.budget.eq": "B = (100 − u0) / D",
      "f.l7.name": "Weekly limit for now (green/red boundary, week ring)",
      "f.l7.eq": "L7 = u0 + B",
      "f.left.name": "Left in today's budget",
      "f.left.eq": "max(0, L7 − week used)",
      "f.l5.name": "5-hour limit (green/red boundary, 5-hour ring)",
      "f.l5.eq": "L5 = 5 h used + left today × 100 / r (max 100)",
      "f.rate.name": "Advised per hour (5-hour %/h)",
      "f.rate.eq": "B / hours per day × 100 / r",
      "f.max.name": "Max possible until reset",
      "f.max.eq": "(100 − 5 h used) / hours left in the window",
      "f.win.name": "Full 5-hour windows left",
      "f.win.eq": "(100 − week used) / r",
      "f.share.name": "Weekly breakdown",
      "f.share.eq": "product share (reported) × week used / 100 = points of the weekly quota",
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
      "legend.limit5": "Limite du budget du jour",
      "legend.today": "Reste du budget du jour",
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
      "compact.legend.limit5": "Limite 5 h du budget du jour",
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
      "foot.limit": "Budget du jour = ce qui restait de ta semaine ce matin, réparti sur les jours jusqu'au reset. Tant que la zone pâle devant la barre est verte, tu restes dans le budget du jour ; la zone rouge, c'est un dépassement. La limite 5 h est le budget restant du jour converti en fenêtre 5 h ; le rythme horaire répartit le budget du jour sur les heures que tu travailles (curseur).",
      "formulas.title": "Comment c'est calculé",
      "formulas.hint": "chaque chiffre, avec tes valeurs",
      "formulas.slider": "Le curseur d'heures par jour ne change que la ligne marquée « curseur » (le rythme horaire). Les deux marqueurs de rythme (5 h et semaine) ne dépendent que du temps écoulé : ils ne bougent donc jamais avec le curseur ; les zones vert/rouge et les limites viennent du budget du jour, qui n'en dépend pas non plus.",
      "formulas.badge": "curseur",
      "f.used.name": "Utilisé (5 h / semaine)",
      "f.used.eq": "% d'utilisation donné par Claude, pour chaque fenêtre",
      "f.pace5.name": "Rythme 5 h",
      "f.pace5.eq": "(5 h − temps restant) / 5 h × 100",
      "f.pace7.name": "Rythme semaine",
      "f.pace7.eq": "(7 j − temps restant) / 7 j × 100",
      "f.ratio.name": "Coût d'une fenêtre 5 h",
      "f.ratio.eq": "r = % de la semaine consommé par 100 % d'une fenêtre 5 h",
      "f.ratio.est": "estimé sur tes relevés",
      "f.ratio.def": "hypothèse par défaut",
      "f.u0.name": "Semaine utilisée en début de journée",
      "f.u0.eq": "u0 = % hebdo au dernier relevé avant minuit (le plus ancien s'il n'y en a pas)",
      "f.days.name": "Jours jusqu'au reset",
      "f.days.eq": "D = (reset hebdo − aujourd'hui 00:00) / 24 h",
      "f.days.calc": "→",
      "f.budget.name": "Budget du jour (dépense possible / jour)",
      "f.budget.eq": "B = (100 − u0) / D",
      "f.l7.name": "Limite hebdo à cet instant (frontière vert/rouge, anneau semaine)",
      "f.l7.eq": "L7 = u0 + B",
      "f.left.name": "Reste du budget du jour",
      "f.left.eq": "max(0, L7 − semaine utilisée)",
      "f.l5.name": "Limite 5 h (frontière vert/rouge, anneau 5 h)",
      "f.l5.eq": "L5 = 5 h utilisé + reste du jour × 100 / r (max 100)",
      "f.rate.name": "Conseillé par heure (% 5 h /h)",
      "f.rate.eq": "B / heures par jour × 100 / r",
      "f.max.name": "Maximum possible jusqu'au reset",
      "f.max.eq": "(100 − 5 h utilisé) / heures restantes de la fenêtre",
      "f.win.name": "Fenêtres 5 h pleines restantes",
      "f.win.eq": "(100 − semaine utilisée) / r",
      "f.share.name": "Répartition de la semaine",
      "f.share.eq": "part du produit (donnée par Claude) × semaine utilisée / 100 = points du quota hebdo",
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
