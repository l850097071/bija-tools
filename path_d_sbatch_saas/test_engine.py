"""Quick smoke test for gate engine"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from gate_engine import run_gates

# Test 1: VASP broken (missing KPOINTS)
print("=== Test 1: VASP (broken — missing KPOINTS) ===")
test_dir = Path(__file__).parent / "test_fixtures" / "vasp_broken"
test_dir.mkdir(parents=True, exist_ok=True)
(test_dir / "INCAR").write_text("ISMEAR = 0\nSIGMA = 0.05\n")
(test_dir / "POSCAR").write_text("Si\n1.0\n3.8 0 0\n0 3.8 0\n0 0 3.8\nSi\n1\nDirect\n0 0 0\n")
(test_dir / "POTCAR").write_text("PAW_PBE Si\n")
r = run_gates(test_dir, "vasp")
print(f"Verdict: {r['verdict']}")
print(f"Passed: {r['passed']}/{r['total']}")
for g in r['gates']:
    print(f"  {'OK' if g['passed'] else 'FAIL'} GATE {g['id']}: {g['detail']}")

# Test 2: VASP complete (all 4 files)
print("\n=== Test 2: VASP (complete) ===")
test_dir2 = Path(__file__).parent / "test_fixtures" / "vasp_good"
test_dir2.mkdir(parents=True, exist_ok=True)
(test_dir2 / "INCAR").write_text("ISMEAR = 0\nSIGMA = 0.05\nNSW = 100\n")
(test_dir2 / "POSCAR").write_text("Si\n1.0\n3.8 0 0\n0 3.8 0\n0 0 3.8\nSi\n1\nDirect\n0 0 0\n")
(test_dir2 / "POTCAR").write_text("PAW_PBE Si\n")
(test_dir2 / "KPOINTS").write_text("Automatic\n0\nGamma\n3 3 1\n0 0 0\n")
r2 = run_gates(test_dir2, "vasp")
print(f"Verdict: {r2['verdict']}")
print(f"Passed: {r2['passed']}/{r2['total']}")
for g in r2['gates']:
    print(f"  {'OK' if g['passed'] else 'FAIL'} GATE {g['id']}: {g['detail']}")

print("Engine smoke test complete")
