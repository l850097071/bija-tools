# bija-tools — Computational Chemistry Research Toolkit

**Five tools, one pipeline. From literature to calculation report.**

```bash
pip install -e .
bija-tools litsearch "CO2 reduction on Cu catalysts"
bija-tools vaspgen --formula "Co3O4" -o my_job
bija-tools gate my_job --preset vasp
# ... sbatch submit ...
bija-tools outcarp OUTCAR
```

---

## Pipeline

```
litsearch ──→ vaspgen ──→ gate ──→ [sbatch] ──→ outcarp
(literature)  (generate)  (validate)  (submit)    (report)
```

---

## Tools

| Tool | What | Presets |
|------|------|---------|
| **vaspgen** | CIF/formula → INCAR+POSCAR+KPOINTS+POTCAR+job script | 59 elements, auto-detects metal/magnetism |
| **gate** | 10-gate pre-submit HPC validation | VASP, PWmat, Gaussian, Quick |
| **litsearch** | Semantic Scholar → structured literature review | — |
| **outcarp** | OUTCAR parser → calculation report | Energy, forces, timing, convergence |
| **recipes** | Searchable VASP parameter database | CO₂ adsorption, NEB, phonon, VASPsol, band structure, Bader, bulk opt, DFT+U |

---

## Quick Start

```bash
# Generate VASP inputs for Co3O4
bija-tools vaspgen --formula "Co3O4" -o co3o4_job

# Validate before HPC submission
bija-tools gate co3o4_job --preset vasp

# Search literature
bija-tools litsearch "single atom catalyst CO2 reduction" --years 2024-2026

# Parse calculation results
bija-tools outcarp OUTCAR
```

---

## Why This Exists

78% of computational researchers spend 10+ hours/week on workflow management. Most errors are preventable: wrong POTCAR, missing dipole correction, unconverged KPOINTS, forgotten vdW.

These tools catch those errors before they waste GPU hours.

---

## Requirements

Python 3.9+. Flask (for web UI). No other dependencies. No VASP license needed (generator outputs text files, validator checks structure).

---

Built by Bija-monetization. MIT license.
