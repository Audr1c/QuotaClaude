/* app.js : chargement des donnees, bascule de vue, bouton de releve, rafraichissement.
   Deux modes :
     - via le serveur local (http://127.0.0.1:8765) : donnees en JSON + bouton "Relever" actif ;
     - fichier ouvert directement (file://) : donnees via data/latest.js, bouton desactive. */
(function (CU) {
  const $ = id => document.getElementById(id);
  const SERVED = location.protocol.startsWith("http");
  const VIEW_KEY = "cu.view", BREAKDOWN_KEY = "cu.breakdownOpen";
  let view = "detail", breakdownOpen = false;
  try {
    view = localStorage.getItem(VIEW_KEY) || "detail";
    breakdownOpen = localStorage.getItem(BREAKDOWN_KEY) === "1";
  } catch (e) { /* stockage indisponible */ }

  if (!CU.compute || !CU.gauge || !CU.views) {           // un script n'a pas charge : le diagnostic l'affiche deja
    $("app").innerHTML = `<div class="card empty">La page n'a pas pu charger tous ses scripts.</div>`;
    return;
  }

  // le deroulant est recree a chaque rendu : on retient s'il est ouvert ('toggle' ne remonte pas, d'ou la capture)
  $("app").addEventListener("toggle", e => {
    if (!e.target.classList.contains("breakdown")) return;
    breakdownOpen = e.target.open;
    try { localStorage.setItem(BREAKDOWN_KEY, breakdownOpen ? "1" : "0"); } catch (err) { /* ignore */ }
  }, true);

  /* ---------- donnees ---------- */
  function loadData() {
    if (SERVED) {
      return fetch("../data/latest.json", { cache: "no-store" })
        .then(r => (r.ok ? r.json() : null))
        .then(d => { if (d) window.CLAUDE_USAGE = d; })
        .catch(() => {});
    }
    return new Promise(resolve => {            // file:// : fetch interdit, on recharge un <script>
      const s = document.createElement("script");
      s.src = "../data/latest.js?t=" + Date.now();
      s.onload = s.onerror = () => { s.remove(); resolve(); };
      document.body.appendChild(s);
    });
  }

  /* ---------- rendu ---------- */
  function render() {
    const D = window.CLAUDE_USAGE, m = CU.compute(D);
    const err = $("err");
    if (!m) {
      $("app").innerHTML = `<div class="card empty">Pas encore de données.<br>
        Clique sur <b>Relever</b> ou lance <code>releve_maintenant</code> (dossier windows ou linux).</div>`;
      err.hidden = !(D && D.error);
      if (D && D.error) err.textContent = D.error;
      $("foot").textContent = "";
      return;
    }
    $("app").innerHTML = CU.views[view](m) + CU.breakdown(m, breakdownOpen);

    $("meta").textContent = m.fetched ? `Relevé il y a ${CU.fmt.left(m.age)} · ${m.samples} relevés` : "—";
    $("meta").classList.toggle("stale", m.age > 30 * 60e3);
    err.hidden = !m.error;
    if (m.error) err.textContent = "Dernier relevé en échec : " + m.error;
    $("foot").innerHTML =
      `Une fenêtre 5 h pleine ≈ <b>${CU.fmt.num(m.ratio)} %</b> de la semaine `
      + (m.ratioEstimated ? `(estimé sur ${m.ratioPoints} pts de 5 h observés).` : `(hypothèse par défaut, affinée dès que l'historique suffit).`)
      + `<br>La limite orange de la fenêtre 5 h répartit le reste de ta semaine uniformément sur les heures restantes, nuits comprises.`;
  }

  /* ---------- bascule détaillé / compact ---------- */
  function setView(v) {
    view = CU.views[v] ? v : "detail";
    try { localStorage.setItem(VIEW_KEY, view); } catch (e) { /* ignore */ }
    document.querySelectorAll("[data-view]").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.view === view)));
    document.body.dataset.view = view;
    render();
  }
  document.querySelectorAll("[data-view]").forEach(b => b.addEventListener("click", () => setView(b.dataset.view)));

  /* ---------- bouton Relever ---------- */
  const btn = $("refresh");
  if (!SERVED) {
    btn.disabled = true;
    btn.title = "Ouvre le widget avec ouvrir_widget (serveur local) pour activer ce bouton";
  }
  btn.addEventListener("click", async () => {
    btn.disabled = true;
    btn.classList.add("busy");
    try {
      const r = await fetch("/api/refresh", { method: "POST" });
      const res = await r.json();
      if (res.state) window.CLAUDE_USAGE = res.state;
    } catch (e) {
      window.CLAUDE_USAGE = Object.assign({}, window.CLAUDE_USAGE, { error: "Serveur local injoignable : " + e.message });
    } finally {
      btn.disabled = false;
      btn.classList.remove("busy");
      render();
    }
  });

  /* ---------- demarrage ---------- */
  setView(view);
  loadData().then(render);
  setInterval(() => loadData().then(render), 60e3);   // nouvelles donnees (tache planifiee)
  setInterval(render, 15e3);                           // comptes a rebours et reperes de temps
})(window.CU || {});
