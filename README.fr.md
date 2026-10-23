# Claude Usage Tracker

[English](README.md)

Enregistre ton quota Claude **sur 5 heures** et **sur 7 jours** (% utilisé + heures de reset) dans un fichier CSV et l'affiche sous forme de jauges, avec des indicateurs de rythme, aux couleurs de Claude. Tout tourne en local sur ta machine.

![Vue détaillée](app/docs/screenshot-detail.png)

| Compact | Sombre |
|---|---|
| ![Vue compacte](app/docs/screenshot-compact.png) | ![Thème sombre](app/docs/screenshot-detail-dark.png) |

> **Non officiel.** Utilise un endpoint Anthropic non documenté (`/api/oauth/usage`) qui peut changer ou disparaître sans préavis.

## Démarrage rapide

Rien à compiler : les lanceurs sont déjà dans le dépôt.

1. Aie **Python 3.8+** (bibliothèque standard uniquement, rien à installer) et **Claude Code connecté** avec ton abonnement Claude, sur la même machine.
2. Télécharge le projet (page **Releases**, ou *Code → Download ZIP*, ou `git clone`) et décompresse-le **en entier**.
3. Lance :

| OS | Lancer |
|---|---|
| Windows | double-clic sur **`claude-usage-tracker.exe`** (ou `run.bat`) |
| Linux | **`claude-usage-tracker`** (ou `app/run.sh` ; après un téléchargement ZIP, lance une fois `chmod +x claude-usage-tracker app/run.sh`) |
| Tous | `python app/run.py` |

> Le `.exe` / programme Linux n'est qu'un lanceur : il démarre `run.bat` / `run.sh` du dossier `app/` voisin, donc il ne fonctionne pas seul. Copie le dossier entier, pas juste le binaire.

Tes relevés sont stockés dans le dossier `app/data/`, à côté du code (voir [Où vont tes données](#où-vont-tes-données)).

Au premier lancement, on choisit la langue (English / Français), puis un menu à flèches s'affiche, avec une courte explication sous chaque entrée :

- **Faire un relevé maintenant** – un relevé manuel, enregistré dans le CSV.
- **Ouvrir le widget** – démarre le serveur local et ouvre les jauges dans le navigateur.
- **Lancer / Arrêter le serveur du widget** – l'entrée suit l'état réel : « Lancer » quand le serveur est arrêté, « Arrêter » quand il tourne.
- **Relevés automatiques…** – installer ou retirer le poller de fond, qui fait des relevés tout seul, plus vite quand ton quota bouge et plus lentement sinon (voir [Fonctionnement](#fonctionnement)). Pas d'intervalle à choisir. Option pour lancer aussi le serveur du widget à l'ouverture de session / au démarrage. Ou rien d'automatique : tu rafraîchis à la main (bouton du widget, ou menu).
- **État** – dernier relevé, état du poller (avec l'heure du prochain relevé), état du serveur.
- **Lancer les tests**, **Language / Langue**, **Quitter**.

### Le widget

Jauges de la fenêtre 5 heures et de la semaine, bascule compact/détaillé, **répartition hebdo** par produit repliée (chaque barre est découpée par jour, voir plus bas), et un **curseur d'heures par jour** sur le côté (1–24 h, grands traits toutes les 5 h) : indique combien d'heures par jour tu utilises vraiment Claude, et le rythme semaine compte ces heures de travail (à partir de ta première requête du jour, 08:00 par défaut) ; le rythme horaire conseillé est calculé dessus. Un encart replié liste toutes les équations (voir plus bas). L'en-tête indique quand aura lieu le prochain relevé automatique (« prochain dans … »).

Dans la répartition, la barre de chaque produit a un segment par jour local, de la même couleur, avec de fins séparateurs, et le nom du jour écrit dedans (nom complet, puis abréviations plus courtes, puis une lettre, puis rien, selon la place). Survole un segment pour voir sa date et ses points. Chaque produit est mesuré séparément : le segment d'un jour correspond à ce que **ce** produit a consommé ce jour-là (d'après les parts par produit enregistrées dans `breakdown.csv` à chaque changement), donc un jour où tu n'as utilisé que Code n'apparaît que dans la barre Code. L'usage d'avant le début du suivi par produit cette semaine forme un seul segment « Avant » (exact au total, mais pas découpé par jour).

### Raccourcis en ligne de commande

```
python app/run.py read                      un relevé
python app/run.py start                     lance le serveur du widget (arrière-plan, sans navigateur)
python app/run.py open                      lance le serveur si besoin et ouvre le widget
python app/run.py stop                      arrête le serveur
python app/run.py status
python app/run.py install [--with-server]   lance le poller de fond à l'ouverture de session (et tout de suite)
python app/run.py uninstall                 le retire (arrête aussi un poller en cours)
python app/run.py tests
python app/run.py --lang fr <command>       force la langue
```

## Lanceurs et icône

En plus de `app/run.bat` / `app/run.sh`, la racine du projet contient deux petits programmes déjà compilés qui ne font que démarrer ces scripts dans un terminal (même menu, mêmes arguments) :

| OS | Programme | Icône |
|---|---|---|
| Windows | `claude-usage-tracker.exe` (double-clic, ou épingle-le à la barre des tâches) | intégrée au .exe |
| Linux | `claude-usage-tracker` (binaire statique) + une entrée de menu avec `make desktop` | via l'entrée de menu |

Le widget a aussi une icône d'onglet (`app/web/favicon.svg`). Logo : deux anneaux, orange = semaine, bleu = fenêtre 5 heures. Le menu du terminal en affiche une version en pixel art.

### Les compiler toi-même (make)

Utile seulement pour les reconstruire ou les modifier. À lancer depuis le dossier `app/` (`cd app`). Prérequis : Python 3 et `pip install ziglang` (le compilateur Zig empaqueté pour pip ; il compile les deux programmes depuis n'importe quel OS, rien d'autre à installer). Les icônes demandent aussi `pip install pillow`.

```
make            explique seulement les cibles (rien n'est compilé)
make all        compile les deux programmes (à côté du README)
make windows    claude-usage-tracker.exe (avec l'icône, via assets/app.rc)
make linux      claude-usage-tracker
make desktop    ajoute « Claude Usage Tracker » au menu des applications Linux
make icons      régénère assets/ et web/favicon.* depuis tools/make_icons.py
make clean      supprime les deux programmes compilés
python tools/build.py [windows|linux|icons|desktop|clean]    pareil sans make (par ex. sous Windows)
```

Fonctionnement : `app/tools/launcher.c` cherche `run.bat` (Windows) ou `run.sh` (Linux) dans le dossier `app/` voisin et le démarre. `app/tools/make_icons.py` dessine le logo une seule fois et écrit les fichiers SVG, PNG et ICO. Les binaires fournis ne sont pas signés : Windows SmartScreen peut afficher un avertissement la première fois ; recompile-les depuis les sources si tu préfères.

## Où vont tes données

Tout reste dans le dossier `app/data/` à côté du code (ignoré par git, créé automatiquement au premier relevé ; rien n'est écrit ailleurs) :

| Fichier | Contenu |
|---|---|
| `usage.csv` | une ligne par relevé : heure, % 5 heures, % semaine, heures de reset |
| `latest.json` / `latest.js` | dernier état + historique récent (seulement les relevés où les valeurs ont changé, plus le dernier), lus par le widget |
| `breakdown.csv` | parts hebdo par produit, une ligne par produit à chaque changement ; sert à découper les barres de répartition par jour |
| `poller.json` | état du poller : heure du prochain relevé, palier actuel |
| `poller.lock` | verrou pour qu'un seul poller tourne à la fois |
| `last_response.json` | réponse brute de l'API au dernier relevé (débogage) |
| `tracker.log` | journal des relevés en arrière-plan (statut, Retry-After, échecs d'affilée) |
| `errors.json` | les 30 derniers relevés en échec, avec tous les détails ; le bandeau rouge du widget les ouvre (**Détails**) |
| `config.json` | ta langue du menu |
| `server.log` | sortie du serveur du widget (Linux) |

Hors de `app/data/` : la tâche planifiée si tu en installes une (Planificateur de tâches Windows, ou service systemd utilisateur / ligne crontab sous Linux ; le menu la retire), et les dossiers `__pycache__` de Python. Le fichier d'identifiants de Claude Code est seulement **lu**, jamais copié. Un relevé demande Claude Code connecté ; sinon le menu t'indique que les identifiants sont introuvables.

## Fonctionnement

- `claude_usage.py` lit ton jeton OAuth Claude Code dans `~/.claude/.credentials.json` (Windows : `%USERPROFILE%\.claude\.credentials.json` ; respecte `CLAUDE_CONFIG_DIR`, ou définis `CLAUDE_USAGE_TOKEN`), interroge l'endpoint d'usage et ajoute une ligne à `data/usage.csv`. Il écrit aussi `data/latest.json` / `latest.js` pour le widget.
- Le jeton d'accès dure environ 8 heures et seul Claude Code le renouvelle : lance `claude` une fois dans un terminal (l'app Claude desktop ne semble pas réécrire ce fichier). Une fois son `expiresAt` passé, aucune requête n'est envoyée (elle prendrait un HTTP 401) ; le poller surveille le fichier et relève dès qu'il change.
- `server.py` sert le widget sur `http://127.0.0.1:8765` (local uniquement ; contrôles Host/Origin contre le DNS rebinding) et permet au bouton **Relever** de déclencher un relevé.
- `poller.py` est le poller adaptatif derrière les relevés automatiques : une boucle qui tourne en continu, pas un intervalle fixe. Après un relevé où le % 5 heures ou hebdo a changé, le suivant a lieu 30 s plus tard ; chaque relevé sans changement monte d'un palier (1 min, 3 min, 5 min, 7 min, puis 10 min, où il reste). Après un HTTP 429 (limite de débit), il attend 2 min, ou le `Retry-After` de l'API s'il est plus long, sans changer de palier. Les autres erreurs comptent comme « pas de changement ». Un seul poller tourne à la fois.
- Lancement en arrière-plan : sous Windows, la tâche planifiée « Claude Usage Tracker » démarre le poller à l'ouverture de session (et dès l'installation) et le relance s'il plante ; sous Linux, c'est le service systemd utilisateur `claude-usage-tracker.service` (`Restart=on-failure`), ou une ligne `@reboot` de crontab sans systemd (le poller est alors lancé tout de suite).
- Le widget fonctionne aussi ouvert comme simple fichier (`app/web/index.html`), mais ne peut alors pas se rafraîchir seul.

Le ratio semaine / 5 heures affiché dans le widget est estimé à partir de tes relevés consécutifs (10 % tant qu'il n'y a pas assez de données).

## Comment les chiffres sont calculés

Le widget contient un encart replié **Comment c'est calculé** qui montre chaque équation avec tes valeurs actuelles. Même contenu ici. Notation : *u5* / *u7* = % utilisé dans la fenêtre 5 heures / la semaine (donnés par Claude), *h* = le curseur d'heures par jour.

| Quoi | Équation |
|---|---|
| Rythme 5 h (repère bleu) | `(5 h − temps restant) / 5 h × 100` – vrai temps écoulé |
| Début de ta journée de travail | premier relevé du jour où la consommation a augmenté (ta première requête), sinon 08:00 |
| Rythme semaine (repère orange, anneau semaine) | `heures de travail écoulées cette semaine / heures de travail de la semaine × 100` – un jour = *h* heures à partir de l'heure de début ; à 24 h c'est le temps calendaire |
| Coût d'une fenêtre 5 h, *r* | % de la semaine consommé par 100 % d'une fenêtre 5 h, estimé sur tes relevés consécutifs (10 % par défaut) |
| Semaine utilisée en début de journée, *u0* | % hebdo au dernier relevé avant minuit local (le plus ancien s'il n'y en a pas ; 0 si la semaine a été remise à zéro) |
| Jours jusqu'au reset, *D* | `(reset hebdo − aujourd'hui 00:00) / 24 h` |
| **Budget du jour** *B* (« dépense possible / jour ») | `(100 − u0) / D` |
| Limite hebdo à cet instant, *L7* (frontière vert/rouge de l'anneau semaine) | `u0 + B` |
| Reste du budget du jour | `max(0, L7 − u7)` |
| Limite 5 h, *L5* (repère orange et frontière vert/rouge de l'anneau 5 h) | `u5 + (L7 − u7) × 100 / r` (peut dépasser 100 % quand le budget du jour couvre plus d'une fenêtre de 5 h) |
| **Conseillé par heure** (% 5 h /h) | `B / h × 100 / r` |
| Maximum possible jusqu'au reset | `(100 − u5) / heures restantes de la fenêtre` |
| Fenêtres 5 h pleines restantes | `(100 − u7) / r` |
| Répartition par produit | `part du produit × u7 / 100` points du quota hebdo, répartis par jour d'après les parts enregistrées dans `breakdown.csv` et le % de la semaine au fil du temps |
| Pastille « en avance / marge » | `utilisé − rythme` ; au-delà de ±5 points : en avance / marge |

**Ce que change le curseur :** le rythme semaine (heures de travail au lieu du temps calendaire) et le rythme horaire conseillé. Le rythme 5 h est du vrai temps, et les zones vert/rouge viennent du budget du jour, qui ne dépend pas du curseur.

## Structure du projet

```
README.md  README.fr.md  LICENSE
claude-usage-tracker.exe    lanceur Windows (double-clic)
claude-usage-tracker        lanceur Linux
app/                        tout le reste
  run.py  run.bat  run.sh   point d'entrée (menu)
  launcher/                 code du menu et traductions (strings.py)
  claude_usage.py           lit le quota, écrit data/
  poller.py                 poller adaptatif (relevés en arrière-plan)
  server.py                 serveur local du widget
  web/                      le widget (HTML, CSS, JS ; EN/FR)
  windows/  linux/          scripts d'installation/désinstallation du planificateur
  tools/  assets/  Makefile source C des lanceurs, scripts de build, icônes
  docs/                     captures du README
  data/                     tes relevés (ignoré par git, jamais commité)
```

## Confidentialité

- Aucune donnée ne quitte ta machine, hormis la requête vers l'API d'Anthropic avec ton propre jeton.
- Le jeton est lu à l'exécution, jamais copié ni journalisé. `app/data/` et les identifiants sont dans `.gitignore`.
- Le serveur n'écoute que sur `127.0.0.1`.

## Remarques

- macOS : les scripts sont du Python/shell standard et peuvent fonctionner, mais l'installation du planificateur n'est pas testée (utilise cron à la main).
- Si tu avais installé les relevés automatiques avec l'ancienne organisation (avant le dossier `app/`), refais **Relevés automatiques** une fois dans le menu : l'ancienne tâche pointe vers l'ancien emplacement.
- Si tu as installé les relevés automatiques avec la v1.0.0 (intervalle fixe), refais **Relevés automatiques** une fois dans le menu pour passer au poller.
- Non affilié à Anthropic.

## Licence

MIT – voir [LICENSE](LICENSE).
