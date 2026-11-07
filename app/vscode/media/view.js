/* view.js: the side view. It draws with the widget's own components (CU.compose and friends, from web/js), at the
   compactness level that fits the width of the view (UI-5), and redraws when the view is resized. */
(function () {
  const vscode = acquireVsCodeApi(), CU = window.CU;
  let state = null;
  function draw() {
    const app = document.getElementById("app"), m = state && CU.compute(state, Date.now(), {});
    if (!m) { app.innerHTML = `<div class="card empty">${CU.t("empty")}</div>`; return; }
    const L = CU.levelFor(document.body.clientWidth - 16);
    document.body.dataset.level = L;
    app.innerHTML = CU.compose(m, L, {});
    app.querySelectorAll("[data-note]").forEach(n => { n.hidden = true; });       // the side bar has no room for them
    CU.fitBars(app);
    if (CU.chartsAfterRender) CU.chartsAfterRender(app);
  }
  window.addEventListener("message", e => {
    const d = e.data || {};
    if (d.lang && d.lang !== CU.lang) CU.setLang(d.lang);
    if (d.state) { state = d.state; if (!CU.dragging) draw(); }
  });
  let t = null;
  new ResizeObserver(() => { clearTimeout(t); t = setTimeout(draw, 60); }).observe(document.body);
  setInterval(() => { if (!CU.dragging) draw(); }, 30e3);             // countdowns
  vscode.postMessage({ ready: true });
})();
