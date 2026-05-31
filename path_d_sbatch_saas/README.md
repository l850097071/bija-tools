# sbatch_gate — HPC作业提交前多门控验证

**一句话**: 在 `sbatch` 之前跑这个。10道门控，任一未过=禁止提交。防止GPU小时浪费。

## 安装
```bash
pip install flask
python gate_engine.py --help
```

## 用法

### CLI
```bash
# PWmat作业
python gate_engine.py /path/to/jobdir --preset pwmat

# VASP作业
python gate_engine.py /path/to/jobdir --preset vasp

# JSON输出 (CI/CD集成)
python gate_engine.py /path/to/jobdir --preset vasp --json
```

### Web UI
```bash
python gate_engine.py --web
# → http://localhost:8765
```

## 门控清单

### PWmat (10 gates)
| Gate | 检查内容 |
|------|---------|
| 1 | etot.input存在 |
| 2 | NPROC=4 + PSP数=原子种类数 |
| 3 | atom.config存在 |
| 4 | 赝势文件可访问 |
| 5 | 关键参数完整 |
| 6 | 溶剂文件一致 |
| 7 | K点-收敛层级-溶剂 三方一致 |
| 8 | 重复提交检测 |
| 9 | 模板完整性 |
| 10 | 作业脚本语法 |

### VASP (5 gates)
| Gate | 检查内容 |
|------|---------|
| V1 | INCAR/POSCAR/POTCAR/KPOINTS四文件 |
| V2 | POTCAR元素与POSCAR一致 |
| V3 | INCAR参数合理性 |
| S1 | 重复提交检测 |
| S2 | 作业脚本语法 |

## 定价 (待上线)
| Tier | 价格 | 功能 |
|------|------|------|
| Free | $0 | 5次检查/月, VASP+Quick预设 |
| Pro | $19/月 | 无限检查, 全部预设, 自定义门控 |
| Lab | $49/月 | Pro + 团队管理 + CI/CD集成 |

## 路线图
- [x] PWmat 10门控引擎
- [x] VASP 5门控
- [x] Web拖拽上传界面
- [ ] Gaussian/QE预设
- [ ] 自定义门控(YAML)
- [ ] Slack/微信通知
- [ ] SaaS付费墙
