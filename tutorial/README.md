# Tutorial code (Milestone M1)

Code from the official tutorials of the libraries the app in `handson/` is built on. Step 0
is Google's own tutorial notebook; steps 1–3 take the same library calls one at a time and
add the pieces our project needs. Each script runs on its own.

| Step | Script | What it does | Tutorial it follows |
|---|---|---|---|
| 0 | `00_mediapipe_notebook.py` | Google's hand landmarker notebook, run as a script: finds both hands in a photo and draws them | MediaPipe [hand_landmarker.ipynb](https://github.com/google-ai-edge/mediapipe-samples/blob/main/examples/hand_landmarker/python/hand_landmarker.ipynb) |
| 1 | `01_hand_landmarker_image.py` | Finds the 21 hand landmarks in one photo and prints them | MediaPipe [Hand landmarks detection guide for Python](https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker/python) (IMAGE mode) |
| 2 | `02_hand_landmarker_webcam.py` | Tracks a hand live from the webcam, draws the skeleton, shows pinch distance and fingers up | Same guide, VIDEO mode with OpenCV webcam capture |
| 3 | `03_molecule_pyvista.py` | Builds caffeine (or any SMILES) in 3D and rotates/zooms/resets the camera with the keyboard | RDKit [Getting Started in Python](https://www.rdkit.org/docs/GettingStartedInPython.html) and PyVista [plotting examples](https://docs.pyvista.org/examples/) |

## Where the code came from

- **Canned tutorial code:** step 0 is Google's notebook unchanged except for the Colab-only
  parts (see the top of the file). The library calls in steps 1–3 are the ones the guides
  show: `HandLandmarker` from options, `mp.Image`, `detect()` / `detect_for_video()`,
  `hand_landmarks` and `handedness`; RDKit `MolFromSmiles` → `AddHs` → `EmbedMolecule`;
  PyVista `Plotter`, `add_mesh`, `camera`.
- **Added for our project:** webcam capture and mirroring with OpenCV, drawing the skeleton
  from the landmark diagram in the guide, the pinch distance divided by palm size, the
  fingers-up count that tells FIST / OPEN / PINCH apart, and keyboard camera control that
  stands in for the gestures.
- **How we made it:** steps 1–3 were written with a generative AI assistant (Claude) while
  we went through the guides and Google's notebook. We ran every step, changed what was
  needed to make it run on our Macs (for example the RGBA image in step 0 and choosing an
  iPhone camera), and had the code explained line by line.

The same ideas are used in the app: step 2 corresponds to `handson/tracking.py` and
`handson/gestures.py`, step 3 to `handson/molecule.py` and the camera calls in
`handson/controller.py`. The tutorial scripts were put together for M1, after the first
version of the app; they keep each library step small enough to explain on its own.

## Run

Set up the environment and download the model as in the main [README](../README.md), then
from the repository root:

```bash
curl -L -o tutorial/woman_hands.jpg https://storage.googleapis.com/mediapipe-tasks/hand_landmarker/woman_hands.jpg
python tutorial/00_mediapipe_notebook.py tutorial/woman_hands.jpg   # the notebook's test photo
python tutorial/01_hand_landmarker_image.py            # one webcam photo (or pass an image path)
python tutorial/02_hand_landmarker_webcam.py           # live tracking, Q or Esc to quit
python tutorial/03_molecule_pyvista.py                 # caffeine; arrows, +/-, R
python tutorial/03_molecule_pyvista.py "CCO"           # any SMILES, here ethanol
```

Step 0 saves `tutorial/step0_result.jpg` and step 1 saves `tutorial/step1_result.jpg`
(both git-ignored, like the downloaded test photo).

To use another camera (for example an iPhone through Continuity Camera), set its number:
`HANDSON_CAMERA=1 python tutorial/02_hand_landmarker_webcam.py`.

In step 2, try a fist (fingers up 0), an open palm (4), and touching thumb and index tips
(pinch below 0.35). The same three shapes drive rotate, reset and zoom in the app.
