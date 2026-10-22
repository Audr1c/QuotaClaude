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
  const VIEW_KEY = "cu.view", BREAKDOWN_KEY = "cu.breakdownOpen", FORMULAS_KEY = "cu.formulasOpen";
  const HOURS_KEY = "cu.hours";
  let view = "detail", breakdownOpen = false, formulasOpen = false, hours = 8;
  try {
    const saved = parseInt(localStorage.getItem(HOURS_KEY), 10);
    if (saved >= 1 && saved <= 24) hours = saved;
    view = localStorage.getItem(VIEW_KEY) || "detail";
    breakdownOpen = localStorage.getItem(BREAKDOWN_KEY) === "1";
    formulasOpen = localStorage.getItem(FORMULAS_KEY) === "1";
  } catch (e) { /* storage unavailable */ }
  if (!CU.views[view]) view = "detail";

  // the breakdown <details> is recreated on every render: remember whether it is open
  $("app").addEventListener("toggle", e => {
    const isFormulas = e.target.classList.contains("formulas");
    if (!isFormulas && !e.target.classList.contains("breakdown")) return;
    if (isFormulas) formulasOpen = e.target.open; else breakdownOpen = e.target.open;
    try { localStorage.setItem(isFormulas ? FORMULAS_KEY : BREAKDOWN_KEY, e.target.open ? "1" : "0"); } catch (err) { /* ignore */ }
  }, true);

  /* ---------- data ---------- */
  function loadData() {
    if (SERVED) {
      return fetch("../data/latest.json", { cache: "no-store" })
        .then(r => (r.ok ? r.json() : null))
        .then(d => { if (d) window.CLAUDE_USAGE = d; })
        .catch(() => {});
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
      + `${row("diag.request", esc(last.request_id))}${row("diag.endpoint", esc(last.url))}</dl>`
      + `<p class="hint">${hint}</p>`
      + (recent ? `<h4>${CU.t("diag.recent")}</h4><ul>${recent}</ul>` : "")
      + `<p class="logs">${CU.t("diag.logs")}</p>`;
    const open = document.querySelector("#err details[open]") ? " open" : "";
    return `<div class="err-line">${esc(CU.t("error.prefix", { msg }))}</div><details${open}><summary>${CU.t("diag.summary")}</summary>${detail}</details>`;
  }

  /* ---------- rendering ---------- */
  function render() {
    const D = window.CLAUDE_USAGE, m = CU.compute(D, Date.now(), { hoursPerDay: hours });
    const err = $("err");
    if (!m) {
      $("app").innerHTML = `<div class="card empty">${CU.t("empty")}</div>`;
      err.hidden = !(D && D.error);
      if (D && D.error) err.innerHTML = errorHtml(D.error_code, D.error, D.diagnostics);
      $("foot").textContent = "";
      $("meta").textContent = "—";
      return;
    }
    $("app").innerHTML = CU.views[view](m) + CU.breakdown(m, breakdownOpen) + CU.formulas(m, formulasOpen);

    $("meta").textContent = m.fetched ? CU.t("meta.updated", { ago: CU.fmt.left(m.age), n: m.samples }) : "—";
    $("meta").classList.toggle("stale", m.age > 30 * 60e3);
    err.hidden = !m.error;
    if (m.error) err.innerHTML = errorHtml(m.errorCode, m.error, m.diagnostics);

    const source = m.ratioEstimated ? CU.t("foot.estimated", { pts: m.ratioPoints }) : CU.t("foot.default");
    $("foot").innerHTML = CU.t("foot.ratio", { ratio: CU.fmt.pct(m.ratio, 1), source }) + "<br>" + CU.t("foot.limit");
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

  /* ---------- start ---------- */
  setView(view);
  applyLanguage();
  loadData().then(render);
  setInterval(() => loadData().then(render), 60e3);   // new data (scheduled task)
  setInterval(render, 15e3);                           // countdowns and time-based markers
})(window.CU);
