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
      "meta.next": "next in {left}",
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
      "error.rate_limited": "Too many requests: the API refused this reading (HTTP 429).",
      "error.file_locked": "data/usage.csv is open in another program (Excel, LibreOffice…): the reading could not be saved.",
      "diag.summary": "Details",
      "diag.what": "What the API said",
      "diag.status": "HTTP status",
      "diag.when": "When",
      "diag.streak": "Failures in a row",
      "diag.retry": "Retry-After",
      "diag.request": "Request id",
      "diag.endpoint": "Endpoint",
      "diag.recent": "Recent failures",
      "diag.logs": "Full history: data/tracker.log (and data/errors.json).",
      "diag.none": "no detail recorded",
      "diag.hint.rate_limited": "Readings are too frequent. Set the automatic interval to 5 minutes or more (launcher menu: Automatic readings). Missed readings cost nothing: the quota is read, not computed.",
      "diag.hint.auth": "The token expired. Open Claude Code once, it refreshes it by itself, then refresh here.",
      "diag.hint.network": "No connection to api.anthropic.com. Check the network or a proxy; the next reading retries by itself.",
      "diag.hint.http": "The API had a problem. If it persists, the endpoint may have changed; check data/last_response.json.",
      "diag.hint.generic": "See data/tracker.log for the full history.",
      "diag.hint.file_locked": "Close the CSV file in your spreadsheet (or open a copy of it instead); the next reading retries by itself.",
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
      "breakdown.days": "Each bar is split by the days that product was really used (hover a segment for its points). “Earlier” = usage from before the per-product tracking started this week: exact in total, but not split by day.",
      "breakdown.earlier": "Earlier",
      "breakdown.earlier.short": "Earl.",
      "breakdown.earlier.title": "Earlier this week (before per-product tracking started)",
      "foot.ratio": "One full 5-hour window ≈ <b>{ratio}</b> of the week {source}",
      "foot.estimated": "(estimated from {pts} pts of 5-hour usage observed).",
      "foot.default": "(default assumption, refined once there is enough history).",
      "foot.limit": "Daily budget = what was left of your week this morning, split over the days until the reset. While the ring's pale zone ahead of the bar is green, you are still inside today's budget; the red zone is overspending. The 5-hour limit is today's remaining budget converted to a 5-hour window; the hourly pace spreads the daily budget over the hours you work (slider).",
      "formulas.title": "How it is computed",
      "formulas.hint": "every number, with your values",
      "formulas.slider": "The hours-per-day slider changes the rows marked “slider”: the weekly pace (it counts working hours instead of calendar time) and the hourly pace. The 5-hour pace is real elapsed time, and the green/red zones and limits come from the daily budget, which does not depend on the slider.",
      "formulas.badge": "slider",
      "f.used.name": "Used (5 h / week)",
      "f.used.eq": "utilization % reported by Claude, for each window",
      "f.pace5.name": "5-hour pace",
      "f.pace5.eq": "(5 h − time left) / 5 h × 100",
      "f.pace7.name": "Weekly pace",
      "f.pace7.eq": "working hours elapsed this week / working hours in the week × 100 (a day = hours per day from the start time; 24 h = plain time)",
      "f.start.name": "Start of your work day",
      "f.start.eq": "first reading today where usage rose; 08:00 when there is none yet",
      "f.start.auto": "(first activity)",
      "f.start.def": "(default)",
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
      "f.l5.eq": "L5 = 5 h used + left today × 100 / r (can exceed 100 %: more than one 5-hour window left today)",
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
      "meta.next": "prochain dans {left}",
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
      "error.rate_limited": "Trop de requêtes : l'API a refusé ce relevé (HTTP 429).",
      "error.file_locked": "data/usage.csv est ouvert dans un autre programme (Excel, LibreOffice…) : le relevé n'a pas pu être enregistré.",
      "diag.summary": "Détails",
      "diag.what": "Ce que l'API a répondu",
      "diag.status": "Statut HTTP",
      "diag.when": "Quand",
      "diag.streak": "Échecs d'affilée",
      "diag.retry": "Retry-After",
      "diag.request": "Identifiant de requête",
      "diag.endpoint": "Endpoint",
      "diag.recent": "Derniers échecs",
      "diag.logs": "Historique complet : data/tracker.log (et data/errors.json).",
      "diag.none": "aucun détail enregistré",
      "diag.hint.rate_limited": "Les relevés sont trop fréquents. Mets l'intervalle automatique à 5 minutes ou plus (menu du lanceur : Relevés automatiques). Un relevé manqué ne coûte rien : le quota est lu, pas calculé.",
      "diag.hint.auth": "Le jeton a expiré. Ouvre Claude Code une fois, il le rafraîchit tout seul, puis actualise ici.",
      "diag.hint.network": "Pas de connexion à api.anthropic.com. Vérifie le réseau ou un proxy ; le prochain relevé réessaiera tout seul.",
      "diag.hint.http": "L'API a eu un problème. Si ça dure, l'endpoint a peut-être changé ; regarde data/last_response.json.",
      "diag.hint.generic": "Voir data/tracker.log pour l'historique complet.",
      "diag.hint.file_locked": "Ferme le fichier CSV dans ton tableur (ou ouvre plutôt une copie) ; le prochain relevé réessaiera tout seul.",
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
      "breakdown.days": "Chaque barre est découpée selon les jours où ce produit a vraiment servi (survole un segment pour ses points). « Avant » = l'usage d'avant le début du suivi par produit cette semaine : exact au total, mais pas découpé par jour.",
      "breakdown.earlier": "Avant",
      "breakdown.earlier.short": "Av.",
      "breakdown.earlier.title": "Plus tôt cette semaine (avant le début du suivi par produit)",
      "foot.ratio": "Une fenêtre 5 h pleine ≈ <b>{ratio}</b> de la semaine {source}",
      "foot.estimated": "(estimé sur {pts} pts de 5 h observés).",
      "foot.default": "(hypothèse par défaut, affinée dès que l'historique suffit).",
      "foot.limit": "Budget du jour = ce qui restait de ta semaine ce matin, réparti sur les jours jusqu'au reset. Tant que la zone pâle devant la barre est verte, tu restes dans le budget du jour ; la zone rouge, c'est un dépassement. La limite 5 h est le budget restant du jour converti en fenêtre 5 h ; le rythme horaire répartit le budget du jour sur les heures que tu travailles (curseur).",
      "formulas.title": "Comment c'est calculé",
      "formulas.hint": "chaque chiffre, avec tes valeurs",
      "formulas.slider": "Le curseur d'heures par jour change les lignes marquées « curseur » : le rythme semaine (il compte les heures de travail au lieu du temps calendaire) et le rythme horaire. Le rythme 5 h est du vrai temps écoulé, et les zones vert/rouge et les limites viennent du budget du jour, qui ne dépend pas du curseur.",
      "formulas.badge": "curseur",
      "f.used.name": "Utilisé (5 h / semaine)",
      "f.used.eq": "% d'utilisation donné par Claude, pour chaque fenêtre",
      "f.pace5.name": "Rythme 5 h",
      "f.pace5.eq": "(5 h − temps restant) / 5 h × 100",
      "f.pace7.name": "Rythme semaine",
      "f.pace7.eq": "heures de travail écoulées cette semaine / heures de travail de la semaine × 100 (un jour = heures par jour à partir de l'heure de début ; 24 h = temps normal)",
      "f.start.name": "Début de ta journée de travail",
      "f.start.eq": "premier relevé du jour où la consommation a augmenté ; 08:00 s'il n'y en a pas encore",
      "f.start.auto": "(première activité)",
      "f.start.def": "(par défaut)",
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
      "f.l5.eq": "L5 = 5 h utilisé + reste du jour × 100 / r (peut dépasser 100 % : plus d'une fenêtre 5 h dans le budget du jour)",
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
