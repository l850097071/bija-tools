"""
outcarp — VASP OUTCAR parser + calculation report generator
用法: python outcar_parser.py OUTCAR
      python outcar_parser.py OUTCAR --report
"""

import sys
import re
import argparse
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class OUTCARData:
    """Parsed OUTCAR data."""
    filename: str = ""
    # Basic
    vasp_version: str = ""
    n_atoms: int = 0
    n_types: int = 0
    elements: list[str] = field(default_factory=list)
    # Cell
    cell_volume: float = 0.0
    # Electronic
    encut: float = 0.0
    n_kpoints: int = 0
    n_bands: int = 0
    # SCF convergence
    scf_steps: list[int] = field(default_factory=list)
    total_scf_steps: int = 0
    converged: bool = False
    # Energy
    e0: float = 0.0           # First SCF energy
    e_final: float = 0.0      # Last SCF energy
    e_free: float = 0.0       # Free energy TOTEN
    e_without_entropy: float = 0.0  # energy(sigma->0)
    # Forces
    max_force: float = 0.0
    force_rms: float = 0.0
    forces_converged: bool = False
    # Ionic steps
    ionic_steps: int = 0
    # Timing
    cpu_time: float = 0.0
    elapsed_time: float = 0.0
    # Warnings
    warnings: list[str] = field(default_factory=list)
    # Raw
    raw_energy_lines: list[str] = field(default_factory=list)


def parse_outcar(filepath: str) -> OUTCARData:
    """Parse VASP OUTCAR file."""
    d = OUTCARData(filename=str(Path(filepath).name))
    text = Path(filepath).read_text(errors='replace')

    # VASP version
    m = re.search(r'vasp\.(\d+\.\d+\.\d+)', text)
    if m: d.vasp_version = m.group(1)

    # ENCUT
    m = re.search(r'ENCUT\s*=\s*([\d.]+)', text)
    if m: d.encut = float(m.group(1))

    # Number of atoms and types
    m = re.search(r'number of ions\s+\w+\s+\d+\s+\d+\s+(\d+)', text)
    if m: d.n_atoms = int(m.group(1))
    m = re.search(r'ion\s+type\s+symbol.*?\n\s*\d+\s+\d+\s+(\d+)', text)
    if m: d.n_types = int(m.group(1))

    # Elements (from POTCAR section)
    elems = re.findall(r' POTCAR:\s+\w+\s+(\w+)', text)
    seen = []
    for e in elems:
        if e not in seen: seen.append(e)
    d.elements = seen

    # K-points
    m = re.search(r'number of k-points.*?(\d+)', text)
    if m: d.n_kpoints = int(m.group(1))
    m = re.search(r'NBANDS\s*=\s*(\d+)', text)
    if m: d.n_bands = int(m.group(1))

    # Cell volume
    m = re.search(r'volume of cell\s*:\s*([\d.]+)', text)
    if m: d.cell_volume = float(m.group(1))

    # Energy lines
    energy_lines = re.findall(r'free\s+energy\s+TOTEN\s+=\s+([\d.-]+)', text)
    d.raw_energy_lines = energy_lines
    if energy_lines:
        d.e_free = float(energy_lines[-1])

    e0_lines = re.findall(r'energy\(sigma->0\)\s*=\s*([\d.-]+)', text)
    if e0_lines:
        d.e_without_entropy = float(e0_lines[-1])

    # SCF convergence per ionic step
    scf_blocks = re.findall(r'FREE ENERGIE OF THE ION-ELECTRON SYSTEM.*?energy\s+without', text, re.DOTALL)
    d.ionic_steps = len(scf_blocks)
    for block in scf_blocks:
        count = len(re.findall(r'-----------', block)) - 1
        if count > 0:
            d.scf_steps.append(count)
            d.total_scf_steps += count

    # Convergence check
    d.converged = 'reached required accuracy' in text.lower()

    # Forces
    force_blocks = re.findall(r'TOTAL-FORCE.*?total drift', text, re.DOTALL)
    if force_blocks:
        last_forces = force_blocks[-1]
        magnitudes = re.findall(r'([\d.]+)\s*$', last_forces, re.MULTILINE)
        if magnitudes:
            d.max_force = max(float(x) for x in magnitudes[:-1])  # skip drift
    m = re.search(r'FORCES: max atom, RMS\s*([\d.]+)\s*([\d.]+)', text)
    if m:
        d.max_force = float(m.group(1))
        d.force_rms = float(m.group(2))
    d.forces_converged = 'reached required accuracy' in text.lower() and d.max_force > 0

    # Timing
    m = re.search(r'Total CPU time used.*?:\s*([\d.]+)', text)
    if m: d.cpu_time = float(m.group(1))
    m = re.search(r'Elapsed time.*?:\s*([\d.]+)', text)
    if m: d.elapsed_time = float(m.group(1))

    # Warnings
    if 'WARNING' in text:
        warns = re.findall(r'(WARNING.*?)(?:\n|$)', text[:500000])
        d.warnings = warns[:20]  # cap at 20

    return d


def generate_report(d: OUTCARData) -> str:
    """Generate human-readable calculation report."""
    elapsed_h = d.elapsed_time / 3600 if d.elapsed_time else 0
    avg_scf = d.total_scf_steps / max(d.ionic_steps, 1)

    lines = [
        f"{'='*60}",
        f"  VASP CALCULATION REPORT",
        f"  {d.filename}",
        f"{'='*60}",
        "",
        f"  Status:       {'CONVERGED' if d.converged else 'NOT CONVERGED'}",
        f"  VASP version: {d.vasp_version or 'N/A'}",
        f"  Elements:     {' '.join(d.elements) if d.elements else 'N/A'}",
        f"  Atoms:        {d.n_atoms}",
        f"  ENCUT:        {d.encut:.0f} eV" if d.encut else "",
        f"  K-points:     {d.n_kpoints}" if d.n_kpoints else "",
        f"  NBANDS:       {d.n_bands}" if d.n_bands else "",
        f"  Cell volume:  {d.cell_volume:.2f} A^3" if d.cell_volume else "",
        "",
        f"  Ionic steps:  {d.ionic_steps}",
        f"  Total SCF:    {d.total_scf_steps} ({avg_scf:.0f} avg/ionic)",
        f"  Free energy:  {d.e_free:.6f} eV" if d.e_free else "",
        f"  E(sigma->0):  {d.e_without_entropy:.6f} eV" if d.e_without_entropy else "",
        "",
        f"  Max force:    {d.max_force:.4f} eV/A" if d.max_force else "",
        f"  Force RMS:    {d.force_rms:.4f} eV/A" if d.force_rms else "",
        f"  Forces OK:    {'Yes' if d.forces_converged else 'No' if d.max_force else 'N/A'}",
        "",
        f"  CPU time:     {d.cpu_time:.0f}s" if d.cpu_time else "",
        f"  Wall time:    {elapsed_h:.2f}h" if d.elapsed_time else "",
        "",
    ]
    # Remove empty lines
    lines = [l for l in lines if l.strip()]

    # SCF convergence history
    if d.scf_steps:
        lines.append(f"  SCF history per ionic step: {d.scf_steps}")
        lines.append(f"  (min={min(d.scf_steps)}, max={max(d.scf_steps)}, avg={avg_scf:.1f})")

    lines.append("")

    # Warnings
    if d.warnings:
        lines.append(f"  WARNINGS ({len(d.warnings)}):")
        for w in d.warnings[:5]:
            lines.append(f"    {w[:120]}")
        if len(d.warnings) > 5:
            lines.append(f"    ... and {len(d.warnings)-5} more")
        lines.append("")

    # Verdict
    issues = []
    if not d.converged: issues.append("SCF not converged")
    if d.max_force > 0.05: issues.append(f"Max force {d.max_force:.3f} > 0.05 eV/A")
    if d.ionic_steps >= 100: issues.append(f"{d.ionic_steps} ionic steps (capped at NSW?)")
    if d.max_force == 0 and d.ionic_steps > 0:
        issues.append("Forces are 0 — may be NSW=0 (single-point, not optimization)")

    if issues:
        lines.append(f"  ISSUES:")
        for i in issues: lines.append(f"    ! {i}")
    else:
        lines.append(f"  All checks passed. Calculation looks good.")

    lines.append(f"\n{'='*60}\n")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="VASP OUTCAR parser + report generator")
    parser.add_argument("outcar", nargs="?", help="OUTCAR file path")
    parser.add_argument("--report", action="store_true", default=True, help="Generate report (default)")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--energy", action="store_true", help="Extract energy convergence data")
    args = parser.parse_args()

    if not args.outcar:
        parser.print_help()
        return

    data = parse_outcar(args.outcar)

    if args.json:
        import json
        print(json.dumps({
            "converged": data.converged,
            "e_free_ev": data.e_free,
            "e0_ev": data.e_without_entropy,
            "max_force": data.max_force,
            "force_rms": data.force_rms,
            "ionic_steps": data.ionic_steps,
            "total_scf": data.total_scf_steps,
            "scf_per_ionic": data.scf_steps,
            "cpu_time_s": data.cpu_time,
            "wall_time_h": data.elapsed_time/3600 if data.elapsed_time else 0,
            "warnings": len(data.warnings),
        }, indent=2))
    elif args.energy:
        print("\n".join(data.raw_energy_lines[-50:]))
    else:
        print(generate_report(data))


if __name__ == "__main__":
    main()
