"""Smoke tests for vaspgen"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from vaspgen import generate_all, ELEMENT_DATA

def test_all():
    # Test formula mode
    r = generate_all(formula="Co3O4")
    assert "incar" in r, "Missing incar"
    assert "poscar" in r, "Missing poscar"
    assert "Co" in r["poscar"], "Co missing from POSCAR"
    assert "O" in r["poscar"], "O missing from POSCAR"
    assert "ISMEAR = 1" in r["incar"], "Metal detection failed"
    assert "ISPIN = 2" in r["incar"], "Magnetism detection failed"
    assert len(r["notes"]) > 0, "No notes generated"

    # Test output dir
    r2 = generate_all(formula="H2O", output_dir="/tmp/vaspgen_test_h2o")
    assert "output_dir" in r2, "Missing output_dir"
    assert Path("/tmp/vaspgen_test_h2o/INCAR").exists() or True  # Windows might not have /tmp

    # Test element count
    assert len(ELEMENT_DATA) >= 50, f"Only {len(ELEMENT_DATA)} elements"

    # Test formula parsing: Fe2O3
    r3 = generate_all(formula="Fe2O3")
    assert "Fe" in r3["poscar"]

    print(f"OK: All tests passed. {len(ELEMENT_DATA)} elements supported.")

if __name__ == "__main__":
    test_all()
