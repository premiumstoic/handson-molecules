"""Build molecules with RDKit and draw them as ball-and-stick models in PyVista."""

from dataclasses import dataclass

import numpy as np
import pyvista as pv
from rdkit import Chem
from rdkit.Chem import AllChem

MOLECULES = {
    "caffeine": "CN1C=NC2=C1C(=O)N(C(=O)N2C)C",
    "aspirin": "CC(=O)OC1=CC=CC=C1C(=O)O",
}

# CPK colours; anything not listed is drawn pink so it stands out.
ELEMENT_COLORS = {"H": "#f0f0f0", "C": "#505050", "N": "#3050f8", "O": "#ff0d0d", "S": "#ffff30", "P": "#ff8000"}
FALLBACK_COLOR = "#ff69b4"
ATOM_RADIUS = {"H": 0.2}
DEFAULT_ATOM_RADIUS = 0.32
BOND_RADIUS = 0.09
BOND_COLOR = "#b0b0b0"


@dataclass
class Molecule:
    name: str
    symbols: list[str]
    positions: np.ndarray            # (N, 3) in Angstrom
    bonds: list[tuple[int, int, float]]  # (atom a, atom b, bond order)


def from_smiles(name: str, smiles: str, seed: int = 42) -> Molecule:
    """Generate 3D coordinates (with hydrogens) from a SMILES string."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Invalid SMILES for {name}: {smiles}")
    mol = Chem.AddHs(mol)
    if AllChem.EmbedMolecule(mol, randomSeed=seed) != 0:
        raise RuntimeError(f"RDKit could not generate 3D coordinates for {name}")
    AllChem.MMFFOptimizeMolecule(mol)
    positions = mol.GetConformer().GetPositions()
    positions = positions - positions.mean(axis=0)  # centre on the origin so rotation looks natural
    return Molecule(
        name=name,
        symbols=[atom.GetSymbol() for atom in mol.GetAtoms()],
        positions=positions,
        bonds=[(b.GetBeginAtomIdx(), b.GetEndAtomIdx(), b.GetBondTypeAsDouble()) for b in mol.GetBonds()],
    )


def load(name: str) -> Molecule:
    if name not in MOLECULES:
        raise KeyError(f"Unknown molecule '{name}'. Choose from: {', '.join(MOLECULES)}")
    return from_smiles(name, MOLECULES[name])


def add_to_plotter(plotter: pv.Plotter, molecule: Molecule) -> None:
    """Draw atoms as spheres and bonds as cylinders (one merged mesh per colour)."""
    by_element: dict[str, list[pv.PolyData]] = {}
    for symbol, center in zip(molecule.symbols, molecule.positions):
        radius = ATOM_RADIUS.get(symbol, DEFAULT_ATOM_RADIUS)
        by_element.setdefault(symbol, []).append(pv.Sphere(radius=radius, center=center))
    for symbol, spheres in by_element.items():
        plotter.add_mesh(pv.merge(spheres), color=ELEMENT_COLORS.get(symbol, FALLBACK_COLOR), smooth_shading=True)

    # TODO (stretch): draw double bonds as two thinner parallel cylinders.
    cylinders = []
    for a, b, _order in molecule.bonds:
        start, end = molecule.positions[a], molecule.positions[b]
        cylinders.append(pv.Cylinder(center=(start + end) / 2, direction=end - start,
                                     radius=BOND_RADIUS, height=float(np.linalg.norm(end - start))))
    if cylinders:
        plotter.add_mesh(pv.merge(cylinders), color=BOND_COLOR, smooth_shading=True)
