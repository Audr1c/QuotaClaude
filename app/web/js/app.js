/* app.js: data loading, compactness level, panel choice, language switch, refresh button, auto-refresh.
   Two modes:
     - through the local server (http://127.0.0.1:8765): data as JSON + the Refresh button works;
     - file opened directly (file://): data via data/latest.js, Refresh button disabled. */
(function (CU) {
  const $ = id => document.getElementById(id);

  if (!CU.compute || !CU.gauge || !CU.views || !CU.t) {      // a script did not load: the inline diagnostic already says why
    $("app").innerHTML = `<div class="card empty">The page could not load all its scripts.</div>`;
    return;
  }

  const SERVED = location.protocol.startsWith("http");
  const LEVEL_KEY = "cu.detail", PANELS_KEY = "cu.panels", BREAKDOWN_KEY = "cu.breakdownOpen";
  const HOURS_KEY = "cu.hours", WORK_KEY = "cu.workHours";
  const chartsOpen = {};
  let panels = {}, levelPref = "auto", breakdownOpen = false, hours = 8, workOn = false;
  try {
    const saved = parseInt(localStorage.getItem(HOURS_KEY), 10);
    if (saved >= 1 && saved <= 24) hours = saved;
    const lv = parseInt(localStorage.getItem(LEVEL_KEY), 10);
    if (lv >= 1 && lv <= 7) levelPref = lv;
    const pn = JSON.parse(localStorage.getItem(PANELS_KEY) || "null");
    if (pn && typeof pn === "object") panels = pn;
    breakdownOpen = localStorage.getItem(BREAKDOWN_KEY) === "1";
    workOn = localStorage.getItem(WORK_KEY) === "1";
  } catch (e) { /* storage unavailable */ }

  // the breakdown <details> is recreated on every render: remember whether it is open
  $("app").addEventListener("toggle", e => {
    if (e.target.classList.contains("chart")) { chartsOpen[e.target.dataset.key] = e.target.open; return; }
    if (!e.target.classList.contains("breakdown")) return;
    breakdownOpen = e.target.open; CU.fitBars(e.target);
    try { localStorage.setItem(BREAKDOWN_KEY, e.target.open ? "1" : "0"); } catch (err) { /* ignore */ }
  }, true);

  /* ---------- data ---------- */
  let pollerState = null;                      // data/poller.json: when the background poller reads next
  function loadData() {
    if (SERVED) {
      const json = url => fetch(url, { cache: "no-store" }).then(r => (r.ok ? r.json() : null)).catch(() => null);
      return Promise.all([json("../data/latest.json"), json("../data/poller.json")])
        .then(([d, p]) => { if (d) window.CLAUDE_USAGE = d; pollerState = p; });
    }
    return new Promise(resolve => {            // file://: fetch is blocked, reload a <script> instead
      const s = document.createElement("script");
      s.src = "../data/latest.js?t=" + Date.now();
      s.onload = s.onerror = () => { s.remove(); resolve(); };
      document.body.appendChild(s);
    });
  }

  /* error banner: one clear line + an expandable diagnostic panel (what the API said, when, streak, hint, history) */
  const esc = x => String(x == null ? "" : x).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const when = iso => { const d = new Date(iso); return isNaN(d) ? esc(iso) : d.toLocaleString(CU.lang === "fr" ? "fr-FR" : "en-GB"); };

  function errorHtml(code, raw, diag) {
    const msg = code && CU.hasText("error." + code) ? CU.t("error." + code) : raw;
    const last = (diag && diag.last) || {};
    const row = (k, v) => v ? `<dt>${CU.t(k)}</dt><dd>${v}</dd>` : "";
    const hint = CU.hasText("diag.hint." + code) ? CU.t("diag.hint." + code) : CU.t("diag.hint.generic");
    const recent = ((diag && diag.recent) || []).map(e =>
      `<li><b>${when(e.t)}</b> ${esc(e.status ? "HTTP " + e.status : e.code)} <span>${esc(e.api_message || e.message)}</span></li>`).join("");
    const api = last.api_message || last.body || raw;
    const detail = `<dl>${row("diag.what", esc(api))}${row("diag.status", esc(last.status))}${row("diag.when", last.t ? when(last.t) : "")}`
      + `${row("diag.streak", diag && diag.consecutive ? diag.consecutive : "")}${row("diag.retry", esc(last.retry_after))}`
      + `${row("diag.expired", last.expires_at ? when(last.expires_at) : "")}`
      + `${row("diag.request", esc(last.request_id))}${row("diag.endpoint", esc(last.url))}</dl>`
      + `<p class="hint">${hint}</p>`
      + (recent ? `<h4>${CU.t("diag.recent")}</h4><ul>${recent}</ul>` : "")
      + `<p class="logs">${CU.t("diag.logs")}</p>`;
    const open = document.querySelector("#err details[open]") ? " open" : "";
    return `<div class="err-line">${esc(CU.t("error.prefix", { msg }))}</div><details${open}><summary>${CU.t("diag.summary")}</summary>${detail}</details>`;
  }

  /* ---------- rendering ---------- */
  const computeNow = () => CU.compute(window.CLAUDE_USAGE, Date.now(), { hoursPerDay: workOn ? hours : 24, workHours: workOn });
  function setMeta(m) {                      // the "Updated … ago · next read in …" line
    const due = pollerState && Date.parse(pollerState.next_at), wait = due - Date.now();
    const next = wait > -60e3 ? " · " + CU.t("meta.next", { left: wait < 60e3 ? Math.max(0, Math.round(wait / 1e3)) + " s" : CU.fmt.left(wait) }) : "";
    $("meta").textContent = m.fetched ? CU.t("meta.updated", { ago: CU.fmt.left(m.age), n: m.samples }) + next : "—";
    $("meta").classList.toggle("stale", m.age > 30 * 60e3);
  }
  // Everything render() depends on besides the clock: if it is unchanged, the periodic tick can skip the rebuild.
  const signature = () => {
    const D = window.CLAUDE_USAGE || {};
    return JSON.stringify([D.generated_at, D.fetched_at, D.error, pollerState && pollerState.next_at, level(), workOn, hours, CU.lang, panels, colsNow()]);
  };
  const colsNow = () => (innerWidth >= 1750 ? 3 : innerWidth >= 1300 ? 2 : 1);      // same breakpoints as style.css
  let lastSig = null, lastRender = 0;
  function render() {
    if (CU.dragging) return;                 // a chart range is being dragged: do not rebuild the page under the pointer
    lastSig = signature(); lastRender = Date.now();
    const D = window.CLAUDE_USAGE, m = computeNow();
    const err = $("err");
    if (!m) {
      $("app").innerHTML = `<div class="card empty">${CU.t("empty")}</div>`;
      err.hidden = !(D && D.error);
      if (D && D.error) err.innerHTML = errorHtml(D.error_code, D.error, D.diagnostics);
      $("meta").textContent = "—";
      return;
    }
    const restoreFocus = CU.captureFocus($("app"));          // the page is rebuilt below: keep the keyboard focus where it was
    $("app").innerHTML = CU.compose(m, level(), { breakdownOpen, chartsOpen, panels, cols: colsNow() });
    applyNotes();
    CU.fitBars($("app"));
    CU.chartsAfterRender($("app"));
    if ($("how").open) $("how-body").innerHTML = CU.formulas(m);
    restoreFocus();

    setMeta(m);
    err.hidden = !m.error;
    if (m.error) err.innerHTML = errorHtml(m.errorCode, m.error, m.diagnostics);

  }

  /* ---------- hours-per-day slider (side panel, outside #app so re-renders never reset it) ---------- */
  const slider = $("hours"), MIN_H = 1, MAX_H = 24;
  (function buildTicks() {
    let html = "";
    for (let v = MIN_H; v <= MAX_H; v++) {
      const bottom = ((v - MIN_H) / (MAX_H - MIN_H) * 100).toFixed(3), big = v % 5 === 0;
      html += `<i class="${big ? "big" : ""}" style="bottom:${bottom}%"></i>`;
      if (big) html += `<b style="bottom:${bottom}%">${v}</b>`;
    }
    $("hours-ticks").innerHTML = html;
  })();
  function showHours() {
    slider.value = hours;
    $("hours-value").textContent = CU.t("hours.value", { n: hours });
    slider.setAttribute("aria-valuetext", CU.t("hours.value", { n: hours }));
  }
  slider.addEventListener("input", () => {
    hours = parseInt(slider.value, 10) || 8;
    try { localStorage.setItem(HOURS_KEY, String(hours)); } catch (e) { /* ignore */ }
    share({ hours });
    showHours();
    render();
  });

  /* ---------- explanations: level 7 is the global switch, plus a "?" per panel that flips its own note ----------
     A note is shown when the global switch is on, unless its panel's "?" hid it (and the other way round).
     The per-panel choices last until the detail level is changed. */
  const noteFlip = {};
  function applyNotes() {
    const on = level() === 7;
    document.querySelectorAll("[data-note]").forEach(n => { n.hidden = on === !!noteFlip[n.dataset.note]; });
    document.querySelectorAll("[data-note-for]").forEach(b => {
      b.setAttribute("aria-pressed", String(on !== !!noteFlip[b.dataset.noteFor]));
    });
  }
  $("app").addEventListener("click", e => {
    const b = e.target.closest && e.target.closest("[data-note-for]");
    if (!b) return;
    e.preventDefault();                        // the button sits in a <summary>: do not let it fold the panel
    const key = b.dataset.noteFor, d = b.closest("details");
    noteFlip[key] = !noteFlip[key];
    if (d && !d.open && (level() === 7) !== noteFlip[key]) d.open = true;    // showing the note of a folded panel opens it
    applyNotes();
  });

  /* ---------- tooltips that also work on a touch screen: a tap (or click) shows the element's title ---------- */
  const tip = document.createElement("div");
  tip.className = "tip"; tip.hidden = true; tip.setAttribute("role", "status");
  document.body.appendChild(tip);
  const titleOf = el => el.getAttribute("title") || (el.querySelector && el.querySelector(":scope > title") ? el.querySelector(":scope > title").textContent : "");
  document.addEventListener("click", e => {
    if (Date.now() - (CU.tipSuppress || 0) < 400) return;            // the end of a drag on a chart is not a tap
    const el = e.target.closest && e.target.closest("#app svg.plot rect, #app svg.plot circle, #app .bars .day, #app .share span, #app .tbar span");
    const text = el && titleOf(el);
    if (!text) { tip.hidden = true; return; }
    tip.textContent = text; tip.hidden = false;
    const r = el.getBoundingClientRect(), w = tip.offsetWidth;
    tip.style.left = Math.max(8, Math.min(innerWidth - w - 8, r.left + r.width / 2 - w / 2)) + "px";
    tip.style.top = Math.max(8, r.top - tip.offsetHeight - 8) + scrollY + "px";
  });
  window.addEventListener("scroll", () => { tip.hidden = true; }, { passive: true });

  /* ---------- "how it is computed": a floating panel opened by the "?" button ---------- */
  const how = $("how");
  $("how-open").addEventListener("click", () => {
    const m = CU.compute(window.CLAUDE_USAGE, Date.now(), { hoursPerDay: workOn ? hours : 24, workHours: workOn });
    $("how-body").innerHTML = m ? CU.formulas(m) : `<p class="lead">${CU.t("empty")}</p>`;
    if (how.showModal) how.showModal(); else how.setAttribute("open", "");
  });
  $("how-close").addEventListener("click", () => how.close ? how.close() : how.removeAttribute("open"));
  how.addEventListener("click", e => { if (e.target === how && how.close) how.close(); });     // click on the backdrop

  /* ---------- working-hours switch: off = the week's pace follows calendar time (24 h a day), slider hidden ---------- */
  const workBox = $("work-on");
  function showWork() {
    workBox.checked = workOn;
    $("hours-panel").hidden = !workOn;
    $("hours-box").classList.toggle("off", !workOn);
  }
  workBox.addEventListener("change", () => {
    workOn = workBox.checked;
    try { localStorage.setItem(WORK_KEY, workOn ? "1" : "0"); } catch (e) { /* ignore */ }
    share({ work_hours: workOn });
    showWork();
    render();
  });
  showWork();

  /* ---------- compactness level (UI-5): slider 1-6 + "Auto" (from the width of the page, not of the screen) ---------- */
  // auto: the widest level whose threshold the width reaches (px of the page content)
  const AUTO = CU.LEVEL_WIDTHS;
  let autoLevel = 6;
  const levelFor = CU.levelFor;
  const baseLevel = () => levelPref === "auto" ? autoLevel : levelPref;
  const level = baseLevel;                           // 7 = level 6 + the explanations
  CU.level = level;
  const levelInput = $("level");
  function showLevel() {
    const b = baseLevel(), L = level();
    levelInput.value = b;
    $("level-value").textContent = CU.t("level.value", { n: b });
    levelInput.setAttribute("aria-valuetext", CU.t("level.value", { n: b }) + (L === 7 ? " + " + CU.t("notes.label") : ""));
    $("level-auto").setAttribute("aria-pressed", String(levelPref === "auto"));
    document.body.dataset.level = L;
    $("hours-box").hidden = L < 6;                     // settings belong to the "everything" level
  }
  levelInput.addEventListener("input", () => {
    levelPref = parseInt(levelInput.value, 10) || 6;
    for (const k in noteFlip) delete noteFlip[k];            // per-panel "?" choices last until the level changes
    try { localStorage.setItem(LEVEL_KEY, String(levelPref)); } catch (e) { /* ignore */ }
    share({ level: levelPref });
    showLevel(); render();
  });
  $("level-auto").addEventListener("click", () => {
    levelPref = "auto";
    try { localStorage.removeItem(LEVEL_KEY); } catch (e) { /* ignore */ }
    share({ level: "auto" });
    measure(); showLevel(); render();
  });
  function measure() {                               // a small dead band around each threshold: no flicker on a scrollbar
    const w = document.querySelector(".wrap").clientWidth - 32, next = levelFor(w);
    if (next === autoLevel) return false;
    const edge = AUTO.find(([min]) => min > 0 && Math.abs(w - min) < 12);
    if (edge && Math.abs(next - autoLevel) === 1) return false;
    autoLevel = next;
    return true;
  }
  if (window.ResizeObserver) new ResizeObserver(() => { if (measure() && levelPref === "auto") { showLevel(); render(); } }).observe(document.querySelector(".wrap"));
  autoLevel = levelFor(document.querySelector(".wrap").clientWidth - 32);

  /* ---------- language switch ---------- */
  const refreshBtn = $("refresh");
  function applyLanguage() {
    CU.applyStatic();
    showHours();
    showLevel();
    document.querySelectorAll("[data-lang]").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.lang === CU.lang)));
    if (!SERVED) refreshBtn.title = CU.t("refresh.disabled");
    render();
  }
  document.querySelectorAll("[data-lang]").forEach(b => b.addEventListener("click", () => { CU.setLang(b.dataset.lang); share({ lang: CU.lang }); applyLanguage(); }));

  /* ---------- Refresh button ---------- */
  if (!SERVED) refreshBtn.disabled = true;
  refreshBtn.addEventListener("click", async () => {
    refreshBtn.disabled = true;
    refreshBtn.classList.add("busy");
    try {
      const r = await fetch("/api/refresh", { method: "POST" });
      const res = await r.json();
      if (res.state) window.CLAUDE_USAGE = res.state;
    } catch (e) {
      window.CLAUDE_USAGE = Object.assign({}, window.CLAUDE_USAGE, {
        error: CU.t("error.server", { msg: e.message }), error_code: null,
      });
    } finally {
      refreshBtn.disabled = false;
      refreshBtn.classList.remove("busy");
      render();
    }
  });

  let resizeTimer = null;                          // day names in the breakdown bars depend on their width
  window.addEventListener("resize", () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(() => { if (signature() !== lastSig) render(); else CU.fitBars($("app")); }, 100); });

  /* ---------- installable app (ACC-1): a service worker, only when served (127.0.0.1 counts as a secure origin) ---------- */
  if (SERVED && "serviceWorker" in navigator) navigator.serviceWorker.register("sw.js").catch(() => { /* not essential */ });

  /* ---------- shared settings (API-2): data/config.json through /api/v1/config, so every client and browser sees
     the same ones. localStorage stays the fallback (page opened as a file, server unreachable). ---------- */
  let pending = {}, shareTimer = null;
  function share(changes) {
    if (!SERVED) return;
    Object.assign(pending, changes);
    clearTimeout(shareTimer);
    shareTimer = setTimeout(() => {                  // a slider sends many values: only the last one, once it rests
      const body = JSON.stringify(pending); pending = {};
      fetch("/api/v1/config", { method: "POST", headers: { "Content-Type": "application/json" }, body }).catch(() => { /* kept locally */ });
    }, 500);
  }
  function loadShared() {
    if (!SERVED) return Promise.resolve();
    return fetch("/api/v1/config", { cache: "no-store" }).then(r => (r.ok ? r.json() : null)).then(c => {
      const w = c && c.widget;
      if (!w) return;
      levelPref = w.level === "auto" || (w.level >= 1 && w.level <= 7) ? w.level : levelPref;
      if (w.panels && typeof w.panels === "object") panels = w.panels;
      workOn = !!w.work_hours;
      if (w.hours >= 1 && w.hours <= 24) hours = w.hours;
      const urlLang = new URLSearchParams(location.search).get("lang");
      if (w.lang && !urlLang && w.lang !== CU.lang) CU.setLang(w.lang);   // ?lang= in the address wins
      if (CU.applyTheme && w.theme) CU.applyTheme(w.theme);
      showWork();
    }).catch(() => { /* server unreachable: keep the local settings */ });
  }

  /* ---------- panels: which panels are shown, apart from the detail level (shared like the other settings) ---------- */
  const PANEL_KEYS = ["gauges", "tokens", "ratio", "hourly", "breakdown"], pdlg = $("panels-dlg");
  function panelsBody() {
    $("panels-body").innerHTML = PANEL_KEYS.map(k => `<label class="switch row"><input type="checkbox" data-panel="${k}"${panels[k] === false ? "" : " checked"}>`
      + `<span class="knob" aria-hidden="true"></span><span class="switch-label">${CU.t("panels.k." + k)}<small>${CU.t("panels.d." + k)}</small></span></label>`).join("")
      + `<p class="note">${CU.t("panels.note")}</p>`;
  }
  $("panels-open").addEventListener("click", () => { panelsBody(); if (pdlg.showModal) pdlg.showModal(); else pdlg.setAttribute("open", ""); });
  $("panels-close").addEventListener("click", () => pdlg.close ? pdlg.close() : pdlg.removeAttribute("open"));
  pdlg.addEventListener("click", e => { if (e.target === pdlg && pdlg.close) pdlg.close(); });
  pdlg.addEventListener("change", e => {
    const k = e.target.dataset && e.target.dataset.panel;
    if (!k) return;
    panels = Object.assign({}, panels, { [k]: e.target.checked });
    try { localStorage.setItem(PANELS_KEY, JSON.stringify(panels)); } catch (err) { /* ignore */ }
    share({ panels: PANEL_KEYS.reduce((o, q) => { o[q] = panels[q] !== false; return o; }, {}) });
    render();
  });

  /* ---------- theme panel (THM-1) ---------- */
  const openTheme = CU.themePanel ? CU.themePanel($("theme-dlg"), th => share({ theme: th })) : null;
  $("theme-open").addEventListener("click", () => openTheme && openTheme());

  /* ---------- start ---------- */
  applyLanguage();
  loadShared().then(() => { applyLanguage(); return loadData(); }).then(render);
  // Periodic tick: new data (the poller can read every 30 s) and countdowns. Countdowns and pace markers depend on
  // the clock, so a full rebuild still happens every 60 s; in between, an unchanged page only gets its meta line refreshed.
  function tick() {
    if (document.visibilityState === "hidden") return;       // nobody is looking: no fetch, no render
    loadData().then(() => {
      if (signature() !== lastSig || Date.now() - lastRender >= 60e3) { render(); return; }
      if (CU.dragging) return;
      const m = computeNow();
      if (m) setMeta(m);
    });
  }
  setInterval(tick, 10e3);
  document.addEventListener("visibilitychange", () => { if (document.visibilityState === "visible") loadData().then(render); });   // catch up at once
})(window.CU);
