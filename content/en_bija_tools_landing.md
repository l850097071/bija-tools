# bija-tools: A CLI Toolkit That Saves Computational Chemists 100+ Hours/Year

**pip install git+https://github.com/l850097071/bija-tools.git**

---

I've spent 5 years doing DFT calculations. Here's what I learned: **most of our time isn't spent doing science. It's spent fighting tools.**

- Copying INCAR parameters from senior students (not knowing which are wrong)
- Getting POTCAR element order backwards (finding out 1 month later)
- Forgetting dipole corrections (reviewers catch it immediately)
- `grep`-ing through 500MB OUTCAR files like it's 1995

Last month I finally automated all of this into a single CLI tool. Sharing it free and open source.

## What It Does

### 1. Auto-generate VASP inputs (`vaspgen`)
```bash
bija-tools vaspgen --formula "Co3O4" -o my_job
```
→ Outputs INCAR, POSCAR, KPOINTS, and job script in one command. Auto-detects magnetic elements and sets ISPIN/MAGMOM. 59 elements supported.

### 2. Pre-submit validation (`gate`)
```bash
bija-tools sbatch run_vasp.job
```
→ Runs **10 gate checks** before submitting: POTCAR mismatch? KPOINTS too sparse? Missing vdW correction? **Blocked before wasting GPU hours.**

### 3. OUTCAR parser (`outcarp`)
```bash
bija-tools outcarp OUTCAR
```
→ Parses convergence status, energies, forces, and timing into a human-readable report. Batch mode watches directories for completed jobs.

### 4. Literature search (`litsearch`)
```bash
bija-tools litsearch "CO2 reduction on metal oxides"
```
→ Semantic Scholar API → structured literature review with thematic grouping.

### 5. Full pipeline in one command
```bash
bija-tools pipeline "CO2 reduction" --formula Co3O4 -o job
```
→ Literature search → generate inputs → validate. 3 steps, 1 command.

## 8 Built-in Calculation Recipes

Each recipe includes **complete INCAR parameters + pitfall checklist**:

| # | Recipe | Key Pitfall Covered |
|---|--------|---------------------|
| 1 | CO₂ Adsorption | Reference state O₂ error, vdW missing |
| 2 | NEB Transition State | Image count, climbing image convergence |
| 3 | Phonon (DFPT) | EDDIFF too loose, imaginary frequencies |
| 4 | VASPsol (Solvation) | Dielectric constant, cavity parameters |
| 5 | Band Structure | High-symmetry path errors, k-point density |
| 6 | Bader Charge | Grid convergence, empty basin in metals |
| 7 | Bulk Optimization | ISIF=3 vs ISIF=7, ENCUT convergence |
| 8 | DFT+U | Projector dependence, U value transferability |

## Installation

```bash
pip install git+https://github.com/l850097071/bija-tools.git
bija-tools --help
```

**Requirements**: Python ≥3.9. Zero external dependencies beyond Flask.

**Limitations**: POTCAR files require your own VASP license (copyright). All other files generated automatically.

## Why I Built This

Every computational chemist I know has a personal "checklist" — scribbled notes, bash aliases, half-broken scripts passed down through lab generations. These are **tribal knowledge** that shouldn't exist in 2026.

bija-tools is my attempt to turn 5 years of DFT suffering into something reusable. **It's the tool I wish someone had given me on day one.**

## The避坑 (Pitfall Avoidance) Series

Beyond the tool, I'm building the **largest Chinese-language DFT pitfall knowledge base** — 29 articles and counting, each covering one specific computational trap with:
- Error symptoms → Physical root cause → Operational fix → Reviewer perspective → Self-check checklist

Topics covered: DFT+U, Bader charge, adsorption energy, vibrational frequency, DOS smearing, band structure k-paths, NEB, vdW corrections, solvation effects, work function, and more.

## Roadmap

- [x] v0.1.0: Core CLI (vaspgen, gate, outcarp, litsearch, pipeline)
- [ ] v0.2.0: Web UI (Flask-based, in development)
- [ ] v0.3.0: Multi-code support (CP2K, Quantum ESPRESSO, Gaussian)
- [ ] v0.4.0: Automated figure generation (DOS, band structure plots)
- [ ] v1.0.0: Full避坑 knowledge base integration + AI-assisted parameter recommendation

## Links

- **GitHub**: https://github.com/l850097071/bija-tools
- **Install**: `pip install git+https://github.com/l850097071/bija-tools.git`
- **License**: MIT — free forever

---

*If this tool saves you time, consider giving it a ⭐ on GitHub. If you find bugs or have feature requests, open an issue — I read every one.*
