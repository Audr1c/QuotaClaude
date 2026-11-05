# Idées pour la suite

Pistes d'évolution de Claude Usage Tracker. Contraintes communes : l'endpoint `GET /api/oauth/usage` n'est pas documenté (il peut changer ou disparaître sans préavis), il répond en HTTP 429 si on l'interroge trop souvent, et le jeton OAuth de Claude Code est un secret qui donne accès au compte.

---

## À faire

### Audit de sécurité du petit serveur (`app/server.py`)
- Vérifier que l'écoute reste limitée à `127.0.0.1` et que le contrôle du `Host` (anti DNS-rebinding) couvre toutes les routes.
- `do_POST` (bouton Actualiser) : un `Origin` absent est accepté aujourd'hui. Vérifier qu'une page tierce ne peut pas déclencher de relevés en boucle (risque de 429), et envisager un jeton anti-CSRF.
- Fichiers statiques `/web/` et `/data/` : tester la traversée de chemin (`..`, `%2e%2e`, `\`, liens symboliques) et s'assurer que seuls les fichiers prévus sont servis (jamais `.credentials.json`, `tracker.log`, `poller.lock`).
- En-têtes de réponse : `Content-Security-Policy`, `X-Content-Type-Options: nosniff`, `Cache-Control` sur les données.
- Vérifier qu'aucune réponse, aucun message d'erreur et aucune ligne de log ne contient le jeton.
- Sur une machine partagée, le port local est accessible aux autres utilisateurs : évaluer ce qu'ils peuvent lire ou déclencher.

### Consommation de ressources
- Mesurer d'abord : CPU, mémoire et réveils du poller (`poller.py`), du serveur et de l'onglet du widget sur une journée (Gestionnaire des tâches / `perfmon`, `ps`/`top` sous Linux).
- Pistes de réduction :
  - le poller se réveille toutes les 5 s (`TICK_S`) pour surveiller l'horloge et le fichier d'identifiants ; allonger ce délai quand il n'y a rien à surveiller ;
  - `importlib.reload` à chaque relevé : à garder seulement si le coût est négligeable ;
  - limiter la taille de `latest.json` et la relecture complète de `usage.csv` et `breakdown.csv` à chaque relevé (ne lire que la semaine en cours) ;
  - côté widget : un seul intervalle de 10 s, mise à jour du DOM seulement si les données ont changé, pause quand l'onglet est caché (`document.visibilityState`).

---

## 1. Décentraliser le poller (NAS local ou serveur externe)

**Objectif.** Faire tourner le relevé 24 h/24 sur une machine toujours allumée (NAS, petit serveur) et consulter le quota depuis n'importe quel appareil, sans dépendre du PC où Claude Code est connecté.

**Esquisse.**
- Le jeton vit dans `~/.claude/.credentials.json` du PC et est renouvelé par Claude Code. Un NAS n'y a pas accès. Trois options :
  - **A. Pousser les relevés (recommandé)** : le PC garde le poller actuel et envoie chaque relevé (`POST /api/readings`, JSON) au NAS. Le jeton ne quitte jamais le PC. Limite : plus de relevés quand le PC est éteint.
  - **B. Copier le jeton** : un script du PC copie `.credentials.json` vers le NAS (scp/rsync sur le réseau privé) à chaque renouvellement. Le NAS interroge l'endpoint lui-même. Simple, mais le secret est dupliqué.
  - **C. Renouvellement OAuth autonome** : le NAS utilise le `refresh_token`. Risque : un refresh token est souvent à usage unique, donc le NAS et Claude Code se déconnecteraient mutuellement. À éviter sans preuve du contraire.
- Séparer dans `app/server.py` une API en lecture seule : `GET /api/latest`, `GET /api/history?since=...` (JSON), consommée par le widget et par les clients des idées 2 et 3.
- Authentification : jeton d'API propre au tracker (en-tête `Authorization: Bearer`), distinct du jeton Claude, stocké dans un fichier de config en `chmod 600`.
- Les contrôles Host/Origin refusent aujourd'hui tout hôte non local : prévoir une liste `allowed_hosts` dans une config, vide par défaut.
- Accès distant : Tailscale ou WireGuard plutôt qu'une exposition Internet ; sinon reverse proxy (Caddy/nginx) avec HTTPS et authentification.
- Image Docker minimale (`python:3-alpine`, stdlib seule), volume pour `data/`, variables d'environnement pour l'hôte, le port et le jeton d'API.

**Difficultés / risques.**
- Sécurité du jeton OAuth (copie, sauvegardes du NAS, logs) : ne jamais le journaliser ni l'exposer via l'API.
- 429 : un seul poller par compte ; si les options A et B coexistent, il faut un verrou ou un intervalle minimal côté serveur, avec backoff sur 429.
- Dérive d'horloge et doublons si plusieurs sources écrivent dans `usage.csv` : dédupliquer sur l'horodatage.
- Endpoint non officiel : isoler l'appel dans une seule fonction pour limiter les dégâts en cas de changement de format.

**Premier petit pas.** Ajouter `GET /api/latest` en lecture seule dans `server.py` (même contrôle Host/Origin), puis une option `--bind` + `--token` désactivée par défaut. Tester le tout via Tailscale entre deux machines.

---

## 2. Version Android avec widget d'écran d'accueil

**Objectif.** Voir les deux anneaux (5 h et semaine) directement sur l'écran d'accueil du téléphone, sans ouvrir de navigateur.

**Esquisse.**
- Dépend de l'idée 1 : le téléphone consomme l'API en lecture seule (via Tailscale ou HTTPS), il ne voit jamais le jeton Claude.
- Étape intermédiaire : une PWA (le widget web existant servi par le serveur, avec manifeste et service worker) ajoutée à l'écran d'accueil. Pas de vrai widget, mais zéro code natif.
- Widget natif : Kotlin, Jetpack Glance (ou `AppWidgetProvider`), rafraîchi par `WorkManager`. Les rafraîchissements périodiques sont limités à environ 15 min minimum et soumis au mode économie d'énergie (Doze).
- Rendu des anneaux : dessiner en `Canvas`/bitmap (les widgets n'acceptent pas de SVG arbitraire), mêmes couleurs que le thème.
- Stocker l'URL du serveur et le jeton d'API dans `EncryptedSharedPreferences`.

**Difficultés / risques.**
- Fraîcheur : 15 min de latence maximale ; afficher l'heure du dernier relevé pour que la donnée périmée soit visible.
- Réseau : hors du réseau domestique, Tailscale doit être actif sur le téléphone.
- Maintenance d'un second code (Kotlin) pour un outil dont l'API source est instable.
- Distribution : APK en installation manuelle (pas de Play Store prévu).

**Premier petit pas.** Ajouter manifeste et service worker à `app/web/` et vérifier que le widget s'installe en PWA sur le téléphone, en lisant `/api/latest` du serveur de l'idée 1.

---

## 3. Extension VS Code (barre latérale + barre d'état)

**Objectif.** Suivre le quota sans quitter l'éditeur : une vue dans la barre latérale et un élément compact dans la barre d'état.

**Esquisse.**
- Source des données : `app/data/latest.json` en local (lecture de fichier avec `fs.watch`, aucune requête réseau), ou l'API de l'idée 1 quand le poller est distant. Réglage `claudeUsage.source`.
- Vue latérale : `WebviewViewProvider` qui réutilise `gauge.js` et le CSS du widget. Pour suivre le thème de l'éditeur, mapper les variables du widget vers `--vscode-*` (`--vscode-foreground`, `--vscode-editor-background`, etc.) dans une feuille dédiée.
- Barre d'état : `window.createStatusBarItem`, texte du type `5h 42 % | sem 18 %`, infobulle avec les heures de réinitialisation, clic qui ouvre la vue.
- Personnalisation via `contributes.configuration` dans `package.json` : format du texte (gabarit `{five}`/`{week}`), fenêtres affichées, seuils de couleur (orange/rouge), intervalle de lecture.
- Couleur de l'élément de la barre d'état : `statusBarItem.warningBackground` / `errorBackground` selon les seuils.

**Difficultés / risques.**
- Le poller doit tourner (planificateur) : l'extension ne fait que lire. Lui faire appeler l'endpoint directement imposerait de lui donner accès au jeton et multiplierait les 429.
- CSP stricte des webviews : pas de script inline, ressources via `asWebviewUri`.
- Données périmées : griser l'élément si le dernier relevé a plus de N minutes.
- Publication sur le Marketplace non nécessaire ; un `.vsix` local suffit.

**Premier petit pas.** Extension minimale : un élément de barre d'état qui lit `latest.json` et affiche le pourcentage 5 h, sans réglage ni webview.

---

## 4. Thème personnalisable

**Objectif.** Choisir ses couleurs (anneau 5 h, anneau semaine, zones vert/orange/rouge) et ses polices, avec quelques préréglages.

**Esquisse.**
- Les couleurs sont déjà des variables CSS sur `:root` dans `app/web/css/style.css` : il suffit de les surcharger.
- Panneau de réglages dans le widget (sélecteurs de couleur, choix de police, aperçu en direct), clair et sombre édités séparément.
- Persistance : `localStorage` pour un usage purement local ; un `config.json` servi par `server.py` (écriture via une route protégée par les mêmes contrôles Host/Origin) pour partager entre navigateurs ou appareils.
- Format de thème : un petit JSON `{ "name": ..., "light": {...}, "dark": {...}, "font": ... }` avec export/import (copier-coller ou fichier).
- Préréglages livrés : Claude (défaut), contraste élevé, daltonien (palette sans vert/rouge), monochrome.
- Réutilisation : l'extension VS Code (idée 3) et le widget Android (idée 2) lisent le même JSON ; l'extension peut aussi choisir de suivre le thème de l'éditeur à la place.

**Difficultés / risques.**
- Lisibilité : valider un contraste minimal (WCAG) et empêcher des seuils inversés.
- Un thème importé est une donnée non fiable : n'accepter que des couleurs hexadécimales et des polices d'une liste, jamais de CSS brut.
- Polices : rester sur des polices système pour ne pas ajouter de dépendance ni de chargement externe.

**Premier petit pas.** Un panneau minimal avec trois sélecteurs de couleur enregistrés dans `localStorage` et appliqués via `document.documentElement.style.setProperty`, plus un bouton de réinitialisation.

---

## Ordre suggéré

1. **Idée 4 (thème)** : la plus rapide, sans nouvelle infrastructure ni risque pour le jeton ; elle fixe aussi le format de thème que les autres clients réutiliseront.
2. **Idée 3 (VS Code), version locale** : lit `latest.json`, donc ne dépend pas de l'idée 1 ; la prise en charge d'une source distante vient plus tard.
3. **Idée 1 (poller distant)** : le plus gros morceau, surtout pour la sécurité ; commencer par l'API en lecture seule et l'option « le PC pousse ses relevés ».
4. **Idée 2 (Android)** : à faire en dernier, car elle exige l'API et l'accès distant de l'idée 1 ; la PWA peut servir d'étape intermédiaire dès que `/api/latest` existe.

5. idee : faire un graphique historiue qui montre l'usage en %5h par heure utiliser récement 
6. faire un graphique de l'evolution de la vaelure de %5h/%7j, qui tourne autoure de 12 13%7j = 100%5h mais   ca évoulue et ca serait bien d'avoir un graph de ca 

7. incorporer lpus de donné et d'idee dans d'autre repo, voir "RepoTolookat.txt"
---

## Statut des idées 5 à 7 (branche `feature/graphiques-historique`)

- **5 (usage par heure)** : fait, graphique « Usage par heure » avec plage réglable et mini-vue (`app/web/js/charts.js`).
- **6 (évolution du ratio 5 h → semaine)** : fait, série quotidienne `ratio_daily` calculée sur tout `usage.csv` (`claude_usage.py`), tracée dans le même fichier.
- **7 (autres dépôts)** : 5 dépôts clonés dans `repos-externes/` (ignoré par Git) avec une analyse `ANALYSE-*.md` chacun et une `SYNTHESE.md`.

### Pistes retenues des dépôts (aucun code copié, aucun dépôt à intégrer)
1. **Lecteur local des transcripts** `~/.claude/projects/**/*.jsonl` (Python, incrémental par décalage d'octets, dédoublonné sur `message.id`, ne gardant que `usage`/`model`/`timestamp`, jamais le contenu) vers un `tokens.csv` par heure. Effort M.
2. **Taux de cache hit** = `cache_read / (cache_read + cache_creation + input)`. Effort S une fois le lecteur écrit.
3. **Tokens par % de quota** : croiser `tokens.csv` et `usage.csv` pour remplacer le ratio estimé par une valeur mesurée. Effort M à L.
4. Tokens par jour / modèle / projet, coût équivalent API (tarifs dans un fichier de config). Effort M.
- Ne jamais exposer les transcripts via `server.py` (vérifié : seuls `latest.json`, `latest.js` et `poller.json` sont servis).

### Audit de la 1.1.0 et corrections de la 1.1.1
Un audit complet de la 1.1.0 (rapport local `AUDIT-1.1.0.md`, non versionné car il cite des chemins et noms de projets de la machine) a couvert la sécurité du serveur et les ressources listées plus haut.
Corrigé en 1.1.1 : double comptage des messages (id déjà vu ailleurs), noms de projets dans `transcripts_state.json` (maintenant hachés), chemin UNC et lecture inter-sites de `/data/` (contrôle `Sec-Fetch-Site`), `POST /api/refresh` sans Origin et sans limite (Origin obligatoire, un seul vrai relevé toutes les 20 s), en-têtes CSP / nosniff / frame, nom de compte dans les diagnostics, `r.name` non échappé, graphique horaire tronqué après 400 barres, clavier et focus de la mini-vue, état corrompu qui désactivait le panneau Tokens, test live désormais opt-in (`CLAUDE_USAGE_LIVE=1`).
Reste à faire (mineur) : relecture complète de `usage.csv` à chaque relevé et volume d'écriture dans `data/` (surtout si le dossier est synchronisé), réveil toutes les 5 s du poller, pause du widget onglet caché, palier de 30 s du poller, premier relevé d'une nouvelle fenêtre de 5 h non compté, jours UTC contre heures locales, année absente des libellés de plage, mobile et contraste du bleu, verrou entre processus (serveur et poller), tests JavaScript plus larges.
