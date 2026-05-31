"""
sbatch_gate — HPC作业提交前多门控验证引擎
协议无关: 支持 PWmat / VASP / Gaussian / QE / 自定义
用法: python gate_engine.py <job_dir> --preset pwmat
       python gate_engine.py <job_dir> --config custom_gates.yaml
"""

import os
import sys
import re
import json
import argparse
from pathlib import Path
from dataclasses import dataclass, field
from typing import Callable, Optional

# ── Gate result ──
@dataclass
class GateResult:
    id: str
    name: str
    passed: bool
    detail: str
    severity: str = "error"  # error | warn

# ── Base gate definition ──
@dataclass
class Gate:
    id: str
    name: str
    check: Callable[[Path], GateResult]

# ══════════════════════════════════════════
# PWmat preset gates (10 gates, ported from sbatch_safe.sh)
# ══════════════════════════════════════════

def gate_etot_exists(workdir: Path) -> GateResult:
    etot = workdir / "etot.input"
    ok = etot.exists()
    return GateResult("1", "输入文件存在", ok,
        f"etot.input found" if ok else "etot.input not found")

def gate_nproc_and_psp(workdir: Path) -> GateResult:
    """NPROC + PSP count vs atom types"""
    etot = workdir / "etot.input"
    if not etot.exists():
        return GateResult("2", "NPROC/PSP验证", False, "etot.input missing — cannot check")
    content = etot.read_text()
    lines = content.strip().split('\n')
    first = lines[0].split()
    nproc = first[0] if first else "?"
    kpar = first[1] if len(first) > 1 else "?"
    # Count PSP lines
    psp_count = len([l for l in lines if 'IN.PSP' in l])
    # Count atom types from atom.config
    ac = workdir / "atom.config"
    atom_types = 0
    if ac.exists():
        ac_text = ac.read_text()
        in_position = False
        types = set()
        for line in ac_text.split('\n'):
            if 'Position' in line:
                in_position = True
                continue
            if in_position and line.strip():
                parts = line.split()
                if parts and parts[0].isdigit():
                    types.add(int(parts[0]))
        atom_types = len(types)
    issues = []
    if nproc != "4":
        issues.append(f"NPROC={nproc} (expected 4)")
    if psp_count != atom_types:
        issues.append(f"PSP={psp_count} != atom_types={atom_types}")
    ok = len(issues) == 0
    return GateResult("2", "NPROC/PSP验证", ok,
        f"NPROC={nproc} PSP={psp_count} atoms={atom_types}" if ok else "; ".join(issues))

def gate_atom_config(workdir: Path) -> GateResult:
    ac = workdir / "atom.config"
    ok = ac.exists()
    natom = "?"
    if ok:
        text = ac.read_text()
        natom = str(text.count('Position'))
    return GateResult("3", "结构文件", ok,
        f"atom.config ({natom} atoms)" if ok else "atom.config missing")

def gate_psp_accessible(workdir: Path) -> GateResult:
    etot = workdir / "etot.input"
    if not etot.exists():
        return GateResult("4", "赝势文件", False, "etot.input missing")
    missing = []
    for line in etot.read_text().split('\n'):
        if 'IN.PSP' in line:
            m = re.search(r'(?:IN\.PSP\w*\s*=\s*)(\S+)', line)
            if m:
                fname = m.group(1)
                if not (Path(fname).exists() or (workdir / fname).exists()):
                    missing.append(fname)
    ok = len(missing) == 0
    return GateResult("4", "赝势文件", ok,
        "All PSP files accessible" if ok else f"Missing: {', '.join(missing)}")

def gate_critical_params(workdir: Path) -> GateResult:
    etot = workdir / "etot.input"
    if not etot.exists():
        return GateResult("5", "关键参数", False, "etot.input missing")
    content = etot.read_text()
    has_err = 'E_ERROR' in content
    has_conv = 'CONVERGENCE' in content
    has_iter = 'SCF_ITER0_1' in content
    has_mp = 'MP_N123' in content
    ok = (has_conv and has_mp) or (has_err and has_iter and has_mp)
    return GateResult("5", "关键参数", ok,
        f"CONV={has_conv} ERR={has_err} ITER={has_iter} MP={has_mp}" if ok else
        f"Missing params — need CONVERGENCE+MP or E_ERROR+SCF_ITER0_1+MP")

def gate_solvent_check(workdir: Path) -> GateResult:
    etot = workdir / "etot.input"
    if not etot.exists():
        return GateResult("6", "溶剂检查", False, "etot.input missing")
    content = etot.read_text()
    has_solvent = 'IN.SOLVENT' in content and re.search(r'IN\.SOLVENT\s*=\s*T', content)
    if has_solvent:
        sol_file = workdir / "IN.SOLVENT"
        ok = sol_file.exists()
        return GateResult("6", "溶剂检查", ok,
            "IN.SOLVENT=T + file present" if ok else "IN.SOLVENT=T but file missing")
    return GateResult("6", "溶剂检查", True, "No solvent (OK)")

def gate_tier_consistency(workdir: Path) -> GateResult:
    etot = workdir / "etot.input"
    if not etot.exists():
        return GateResult("7", "层级一致性", False, "etot.input missing")
    content = etot.read_text()
    # Extract MP_N123
    m = re.search(r'MP_N123\s*=\s*(\d)\s*(\d)\s*(\d)', content)
    if not m:
        return GateResult("7", "层级一致性", True, "No MP_N123 — skip")
    mp = m.group(1) + m.group(2) + m.group(3)
    has_solvent = bool(re.search(r'IN\.SOLVENT\s*=\s*T', content))
    # Determine tier
    if 'CONVERGENCE' in content:
        tier = 'DIFFICULT' if 'DIFFICULT' in content else 'NORM'
    elif 'E_ERROR' in content:
        m2 = re.search(r'E_ERROR\s*=\s*([\d.eE+-]+)', content)
        tier = 'DIFFICULT' if m2 and '1E-5' in m2.group(1).upper() else 'NORM'
    else:
        tier = 'UNKNOWN'
    # Validate
    if mp == '771' and tier != 'DIFFICULT':
        return GateResult("7", "层级一致性", False, f"K=7x7x1 expects DIFFICULT, got {tier}")
    if mp == '771' and not has_solvent:
        return GateResult("7", "层级一致性", False, "DIFFICULT tier requires IN.SOLVENT=T")
    return GateResult("7", "层级一致性", True, f"Tier={tier} K={mp} SOLVENT={has_solvent}")

def gate_duplicate_check(workdir: Path) -> GateResult:
    rpt = workdir / "REPORT"
    if rpt.exists():
        content = rpt.read_text()
        if 'ending_scf_reason' in content and 'tol' in content:
            e_tot = re.search(r'E_tot\(eV\)\s*=\s*([\d.-]+)', content)
            return GateResult("8", "重复检测", False,
                f"ALREADY CONVERGED E_tot={e_tot.group(1) if e_tot else '?'} — blocked")
    return GateResult("8", "重复检测", True, "No converged REPORT — OK to submit")

def gate_template_integrity(workdir: Path) -> GateResult:
    """Check etot.input matches a known template (configurable paths)"""
    return GateResult("9", "模板完整性", True, "Template check skipped (no template dir configured)")

def gate_job_script_syntax(workdir: Path) -> GateResult:
    """Universal: check job script for common mistakes"""
    # Find any .job or .sh file
    scripts = list(workdir.glob("*.job")) + list(workdir.glob("*.sh"))
    if not scripts:
        return GateResult("10", "脚本语法", False, "No job script found")
    script = scripts[0]
    content = script.read_text()
    issues = []
    if '#!/bin/' not in content:
        issues.append("Missing shebang")
    if '#SBATCH' not in content and '#PBS' not in content:
        issues.append("No scheduler directives (#SBATCH/#PBS)")
    if 'mpirun' not in content and 'srun' not in content:
        issues.append("No mpirun/srun found")
    ok = len(issues) == 0
    return GateResult("10", "脚本语法", ok,
        f"{script.name} OK" if ok else "; ".join(issues),
        severity="warn" if issues else "error")

# ══════════════════════════════════════════
# VASP preset gates
# ══════════════════════════════════════════

def vasp_gate_four_files(workdir: Path) -> GateResult:
    """Check INCAR, POSCAR, POTCAR, KPOINTS all exist"""
    required = ["INCAR", "POSCAR", "POTCAR", "KPOINTS"]
    missing = [f for f in required if not (workdir / f).exists()]
    ok = len(missing) == 0
    return GateResult("V1", "VASP四文件", ok,
        "All 4 files present" if ok else f"Missing: {', '.join(missing)}")

def vasp_gate_potcar_elements(workdir: Path) -> GateResult:
    """Check POTCAR element order matches POSCAR"""
    potcar = workdir / "POTCAR"
    poscar = workdir / "POSCAR"
    if not (potcar.exists() and poscar.exists()):
        return GateResult("V2", "POTCAR元素", False, "POSCAR or POTCAR missing")
    pot_text = potcar.read_text()
    pos_text = poscar.read_text()
    # POTCAR elements: find all "TITEL = ..." lines, extract element symbol
    pot_elements = re.findall(r'TITEL[= ]+.*?([A-Z][a-z]?)', pot_text)
    if not pot_elements:
        # Fallback: "PAW_PBE Si" format
        pot_elements = re.findall(r'PAW\w*\s+([A-Z][a-z]?)', pot_text)
    pos_lines = pos_text.strip().split('\n')
    if len(pos_lines) >= 6:
        pos_elements = pos_lines[5].split()
        if len(pot_elements) != len(pos_elements):
            return GateResult("V2", "POTCAR元素", False,
                f"POTCAR has {len(pot_elements)} elements, POSCAR line6 has {len(pos_elements)}")
    return GateResult("V2", "POTCAR元素", True,
        f"Elements: {', '.join(pot_elements)}")

def vasp_gate_incar_sanity(workdir: Path) -> GateResult:
    """Common INCAR parameter conflicts"""
    incar = workdir / "INCAR"
    if not incar.exists():
        return GateResult("V3", "INCAR合理性", False, "INCAR missing")
    content = incar.read_text().upper()
    warnings = []
    # ISMEAR for semiconductors
    if 'ISMEAR' in content and '-5' in content:
        warnings.append("ISMEAR=-5 (tetrahedron) — ensure this is a semiconductor")
    # NSW=0
    if re.search(r'NSW\s*=\s*0', content):
        warnings.append("NSW=0 means single-point, not optimization")
    # Missing MAGMOM for transition metals
    # (heuristic - just warn if ISPIN=2 and no MAGMOM)
    if 'ISPIN' in content and '2' in content and 'MAGMOM' not in content:
        warnings.append("ISPIN=2 but no MAGMOM — verify magnetic moments")
    if warnings:
        return GateResult("V3", "INCAR合理性", True,
            "Warnings: " + "; ".join(warnings), severity="warn")
    return GateResult("V3", "INCAR合理性", True, "INCAR looks reasonable")


# ══════════════════════════════════════════
# Gaussian preset gates
# ══════════════════════════════════════════

def gauss_gate_input_exists(workdir: Path) -> GateResult:
    """Check .gjf or .com input file exists"""
    inputs = list(workdir.glob("*.gjf")) + list(workdir.glob("*.com"))
    ok = len(inputs) > 0
    return GateResult("G1", "输入文件", ok,
        f"Found: {inputs[0].name}" if ok else "No .gjf or .com file found")

def gauss_gate_route_section(workdir: Path) -> GateResult:
    """Check #P route section present"""
    inputs = list(workdir.glob("*.gjf")) + list(workdir.glob("*.com"))
    if not inputs:
        return GateResult("G2", "Route段", False, "No input file")
    content = inputs[0].read_text()
    has_route = bool(re.search(r'^[#!]\s*[pnPN]', content, re.MULTILINE))
    return GateResult("G2", "Route段", has_route,
        "#P/#N route found" if has_route else "Missing #P/#N route section")

def gauss_gate_charge_mult(workdir: Path) -> GateResult:
    """Check charge and spin multiplicity line"""
    inputs = list(workdir.glob("*.gjf")) + list(workdir.glob("*.com"))
    if not inputs:
        return GateResult("G3", "电荷/自旋", False, "No input file")
    content = inputs[0].read_text()
    # Find the charge/mult line (after route, before coords)
    m = re.search(r'^\s*(-?\d+)\s+(\d+)\s*$', content, re.MULTILINE)
    ok = m is not None
    return GateResult("G3", "电荷/自旋", ok,
        f"Charge={m.group(1)} Mult={m.group(2)}" if ok else "Missing charge/spin multiplicity")

def gauss_gate_coordinates(workdir: Path) -> GateResult:
    """Check atomic coordinates present"""
    inputs = list(workdir.glob("*.gjf")) + list(workdir.glob("*.com"))
    if not inputs:
        return GateResult("G4", "坐标", False, "No input file")
    content = inputs[0].read_text()
    # Look for element symbol followed by coordinates
    coords = re.findall(r'^\s*[A-Z][a-z]?\s+[-0-9.\s]+$', content, re.MULTILINE)
    ok = len(coords) >= 1
    return GateResult("G4", "坐标", ok,
        f"{len(coords)} atoms found" if ok else "No atomic coordinates")


# ══════════════════════════════════════════
# Preset registry
# ══════════════════════════════════════════

PRESETS = {
    "pwmat": [
        Gate("1", "输入文件存在", gate_etot_exists),
        Gate("2", "NPROC/PSP验证", gate_nproc_and_psp),
        Gate("3", "结构文件", gate_atom_config),
        Gate("4", "赝势文件", gate_psp_accessible),
        Gate("5", "关键参数", gate_critical_params),
        Gate("6", "溶剂检查", gate_solvent_check),
        Gate("7", "层级一致性", gate_tier_consistency),
        Gate("8", "重复检测", gate_duplicate_check),
        Gate("9", "模板完整性", gate_template_integrity),
        Gate("10", "脚本语法", gate_job_script_syntax),
    ],
    "vasp": [
        Gate("V1", "VASP四文件", vasp_gate_four_files),
        Gate("V2", "POTCAR元素", vasp_gate_potcar_elements),
        Gate("V3", "INCAR合理性", vasp_gate_incar_sanity),
        Gate("S1", "重复检测", gate_duplicate_check),
        Gate("S2", "脚本语法", gate_job_script_syntax),
    ],
    "gaussian": [
        Gate("G1", "输入文件", gauss_gate_input_exists),
        Gate("G2", "Route段", gauss_gate_route_section),
        Gate("G3", "电荷/自旋", gauss_gate_charge_mult),
        Gate("G4", "坐标", gauss_gate_coordinates),
        Gate("S1", "重复检测", gate_duplicate_check),
        Gate("S2", "脚本语法", gate_job_script_syntax),
    ],
    "quick": [
        Gate("1", "输入文件存在", gate_etot_exists),
        Gate("3", "结构文件", gate_atom_config),
        Gate("10", "脚本语法", gate_job_script_syntax),
    ],
}


def run_gates(workdir: Path, preset: str = "pwmat",
              custom_gates: Optional[list] = None) -> dict:
    """Run all gates and return results."""
    if custom_gates:
        gates = custom_gates
    else:
        gates = PRESETS.get(preset, PRESETS["pwmat"])

    results = []
    for gate in gates:
        try:
            result = gate.check(workdir)
        except Exception as e:
            result = GateResult(gate.id, gate.name, False, f"Gate error: {e}")
        results.append(result)

    all_pass = all(r.passed for r in results if r.severity == "error")
    fails = [r for r in results if not r.passed]

    return {
        "workdir": str(workdir),
        "preset": preset,
        "all_pass": all_pass,
        "total": len(results),
        "passed": sum(1 for r in results if r.passed),
        "failed": len(fails),
        "warnings": sum(1 for r in results if r.severity == "warn" and not r.passed),
        "gates": [{"id": r.id, "name": r.name, "passed": r.passed,
                    "detail": r.detail, "severity": r.severity}
                   for r in results],
        "verdict": "ALL CLEAR — safe to submit" if all_pass else
                   f"BLOCKED — {len(fails)} gate(s) failed"
    }


def main():
    parser = argparse.ArgumentParser(description="HPC作业提交前门控验证")
    parser.add_argument("workdir", help="作业目录路径")
    parser.add_argument("--preset", choices=list(PRESETS.keys()),
                        default="pwmat", help="门控预设")
    parser.add_argument("--json", action="store_true", help="JSON输出")
    parser.add_argument("--web", action="store_true", help="启动Web界面")
    parser.add_argument("--port", type=int, default=8765, help="Web端口")
    args = parser.parse_args()

    if args.web:
        from web_ui import run_web
        run_web(args.port)
        return

    results = run_gates(Path(args.workdir), args.preset)

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print(f"\n{'='*50}")
        print(f"sbatch_gate — {args.preset.upper()} preset")
        print(f"Workdir: {results['workdir']}")
        print(f"{'='*50}")
        for g in results["gates"]:
            icon = "[OK]" if g["passed"] else ("[WARN]" if g["severity"] == "warn" else "[FAIL]")
            print(f"  {icon} GATE {g['id']}: {g['name']} — {g['detail']}")
        print(f"{'='*50}")
        print(f"Result: {results['passed']}/{results['total']} gates passed")
        print(results["verdict"])
        print(f"{'='*50}\n")

    sys.exit(0 if results["all_pass"] else 1)


if __name__ == "__main__":
    main()
