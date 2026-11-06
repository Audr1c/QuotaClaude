/* app.js: data loading, view and language switches, refresh button, auto-refresh.
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
  const VIEW_KEY = "cu.view", BREAKDOWN_KEY = "cu.breakdownOpen", NOTES_KEY = "cu.notes";
  const HOURS_KEY = "cu.hours", WORK_KEY = "cu.workHours";
  const chartsOpen = {};
  let view = "detail", breakdownOpen = false, notesOn = true, hours = 8, workOn = false;
  try {
    const saved = parseInt(localStorage.getItem(HOURS_KEY), 10);
    if (saved >= 1 && saved <= 24) hours = saved;
    view = localStorage.getItem(VIEW_KEY) || "detail";
    breakdownOpen = localStorage.getItem(BREAKDOWN_KEY) === "1";
    notesOn = localStorage.getItem(NOTES_KEY) !== "0";
    workOn = localStorage.getItem(WORK_KEY) === "1";
  } catch (e) { /* storage unavailable */ }
  if (!CU.views[view]) view = "detail";

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
  function render() {
    if (CU.dragging) return;                 // a chart range is being dragged: do not rebuild the page under the pointer
    const D = window.CLAUDE_USAGE, m = CU.compute(D, Date.now(), { hoursPerDay: workOn ? hours : 24, workHours: workOn });
    const err = $("err");
    if (!m) {
      $("app").innerHTML = `<div class="card empty">${CU.t("empty")}</div>`;
      err.hidden = !(D && D.error);
      if (D && D.error) err.innerHTML = errorHtml(D.error_code, D.error, D.diagnostics);
      $("meta").textContent = "—";
      return;
    }
    const restoreFocus = CU.captureFocus($("app"));          // the page is rebuilt below: keep the keyboard focus where it was
    const open = html => html.replace(/<details class="card chart" data-key="(\w+)"/g, (a, k) => a + (chartsOpen[k] ? " open" : ""));
    // three columns on a wide screen (gauges, history charts, tokens), stacked when there is no room (style.css)
    $("app").innerHTML = `<div class="dash"><div class="col col-gauges">${CU.views[view](m)}${CU.breakdown(m, breakdownOpen)}</div>`
      + `<div class="col col-charts">${open(CU.charts(m, ["hourly", "ratio"]))}</div>`
      + `<div class="col col-tokens">${open(CU.charts(m, ["tokens"]))}</div></div>`;
    applyNotes();
    CU.fitBars($("app"));
    CU.chartsAfterRender($("app"));
    if ($("how").open) $("how-body").innerHTML = CU.formulas(m);
    restoreFocus();

    const due = pollerState && Date.parse(pollerState.next_at), wait = due - Date.now();
    const next = wait > -60e3 ? " · " + CU.t("meta.next", { left: wait < 60e3 ? Math.max(0, Math.round(wait / 1e3)) + " s" : CU.fmt.left(wait) }) : "";
    $("meta").textContent = m.fetched ? CU.t("meta.updated", { ago: CU.fmt.left(m.age), n: m.samples }) + next : "—";
    $("meta").classList.toggle("stale", m.age > 30 * 60e3);
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
    showHours();
    render();
  });

  /* ---------- explanations: one global switch, plus a "?" per panel that flips its own note ----------
     A note is shown when the global switch is on, unless its panel's "?" hid it (and the other way round).
     The per-panel choices last until the global switch is used again. */
  const noteFlip = {};
  function applyNotes() {
    document.body.classList.toggle("notes-off", !notesOn);
    const notesBtn = $("notes");
    notesBtn.setAttribute("aria-pressed", String(notesOn));
    document.querySelectorAll("[data-note]").forEach(n => { n.hidden = notesOn === !!noteFlip[n.dataset.note]; });
    document.querySelectorAll("[data-note-for]").forEach(b => {
      b.setAttribute("aria-pressed", String(notesOn !== !!noteFlip[b.dataset.noteFor]));
    });
  }
  $("notes").addEventListener("click", () => {
    notesOn = !notesOn;
    for (const k in noteFlip) delete noteFlip[k];
    try { localStorage.setItem(NOTES_KEY, notesOn ? "1" : "0"); } catch (e) { /* ignore */ }
    applyNotes();
  });
  $("app").addEventListener("click", e => {
    const b = e.target.closest && e.target.closest("[data-note-for]");
    if (!b) return;
    e.preventDefault();                        // the button sits in a <summary>: do not let it fold the panel
    const key = b.dataset.noteFor, d = b.closest("details");
    noteFlip[key] = !noteFlip[key];
    if (d && !d.open && notesOn !== noteFlip[key]) d.open = true;      // showing the note of a folded panel opens it
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
    showWork();
    render();
  });
  showWork();

  /* ---------- view switch (detailed / compact) ---------- */
  function setView(v) {
    view = CU.views[v] ? v : "detail";
    try { localStorage.setItem(VIEW_KEY, view); } catch (e) { /* ignore */ }
    document.querySelectorAll("[data-view]").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.view === view)));
    document.body.dataset.view = view;
    render();
  }
  document.querySelectorAll("[data-view]").forEach(b => b.addEventListener("click", () => setView(b.dataset.view)));

  /* ---------- language switch ---------- */
  const refreshBtn = $("refresh");
  function applyLanguage() {
    CU.applyStatic();
    showHours();
    document.querySelectorAll("[data-lang]").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.lang === CU.lang)));
    if (!SERVED) refreshBtn.title = CU.t("refresh.disabled");
    render();
  }
  document.querySelectorAll("[data-lang]").forEach(b => b.addEventListener("click", () => { CU.setLang(b.dataset.lang); applyLanguage(); }));

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
  window.addEventListener("resize", () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(() => CU.fitBars($("app")), 100); });

  /* ---------- start ---------- */
  setView(view);
  applyLanguage();
  loadData().then(render);
  setInterval(() => loadData().then(render), 10e3);   // new data (the poller can read every 30 s) and countdowns
})(window.CU);
