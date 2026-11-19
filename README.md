# Communication au chevet

Prototype de communication assistée pour une soutenance en situation simulée. La webcam intégrée d’un PC estime le regard de l’œil droit. Un clin d’œil gauche confirme la phrase survolée. La phrase s’affiche dans l’onglet Communication et une voix locale la prononce.

## Installation

Utiliser Python 3.12 et un environnement graphique avec Tkinter. Ouvrir un terminal dans ce dossier.

```shell
python -m venv .venv
```

Activer l’environnement avec `source .venv/bin/activate` sur Linux ou macOS, ou `.\.venv\Scripts\Activate.ps1` dans PowerShell. Si l’activation PowerShell est désactivée, appeler directement `.\.venv\Scripts\python.exe` à la place de `python`.

```shell
python -m pip install -r requirements.txt
python telecharger_modele.py
python main.py
```

Le script télécharge le [modèle officiel Face Landmarker](https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker/python) dans `modeles/`. Une fois le modèle et les bibliothèques installés, le suivi s’exécute hors ligne. `--model` accepte un chemin vers un modèle déjà disponible et `--camera 1` sélectionne un autre périphérique.

Pour la voix française hors ligne :

- **Debian et Ubuntu** · installer `python3-tk` si Tkinter manque, puis `espeak-ng` pour la voix. Tester avec `espeak-ng -v fr "J’ai mal"`.
- **Windows** · installer une voix de synthèse française disponible pour Windows PowerShell et System.Speech.
- **macOS** · rendre disponible la voix française Thomas dans Réglages système, puis tester `say -v Thomas "J’ai mal"`.

`python main.py --muet` désactive l’audio pour les tests et la simulation fonctionne sans télécharger MediaPipe ou son modèle. Démarrer avec `--wink-min 0.15 --wink-max 0.8` pour les réglages par défaut, en secondes.

## Démonstration sans webcam

1. Lancer `python main.py --muet`. En mode **Simulation**, déplacer la souris dans la grille pour simuler le regard. Cliquer sur la cible ou utiliser Espace lorsque la grille a le focus pour produire un signal de clin d’œil simulé. Dans **Communication**, vérifier la phrase affichée.
2. Ouvrir **Évaluation**, puis **Cas simulés**. Vérifier les quatre résultats. **Exporter CSV** enregistre le résumé et le détail.
3. Lancer **Sélection guidée**. Choisir les phrases demandées. Dix essais sont proposés, avec dix secondes par essai. Chaque essai retient la première sélection ou une absence de réponse au terme du délai. Pour tester un échec, sélectionner volontairement une autre phrase.
4. Lancer **Observation libre**, puis rester une minute sans sélectionner. Pour vérifier le compteur en simulation, provoquer un clic intentionnel. Exporter les résultats avant de lancer une autre session.
5. Répéter avec quatre phrases et vérifier la colonne `source` de chaque CSV. Les mesures issues de la simulation ne permettent pas d’estimer les performances avec une webcam.

## Démonstration avec une webcam

1. Placer l’écran face à l’utilisateur, avec une lumière douce devant le visage. Lancer `python main.py`, choisir deux phrases puis **Webcam**.
2. Regarder chaque cible rouge avec les deux yeux ouverts jusqu’à ce qu’elle change de position. Le mode à deux phrases calibre le déplacement horizontal avec deux cibles. Le mode à quatre phrases calibre les deux axes avec les quatre zones et le centre.
3. Regarder un bouton jusqu’à voir son contour actif. Faire un clin d’œil gauche pendant que l’œil droit reste ouvert, puis rouvrir l’œil. Vérifier que la sélection correspond au bouton survolé au début du geste.
4. Ouvrir **Évaluation**. La calibration redémarre car la position de la grille est propre à chaque écran. Recalibrer aussi si le PC, la fenêtre ou l’utilisateur change de position. Lancer une sélection guidée, puis une observation libre. Si les quatre cibles restent difficiles à distinguer, reprendre les essais à deux phrases.
5. Vérifier la voix sur la machine de la soutenance et la disponibilité du périphérique. Si le suivi disparaît, recentrer le visage avant de poursuivre. Les clignements des deux yeux et les gestes interrompus par une perte de suivi annulent la sélection.

## Organisation et vérification

- `vision.py` · Capture et inférence dans un fil séparé. Mesure de l’iris droit et de l’ouverture des deux yeux sur les images brutes.
- `logique.py` · Calibration, lissage, détection de la cible et validation du geste. Le même moteur reçoit les signaux webcam et les signaux simulés.
- `interface.py` · Écrans Tkinter, calibration guidée, communication et commandes d’évaluation.
- `evaluation.py` · Sessions, cas simulés, métriques et export CSV. Le taux de réussite inclut les essais sans réponse dans son dénominateur. Le temps médian porte sur les choix corrects.
- `audio_local.py` · Synthèse vocale locale, selon le système.

```shell
python -m unittest discover -s tests -v
```

Configuration vérifiée durant le développement · Debian 13 x86_64, Python 3.12.14, Tk 9.0.4, MediaPipe 0.10.32 et OpenCV 4.13.0. Tests de logique et de métriques exécutés. Parcours graphique simulé vérifié sous Xvfb, avec affichage d’une phrase, session guidée, observation avec échéance accélérée, quatre cas simulés et export CSV. Chargement du modèle et inférence CPU vérifiés sur une image sans visage. OpenCV a échoué à ouvrir l’index 0 et aucun périphérique vidéo n’était exposé. L’essai avec une vraie webcam, la calibration en conditions réelles et l’écoute de la voix restent à vérifier sur le PC de la soutenance.

Les images de la webcam sont traitées en mémoire. Les exports contiennent les phrases de démonstration et les résultats des essais. Utiliser des volontaires consentants pour l’évaluation technique. En atelier ou en service, l’appel infirmier reste indépendant du prototype.
