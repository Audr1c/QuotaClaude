# Claude Usage Tracker

Relève ton quota Claude (fenêtre de 5 heures et fenêtre de 7 jours : % utilisé et heure de reset) toutes les 10 minutes dans `data/usage.csv`, et l'affiche dans un widget web local à deux vues (Détaillé / Compact) avec un bouton « Relever » pour forcer un relevé.

<p align="center">
  <img src="docs/screenshot-detail.png" alt="Vue détaillée : jauge 5 heures et jauge 7 jours" width="640"><br>
  <img src="docs/screenshot-compact.png" alt="Vue compacte : deux anneaux concentriques" width="300">
  <img src="docs/screenshot-detail-dark.png" alt="Thème sombre avec la répartition par produit" width="300">
</p>

*Captures réalisées avec des données fictives.*

> Projet indépendant, **non affilié à Anthropic**. « Claude » est une marque d'Anthropic. L'outil s'appuie sur un endpoint non documenté qui peut changer sans préavis (voir [Limites](#limites)).

## Prérequis

- Télécharger le dépôt (bouton **Code → Download ZIP**, ou `git clone`). Il n'y a rien à compiler ni à installer.
- Python 3.8+ (bibliothèque standard uniquement, rien à `pip install`).
- Claude Code installé et connecté avec un abonnement Pro/Max (pas une clé API).
- Le jeton OAuth est lu dans `~/.claude/.credentials.json` (Windows : `%USERPROFILE%\.claude\.credentials.json`).
  - `CLAUDE_CONFIG_DIR` est respecté s'il est défini.
  - `CLAUDE_USAGE_TOKEN` (variable d'environnement) remplace le fichier.
- **macOS** : non pris en charge pour l'instant (non testé ; Claude Code y range en général ses identifiants dans le Trousseau, pas dans ce fichier). Windows et Linux uniquement.
- Le jeton expire et c'est Claude Code qui le rafraîchit à son ouverture. Si tu n'ouvres pas Claude Code pendant longtemps, les relevés échouent (erreur 401/403 dans `data/tracker.log`) jusqu'à la prochaine ouverture.

## Démarrage rapide

### Windows

Le Planificateur de tâches joue le rôle de cron.

```bat
:: Premier relevé + tests + ouverture du widget
windows\releve_maintenant.bat

:: Installer le relevé automatique (toutes les 10 min)
windows\installer_tache.bat

:: Variantes : autre intervalle, et/ou serveur du widget lancé à l'ouverture de session
windows\installer_tache.bat -Minutes 15
windows\installer_tache.bat -AvecServeur
windows\installer_tache.bat -Minutes 15 -AvecServeur

:: Ouvrir le widget (http://127.0.0.1:8765/)
windows\ouvrir_widget.bat

:: Désinstaller (data\ est conservé)
windows\desinstaller_tache.bat
```

Les tâches créées s'appellent `Claude Usage Tracker` et `Claude Usage Server`. Il faut `pythonw.exe` dans le PATH (pas l'alias du Microsoft Store).

### Linux

Systemd (timer utilisateur) si disponible, sinon repli sur crontab.

```bash
chmod +x linux/*.sh        # une fois (ou lance les scripts avec bash)

# Premier relevé + tests + lancement du serveur et du navigateur
./linux/releve_maintenant.sh

# Installer le relevé automatique (toutes les 10 min)
./linux/installer_tache.sh

# Variantes : MINUTES en argument, et/ou serveur du widget au démarrage
./linux/installer_tache.sh 15
./linux/installer_tache.sh --avec-serveur
./linux/installer_tache.sh 15 --avec-serveur

# Ouvrir le widget (http://127.0.0.1:8765/)
./linux/ouvrir_widget.sh

# Désinstaller (data/ est conservé)
./linux/desinstaller_tache.sh
```

Vérifier : `systemctl --user list-timers` (ou `crontab -l` en repli). Pour que le timer tourne sans session ouverte : `loginctl enable-linger $USER`. Avec crontab, `MINUTES` doit être entre 1 et 59.

## Structure du projet

```
claude-usage-tracker/
├── LICENSE                licence MIT
├── .gitignore             exclut data/ (tes données) et tout fichier de secrets
├── .gitattributes         fins de ligne fixes (.sh en LF, .bat/.ps1 en CRLF)
├── claude_usage.py        un relevé : appelle l'API, écrit CSV + JSON, estime le ratio 5 h -> semaine
├── server.py              serveur local (127.0.0.1:8765) : sert web/ et data/, POST /api/refresh
├── test_claude_usage.py   tests unitaires hors ligne + un test réel de l'API si les identifiants existent
├── web/
│   ├── index.html         page du widget
│   ├── css/style.css      styles
│   └── js/
│       ├── model.js       calculs de rythme (aucun affichage)
│       ├── gauge.js       dessin SVG des jauges
│       ├── views.js       vues Détaillé et Compact
│       └── app.js         chargement des données, bascule de vue, bouton Relever
├── docs/                  captures d'écran du README (données fictives)
├── windows/               .bat + installer_tache.ps1 (Planificateur de tâches)
├── linux/                 scripts .sh (systemd utilisateur / crontab)
└── data/                  généré automatiquement, ignoré par Git (données personnelles)
    ├── usage.csv          historique complet, une ligne par relevé
    ├── latest.json        dernier état + historique récent (8 jours) + ratio estimé
    ├── latest.js          même contenu, lisible par la page ouverte en file://
    ├── last_response.json réponse brute de l'API (debug)
    ├── tracker.log        journal des relevés (la tâche tourne sans console)
    └── server.log         journal du serveur (écrit par les scripts Linux)
```

## Le widget

**Jauge 5 h (bleue)**
- Repère bleu : où tu en serais en dépensant à rythme régulier sur les 5 h.
- Repère orange : jusqu'où tu peux aller sur cette fenêtre en restant au rythme de la semaine.

**Jauge 7 jours (orange)**
- Repère orange : part de la semaine déjà écoulée.

**Vue Compact** : anneaux concentriques, extérieur = semaine, intérieur = 5 h.

**Répartition de la semaine** : menu déroulant, fermé par défaut, qui détaille la part de chaque produit (Claude Code, Chats, Cowork…) dans ce que tu as consommé, avec l'équivalent en points de quota.

**Bouton « Relever »** : ne fonctionne que si la page est ouverte via le serveur local (`ouvrir_widget`). Il est désactivé quand `index.html` est ouvert directement comme fichier, car une page web ne peut pas lancer un script elle-même. Dans ce mode, le widget affiche quand même les données de `data/latest.js`.

## Le ratio 5 h -> semaine

On ne sait pas combien de % de la semaine coûte une fenêtre de 5 h pleine. Au départ, le projet suppose **10 %**. Ensuite le ratio est estimé automatiquement depuis l'historique : on compare la hausse du % 5 h et celle du % 7 j entre relevés consécutifs situés dans les mêmes fenêtres (sans reset entre les deux). L'estimation remplace l'hypothèse dès qu'au moins 20 points de 5 h cumulés ont été observés. La valeur utilisée, et son origine (estimée ou par défaut), s'affichent en bas du widget.

## Confidentialité et sécurité

- **Le jeton** est lu localement (`~/.claude/.credentials.json` ou `CLAUDE_USAGE_TOKEN`) et envoyé uniquement à `api.anthropic.com`, dans l'en-tête `Authorization`. Il n'est ni écrit dans `data/`, ni journalisé.
- **Aucune dépendance, aucune télémétrie** : bibliothèque standard Python seulement ; la page web n'appelle aucun service externe (pas de CDN, pas de police distante).
- **Tes données restent chez toi** : tout est écrit dans `data/`, que `.gitignore` exclut. Évite de partager `data/last_response.json` (réponse brute de l'API, qui peut contenir des infos de compte) si tu ouvres un ticket.
- **Le serveur local** n'écoute que sur `127.0.0.1`, ne sert que `web/` et `data/latest.*`, et refuse les requêtes dont l'en-tête `Host` ou `Origin` n'est pas local (protection contre le DNS rebinding et les requêtes depuis un autre site).
- Le code est court (quelques centaines de lignes) : relis `claude_usage.py` avant de lui confier ton jeton, c'est le seul fichier qui le manipule.

## Limites

- L'endpoint `api.anthropic.com/api/oauth/usage` n'est pas documenté : il peut changer ou disparaître sans préavis.
- Le jeton expire (voir Prérequis) : pas de relevé tant que Claude Code n'a pas été rouvert.
- Le serveur écoute uniquement sur `127.0.0.1` : rien n'est exposé sur le réseau.

## Licence

[MIT](LICENSE) : tu peux utiliser, copier, modifier et redistribuer ce projet librement, à condition de conserver la mention de copyright.
