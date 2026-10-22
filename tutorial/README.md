# Tutorial code (Milestone M1)

The code we wrote while working through the tutorials the project is built on, before
writing the app in `handson/`. Each step is one script that runs on its own.

| Step | Script | What it does | Tutorial it follows |
|---|---|---|---|
| 1 | `01_hand_landmarker_image.py` | Finds the 21 hand landmarks in one photo and prints them | MediaPipe [Hand landmarks detection guide for Python](https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker/python) (IMAGE mode) |
| 2 | `02_hand_landmarker_webcam.py` | Tracks a hand live from the webcam, draws the skeleton, shows pinch distance and fingers up | Same guide, VIDEO mode with OpenCV webcam capture |
| 3 | `03_molecule_pyvista.py` | Builds caffeine (or any SMILES) in 3D and rotates/zooms/resets the camera with the keyboard | RDKit [Getting Started in Python](https://www.rdkit.org/docs/GettingStartedInPython.html) and PyVista [plotting examples](https://docs.pyvista.org/examples/) |

## Where the code came from

- **From the tutorials (canned code):** creating the `HandLandmarker` from options, building an
  `mp.Image`, `detect()` / `detect_for_video()`, reading `hand_landmarks` and `handedness`; RDKit
  `MolFromSmiles` → `AddHs` → `EmbedMolecule`; PyVista `Plotter`, `add_mesh`, `camera`.
- **What we added:** webcam capture and mirroring with OpenCV, drawing the skeleton ourselves
  (from the landmark diagram in the guide), the pinch distance normalized by palm size, the
  fingers-up count used to tell FIST / OPEN / PINCH apart, and keyboard camera control that
  stands in for the gestures.
- We used a generative AI assistant (Claude) to help explain the APIs and fix errors while
  following the guides.

What we learned here went into the app: step 2 became `handson/tracking.py` and
`handson/gestures.py`, step 3 became `handson/molecule.py` and the camera calls in
`handson/controller.py`.

## Run

Set up the environment and download the model as in the main [README](../README.md), then
from the repository root:

```bash
python tutorial/01_hand_landmarker_image.py            # one webcam photo (or pass an image path)
python tutorial/02_hand_landmarker_webcam.py           # live tracking, Q or Esc to quit
python tutorial/03_molecule_pyvista.py                 # caffeine; arrows, +/-, R
python tutorial/03_molecule_pyvista.py "CCO"           # any SMILES, here ethanol
```

Step 1 saves `tutorial/step1_result.jpg` with the landmarks drawn (git-ignored).

In step 2, try a fist (fingers up 0), an open palm (4), and touching thumb and index tips
(pinch below 0.35). The same three shapes drive rotate, reset and zoom in the app.
