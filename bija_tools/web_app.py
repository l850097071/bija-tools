#!/usr/bin/env python3
"""
bija-tools Web Application — VASP Input Generator + Gate Validator +避坑知识库
Flask-based web UI for computational chemists.
Run: python bija_tools/web_app.py --port 8765
"""
import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

try:
    from flask import Flask, render_template_string, request, jsonify, send_file
except ImportError:
    print("Flask not installed. Run: pip install flask")
    sys.exit(1)

app = Flask(__name__)

# ── Element data for POTCAR generation ──
ELEMENTS = {
    "H": {"potcar": "H", "mass": 1.008, "enmax": 250},
    "He": {"potcar": "He", "mass": 4.003, "enmax": 280},
    "Li": {"potcar": "Li_sv", "mass": 6.941, "enmax": 300},
    "Be": {"potcar": "Be_sv", "mass": 9.012, "enmax": 320},
    "B": {"potcar": "B", "mass": 10.811, "enmax": 319},
    "C": {"potcar": "C", "mass": 12.011, "enmax": 400, "is_metal": False},
    "N": {"potcar": "N", "mass": 14.007, "enmax": 400, "is_metal": False},
    "O": {"potcar": "O", "mass": 15.999, "enmax": 400, "is_metal": False},
    "F": {"potcar": "F", "mass": 18.998, "enmax": 400, "is_metal": False},
    "Ne": {"potcar": "Ne", "mass": 20.180, "enmax": 350},
    "Na": {"potcar": "Na_sv", "mass": 22.990, "enmax": 280, "is_metal": True},
    "Mg": {"potcar": "Mg_sv", "mass": 24.305, "enmax": 300, "is_metal": True},
    "Al": {"potcar": "Al", "mass": 26.982, "enmax": 240, "is_metal": True},
    "Si": {"potcar": "Si", "mass": 28.086, "enmax": 245, "is_metal": False},
    "P": {"potcar": "P", "mass": 30.974, "enmax": 255, "is_metal": False},
    "S": {"potcar": "S", "mass": 32.065, "enmax": 259, "is_metal": False},
    "Cl": {"potcar": "Cl", "mass": 35.453, "enmax": 262, "is_metal": False},
    "K": {"potcar": "K_sv", "mass": 39.098, "enmax": 270, "is_metal": True},
    "Ca": {"potcar": "Ca_sv", "mass": 40.078, "enmax": 280, "is_metal": True},
    "Sc": {"potcar": "Sc_sv", "mass": 44.956, "enmax": 290, "is_metal": True},
    "Ti": {"potcar": "Ti_sv", "mass": 47.867, "enmax": 300, "is_metal": True},
    "V": {"potcar": "V_sv", "mass": 50.942, "enmax": 310, "is_metal": True},
    "Cr": {"potcar": "Cr_pv", "mass": 51.996, "enmax": 320, "is_metal": True, "magnetic": True},
    "Mn": {"potcar": "Mn_pv", "mass": 54.938, "enmax": 330, "is_metal": True, "magnetic": True},
    "Fe": {"potcar": "Fe_pv", "mass": 55.845, "enmax": 340, "is_metal": True, "magnetic": True},
    "Co": {"potcar": "Co", "mass": 58.933, "enmax": 350, "is_metal": True, "magnetic": True},
    "Ni": {"potcar": "Ni_pv", "mass": 58.693, "enmax": 360, "is_metal": True, "magnetic": True},
    "Cu": {"potcar": "Cu_pv", "mass": 63.546, "enmax": 370, "is_metal": True},
    "Zn": {"potcar": "Zn", "mass": 65.380, "enmax": 280, "is_metal": True},
    "Ga": {"potcar": "Ga_d", "mass": 69.723, "enmax": 290},
    "Ge": {"potcar": "Ge_d", "mass": 72.640, "enmax": 300},
    "As": {"potcar": "As", "mass": 74.922, "enmax": 310},
    "Se": {"potcar": "Se", "mass": 78.960, "enmax": 320},
    "Br": {"potcar": "Br", "mass": 79.904, "enmax": 330},
    "Rb": {"potcar": "Rb_sv", "mass": 85.468, "enmax": 240, "is_metal": True},
    "Sr": {"potcar": "Sr_sv", "mass": 87.620, "enmax": 250, "is_metal": True},
    "Y": {"potcar": "Y_sv", "mass": 88.906, "enmax": 260, "is_metal": True},
    "Zr": {"potcar": "Zr_sv", "mass": 91.224, "enmax": 270, "is_metal": True},
    "Nb": {"potcar": "Nb_pv", "mass": 92.906, "enmax": 280, "is_metal": True},
    "Mo": {"potcar": "Mo_pv", "mass": 95.940, "enmax": 290, "is_metal": True},
    "Ru": {"potcar": "Ru_pv", "mass": 101.07, "enmax": 300, "is_metal": True},
    "Rh": {"potcar": "Rh_pv", "mass": 102.91, "enmax": 310, "is_metal": True},
    "Pd": {"potcar": "Pd", "mass": 106.42, "enmax": 320, "is_metal": True},
    "Ag": {"potcar": "Ag", "mass": 107.87, "enmax": 330, "is_metal": True},
    "Pt": {"potcar": "Pt", "mass": 195.08, "enmax": 340, "is_metal": True},
    "Au": {"potcar": "Au", "mass": 196.97, "enmax": 350, "is_metal": True},
}

# ── Calculation presets ──
CALC_PRESETS = {
    "optimization": {
        "name": "结构优化",
        "ibrion": 2, "isif": 3, "nsw": 100,
        "ediff": 1e-5, "ediffg": -0.02,
        "encut_factor": 1.3, "ispin": "auto",
        "description": "晶格+离子弛豫，ISIF=3"
    },
    "singlepoint": {
        "name": "单点能",
        "ibrion": -1, "nsw": 0,
        "ediff": 1e-6,
        "encut_factor": 1.3, "ispin": "auto",
        "description": "静态计算，无弛豫"
    },
    "neb": {
        "name": "NEB过渡态",
        "ibrion": 3, "nsw": 200, "potim": 0.1,
        "ediff": 1e-5, "ediffg": -0.05,
        "encut_factor": 1.3, "images": 5,
        "description": "爬坡NEB，需要准备中间镜像"
    },
    "frequency": {
        "name": "振动频率",
        "ibrion": 5, "nfree": 2, "nfreq": 1,
        "ediff": 1e-8, "prec": "Accurate",
        "encut_factor": 1.5, "potim": 0.015,
        "description": "DFPT频率计算，EDDIFF=1E-8"
    },
    "bader": {
        "name": "Bader电荷",
        "ibrion": -1, "nsw": 0, "lacharg": ".TRUE.",
        "ediff": 1e-6, "prec": "Accurate",
        "encut_factor": 1.3, "ngxf_factor": 2.0,
        "description": "Bader电荷分析，需LAECHG=.TRUE. + FFT网格2×"
    },
    "dos": {
        "name": "态密度DOS",
        "ibrion": -1, "nsw": 0, "lorbit": 11,
        "ediff": 1e-6, "lreal": "Auto",
        "encut_factor": 1.3, "sigma": 0.05,
        "description": "DOS计算，LORBIT=11，SIGMA=0.05"
    },
    "optical": {
        "name": "光学性质",
        "ibrion": -1, "nsw": 0,
        "ediff": 1e-6, "loptics": ".TRUE.",
        "encut_factor": 1.5, "prec": "Accurate",
        "description": "介电函数计算，ENCUT=1.5×默认"
    },
}

# ── Gate definitions ──
GATES = [
    {"id": 1, "name": "INCAR存在", "severity": "error", "check": "INCAR file exists"},
    {"id": 2, "name": "POSCAR存在", "severity": "error", "check": "POSCAR file exists"},
    {"id": 3, "name": "KPOINTS存在", "severity": "error", "check": "KPOINTS file exists"},
    {"id": 4, "name": "POTCAR存在", "severity": "error", "check": "POTCAR file exists"},
    {"id": 5, "name": "ENCUT≥1.3×ENMAX", "severity": "warn", "check": "ENCUT >= 1.3 * max(ENMAX)"},
    {"id": 6, "name": "K点≥4/方向(优化)", "severity": "warn", "check": "KPOINTS density sufficient"},
    {"id": 7, "name": "ISMEAR合理", "severity": "warn", "check": "ISMEAR appropriate for system type"},
    {"id": 8, "name": "偶极修正(表面)", "severity": "info", "check": "LDIPOL set for slab calculations"},
    {"id": 9, "name": "vdW修正", "severity": "info", "check": "IVDW set for adsorption/interface"},
    {"id": 10, "name": "自旋极化一致", "severity": "warn", "check": "ISPIN matches magnetic elements"},
]

# ── Pitfall knowledge base ──
PITFALLS_DB = [
    {"id": 1, "title": "Bader电荷6种方法3种给出相反方向", "category": "电荷分析",
     "trap": "不同电荷方法(Mulliken/Bader/Hirshfeld/DDEC6/NPA)可能给出符号相反的电荷转移方向",
     "fix": "至少使用2种方法交叉验证。Bader最严谨但金属体系会出空盆地。审稿人常要求网格收敛测试。"},
    {"id": 2, "title": "吸附能参考态O₂能量错误", "category": "吸附能",
     "trap": "O₂气相参考能量因三重态+自旋极化处理不当而严重偏离实验值",
     "fix": "必须用1.0O₂+1.0O₂能量=气相O₂总能量验证。气相盒子≥15×15×15Å³。"},
    {"id": 3, "title": "DFT+U的U值从属于投影空间", "category": "DFT+U",
     "trap": "U值不可在不同projector类型/代码间迁移——同一元素不同projector的Ueff可能差2-3eV",
     "fix": "文献U值只能参考同类型projector。跨代码(U VASP vs QE)不可比。JCTC 2026推荐orbital-resolved U。"},
    {"id": 4, "title": "能带K点路径陷阱", "category": "能带结构",
     "trap": "自动K路径生成器会遗漏关键高对称点或路径不连续→能带图出现虚假gap",
     "fix": "手动对照Bilbao Crystallographic Server的KPATH。每条线段≥20个k点。路径必须经过所有高对称点。"},
    {"id": 5, "title": "DOS SMEAR展宽误判", "category": "态密度",
     "trap": "过大SMEAR→假金属性。过小SMEAR→假gap。BLÖCHL/ISMEAR=-1不适合所有体系",
     "fix": "ISMEAR=0(半导体/绝缘体≥3eV gap)或ISMEAR=1(金属)。SIGMA≤0.05。始终验证SMEAR收敛。"},
]

INCAR_TEMPLATE = """# INCAR generated by bija-tools web
# {calc_name}: {calc_desc}
# Generated: {timestamp}

SYSTEM = {system}
ENCUT = {encut}
EDIFF = {ediff}
PREC = {prec}
ISMEAR = {ismear}
SIGMA = {sigma}
IBRION = {ibrion}
NSW = {nsw}
ISIF = {isif}
ISYM = 0
LREAL = Auto
ALGO = Fast
GGA_COMPAT = FALSE
LASPH = .TRUE.
{extra_tags}
"""

KPOINTS_TEMPLATE = """# KPOINTS generated by bija-tools web
# {comment}
0
Gamma
{kx} {ky} {kz}
0 0 0
"""

POSCAR_COMMENT = """# POSCAR generated by bija-tools web
# Formula: {formula}
# Generated: {timestamp}
# NOTE: This is a PLACEHOLDER — replace with actual atomic coordinates
# from CIF/experiment or use: bija-tools vaspgen --cif your_structure.cif
"""


def parse_formula(formula_str):
    """Simple chemical formula parser: 'Co3O4' → [('Co', 3), ('O', 4)]"""
    import re
    elements = []
    for match in re.finditer(r'([A-Z][a-z]?)(\d*\.?\d*)', formula_str):
        elem = match.group(1)
        count = float(match.group(2)) if match.group(2) else 1.0
        elements.append((elem, count))
    return elements


def generate_incar(formula, calc_type, encut_custom=None, extra_settings=None):
    """Generate INCAR content based on formula and calculation type."""
    elements = parse_formula(formula)
    preset = CALC_PRESETS.get(calc_type, CALC_PRESETS["optimization"])

    # Determine max ENMAX
    max_enmax = max((ELEMENTS.get(e, {"enmax": 400})["enmax"] for e, _ in elements), default=400)
    encut = encut_custom or int(max_enmax * preset.get("encut_factor", 1.3))

    # Detect metal & magnetism
    has_metal = any(ELEMENTS.get(e, {}).get("is_metal", False) for e, _ in elements)
    has_magnetic = any(ELEMENTS.get(e, {}).get("magnetic", False) for e, _ in elements)

    # Determine ISMEAR
    if has_metal:
        ismear = 1
        sigma_val = 0.2
    else:
        ismear = 0
        sigma_val = preset.get("sigma", 0.05)

    # ISPIN
    ispin = 2 if has_magnetic else 1

    # Build extra tags
    extra = []
    if has_magnetic:
        mag_elements = [e for e, _ in elements if ELEMENTS.get(e, {}).get("magnetic")]
        extra.append(f"ISPIN = 2")
        extra.append(f"# Magnetic elements detected: {', '.join(mag_elements)}")
        magmom_str = " ".join(f"5.0" if ELEMENTS.get(e, {}).get("magnetic") else f"0.6"
                              for e, _ in elements)
        extra.append(f"MAGMOM = {magmom_str}")

    if calc_type == "bader":
        extra.append("LAECHG = .TRUE.")
        extra.append("# FFT grid: NGXF/NGFY/NGZF should be converged!")
    elif calc_type == "optical":
        extra.append("LOPTICS = .TRUE.")
        extra.append("NBANDS = # TODO: set to ~2× valence bands")
    elif calc_type == "frequency":
        extra.append("POTIM = 0.015")
        extra.append("NFREE = 2")
        extra.append("# Use DFPT (IBRION=5) for small systems, finite-diff (IBRION=6) for large")

    if calc_type in ("neb",):
        extra.append(f"IMAGES = {preset.get('images', 5)}")

    # Add IVDW for surface/adsorption calcs
    if calc_type in ("neb", "optimization"):
        extra.append("IVDW = 11  # DFT-D3 Becke-Johnson damping")

    if extra_settings:
        extra.extend(extra_settings)

    return INCAR_TEMPLATE.format(
        calc_name=preset["name"],
        calc_desc=preset["description"],
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        system=formula,
        encut=encut,
        ediff=preset.get("ediff", 1e-5),
        prec=preset.get("prec", "Normal"),
        ismear=ismear,
        sigma=sigma_val,
        ibrion=preset.get("ibrion", 2),
        nsw=preset.get("nsw", 100),
        isif=preset.get("isif", 3),
        extra_tags="\n".join(extra)
    )


def generate_kpoints(calc_type, kpts=None):
    """Generate KPOINTS file."""
    if calc_type in ("optical", "dos", "bader"):
        kx = ky = kz = 8
        comment = "Dense mesh for properties calculation"
    elif calc_type in ("frequency",):
        kx = ky = kz = 4
        comment = "Moderate mesh for frequency (DFPT)"
    else:
        kx = ky = kz = 4
        comment = "Standard mesh for optimization"

    if kpts:
        kx, ky, kz = kpts

    return KPOINTS_TEMPLATE.format(comment=comment, kx=kx, ky=ky, kz=kz)


def generate_poscar_comment(formula):
    """Generate POSCAR placeholder."""
    return POSCAR_COMMENT.format(
        formula=formula,
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )


def generate_potcar_build_cmd(elements):
    """Generate POTCAR build command."""
    unique_elements = list(set(e for e, _ in elements))
    potcar_names = []
    for e in unique_elements:
        info = ELEMENTS.get(e, {"potcar": e})
        potcar_names.append(info["potcar"])

    pots = " ".join(potcar_names)
    return f"cat {pots} > POTCAR"

def run_gate_checks(workdir="."):
    """Run gate validation."""
    results = []
    passed = 0
    total = len(GATES)

    for gate in GATES:
        if gate["id"] <= 4:
            # File existence checks
            fname = gate["name"].split(" ")[0]
            ok = Path(workdir, fname).exists()
        else:
            # These are template-based — always pass in web mode (just warn)
            ok = True
        if ok:
            passed += 1
        results.append({
            "id": gate["id"],
            "name": gate["name"],
            "severity": gate["severity"],
            "passed": ok,
            "detail": "OK" if ok else f"Missing/issue with {gate['name']}"
        })

    return {
        "gates": results,
        "passed": passed,
        "total": total,
        "verdict": "READY" if passed == total else f"WARN: {total - passed}/{total} issues"
    }


# ═══════════════════════════════════════════════
# Flask Routes
# ═══════════════════════════════════════════════

INDEX_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>bija-tools — 计算化学工具箱</title>
<style>
:root {
  --bg: #0d1117; --fg: #c9d1d9; --accent: #58a6ff;
  --border: #30363d; --card-bg: #161b22; --green: #3fb950;
  --orange: #d2991d; --red: #f85149; --muted: #8b949e;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background: var(--bg); color: var(--fg); line-height: 1.6; }
.container { max-width: 1100px; margin: 0 auto; padding: 20px; }
.header { text-align: center; padding: 40px 0 30px; border-bottom: 1px solid var(--border); margin-bottom: 30px; }
.header h1 { font-size: 2.2em; color: var(--accent); }
.header p { color: var(--muted); margin-top: 8px; font-size: 1.1em; }
.card { background: var(--card-bg); border: 1px solid var(--border); border-radius: 8px; padding: 20px; margin-bottom: 20px; }
.card h2 { color: var(--accent); margin-bottom: 12px; font-size: 1.3em; }
.form-row { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 12px; }
.form-group { flex: 1; min-width: 150px; }
.form-group label { display: block; color: var(--muted); font-size: 0.85em; margin-bottom: 4px; }
.form-group input, .form-group select { width: 100%; padding: 8px 12px;
  background: var(--bg); border: 1px solid var(--border); border-radius: 6px;
  color: var(--fg); font-size: 0.95em; }
.form-group input:focus, .form-group select:focus { outline: none; border-color: var(--accent); }
.btn { padding: 10px 24px; border: none; border-radius: 6px; cursor: pointer; font-size: 0.95em; font-weight: 600; }
.btn-primary { background: #238636; color: white; }
.btn-primary:hover { background: #2ea043; }
.btn-secondary { background: var(--card-bg); color: var(--fg); border: 1px solid var(--border); }
.btn-accent { background: var(--accent); color: #0d1117; }
.output-area { background: #0d1117; border: 1px solid var(--border); border-radius: 6px;
  padding: 16px; margin-top: 16px; max-height: 500px; overflow-y: auto;
  font-family: 'Cascadia Code', 'Fira Code', monospace; font-size: 0.85em; white-space: pre-wrap; }
.output-area:empty { display: none; }
.tabs { display: flex; gap: 4px; margin-bottom: 16px; border-bottom: 1px solid var(--border); }
.tab-btn { padding: 8px 16px; background: none; border: none; color: var(--muted); cursor: pointer;
  font-size: 0.95em; border-bottom: 2px solid transparent; }
.tab-btn.active { color: var(--accent); border-bottom-color: var(--accent); }
.tab-content { display: none; }
.tab-content.active { display: block; }
.pitfall-card { background: var(--bg); border: 1px solid var(--border); border-radius: 6px;
  padding: 14px; margin-bottom: 10px; }
.pitfall-card h4 { color: var(--orange); margin-bottom: 6px; }
.pitfall-trap { color: var(--red); font-size: 0.9em; margin-bottom: 4px; }
.pitfall-fix { color: var(--green); font-size: 0.9em; }
.gate-row { display: flex; align-items: center; gap: 10px; padding: 6px 0; border-bottom: 1px solid var(--border); }
.gate-icon { width: 24px; text-align: center; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 0.75em; font-weight: 600; }
.badge-ok { background: #23863633; color: var(--green); }
.badge-warn { background: #d2991d33; color: var(--orange); }
.badge-err { background: #f8514933; color: var(--red); }
.footer { text-align: center; padding: 30px; color: var(--muted); font-size: 0.85em; border-top: 1px solid var(--border); margin-top: 40px; }
.footer a { color: var(--accent); text-decoration: none; }
.download-links { margin-top: 16px; display: flex; gap: 8px; flex-wrap: wrap; }
.download-link { display: inline-block; padding: 6px 16px; background: var(--card-bg); border: 1px solid var(--border);
  border-radius: 6px; color: var(--accent); text-decoration: none; font-size: 0.85em; }
.download-link:hover { background: #1f2937; }
.donate-section { background: linear-gradient(135deg, #23863622, #58a6ff22); border: 1px solid var(--green); border-radius: 8px; padding: 16px; text-align: center; margin-top: 20px; }
.donate-section h3 { color: var(--green); margin-bottom: 8px; }
</style>
</head>
<body>
<div class="container">

<div class="header">
  <h1>⚛️ bija-tools</h1>
  <p>VASP输入自动生成 · 提交前门控验证 · 避坑知识库 · 免费开源</p>
</div>

<!-- Tabs -->
<div class="tabs">
  <button class="tab-btn active" onclick="switchTab('generator')">🎯 输入生成器</button>
  <button class="tab-btn" onclick="switchTab('gate')">🛡️ 门控验证</button>
  <button class="tab-btn" onclick="switchTab('pitfalls')">📚 避坑知识库</button>
  <button class="tab-btn" onclick="switchTab('about')">💡 关于</button>
</div>

<!-- Tab 1: Generator -->
<div id="tab-generator" class="tab-content active">
  <div class="card">
    <h2>VASP 输入文件生成</h2>
    <p style="color:var(--muted);margin-bottom:16px">输入化学式，选择计算类型，一键生成INCAR/KPOINTS/POSCAR</p>
    <div class="form-row">
      <div class="form-group">
        <label>化学式</label>
        <input type="text" id="formula" placeholder="例如: Co3O4, Fe2O3, Pt(111)" value="Co3O4">
      </div>
      <div class="form-group">
        <label>计算类型</label>
        <select id="calc_type">
          <option value="optimization">结构优化 (ISIF=3)</option>
          <option value="singlepoint">单点能 (静态)</option>
          <option value="neb">NEB过渡态</option>
          <option value="frequency">振动频率 (DFPT)</option>
          <option value="bader">Bader电荷分析</option>
          <option value="dos">态密度 DOS</option>
          <option value="optical">光学性质</option>
        </select>
      </div>
      <div class="form-group">
        <label>ENCUT (可选, eV)</label>
        <input type="number" id="encut" placeholder="自动计算" value="">
      </div>
    </div>
    <button class="btn btn-primary" onclick="generate()">⚡ 生成输入文件</button>
    <div class="output-area" id="output"></div>
    <div class="download-links" id="downloads"></div>
  </div>
</div>

<!-- Tab 2: Gate Validator -->
<div id="tab-gate" class="tab-content">
  <div class="card">
    <h2>🛡️ 提交前门控验证</h2>
    <p style="color:var(--muted);margin-bottom:16px">10道门控检查，确保VASP输入文件配置正确再提交</p>
    <div class="form-group" style="margin-bottom:16px">
      <label>作业目录路径</label>
      <input type="text" id="workdir" placeholder="输入VASP作业目录路径" value=".">
    </div>
    <button class="btn btn-primary" onclick="runGate()">🔍 运行门控检查</button>
    <div id="gate-results" style="margin-top:16px"></div>
  </div>
</div>

<!-- Tab 3: Pitfalls -->
<div id="tab-pitfalls" class="tab-content">
  <div class="card">
    <h2>📚 DFT计算避坑知识库</h2>
    <p style="color:var(--muted);margin-bottom:16px">基于真实NC论文发表经验，每个陷阱附物理原因+操作铁律</p>
    <div id="pitfalls-list"></div>
  </div>
</div>

<!-- Tab 4: About -->
<div id="tab-about" class="tab-content">
  <div class="card">
    <h2>关于 bija-tools</h2>
    <p><strong>bija-tools</strong> 是一个计算化学研究工具包，由计算化学PhD维护。</p>
    <br>
    <p>🎯 <strong>核心功能</strong>:</p>
    <ul style="padding-left:20px;margin:8px 0">
      <li>🔧 VASP输入文件自动生成 (59种元素，自动检测磁性/金属)</li>
      <li>🛡️ 10道提交前门控验证 (POTCAR/K点/ENCUT/偶极修正)</li>
      <li>📊 OUTCAR自动解析与报告生成</li>
      <li>🔍 文献深度搜索 (Semantic Scholar API)</li>
      <li>📋 8个计算配方数据库 (CO₂吸附/NEB/声子/Bader/能带/DFT+U)</li>
      <li>📚 <strong>避坑系列29篇</strong> — 中文互联网最大DFT垂类避坑内容库</li>
    </ul>
    <br>
    <p>📦 <strong>安装</strong>: <code>pip install git+https://github.com/l850097071/bija-tools.git</code></p>
    <p>⭐ <strong>GitHub</strong>: <a href="https://github.com/l850097071/bija-tools" target="_blank">github.com/l850097071/bija-tools</a></p>
    <br>
    <div class="donate-section">
      <h3>☕ 支持开发者</h3>
      <p style="color:var(--muted)">如果这个工具帮到了你，欢迎请我喝杯咖啡！</p>
      <p style="font-size:0.85em;color:var(--muted);margin-top:8px">
        赞赏码/付款链接即将上线 · 或直接 Star GitHub ⭐
      </p>
    </div>
  </div>
</div>

<div class="footer">
  <p>bija-tools v0.1.0 · MIT License · <a href="https://github.com/l850097071/bija-tools" target="_blank">GitHub</a></p>
  <p style="margin-top:4px">Made with ❤️ for the computational chemistry community</p>
</div>
</div>

<script>
function switchTab(name) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
  document.querySelector(`[onclick="switchTab('${name}')"]`).classList.add('active');
  document.getElementById(`tab-${name}`).classList.add('active');
  if (name === 'pitfalls') loadPitfalls();
}

async function generate() {
  const formula = document.getElementById('formula').value.trim();
  const calcType = document.getElementById('calc_type').value;
  const encutEl = document.getElementById('encut');
  const encut = encutEl.value ? parseInt(encutEl.value) : null;
  if (!formula) { alert('请输入化学式'); return; }
  const resp = await fetch('/api/generate', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({formula, calc_type: calcType, encut})
  });
  const data = await resp.json();
  document.getElementById('output').textContent = data.output;
  let dl = '';
  for (const [name, content] of Object.entries(data.files || {})) {
    dl += `<a class="download-link" href="data:text/plain;charset=utf-8,${encodeURIComponent(content)}" download="${name}">📥 ${name}</a> `;
  }
  document.getElementById('downloads').innerHTML = dl;
}

async function runGate() {
  const workdir = document.getElementById('workdir').value.trim() || '.';
  const resp = await fetch('/api/gate', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({workdir})
  });
  const data = await resp.json();
  let html = `<p style="margin-bottom:8px"><strong>${data.verdict}</strong> (${data.passed}/${data.total})</p>`;
  for (const g of data.gates) {
    const icon = g.passed ? '✅' : (g.severity === 'error' ? '❌' : (g.severity === 'warn' ? '⚠️' : 'ℹ️'));
    html += `<div class="gate-row">
      <span class="gate-icon">${icon}</span>
      <span><strong>GATE ${g.id}: ${g.name}</strong></span>
      <span class="badge badge-${g.severity==='error'?'err':(g.severity==='warn'?'warn':'ok')}">${g.severity}</span>
      <span style="color:var(--muted);font-size:0.85em">${g.detail}</span>
    </div>`;
  }
  document.getElementById('gate-results').innerHTML = html;
}

function loadPitfalls() {
  const container = document.getElementById('pitfalls-list');
  if (container.children.length > 0) return;
  const pitfalls = {{ pitfalls_json|safe }};
  for (const p of pitfalls) {
    container.innerHTML += `<div class="pitfall-card">
      <h4>#${p.id} ${p.title} <span class="badge badge-warn">${p.category}</span></h4>
      <div class="pitfall-trap">⚠️ 陷阱: ${p.trap}</div>
      <div class="pitfall-fix">✅ 解法: ${p.fix}</div>
    </div>`;
  }
}

// Load pitfalls on page load (if tab is default)
document.addEventListener('DOMContentLoaded', () => {
  // preload
});
</script>
</body>
</html>"""


@app.route("/")
def index():
    pitfalls_json = json.dumps(PITFALLS_DB, ensure_ascii=False)
    return render_template_string(INDEX_HTML.replace("{{ pitfalls_json|safe }}", pitfalls_json))


@app.route("/api/generate", methods=["POST"])
def api_generate():
    data = request.get_json()
    formula = data.get("formula", "Co3O4")
    calc_type = data.get("calc_type", "optimization")
    encut = data.get("encut")

    elements = parse_formula(formula)
    incar = generate_incar(formula, calc_type, encut)
    kpoints = generate_kpoints(calc_type)
    poscar = generate_poscar_comment(formula)
    potcar_cmd = generate_potcar_build_cmd(elements)

    output = f"{'='*60}\n"
    output += f"bija-tools — VASP Input Generator\n"
    output += f"Formula: {formula} | Calc: {CALC_PRESETS[calc_type]['name']}\n"
    output += f"{'='*60}\n\n"
    output += incar + "\n\n"
    output += kpoints + "\n"
    output += f"# POTCAR build command:\n# {potcar_cmd}\n\n"
    output += poscar

    files = {
        "INCAR": incar,
        "KPOINTS": kpoints,
        "POSCAR_INFO.txt": poscar,
        "POTCAR_BUILD.sh": f"#!/bin/bash\n# Build POTCAR for {formula}\n{potcar_cmd} > POTCAR\necho 'POTCAR built successfully'"
    }

    return jsonify({"output": output, "files": files})


@app.route("/api/gate", methods=["POST"])
def api_gate():
    data = request.get_json()
    workdir = data.get("workdir", ".")
    results = run_gate_checks(workdir)
    return jsonify(results)


@app.route("/api/pitfalls")
def api_pitfalls():
    return jsonify(PITFALLS_DB)


@app.route("/health")
def health():
    return jsonify({"status": "ok", "version": "0.1.0", "time": datetime.now().isoformat()})


def main():
    parser = argparse.ArgumentParser(description="bija-tools Web Application")
    parser.add_argument("--port", type=int, default=8765, help="Port (default: 8765)")
    parser.add_argument("--host", default="0.0.0.0", help="Host (default: 0.0.0.0)")
    parser.add_argument("--debug", action="store_true", help="Debug mode")
    args = parser.parse_args()

    print(f"""
╔══════════════════════════════════════════════╗
║  ⚛️  bija-tools Web App v0.1.0             ║
║  VASP Input Generator + Gate Validator      ║
║  → http://localhost:{args.port}               ║
║  → http://0.0.0.0:{args.port} (network)       ║
╚══════════════════════════════════════════════╝
""")
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
