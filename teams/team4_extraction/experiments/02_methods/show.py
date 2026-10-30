"""show.py - In nhanh bảng tóm tắt từ results_<split>_<gold>.json (số tổng hợp, không có giá trị trường).  show.py DEV all"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
split, gold = (sys.argv[1], sys.argv[2]) if len(sys.argv) > 2 else ("DEV", "all")
d = json.loads((HERE / f"results_{split}_{gold}.json").read_text(encoding="utf-8"))
f = lambda x: "  n/a" if x is None or x != x else f"{x:.2f}"  # noqa: E731
print(f"{split}/{gold} units={d['n_units']} {d['units_by_type']} incomplete={d['incomplete']} rule={d['chosen_expiry_rule']}")
print(f"{'config':58s} {'n':>3s} {'F1s':>5s} {'F1l':>5s} | {'date':>5s} {'num':>5s} {'id':>5s} {'txt_s':>5s} {'txt_l':>5s} | {'doc':>5s} | {'exp_ok':>6s} {'empty':>6s} {'WRONG':>6s} (n)")
for n, c in d["configs"].items():
    s, l = c["normalized"], c["lenient"]
    pt, pl = s["per_type"], l["per_type"]
    e = s["expiry_all"]
    print(f"{n[:58]:58s} {c['units']:3d} {f(s['overall']['f1'])} {f(l['overall']['f1'])} | {f(pt['date']['f1'])} {f(pt['number']['f1'])} {f(pt['id']['f1'])} "
          f"{f(pt['text']['f1'])} {f(pl['text']['f1'])} | {f(s['doc_level']['rate'])} | {f(e['correct_rate']):>6s} {f(e['empty_rate']):>6s} {f(e['wrong_rate']):>6s} ({e['n_gold_present']})")
if "--abst" in sys.argv:
    print("\nrule | emitted | correct | wrong | spurious | automation | wrong_upper95")
    for r in d["abstention"]:
        print(f"{r['rule'][:42]:42s} {r['n_emitted']:3d} {r['n_correct']:3d} {r['n_wrong']:3d} {r['n_spurious']:3d} {f(r['automation'])} {f(r['wrong_upper95'])}  wrong_units={r['wrong_units'][:6]}")
