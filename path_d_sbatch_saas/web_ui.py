"""
sbatch_gate Web UI — Flask单页应用
运行: python web_ui.py 或 python gate_engine.py --web
"""

import json
import tempfile
import shutil
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory
from gate_engine import run_gates, PRESETS

app = Flask(__name__, static_folder='static')

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/api/presets')
def list_presets():
    return jsonify(list(PRESETS.keys()))

@app.route('/api/check', methods=['POST'])
def check_job():
    """Check a job directory or uploaded files"""
    data = request.get_json() or {}
    preset = data.get('preset', 'vasp')
    path = data.get('path', '')

    if path and Path(path).exists():
        results = run_gates(Path(path), preset)
    else:
        # Demo mode — run against sample data
        results = {
            "workdir": path or "(demo)",
            "preset": preset,
            "all_pass": False,
            "total": 0,
            "passed": 0,
            "failed": 1,
            "warnings": 0,
            "gates": [{
                "id": "E1", "name": "路径检查",
                "passed": False,
                "detail": f"Directory not found: {path}",
                "severity": "error"
            }],
            "verdict": "❌ Directory not found"
        }

    return jsonify(results)

@app.route('/api/check-files', methods=['POST'])
def check_files():
    """Check uploaded job files"""
    preset = request.form.get('preset', 'vasp')
    files = request.files

    if not files:
        return jsonify({"error": "No files uploaded"}), 400

    # Save to temp dir and run gates
    tmpdir = Path(tempfile.mkdtemp(prefix='sbatch_gate_'))
    try:
        for f in files.values():
            if f.filename:
                f.save(str(tmpdir / f.filename))

        results = run_gates(tmpdir, preset)
        results["workdir"] = "(uploaded files)"
        # Clean tmpdir
        shutil.rmtree(tmpdir, ignore_errors=True)
    except Exception as e:
        shutil.rmtree(tmpdir, ignore_errors=True)
        return jsonify({"error": str(e)}), 500

    return jsonify(results)


def run_web(port=8765):
    print(f"\n  sbatch_gate Web UI → http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)


if __name__ == '__main__':
    run_web()
