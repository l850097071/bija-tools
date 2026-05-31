"""bija-tools unified CLI — computational chemistry research toolkit."""
import sys
import os
import json
import time
import subprocess
import argparse
from pathlib import Path

PKG = Path(__file__).parent.parent


def cmd_vaspgen(args):
    sys.path.insert(0, str(PKG / "vaspgen"))
    from vaspgen import generate_all
    result = generate_all(args.cif, args.formula, args.calc, args.output)
    if "error" in result:
        print(f"Error: {result['error']}", file=sys.stderr)
        return 1
    for fname in ["incar", "poscar", "kpoints"]:
        print(f"\n{'='*50}\n=== {fname.upper()} ===\n{'='*50}")
        print(result[fname])
    print(f"\nPOTCAR: {result['potcar_build_cmd']}")
    for n in result.get("notes", []):
        print(f"  NOTE: {n}")
    return 0


def cmd_gate(args):
    sys.path.insert(0, str(PKG / "gate"))
    from gate_engine import run_gates
    if args.web:
        from web_ui import run_web
        run_web(args.port)
        return 0
    results = run_gates(Path(args.workdir), args.preset)
    for g in results["gates"]:
        icon = "[OK]" if g["passed"] else ("[WARN]" if g["severity"] == "warn" else "[FAIL]")
        print(f"  {icon} GATE {g['id']}: {g['name']} -- {g['detail']}")
    print(f"\n{results['passed']}/{results['total']} passed -- {results['verdict']}")
    return 0 if results["all_pass"] else 1


def cmd_litsearch(args):
    sys.path.insert(0, str(PKG / "litsearch"))
    from litsearch import search_papers, group_by_theme, generate_report
    papers = search_papers(args.query, args.limit, args.years)
    if not papers:
        print("No results found.")
        return 1
    themes = group_by_theme(papers)
    print(generate_report(args.query, papers, themes))
    return 0


def cmd_outcarp(args):
    sys.path.insert(0, str(PKG / "outcarp"))
    from outcar_parser import parse_outcar, generate_report
    if not args.outcar:
        print("Usage: bija-tools outcarp <OUTCAR>")
        return 1
    data = parse_outcar(args.outcar)
    if args.json:
        print(json.dumps({"converged": data.converged, "e_free_ev": data.e_free,
              "max_force": data.max_force, "ionic_steps": data.ionic_steps,
              "total_scf": data.total_scf_steps}, indent=2))
    elif args.energy:
        print("\n".join(data.raw_energy_lines[-50:]))
    else:
        print(generate_report(data))
    return 0


def cmd_sbatch(args):
    """Auto-validate then submit."""
    jobdir = str(Path(args.job_script).parent)
    print(f"sbatch_gate: validating {jobdir} before submission...")

    sys.path.insert(0, str(PKG / "gate"))
    from gate_engine import run_gates
    results = run_gates(Path(jobdir), args.preset)

    for g in results["gates"]:
        icon = "[OK]" if g["passed"] else ("[WARN]" if g["severity"] == "warn" else "[FAIL]")
        print(f"  {icon} GATE {g['id']}: {g['detail']}")

    if not results["all_pass"]:
        print(f"\nBLOCKED: {results['failed']} gate(s) failed.")
        if args.force:
            print("--force set, submitting anyway...")
        else:
            print("Fix errors above or use --force to submit anyway.")
            return 1

    if args.dry_run:
        print("\nDry run — not submitting.")
        return 0

    print(f"\nSubmitting: sbatch {args.job_script}")
    try:
        subprocess.run(["/usr/bin/sbatch", args.job_script], check=True)
    except FileNotFoundError:
        print("sbatch not found — is SLURM installed?")
        return 1
    return 0


def cmd_watch(args):
    """Watch directory for OUTCAR changes and auto-parse."""
    watchdir = Path(args.directory)
    if not watchdir.exists():
        print(f"Directory not found: {watchdir}")
        return 1

    print(f"Watching {watchdir} (interval={args.interval}s)...")
    checked = set()

    while True:
        for outcar in watchdir.rglob("OUTCAR"):
            mtime = outcar.stat().st_mtime
            key = str(outcar)
            if key not in checked:
                checked.add(key)
                print(f"\n{'='*50}")
                print(f"New OUTCAR detected: {outcar}")
                print(f"{'='*50}")

                sys.path.insert(0, str(PKG / "outcarp"))
                from outcar_parser import parse_outcar, generate_report
                try:
                    data = parse_outcar(str(outcar))
                    print(generate_report(data))
                except Exception as e:
                    print(f"Parse error: {e}")

                # Save report alongside OUTCAR
                report_path = outcar.parent / "REPORT.txt"
                try:
                    report_path.write_text(generate_report(data))
                    print(f"Report saved: {report_path}")
                except Exception:
                    pass

        if args.once:
            break

        time.sleep(args.interval)


def cmd_pipeline(args):
    """Full workflow: litsearch + vaspgen + gate in one command."""
    outdir = Path(args.output)
    outdir.mkdir(parents=True, exist_ok=True)

    # Step 1: literature search
    print(f"{'='*60}")
    print(f"STEP 1/3: Literature search — {args.query}")
    print(f"{'='*60}")
    sys.path.insert(0, str(PKG / "litsearch"))
    from litsearch import search_papers, group_by_theme, generate_report
    papers = search_papers(args.query, limit=10, year_range=args.years)
    if papers:
        report = generate_report(args.query, papers, group_by_theme(papers))
        (outdir / "LITERATURE_REPORT.md").write_text(report)
        print(f"  Found {len(papers)} papers → {outdir / 'LITERATURE_REPORT.md'}")

    # Step 2: generate VASP inputs
    print(f"\n{'='*60}")
    print(f"STEP 2/3: Generate VASP inputs — {args.formula}")
    print(f"{'='*60}")
    sys.path.insert(0, str(PKG / "vaspgen"))
    from vaspgen import generate_all
    result = generate_all(formula=args.formula, calc_type="optimization",
                          output_dir=str(outdir))
    if "error" in result:
        print(f"  Error: {result['error']}")
        return 1
    for n in result.get("notes", []):
        print(f"  NOTE: {n}")
    print(f"  Files generated in {outdir}/")

    # Step 3: validate
    print(f"\n{'='*60}")
    print(f"STEP 3/3: Validate — {args.preset} preset")
    print(f"{'='*60}")
    sys.path.insert(0, str(PKG / "gate"))
    from gate_engine import run_gates
    gate_result = run_gates(outdir, args.preset)
    for g in gate_result["gates"]:
        icon = "[OK]" if g["passed"] else ("[WARN]" if g["severity"] == "warn" else "[FAIL]")
        print(f"  {icon} GATE {g['id']}: {g['detail']}")
    print(f"\n  {gate_result['verdict']}")

    # Summary
    print(f"\n{'='*60}")
    print(f"PIPELINE COMPLETE")
    print(f"{'='*60}")
    print(f"  Output: {outdir}/")
    print(f"  Files: INCAR, POSCAR, KPOINTS, POTCAR_INFO.txt, run_vasp.job, LITERATURE_REPORT.md")
    if gate_result["all_pass"]:
        print(f"  Next: bija-tools sbatch {outdir}/run_vasp.job")
    else:
        print(f"  Next: Fix gate failures, then bija-tools sbatch {outdir}/run_vasp.job")
    return 0


def main():
    parser = argparse.ArgumentParser(description="bija-tools: computational chemistry toolkit")
    sub = parser.add_subparsers(dest="cmd")

    p1 = sub.add_parser("vaspgen", help="Generate VASP input files")
    p1.add_argument("--cif")
    p1.add_argument("--formula")
    p1.add_argument("--calc", choices=["optimization", "singlepoint"], default="optimization")
    p1.add_argument("--output", "-o")

    p2 = sub.add_parser("gate", help="Validate HPC job before submission")
    p2.add_argument("workdir", nargs="?")
    p2.add_argument("--preset", choices=["vasp", "pwmat", "gaussian", "quick"], default="vasp")
    p2.add_argument("--web", action="store_true")
    p2.add_argument("--port", type=int, default=8765)

    p3 = sub.add_parser("litsearch", help="Deep literature search")
    p3.add_argument("query")
    p3.add_argument("--years", default="2022-2026")
    p3.add_argument("--limit", type=int, default=20)

    p4 = sub.add_parser("outcarp", help="Parse OUTCAR + generate report")
    p4.add_argument("outcar", nargs="?")
    p4.add_argument("--json", action="store_true")
    p4.add_argument("--energy", action="store_true")

    # sbatch: auto-gate + submit
    p5 = sub.add_parser("sbatch", help="Auto-validate then submit (drop-in replacement for sbatch)")
    p5.add_argument("job_script", help="SLURM job script")
    p5.add_argument("--preset", choices=["vasp","pwmat","gaussian","quick"], default="vasp")
    p5.add_argument("--force", action="store_true", help="Submit even if gates fail")
    p5.add_argument("--dry-run", action="store_true", help="Validate only, don't submit")

    # watch: monitor directory + auto-parse
    p6 = sub.add_parser("watch", help="Watch directory, auto-parse OUTCAR on job completion")
    p6.add_argument("directory", help="Directory to watch")
    p6.add_argument("--interval", type=int, default=30, help="Check interval in seconds")
    p6.add_argument("--once", action="store_true", help="Check once and exit")

    # pipeline: research → generate → validate in one command
    p7 = sub.add_parser("pipeline", help="Full workflow: litsearch + vaspgen + gate")
    p7.add_argument("query", help="Literature search query")
    p7.add_argument("--formula", required=True, help="Chemical formula for VASP inputs")
    p7.add_argument("--output", "-o", default="./pipeline_output", help="Output directory")
    p7.add_argument("--preset", default="vasp", help="Gate preset")
    p7.add_argument("--years", default="2023-2026", help="Literature year range")

    args = parser.parse_args()
    if not args.cmd:
        parser.print_help()
        return 1

    return {"vaspgen": cmd_vaspgen, "gate": cmd_gate,
            "litsearch": cmd_litsearch, "outcarp": cmd_outcarp,
            "sbatch": cmd_sbatch, "watch": cmd_watch,
            "pipeline": cmd_pipeline}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
