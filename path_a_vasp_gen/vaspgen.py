"""
vaspgen — VASP输入文件生成器
从CIF/公式 → INCAR + POSCAR + POTCAR推荐 + KPOINTS
用法: python vaspgen.py --cif structure.cif
      python vaspgen.py --formula "Co3O4" --cell 8.0
"""

import sys
import re
import json
import argparse
import shutil
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

# ── Element database ──
# Common oxidation states, POTCAR recommendations, ENMAX values
ELEMENT_DATA = {
    "H":  {"enmax": 250, "potcar": "H", "valence": 1, "mass": 1.008},
    "Li": {"enmax": 140, "potcar": "Li_sv", "valence": 3, "mass": 6.941},
    "C":  {"enmax": 400, "potcar": "C", "valence": 4, "mass": 12.011},
    "N":  {"enmax": 400, "potcar": "N", "valence": 5, "mass": 14.007},
    "O":  {"enmax": 400, "potcar": "O", "valence": 6, "mass": 15.999},
    "F":  {"enmax": 400, "potcar": "F", "valence": 7, "mass": 18.998},
    "Na": {"enmax": 100, "potcar": "Na_sv", "valence": 9, "mass": 22.990},
    "Mg": {"enmax": 200, "potcar": "Mg_sv", "valence": 10, "mass": 24.305},
    "Al": {"enmax": 240, "potcar": "Al", "valence": 3, "mass": 26.982},
    "Si": {"enmax": 245, "potcar": "Si", "valence": 4, "mass": 28.086},
    "P":  {"enmax": 255, "potcar": "P", "valence": 5, "mass": 30.974},
    "S":  {"enmax": 260, "potcar": "S", "valence": 6, "mass": 32.065},
    "Cl": {"enmax": 260, "potcar": "Cl", "valence": 7, "mass": 35.453},
    "K":  {"enmax": 120, "potcar": "K_sv", "valence": 9, "mass": 39.098},
    "Ca": {"enmax": 150, "potcar": "Ca_sv", "valence": 10, "mass": 40.078},
    "Ti": {"enmax": 275, "potcar": "Ti_sv", "valence": 12, "mass": 47.867},
    "V":  {"enmax": 280, "potcar": "V_sv", "valence": 13, "mass": 50.942},
    "Cr": {"enmax": 285, "potcar": "Cr_pv", "valence": 14, "mass": 51.996},
    "Mn": {"enmax": 270, "potcar": "Mn_pv", "valence": 15, "mass": 54.938},
    "Fe": {"enmax": 290, "potcar": "Fe_pv", "valence": 16, "mass": 55.845},
    "Co": {"enmax": 290, "potcar": "Co", "valence": 17, "mass": 58.933},
    "Ni": {"enmax": 295, "potcar": "Ni_pv", "valence": 18, "mass": 58.693},
    "Cu": {"enmax": 295, "potcar": "Cu_pv", "valence": 19, "mass": 63.546},
    "Zn": {"enmax": 280, "potcar": "Zn", "valence": 20, "mass": 65.380},
    "Zr": {"enmax": 240, "potcar": "Zr_sv", "valence": 12, "mass": 91.224},
    "Nb": {"enmax": 250, "potcar": "Nb_pv", "valence": 13, "mass": 92.906},
    "Mo": {"enmax": 260, "potcar": "Mo_pv", "valence": 14, "mass": 95.950},
    "Ru": {"enmax": 260, "potcar": "Ru_pv", "valence": 16, "mass": 101.070},
    "Rh": {"enmax": 265, "potcar": "Rh_pv", "valence": 17, "mass": 102.906},
    "Pd": {"enmax": 250, "potcar": "Pd", "valence": 18, "mass": 106.420},
    "Ag": {"enmax": 250, "potcar": "Ag", "valence": 19, "mass": 107.868},
    "Pt": {"enmax": 260, "potcar": "Pt", "valence": 18, "mass": 195.084},
    "Au": {"enmax": 260, "potcar": "Au", "valence": 19, "mass": 196.967},
    "Ga": {"enmax": 280, "potcar": "Ga_d", "valence": 13, "mass": 69.723},
    "Ge": {"enmax": 280, "potcar": "Ge_d", "valence": 14, "mass": 72.630},
    "As": {"enmax": 275, "potcar": "As", "valence": 15, "mass": 74.922},
    "Se": {"enmax": 270, "potcar": "Se", "valence": 16, "mass": 78.971},
    "Br": {"enmax": 270, "potcar": "Br", "valence": 17, "mass": 79.904},
    "Rb": {"enmax": 100, "potcar": "Rb_sv", "valence": 9, "mass": 85.468},
    "Sr": {"enmax": 140, "potcar": "Sr_sv", "valence": 10, "mass": 87.620},
    "Y":  {"enmax": 220, "potcar": "Y_sv", "valence": 11, "mass": 88.906},
    "In": {"enmax": 250, "potcar": "In_d", "valence": 13, "mass": 114.818},
    "Sn": {"enmax": 250, "potcar": "Sn_d", "valence": 14, "mass": 118.710},
    "Sb": {"enmax": 250, "potcar": "Sb", "valence": 15, "mass": 121.760},
    "Te": {"enmax": 250, "potcar": "Te", "valence": 16, "mass": 127.600},
    "I":  {"enmax": 250, "potcar": "I", "valence": 17, "mass": 126.904},
    "Cs": {"enmax": 90,  "potcar": "Cs_sv", "valence": 9, "mass": 132.905},
    "Ba": {"enmax": 130, "potcar": "Ba_sv", "valence": 10, "mass": 137.327},
    "La": {"enmax": 220, "potcar": "La", "valence": 11, "mass": 138.905},
    "Ce": {"enmax": 230, "potcar": "Ce", "valence": 12, "mass": 140.116},
    "Hf": {"enmax": 250, "potcar": "Hf_pv", "valence": 12, "mass": 178.490},
    "Ta": {"enmax": 260, "potcar": "Ta_pv", "valence": 13, "mass": 180.948},
    "W":  {"enmax": 280, "potcar": "W_pv", "valence": 14, "mass": 183.840},
    "Re": {"enmax": 280, "potcar": "Re_pv", "valence": 15, "mass": 186.207},
    "Os": {"enmax": 290, "potcar": "Os_pv", "valence": 16, "mass": 190.230},
    "Ir": {"enmax": 290, "potcar": "Ir", "valence": 17, "mass": 192.217},
    "Hg": {"enmax": 240, "potcar": "Hg", "valence": 20, "mass": 200.590},
    "Pb": {"enmax": 240, "potcar": "Pb_d", "valence": 14, "mass": 207.200},
    "Bi": {"enmax": 250, "potcar": "Bi_d", "valence": 15, "mass": 208.980},
}


@dataclass
class VASPInput:
    """Container for generated VASP input files"""
    incar: str
    poscar: str
    potcar_recommendations: list[str]
    kpoints: str
    notes: list[str] = field(default_factory=list)


def parse_cif(cif_path: str) -> dict:
    """Minimal CIF parser — extract cell params and atomic positions."""
    text = Path(cif_path).read_text()
    result = {"elements": [], "positions": [], "cell_a": 1.0, "cell_b": 1.0,
              "cell_c": 1.0, "alpha": 90, "beta": 90, "gamma": 90}

    for line in text.split('\n'):
        # Cell parameters
        m = re.match(r'_cell_length_a\s+([\d.]+)', line)
        if m: result["cell_a"] = float(m.group(1))
        m = re.match(r'_cell_length_b\s+([\d.]+)', line)
        if m: result["cell_b"] = float(m.group(1))
        m = re.match(r'_cell_length_c\s+([\d.]+)', line)
        if m: result["cell_c"] = float(m.group(1))
        m = re.match(r'_cell_angle_alpha\s+([\d.]+)', line)
        if m: result["alpha"] = float(m.group(1))
        m = re.match(r'_cell_angle_beta\s+([\d.]+)', line)
        if m: result["beta"] = float(m.group(1))
        m = re.match(r'_cell_angle_gamma\s+([\d.]+)', line)
        if m: result["gamma"] = float(m.group(1))

    # Find atomic positions
    in_loop = False
    loop_keys = []
    for line in text.split('\n'):
        if '_atom_site_' in line and 'label' not in line.lower():
            continue
        if line.strip().startswith('_atom_site'):
            in_loop = True
            continue
        if in_loop and line.strip().startswith('_'):
            break
        if in_loop and line.strip():
            parts = line.split()
            if len(parts) >= 4:
                # Typical: label type_symbol x y z
                elem = parts[1] if len(parts) > 1 else parts[0]
                try:
                    x, y, z = float(parts[-3]), float(parts[-2]), float(parts[-1])
                    if re.match(r'^[A-Z][a-z]?$', elem):
                        result["elements"].append(elem)
                        result["positions"].append((x, y, z))
                except (ValueError, IndexError):
                    pass

    return result


def generate_poscar(elements: list[str], positions: list[tuple],
                    cell_a: float, cell_b: float, cell_c: float,
                    alpha: float = 90, beta: float = 90, gamma: float = 90,
                    comment: str = "Generated by vaspgen") -> str:
    """Generate POSCAR file."""
    # Count elements
    elem_counts = {}
    for e in elements:
        elem_counts[e] = elem_counts.get(e, 0) + 1
    unique_elems = list(elem_counts.keys())
    counts = [str(elem_counts[e]) for e in unique_elems]

    # Convert angles to radians for lattice vectors
    import math
    a_rad = math.radians(alpha)
    b_rad = math.radians(beta)
    g_rad = math.radians(gamma)

    # Lattice vectors (simplified for orthogonal/small-angle cases)
    # For general case, we'd need full matrix. Here we do orthogonal.
    if alpha == 90 and beta == 90 and gamma == 90:
        v1 = f"   {cell_a:.6f}    0.000000    0.000000"
        v2 = f"   0.000000    {cell_b:.6f}    0.000000"
        v3 = f"   0.000000    0.000000    {cell_c:.6f}"
    else:
        # Simplified non-orthogonal
        v1 = f"   {cell_a:.6f}    0.000000    0.000000"
        v2 = f"   {cell_b * math.cos(g_rad):.6f}    {cell_b * math.sin(g_rad):.6f}    0.000000"
        v3 = f"   {cell_c * math.cos(b_rad):.6f}    0.000000    {cell_c * math.sin(b_rad):.6f}"

    lines = [comment, "1.0", v1, v2, v3,
             "  " + "  ".join(unique_elems),
             "  " + "  ".join(counts),
             "Direct"]

    for e, (x, y, z) in zip(elements, positions):
        lines.append(f"  {x:.8f}  {y:.8f}  {z:.8f}")

    return "\n".join(lines)


def generate_incar(elements: list[str], calc_type: str = "optimization",
                   is_metal: bool = None, has_magnetism: bool = None,
                   solvent: bool = False) -> tuple[str, list[str]]:
    """Generate sensible INCAR with notes."""
    notes = []
    unique = list(set(elements))

    # Auto-detect metal/magnetism
    magnetic_elems = {"Fe", "Co", "Ni", "Mn", "Cr", "V", "Cu", "Ti"}
    if is_metal is None:
        is_metal = any(e in magnetic_elems or (
            e in ELEMENT_DATA and ELEMENT_DATA[e]["valence"] > 12) for e in unique)
    if has_magnetism is None:
        has_magnetism = any(e in magnetic_elems for e in unique)

    # Determine ENCUT
    encut_vals = [ELEMENT_DATA.get(e, {"enmax": 400})["enmax"] for e in unique]
    encut = int(max(encut_vals) * 1.3 / 10) * 10  # Round to nearest 10

    lines = []
    lines.append(f"# INCAR generated by vaspgen")
    lines.append(f"# Elements: {' '.join(unique)}")
    lines.append(f"SYSTEM = {'_'.join(unique)}")
    lines.append(f"ENCUT = {encut}")

    # Electronic convergence
    if is_metal:
        lines.append("ISMEAR = 1        # Methfessel-Paxton (metal)")
        lines.append("SIGMA = 0.2")
        notes.append("Metal detected -> ISMEAR=1. Verify with DOS check.")
    else:
        lines.append("ISMEAR = 0        # Gaussian smearing")
        lines.append("SIGMA = 0.05")

    lines.append("EDIFF = 1E-6")
    lines.append("PREC = Normal")

    # Magnetism
    if has_magnetism:
        lines.append("ISPIN = 2")
        mag_line = "MAGMOM = " + " ".join(
            ["5.0" if e in magnetic_elems else "0.6" for e in elements])
        lines.append(f"{mag_line}  # AUTO-GENERATED — verify per atom!")
        notes.append("MAGMOM auto-set. Verify initial magnetic moments for your system.")

    # Ionic optimization
    if calc_type == "optimization":
        lines.append("IBRION = 2")
        lines.append("NSW = 100")
        lines.append("EDIFFG = -0.02")
        lines.append("ISIF = 3         # cell+ions — change to 2 if surface slab")
        notes.append("ISIF=3 (cell+ions). For surface slabs, change to ISIF=2.")
    elif calc_type == "singlepoint":
        lines.append("NSW = 0")
        lines.append("IBRION = -1")

    # Van der Waals
    lines.append("IVDW = 12         # DFT-D3 with Becke-Johnson damping")

    # Solvent
    if solvent:
        lines.append("LSOL = .TRUE.")
        notes.append("LSOL=TRUE set. Ensure VASPsol is compiled.")

    # Performance
    lines.append("LREAL = Auto")
    lines.append("LWAVE = .FALSE.")
    lines.append("LCHARG = .FALSE.")

    return "\n".join(lines), notes


def generate_kpoints(cell_a: float, cell_b: float, cell_c: float,
                     is_metal: bool = False) -> str:
    """Generate KPOINTS based on cell dimensions."""
    density = 0.04 if is_metal else 0.05  # per Angstrom
    k1 = max(1, int(cell_a * density) if cell_a > 0 else 1)
    k2 = max(1, int(cell_b * density) if cell_b > 0 else 1)
    k3 = max(1, int(cell_c * density) if cell_c > 0 else 1)

    return f"""Automatic mesh
0
Gamma
{k1} {k2} {k3}
0 0 0"""


def recommend_potcar(elements: list[str], functional: str = "PBE") -> list[str]:
    """Recommend POTCAR types for each element."""
    unique = list(dict.fromkeys(elements))  # Preserve order, deduplicate
    result = []
    for e in unique:
        data = ELEMENT_DATA.get(e, {"potcar": e})
        pot = data["potcar"]
        result.append(f"POTCAR_{functional}/{pot}")
    return result


def generate_job_script(nproc: int = 4, walltime: str = "24:00:00",
                        job_name: str = "vasp_job") -> str:
    """Generate SLURM job script."""
    return f"""#!/bin/bash
#SBATCH -J {job_name}
#SBATCH -N 1
#SBATCH --ntasks-per-node={nproc}
#SBATCH -t {walltime}
#SBATCH --partition=compute

module load vasp/6.4.3

mpirun -np {nproc} vasp_std > vasp.log

# Post-run validation
if grep -q "reached required accuracy" OUTCAR; then
    echo "JOB COMPLETE: Electronic convergence reached."
else
    echo "WARNING: Check OUTCAR for convergence."
fi
"""


def generate_all(cif_path: str = None, formula: str = None,
                 calc_type: str = "optimization",
                 output_dir: str = None,
                 with_job_script: bool = True) -> dict:
    """Generate all VASP input files."""
    notes = []

    if cif_path:
        data = parse_cif(cif_path)
        elements = data["elements"]
        positions = data["positions"]
        cell_a, cell_b, cell_c = data["cell_a"], data["cell_b"], data["cell_c"]
        alpha, beta, gamma = data["alpha"], data["beta"], data["gamma"]
        if not elements:
            return {"error": "No atomic positions found in CIF"}
    elif formula:
        # Parse formula: "Co3O4" -> ["Co","Co","Co","O","O","O","O"]
        elements = []
        for m in re.finditer(r'([A-Z][a-z]?)(\d*)', formula):
            elem, count = m.group(1), m.group(2)
            count = int(count) if count else 1
            elements.extend([elem] * count)
        # Simple cubic cell
        cell_a = cell_b = cell_c = 10.0
        alpha = beta = gamma = 90
        # Generate fractional positions (simple cubic)
        n = len(elements)
        positions = [(i/n, i/n, i/n) for i in range(n)]
        notes.append("WARNING: Simple cubic guess. Use --cif for real structure.")
    else:
        return {"error": "Need --cif or --formula"}

    poscar = generate_poscar(elements, positions, cell_a, cell_b, cell_c,
                             alpha, beta, gamma)
    incar, incar_notes = generate_incar(elements, calc_type)
    notes.extend(incar_notes)
    kpoints = generate_kpoints(cell_a, cell_b, cell_c)
    potcars = recommend_potcar(elements)

    result = {
        "incar": incar,
        "poscar": poscar,
        "kpoints": kpoints,
        "potcar_recommendations": potcars,
        "potcar_build_cmd": f"cat {' '.join(potcars)} > POTCAR",
        "notes": notes,
    }

    # Write files if output_dir specified
    if output_dir:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / "INCAR").write_text(incar)
        (out / "POSCAR").write_text(poscar)
        (out / "KPOINTS").write_text(kpoints)
        (out / "POTCAR_INFO.txt").write_text(
            "Build POTCAR with:\n  " + result["potcar_build_cmd"] + "\n")
        (out / "VASPGEN_NOTES.txt").write_text("\n".join(notes))
        if with_job_script:
            job = generate_job_script()
            (out / "run_vasp.job").write_text(job)
        result["output_dir"] = str(out)

    return result


def main():
    parser = argparse.ArgumentParser(description="VASP input file generator")
    parser.add_argument("--cif", help="CIF file path")
    parser.add_argument("--formula", help="Chemical formula (e.g. Co3O4)")
    parser.add_argument("--calc", choices=["optimization", "singlepoint"],
                        default="optimization")
    parser.add_argument("--output", "-o", help="Output directory")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    if not args.cif and not args.formula:
        parser.error("Need --cif or --formula")

    result = generate_all(args.cif, args.formula, args.calc, args.output)

    if "error" in result:
        print(f"Error: {result['error']}", file=sys.stderr)
        sys.exit(1)

    if args.json or not args.output:
        # Print to stdout
        for fname in ["incar", "poscar", "kpoints"]:
            print(f"\n{'='*60}")
            print(f"=== {fname.upper()} ===")
            print(f"{'='*60}")
            print(result[fname])
        print(f"\n{'='*60}")
        print("=== POTCAR BUILD COMMAND ===")
        print(f"{'='*60}")
        print(result["potcar_build_cmd"])
        if result.get("notes"):
            print(f"\n{'='*60}")
            print("=== NOTES ===")
            for n in result["notes"]:
                print(f"  * {n}")

    if args.output:
        print(f"Files written to {args.output}/")
        for f in ["INCAR", "POSCAR", "KPOINTS", "POTCAR_INFO.txt", "VASPGEN_NOTES.txt"]:
            print(f"  {f}")
        for n in result.get("notes", []):
            print(f"  NOTE: {n}")


if __name__ == "__main__":
    main()
