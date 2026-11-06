# Idées pour la suite

Contraintes communes : l'endpoint `GET /api/oauth/usage` n'est pas documenté (il peut changer ou disparaître sans préavis), il répond en HTTP 429 si on l'interroge trop souvent, et le jeton OAuth de Claude Code est un secret qui donne accès au compte.

**Lecture du document.** Chaque idée a un code (`ONB-1`, `UI-3`…) pour pouvoir s'y référer dans un commit ou une discussion. Effort : **S** = quelques heures, **M** = une à deux sessions, **L** = plusieurs sessions. Statut : ⬜ à faire · ✅ fait.

| Famille | Codes | Sujet |
|---|---|---|
| ONB | `ONB-1` | Première utilisation et menu |
| UI | `UI-1` à `UI-5` | Page web : textes, mise en page, réglages, cadrans, niveaux de compacité |
| ACC | `ACC-1` | Lancer et voir le widget plus facilement |
| API | `API-1`, `API-2` | Socle commun à tous les clients (stockage unique, API, réglages partagés) |
| CLI | `THM-1`, `VSC-1`, `AND-1`, `HUB-1` | Thème, extension VS Code, Android, poller distant |
| TOK | `TOK-1` à `TOK-4` | Pistes restantes sur les tokens |
| DIV | `RES-*`, `SEC-*`, `DAT-*`, `TST-*` | Reste de l'audit 1.1.0 (mineur) |

---

## ✅ Déjà fait

| Statut | Idée | Livré en |
|---|---|---|
| ✅ | Graphique « Usage par heure » (en % de la fenêtre 5 h), avec plage réglable et mini-vue glissable | 1.1.0 |
| ✅ | Graphique « Ratio 5 h → semaine dans le temps », jour par jour et en cumul, même sélecteur de plage | 1.1.0 |
| ✅ | Analyse de 5 dépôts GitHub (dossier `repos-externes/`, ignoré par Git) et reprise des idées utiles sans copier de code | 1.1.0 |
| ✅ | Lecteur local des transcripts Claude Code (`app/transcripts.py`) : tokens par heure, modèle, type d'agent ; cache hit ; tokens par % de semaine | 1.1.0 |
| ✅ | Panneau « Tokens et cache » : 4 types de tokens (entrée fraîche, écriture de cache, lecture de cache, sortie), part des tokens contre part du coût relatif, économie du cache, vue par jour | 1.1.0 |
| ✅ | Audit de sécurité du serveur et étude des ressources (rapport local `AUDIT-1.1.0.md`, non versionné) | 1.1.0 |
| ✅ | Corrections de l'audit : messages comptés une fois, noms de projets hachés, chemins UNC refusés, lecture inter-sites de `/data/` refusée (`Sec-Fetch-Site`), Origin obligatoire sur `POST /api/refresh` et un seul vrai relevé toutes les 20 s, en-têtes CSP / nosniff / frame, plus de nom de compte dans les diagnostics, noms de produits échappés, plage « Tout » non tronquée, mini-vue utilisable au clavier | 1.1.1 |

Ce qui était vérifié et correct dès la 1.1.0 : écoute sur `127.0.0.1` seulement, contrôle `Host` (DNS rebinding), liste blanche de trois fichiers servis dans `data/`, aucun jeton dans les réponses, les logs, `errors.json` ou `last_response.json`.

---

## ⬜ À faire, par ordre conseillé

| # | Code | Idée | Effort | Dépend de |
|---|---|---|---|---|
| 1 | ✅ `UI-3` | Rythme selon les heures de travail : interrupteur on/off (fait) | S | — |
| 2 | ✅ `UI-1` | Textes d'aide : raccourcir, supprimer les doublons, pouvoir les masquer (fait) | S à M | — |
| 3 | ✅ `UI-4` | Graduations de temps sur les deux cadrans (fait) | M | `UI-3` (pour la semaine) |
| 4 | `UI-2` | Page qui utilise la largeur, compatible tactile, vue compacte lisible | M à L | `UI-1` |
| 5 | `UI-5` | Curseur de compacité (une dizaine de crans) et niveau choisi selon la largeur | L | `UI-1`, `UI-2` |
| 6 | `ONB-1` | Assistant de première utilisation et menu plus clair | M | — |
| 7 | `ACC-1` | Lancer et ouvrir le widget sans terminal | M | `ONB-1` |
| 8 | `API-1`, `API-2` | Socle commun : stockage unique, API de lecture versionnée, réglages côté serveur | M à L | — |
| 9 | `THM-1` | Thème personnalisable | M | `API-2` |
| 10 | `VSC-1` | Extension VS Code : vue latérale et indicateur dans la barre d'état | M à L | `API-1`, `UI-5` |
| 11 | `HUB-1` | Poller sur une machine toujours allumée | L | `API-1` |
| 12 | `AND-1` | Android : PWA d'abord, widget natif ensuite | L | `API-1`, `HUB-1` |

Les quatre premières sont des retouches de la page et ne touchent ni au jeton ni aux données : elles peuvent se faire dans l'ordre, une branche chacune. `UI-5` est le gros chantier de la page : il remplace la bascule Détaillé / Compact et prépare l'affichage sur les autres plateformes (VS Code, Android). Le socle `API-1` / `API-2` est ce qui permet de garder **un seul stockage** pour tous les appareils (voir le plan plus bas).

---

### `ONB-1` · Première utilisation et menu plus clair

**Problème.** Au premier lancement, rien n'explique quoi faire ni dans quel ordre.

**Objectif.** Un assistant « Configuration rapide » où il suffit d'appuyer sur **Entrée** pour obtenir une installation qui marche, et où chaque choix est une question oui/non avec la réponse recommandée par défaut.

**Esquisse.**
- Détection du premier lancement : pas de `data/config.json`, ou clé `setup_done` absente. L'assistant se relance aussi depuis le menu (« Configuration rapide ») et en ligne de commande (`--setup`, avec `--yes` pour tout accepter sans question).
- Étapes, chacune avec une phrase d'explication et un défaut sur Entrée :
  1. Langue (FR / EN).
  2. Vérifier que Claude Code est connecté (jeton trouvé ?) ; sinon dire exactement quoi faire (`/login` dans Claude Code) et proposer de réessayer.
  3. Faire un premier relevé [O/n] et montrer le résultat (5 h, semaine).
  4. Installer le relevé automatique en arrière-plan [O/n] : dire ce que ça crée (tâche planifiée / service) et comment l'enlever.
  5. Démarrer le widget à l'ouverture de session [O/n] (voir `ACC-1`).
  6. Ouvrir le widget maintenant [O/n].
- Écran de récapitulatif final : ce qui est installé, où sont les données, comment tout désinstaller.
- Menu principal : regroupé (Voir · Relevés · Réglages · Maintenance), avec une ligne d'état en haut (« relevé auto : actif · serveur : actif · dernier relevé il y a 3 min »).
- Les textes passent par `launcher/strings.py` (FR et EN, vérifiés par les tests).

**Risques.** Ne rien installer sans réponse explicite ; l'assistant doit être rejouable sans doublon (tâche déjà installée, etc.).

**Premier pas.** Ligne d'état en haut du menu actuel, puis l'assistant avec seulement les étapes 1 à 3.

---

### `UI-1` · Textes d'aide : plus courts, sans doublons, masquables

**Problème.** Beaucoup de petits textes explicatifs sous les panneaux sont lourds, et certains répètent ce qui est déjà affiché.

**Objectif.** Garder les explications, mais plus brèves, sans répétition, et pouvoir les masquer d'un geste une fois lues.

**Esquisse.**
- **Interrupteur global « Explications »** dans l'en-tête (activé par défaut), mémorisé dans `localStorage` (puis dans les réglages serveur, voir `API-2`). Quand il est coupé, toutes les notes `.note`, les `.hint` longs et la légende du pied de page disparaissent. Avec `UI-5`, cet interrupteur devient le dernier cran du curseur de compacité.
- **« Comment c'est calculé » dans un bouton « ? »** en haut à droite de la page : il ouvre un encart (fenêtre flottante ou panneau latéral) au lieu d'occuper un panneau entier en bas de page.
- **Une icône « ? » par panneau** pour afficher ou masquer sa propre note sans toucher au reste.
- **Raccourcir** chaque note à une ou deux phrases ; le détail complet reste dans « Comment c'est calculé ».
- **Doublons à supprimer** (repérés sur la 1.1.1) :
  - le pied de page « Une fenêtre de 5 h pleine ≈ 12,7 % de la semaine (estimé sur N points) » répète l'en-tête du graphique « Ratio 5 h → semaine » : ne garder qu'un des deux ;
  - le pied de page « Budget du jour = … » répète le panneau « Comment c'est calculé » ;
  - dans le panneau Tokens, le taux de cache apparaît trois fois (en-tête, chiffre principal, note « Cache hit = … ») ;
  - l'en-tête « Usage par heure » répète le total qui figure sous le graphique.
- Inventaire à faire d'abord : lister chaque texte (clé i18n, où il s'affiche), décider garder / raccourcir / supprimer.

**Risques.** Les tests vérifient que toutes les clés existent en FR et en EN : retirer une clé des deux côtés.

**Premier pas.** Interrupteur global + suppression des doublons du pied de page.

---

### `UI-2` · Utiliser la largeur, tactile, vue compacte lisible

**Problème.** La page est une colonne étroite centrée (860 px, et 640 px en vue compacte) : la largeur d'un grand écran ne sert à rien, et la vue compacte rétrécit tout au lieu de le rendre plus lisible. Le widget doit aussi marcher sur d'autres appareils (téléphone, tablette).

**Objectif.** Une mise en page qui s'adapte à la largeur disponible, utilisable au doigt, avec une vue compacte vraiment lisible.

**Esquisse.**
- **Grille adaptative** (CSS grid, `@container` ou media queries) :
  - étroit (< 700 px) : une colonne, comme aujourd'hui ;
  - moyen (≥ 900 px) : les deux cadrans côte à côte, puis les graphiques « Usage par heure » et « Ratio » côte à côte ;
  - large (≥ 1300 px) : trois colonnes (cadrans, graphiques, tokens), le curseur d'heures rangé dans l'en-tête ;
  - on garde l'empilement quand il n'y a pas la place.
- **Vue compacte** (à terme remplacée par les crans de `UI-5`) : un mode « widget » qui remplit toute la fenêtre (les anneaux et les chiffres s'agrandissent avec la fenêtre, peu d'éléments), prévu pour une petite fenêtre épinglée ou un second écran, au lieu de réduire la largeur maximale.
- **Tactile** :
  - zones de toucher d'au moins 44 px (poignées de la mini-vue, boutons de plage) ;
  - un appui sur une barre ou un point affiche une infobulle (les `title` n'existent pas au toucher) ;
  - pincer pour zoomer et glisser pour déplacer sur le graphique principal, en plus de la mini-vue ;
  - pas d'action qui n'existe qu'au survol.
- **Tableaux** : défilement horizontal ou présentation en cartes sous 600 px (le tableau par jour des tokens a 7 colonnes).
- **Contraste** : le bleu `--blue` sur la carte claire est à environ 2,7:1 (relevé par l'audit) ; l'assombrir pour les éléments graphiques.

**Risques.** Tester sur de vrais formats (téléphone, tablette, grand écran) et en clair comme en sombre.

**Premier pas.** Grille à deux colonnes à partir de 900 px, sans toucher au reste.

---

### `UI-3` · Rythme selon les heures de travail : interrupteur

**Problème.** Le curseur « heures par jour » est toujours visible alors que ce n'est ni évident ni utile pour tout le monde.

**Objectif.** Un interrupteur on/off ; le curseur n'apparaît que quand il est activé.

**Esquisse.**
- Interrupteur « Rythme selon mes heures de travail » (désactivé par défaut) dans le panneau latéral.
- **Désactivé** : le rythme de la semaine suit le temps du calendrier (ce que fait déjà `hoursPerDay = 24` dans `model.js`) ; les formules du panneau « Comment c'est calculé » s'adaptent.
- **Activé** : le curseur 1–24 h s'affiche et on choisit le nombre d'heures.
- Mémorisé comme les autres réglages (`localStorage`, puis serveur : `API-2`).

**Premier pas.** Une case à cocher qui masque le curseur et force `hours = 24` quand elle est décochée.

---

### `UI-4` · Graduations de temps sur les deux cadrans

**Contexte.** Sur chaque anneau, l'angle représente le **% utilisé** (arc de 270°). Les petits traits gris actuels sont tous les 10 % (0 à 100 %). Le repère de rythme (triangle) place déjà le **temps écoulé** sur cette même échelle (temps écoulé ÷ durée × 100 %), donc une graduation de temps se place sur le même cadran sans changer l'échelle.

**Anneau 5 heures.**
- Un trait tous les **15 minutes** (5 % de l'arc), de trois longueurs : court (15 min), moyen (30 min), long (heure pleine).
- Les heures pleines portent un numéro : **1 h, 2 h, 3 h, 4 h, 5 h** (temps écoulé depuis le début de la fenêtre).

**Anneau semaine.**
- Sept traits placés aux **minuits locaux** de chaque jour de la fenêtre, avec l'initiale ou l'abréviation du jour (L M M J V S D).
- La fenêtre commence à l'heure du reset (par exemple samedi 19 h), donc les traits ne sont pas répartis en 7 parts égales depuis le départ : c'est voulu, ils indiquent où on en est dans le calendrier.
- Avec `UI-3` activé (heures de travail), le rythme n'est plus le temps du calendrier : le dire dans la note ; les minuits restent des repères de calendrier.

**Points de conception à trancher.**
- Garder les graduations en % (0, 50, 100) en plus ? Proposition : graduations de temps à l'**extérieur** de l'arc, graduations de % à l'**intérieur**, pour ne pas les confondre.
- Étiquettes lisibles à la taille de la vue compacte (voir `UI-2`) : n'afficher les numéros que si la place le permet.
- Fuseau : minuits locaux du navigateur.

**Premier pas.** Les traits de 15 minutes sur l'anneau 5 h, dans `gauge.js` (fonction `ticks`).

---

### `UI-5` · Curseur de compacité à une dizaine de crans

**Problème.** Il n'y a que deux vues, Détaillé et Compact. Rien entre les deux, et rien de plus petit que la vue compacte : impossible de caser le widget dans une bande étroite (barre latérale de VS Code, écran d'accueil d'un téléphone, coin d'écran).

**Objectif.** Remplacer la bascule par un **curseur à une dizaine de crans**, du plus compact au plus détaillé. Chaque cran garde **toute** l'information du cran précédent et en ajoute, sans empiéter sur ce qui était déjà là. Quand on descend d'un cran de compacité, on voit la même information de façon encore plus claire, plus un peu d'information en plus.

**Crans proposés** (à affiner en maquettant ; la frontière entre deux crans peut bouger) :

| Cran | Ce qui s'affiche |
|---|---|
| 1 | **Liseré** : deux fines barres aux couleurs des anneaux (5 h, semaine), remplies au % utilisé ; éventuellement une 3ᵉ barre empilée avec la répartition des tokens (entrée fraîche, écriture de cache, lecture de cache, sortie) |
| 2 | Les mêmes barres avec le % écrit et le repère de rythme |
| 3 | + heure de réinitialisation de chaque fenêtre |
| 4 | Les **deux cadrans** remplacent les barres (petits, chiffres au centre) |
| 5 | Cadrans plus grands + chiffres clés (budget du jour, rythme, limite conseillée) |
| 6 | + graphique « Usage par heure » en version réduite (sans axes détaillés ni mini-vue) |
| 7 | + graphique « Ratio 5 h → semaine » réduit, + résumé du panneau Tokens |
| 8 | Graphiques complets (axes, sélecteur de plage, mini-vue glissable) |
| 9 | **Tout** : tableau par jour des tokens, répartition par produit, réglages, etc. |
| 10 · Explications | Cran **à part**, séparé visuellement des autres : tout le cran 9, plus toutes les petites notes qui expliquent chaque graphique et comment il est calculé (remplace l'interrupteur « Explications » de `UI-1`) |

**Règles de conception.**
- **Hiérarchie stricte** : un élément présent à un cran l'est à tous les crans moins compacts, au même endroit ou en plus grand. On ajoute, on ne remplace pas une information par une autre.
- **Chaque graphique a ses versions réduites** : c'est le gros du travail. Pour chaque graphique, décider ce qu'on retire en premier (légende, axes, étiquettes, mini-vue…) pour ne garder à la fin que l'essentiel, et optimiser l'espace à chaque cran.
- **Composants paramétrés par le cran** (`level` passé à `gauge.js`, `charts.js`, etc.) plutôt que du CSS qui masque des éléments : ces mêmes composants serviront à l'extension VS Code (`VSC-1`) et à Android (`AND-1`).
- « Comment c'est calculé » reste accessible à tous les crans par le bouton « ? » en haut à droite (voir `UI-1`), sauf au cran 1 où il n'y a pas la place.

**Cran par défaut selon la largeur.**
- Mode **« Auto »** (par défaut) : le cran est choisi d'après la largeur disponible au démarrage et quand la fenêtre change de taille (`ResizeObserver` sur le conteneur, pas sur l'écran), avec des seuils à définir (par exemple < 200 px → cran 1, < 400 px → cran 4…).
- Si l'utilisateur bouge le curseur, son choix est retenu (`localStorage`, puis `API-2`) ; un bouton « Auto » revient au choix automatique.
- Même logique pour la vue latérale de VS Code, dont la largeur de la bande décide du cran.

**Risques.** Beaucoup de combinaisons à tester (10 crans × clair/sombre × largeurs) ; garder des captures de référence par cran. Les tests i18n doivent couvrir les nouveaux libellés.

**Premier pas.** Inventaire : pour chaque élément de la page, à partir de quel cran il apparaît. Puis le curseur avec trois crans seulement (liseré, cadrans, tout) branché sur la vue actuelle, et le mode Auto.

---

### `ACC-1` · Lancer et voir le widget sans passer par le terminal

**Problème.** Aujourd'hui il faut ouvrir un terminal, aller dans le bon dossier, lancer le menu, puis demander l'ouverture du navigateur. Ce n'est ni intuitif ni facile à observer.

**Pistes, de la plus simple à la plus ambitieuse** (cumulables) :
1. **Serveur toujours actif.** Le démarrer à l'ouverture de session (tâche planifiée Windows ou service utilisateur systemd, déjà utilisés pour le relevé) : `http://127.0.0.1:8765` répond toujours, rien à lancer.
2. **Un double-clic qui ouvre directement le widget.** Le lanceur `.exe` / Linux ouvre le menu ; ajouter un raccourci (Bureau, menu Démarrer) qui démarre le serveur s'il ne tourne pas et ouvre le navigateur, sans menu.
3. **Application installable (PWA).** Manifeste et service worker : Chrome ou Edge propose « Installer l'application », avec sa propre fenêtre et son icône dans la barre des tâches. Sert aussi d'étape pour Android (`AND-1`).
4. **Adresse plus facile à retenir** (par exemple `http://claude.localhost:8765`) : à autoriser dans le contrôle `Host`.
5. **Icône dans la zone de notification** avec les pourcentages dans l'infobulle (demande une bibliothèque ou du code natif : à étudier, la bibliothèque standard seule ne suffit pas).

**Conseil.** Commencer par 1 et 2 (rien de nouveau à installer), puis 3. Les étapes 1 et 2 s'intègrent à l'assistant `ONB-1`.

**Risques.** Un serveur toujours actif élargit un peu l'exposition : garder `127.0.0.1` et les contrôles Host / Origin / Sec-Fetch-Site de la 1.1.1.

---

## Plan : un seul stockage pour tous les clients (`API-1`, `API-2`)

**Besoin exprimé.** Web, extension VS Code et Android doivent s'appuyer sur **le même stockage** et **le même usage collecté depuis le début**, sans versions indépendantes qui divergent.

**Principe.** Une seule machine collecte (le « hub » : celle où tourne le poller) et possède les données. Tous les clients sont de simples lecteurs d'une même API ; aucun ne calcule sa propre histoire.

```
 Claude Code ──jeton──▶ poller ──▶ data/ (usage.csv, tokens.csv, config.json)   ← source unique
                                      │
                               serveur (API de lecture v1)
                  ┌───────────────┬───┴───────────┬────────────────┐
              widget web      extension VS Code    PWA / Android    (autres)
```

**`API-1` · Contrat de données versionné** (M)
- `latest.json` et l'historique reçoivent un champ `schema: 1` ; toute évolution incompatible change ce numéro.
- Routes de lecture seule, stables : `GET /api/v1/latest`, `GET /api/v1/history?since=…`, `GET /api/v1/tokens?since=…`, `GET /api/v1/config`. Les routes `/data/*` actuelles restent pour le widget.
- **Les calculs (rythme, limites, ratio) ne doivent exister qu'à un endroit.** Aujourd'hui ils sont dans `web/js/model.js`. Deux options :
  - **A. Module JS partagé** (`model.js` sans dépendance au navigateur) réutilisé par le widget, la PWA et l'extension VS Code (Node / webview). Android natif devrait alors le réécrire ou l'embarquer dans une WebView.
  - **B. Le serveur calcule** et renvoie un modèle prêt à afficher (`/api/v1/model`) ; les clients ne font que dessiner. Plus simple pour Android, au prix d'une dépendance au serveur pour tout affichage.
  - Conseil : **B** pour le noyau (valeurs de la jauge, limites, rythme) et **A** seulement si un client doit fonctionner hors ligne.
- Test de contrat : un fichier d'exemple `latest.v1.json` vérifié par les tests, pour que tous les clients partent de la même forme.

**`API-2` · Réglages côté serveur** (M)
- `data/config.json` devient la source des réglages partagés : thème (`THM-1`), interrupteur et nombre d'heures (`UI-3`), explications affichées (`UI-1`), vue par défaut, langue.
- `GET /api/v1/config` et `POST /api/v1/config` (même contrôle Origin et même limite de fréquence que `/api/refresh`) ; valeurs validées côté serveur (couleurs hexadécimales, listes fermées), jamais de CSS ou de HTML brut.
- Le widget garde `localStorage` en repli quand le serveur n'est pas joignable.

**Phasage conseillé.**
1. `API-1` : schéma, routes `/api/v1/*`, modèle calculé côté serveur.
2. `API-2` : réglages partagés ; le widget les utilise.
3. `VSC-1` : extension qui lit `latest.json` en local puis l'API.
4. `HUB-1` : accès depuis d'autres machines (jeton d'API, Tailscale).
5. `AND-1` : PWA, puis widget natif.

**Garde-fous.** Les clients n'ont jamais accès au jeton Claude ; un seul poller par compte (429) ; le jeton d'API du tracker est distinct du jeton Claude, dans un fichier en `chmod 600`.

---

### `THM-1` · Thème personnalisable (ancienne idée 4)

**Objectif.** Choisir ses couleurs (anneau 5 h, anneau semaine, zones vert / orange / rouge) et sa police, avec quelques préréglages, partagés par tous les clients.

**Esquisse.**
- Les couleurs sont déjà des variables CSS sur `:root` (`app/web/css/style.css`) : il suffit de les surcharger.
- Panneau de réglages avec sélecteurs de couleur et aperçu en direct, clair et sombre édités séparément.
- Format : `{ "name", "light": {…}, "dark": {…}, "font" }`, export / import (copier-coller ou fichier), stocké dans `config.json` (`API-2`).
- Préréglages : Claude (défaut), contraste élevé, daltonien (sans vert / rouge), monochrome.
- Réutilisation par `VSC-1` (qui peut aussi suivre le thème de l'éditeur) et `AND-1`.

**Risques.** Lisibilité (contraste WCAG minimal, seuils non inversés) ; un thème importé est une donnée non fiable : couleurs hexadécimales et polices d'une liste seulement. Polices système, pas de chargement externe.

**Premier pas.** Trois sélecteurs de couleur dans `localStorage` appliqués par `setProperty`, avec un bouton de réinitialisation.

---

### `VSC-1` · Extension VS Code (ancienne idée 3)

**Objectif.** Suivre le quota sans quitter l'éditeur : vue latérale (bandeau sur le côté gauche) et petit indicateur en bas à droite dans la barre d'état.

**Esquisse.**
- Source : `app/data/latest.json` en local (lecture de fichier avec `fs.watch`, aucune requête réseau), ou `/api/v1/latest` quand le hub est distant (réglage `claudeUsage.source`). Même stockage que le widget : l'extension ne collecte rien.
- Vue latérale : `WebviewViewProvider` réutilisant `gauge.js` et le CSS du widget (variables mappées vers `--vscode-*`). Le cran de compacité (`UI-5`) suit la **largeur de la bande** : bande étroite → barres ou petits cadrans, bande large → graphiques.
- Indicateur dans la barre d'état, en bas à droite, avec trois niveaux de détail :
  - **au repos** : les deux petites barres (comme le cran 1 de `UI-5`) avec le % de la fenêtre 5 h et le % des 7 jours, par exemple `▰▰▱ 42 % · ▰▱▱ 18 %` ; couleur `statusBarItem.warningBackground` / `errorBackground` selon les seuils, grisé si la donnée est ancienne ;
  - **au survol** : une infobulle avec un peu plus d'informations (heures de réinitialisation, rythme, heure du dernier relevé), sans tout montrer ;
  - **au clic** : une vue plus grande avec plus d'informations (ouvre la vue latérale ou un panneau à un cran plus détaillé).
- Les barres de la barre d'état sont du texte (caractères ou icônes `$(…)`) : pas de dessin libre possible à cet endroit dans VS Code, à vérifier en maquettant.
- Réglages `contributes.configuration` : gabarit du texte, seuils, intervalle de lecture.

**Risques.** Le poller doit tourner (l'extension ne fait que lire) ; CSP stricte des webviews (pas de script inline, `asWebviewUri`) ; un `.vsix` local suffit, pas de Marketplace.

**Premier pas.** Un élément de barre d'état qui lit `latest.json` et affiche les deux pourcentages, avec l'infobulle au survol.

---

### `HUB-1` · Poller sur une machine toujours allumée (ancienne idée 1)

**Objectif.** Relever 24 h / 24 sur un NAS ou petit serveur et consulter depuis n'importe quel appareil, sans dépendre du PC où Claude Code est connecté.

**Options pour le jeton.**
- **A. Le PC pousse ses relevés** (recommandé) : le poller reste sur le PC et envoie chaque relevé (`POST /api/readings`) au hub ; le jeton ne quitte jamais le PC. Limite : plus de relevés quand le PC est éteint.
- **B. Copier le jeton** vers le hub à chaque renouvellement : simple, mais le secret est dupliqué.
- **C. Renouvellement OAuth autonome** (`refresh_token`) : à éviter, un refresh token est souvent à usage unique et déconnecterait Claude Code.

**Esquisse.**
- Liste `allowed_hosts` dans la config (vide par défaut) pour les contrôles Host, option `--bind` + jeton d'API (en-tête `Authorization: Bearer`) désactivés par défaut.
- Accès distant par Tailscale ou WireGuard plutôt qu'Internet ; sinon reverse proxy HTTPS avec authentification.
- Image Docker minimale (`python:3-alpine`, bibliothèque standard seule), volume pour `data/`.
- Déduplication sur l'horodatage si plusieurs sources écrivent dans `usage.csv` ; backoff sur 429 ; appel à l'endpoint isolé dans une seule fonction.

**Risques.** Sécurité du jeton (copies, sauvegardes, logs), 429, dérive d'horloge.

**Premier pas.** Les routes `/api/v1/*` en lecture seule (`API-1`), puis `--bind` et `--token` testés par Tailscale entre deux machines.

---

### `AND-1` · Android avec widget d'écran d'accueil (ancienne idée 2)

**Objectif.** Voir les deux anneaux sur l'écran d'accueil du téléphone, sans ouvrir de navigateur, à partir du **même stockage** que le reste.

**Esquisse.**
- Dépend de `API-1` et `HUB-1` : le téléphone lit l'API en lecture seule (Tailscale ou HTTPS), il ne voit jamais le jeton Claude.
- **Étape 1 : PWA** (manifeste et service worker, voir `ACC-1`) installée sur l'écran d'accueil : pas de code natif, pas de vrai widget.
- **Étape 2 : widget natif** (Kotlin, Jetpack Glance ou `AppWidgetProvider`, rafraîchi par `WorkManager`, environ 15 min minimum et soumis à Doze). Anneaux dessinés en `Canvas` avec les mêmes couleurs que le thème (`THM-1`) ; si le serveur calcule le modèle (option B de `API-1`), le widget n'a qu'à dessiner.
- URL du serveur et jeton d'API dans `EncryptedSharedPreferences`.

**Risques.** Fraîcheur (15 min de latence maximale : afficher l'heure du dernier relevé), Tailscale actif sur le téléphone, second code à maintenir pour une API source instable, APK installé à la main.

**Premier pas.** Manifeste et service worker dans `app/web/` et installation en PWA sur le téléphone.

---

## Pistes sur les tokens non retenues pour l'instant

Données disponibles dans les transcripts mais pas encore lues ou affichées. À reprendre seulement si le besoin se confirme.

| Code | Piste | Effort |
|---|---|---|
| `TOK-1` | Taille du contexte à chaque tour (entrée + cache lu + cache écrit), pics avant un `/compact` | M |
| `TOK-2` | Écritures de cache 5 min contre 1 h : déjà séparées dans les données (`cache_write_1h`), pas encore montrées comme un graphique | S |
| `TOK-3` | Tokens par projet (le dossier du transcript le donne ; nom à hacher, ou à n'afficher qu'en local) | M |
| `TOK-4` | Coût en dollars avec des tarifs par modèle dans un fichier de config (aujourd'hui : coût relatif en équivalents de tokens d'entrée) | S à M |

Déjà disponibles dans `latest.json` mais masqués dans le panneau depuis la refonte : séparation par modèle (Opus / Sonnet), part de réflexion (`thinking`), session principale contre sous-agents (visibles dans la version taguée `v-tokens-detaille`).

---

## Reste de l'audit 1.1.0 (mineur)

| Code | Point | Effort |
|---|---|---|
| `RES-1` | Relecture complète de `usage.csv` à chaque relevé : analyser les dates une fois, ou cache incrémental (≈ 3 s par relevé à 100 000 lignes) | M |
| `RES-2` | Volume d'écriture dans `data/` à chaque relevé (surtout si le dossier est synchronisé) : n'écrire que ce qui a changé | M |
| `RES-3` | Poller : réveil toutes les 5 s (`TICK_S`), à allonger quand il n'y a rien à surveiller ; premier palier de 30 s à reconsidérer | S |
| `RES-4` | Widget : ne pas re-rendre toutes les 10 s si les données n'ont pas changé, pause quand l'onglet est caché (`visibilityState`) | S |
| `SEC-1` | Pas de verrou entre le serveur et le poller (deux relevés simultanés possibles) | M |
| `SEC-2` | Machine partagée : `SO_EXCLUSIVEADDRUSE` sous Windows, droits `chmod 600` de `data/` sous Linux | S |
| `SEC-3` | Le lanceur vérifie mieux le pid renvoyé par `/api/ping` avant de l'arrêter | S |
| `DAT-1` | Le premier relevé d'une nouvelle fenêtre de 5 h n'est pas compté dans l'usage par heure ni dans le ratio | S |
| `DAT-2` | Jours UTC (tokens, ratio) contre jours locaux (répartition par produit, usage par heure) : harmoniser ou le dire dans les libellés | M |
| `DAT-3` | Année absente des libellés de plage au-delà d'un an | S |
| `TST-1` | Tests JavaScript plus larges (rendu des graphiques, glisser-déposer, passage à l'heure d'été) et test dans un vrai navigateur | M |
| `TST-2` | Vérifier la compatibilité Python 3.8 à 3.10 (annoncée « 3.8+ » mais non testée) | S |
