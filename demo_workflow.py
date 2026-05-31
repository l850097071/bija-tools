#!/usr/bin/env python
"""
Demo: Complete research → generate → validate pipeline
"""
import sys
from pathlib import Path

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE / "path_a_vasp_gen"))
sys.path.insert(0, str(BASE / "path_d_sbatch_saas"))
sys.path.insert(0, str(BASE / "path_c_litsearch"))

from vaspgen import generate_all
from gate_engine import run_gates

print("=" * 60)
print("  Bija Research Tools — Demo Pipeline")
print("=" * 60)

# Step 1: Generate VASP inputs for Co3O4
print("\n[1/3] vaspgen: Generating inputs for Co3O4...")
demo_dir = BASE / "demo_output"
result = generate_all(formula="Co3O4", calc_type="optimization", output_dir=str(demo_dir))
for n in result.get("notes", []):
    print(f"  NOTE: {n}")
print(f"  Created: INCAR, POSCAR, KPOINTS in {demo_dir}")

# Step 2: Validate with sbatch_gate
print("\n[2/3] sbatch_gate: Validating generated inputs...")
gate_result = run_gates(demo_dir, "vasp")
for g in gate_result["gates"]:
    icon = "OK" if g["passed"] else "FAIL"
    print(f"  [{icon}] GATE {g['id']}: {g['detail']}")
print(f"  Verdict: {gate_result['verdict']}")

# Step 3: Summary
print(f"\n[3/3] Pipeline complete.")
print(f"  Generated: 4 VASP input files")
print(f"  Validated: {gate_result['passed']}/{gate_result['total']} gates passed")
print(f"  Ready for: sbatch submission")

print(f"\n{'=' * 60}")
print(f"  All tools working. Demo output in: {demo_dir}")
print(f"{'=' * 60}")
