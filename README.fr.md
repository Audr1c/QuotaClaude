# Claude Usage Tracker

[English](README.md)

Enregistre ton quota Claude **sur 5 heures** et **sur 7 jours** (% utilisé + heures de reset) dans un fichier CSV et l'affiche sous forme de jauges, avec des indicateurs de rythme, aux couleurs de Claude. Tout tourne en local sur ta machine.

![Vue détaillée](docs/screenshot-detail.png)

| Compact | Sombre |
|---|---|
| ![Vue compacte](docs/screenshot-compact.png) | ![Thème sombre](docs/screenshot-detail-dark.png) |

> **Non officiel.** Utilise un endpoint Anthropic non documenté (`/api/oauth/usage`) qui peut changer ou disparaître sans préavis.

## Démarrage rapide

Prérequis : Python 3.8+ (bibliothèque standard uniquement, rien à installer) et Claude Code connecté sur la même machine.

| OS | Lancement |
|---|---|
| Windows | double-clic sur `run.bat` (ou `run.bat` dans un terminal) |
| Linux | `./run.sh` (la première fois : `chmod +x run.sh`) |
| Tous | `python run.py` |

Au premier lancement, on choisit la langue (English / Français), puis un menu à flèches s'affiche, avec une courte explication sous chaque entrée :

- **Faire un relevé maintenant** – un relevé manuel, enregistré dans le CSV.
- **Ouvrir le widget** – démarre le serveur local et ouvre les jauges dans le navigateur.
- **Lancer / Arrêter le serveur du widget** – l'entrée suit l'état réel : « Lancer » quand le serveur est arrêté, « Arrêter » quand il tourne.
- **Relevés automatiques…** – installer, modifier ou retirer la tâche de fond. Par défaut : toutes les **10 minutes** ; choisis un préréglage ou tape le nombre de minutes voulu. Option pour lancer aussi le serveur du widget à l'ouverture de session / au démarrage. Ou rien d'automatique : tu rafraîchis à la main (bouton du widget, ou menu).
- **État** – dernier relevé, état du planificateur, état du serveur.
- **Lancer les tests**, **Language / Langue**, **Quitter**.

### Le widget

Jauges de la fenêtre 5 heures et de la semaine, bascule compact/détaillé, répartition par produit repliée, et un **curseur d'heures par jour** sur le côté (1–24 h, grands traits toutes les 5 h) : indique combien d'heures par jour tu utilises vraiment Claude, et le rythme horaire conseillé ainsi que la limite 5 h sont recalculés sur ces heures plutôt que sur les nuits aussi.

### Raccourcis en ligne de commande

```
python run.py read                      un relevé
python run.py start                     lance le serveur du widget (arrière-plan, sans navigateur)
python run.py open                      lance le serveur si besoin et ouvre le widget
python run.py stop                      arrête le serveur
python run.py status
python run.py install --minutes 10 [--with-server]
python run.py uninstall
python run.py tests
python run.py --lang fr <command>       force la langue
```

## Fonctionnement

- `claude_usage.py` lit ton jeton OAuth Claude Code dans `~/.claude/.credentials.json` (Windows : `%USERPROFILE%\.claude\.credentials.json` ; respecte `CLAUDE_CONFIG_DIR`, ou définis `CLAUDE_USAGE_TOKEN`), interroge l'endpoint d'usage et ajoute une ligne à `data/usage.csv`. Il écrit aussi `data/latest.json` / `latest.js` pour le widget.
- `server.py` sert le widget sur `http://127.0.0.1:8765` (local uniquement ; contrôles Host/Origin contre le DNS rebinding) et permet au bouton **Relever** de déclencher un relevé.
- Planification : Planificateur de tâches Windows, ou timer systemd utilisateur sous Linux (cron en secours).
- Le widget fonctionne aussi ouvert comme simple fichier (`web/index.html`), mais ne peut alors pas se rafraîchir seul.

Le ratio semaine / 5 heures affiché dans le widget est estimé à partir de tes relevés consécutifs (10 % tant qu'il n'y a pas assez de données).

## Structure du projet

```
run.py / run.bat / run.sh   entry point (menu)
launcher/                   menu code and translations (strings.py)
claude_usage.py             reads the quota, writes data/
server.py                   local widget server
web/                        the widget (HTML, CSS, JS; EN/FR)
windows/  linux/            scheduler install/uninstall scripts
data/                       your readings (git-ignored, never committed)
```

## Confidentialité

- Aucune donnée ne quitte ta machine, hormis la requête vers l'API d'Anthropic avec ton propre jeton.
- Le jeton est lu à l'exécution, jamais copié ni journalisé. `data/` et les identifiants sont dans `.gitignore`.
- Le serveur n'écoute que sur `127.0.0.1`.

## Remarques

- macOS : les scripts sont du Python/shell standard et peuvent fonctionner, mais l'installation du planificateur n'est pas testée (utilise cron à la main).
- Les tâches planifiées créées par les versions précédentes continuent de fonctionner.
- Non affilié à Anthropic.

## Licence

MIT – voir [LICENSE](LICENSE).
