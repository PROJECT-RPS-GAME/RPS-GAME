# Rock Paper Scissors

Camera-controlled Rock Paper Scissors with a browser interface. The Python
application handles the camera, hand tracking, gesture recognition, match
rules, scoring, and round history. All browser UI files are kept in `web/`.

## Requirements

- Python 3.10 or newer
- A webcam
- A modern browser

Install the Python dependencies from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Run

```powershell
python main.py
```

The application starts at `http://127.0.0.1:8000` and opens the page in your
browser. Use `--no-browser` to keep it from opening a browser, `--port 8001` to
choose another port, or `--camera 1` to select a different camera.

The hand-tracking model is downloaded to `data/hand_landmarker.task` the first
time the game starts. Round results are saved in `data/game_history.json`.

## Project layout

- `main.py`: starts and shuts down the web server and camera worker
- `src/`: camera input, hand tracking, gestures, game controller, scoring, rules,
  history, rendering, audio configuration, and server
- `assets/`: icons and sound effects
- `data/`: hand-tracking model and saved game history
- `tests/`: gesture, rules, score, game-flow, camera, and server tests
- `web/`: HTML, CSS, and JavaScript for the browser interface

## Tests

```powershell
python -m unittest discover -s tests -v
```
