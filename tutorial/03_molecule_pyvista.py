"""Tutorial step 3: draw a molecule in 3D with RDKit and PyVista.

Follows two short guides: RDKit "Getting Started in Python" (SMILES -> molecule ->
AddHs -> EmbedMolecule for 3D coordinates) and PyVista's basic plotting examples
(pv.Sphere, pv.Tube, Plotter.add_mesh). The camera calls at the end are the ones the
gesture controller uses later (azimuth, elevation, zoom, reset).

    python tutorial/03_molecule_pyvista.py              # caffeine
    python tutorial/03_molecule_pyvista.py "CCO"        # any SMILES, here ethanol
"""

import sys

import pyvista as pv
from rdkit import Chem
from rdkit.Chem import AllChem

COLORS = {"H": "white", "C": "dimgray", "N": "blue", "O": "red"}  # CPK colours

smiles = sys.argv[1] if len(sys.argv) > 1 else "CN1C=NC2=C1C(=O)N(C(=O)N2C)C"  # caffeine

# RDKit: read the SMILES, add hydrogens, and generate 3D coordinates.
mol = Chem.AddHs(Chem.MolFromSmiles(smiles))
AllChem.EmbedMolecule(mol, randomSeed=42)
AllChem.MMFFOptimizeMolecule(mol)
positions = mol.GetConformer().GetPositions()
positions -= positions.mean(axis=0)  # centre it so it spins around its middle

# PyVista: one sphere per atom, one tube per bond.
plotter = pv.Plotter(window_size=(900, 700))
plotter.set_background("black")
for atom, pos in zip(mol.GetAtoms(), positions):
    symbol = atom.GetSymbol()
    radius = 0.2 if symbol == "H" else 0.32
    plotter.add_mesh(pv.Sphere(radius=radius, center=pos), color=COLORS.get(symbol, "pink"), smooth_shading=True)
for bond in mol.GetBonds():
    a, b = positions[bond.GetBeginAtomIdx()], positions[bond.GetEndAtomIdx()]
    plotter.add_mesh(pv.Line(a, b).tube(radius=0.09), color="lightgray", smooth_shading=True)

plotter.add_text(f"{smiles}\nkeys: arrows rotate, +/- zoom, r reset", font_size=10)
plotter.reset_camera()
start = plotter.camera.copy()


# Camera control by keyboard, standing in for the hand gestures added in the main app.
def turn(azimuth: float = 0, elevation: float = 0) -> None:
    plotter.camera.azimuth += azimuth
    plotter.camera.elevation += elevation
    plotter.render()


def zoom(factor: float) -> None:
    plotter.camera.zoom(factor)
    plotter.render()


def reset() -> None:
    plotter.camera = start.copy()
    plotter.render()


plotter.add_key_event("Left", lambda: turn(azimuth=-10))
plotter.add_key_event("Right", lambda: turn(azimuth=10))
plotter.add_key_event("Up", lambda: turn(elevation=10))
plotter.add_key_event("Down", lambda: turn(elevation=-10))
plotter.add_key_event("plus", lambda: zoom(1.2))
plotter.add_key_event("minus", lambda: zoom(1 / 1.2))
plotter.add_key_event("r", reset)
plotter.show()
