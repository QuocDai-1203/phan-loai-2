"""eval_on_gold.py - do CER/WER tren gold THAT (25 trang scan do sinh vien go lai) cho mot hoac nhieu engine.

  .venv/Scripts/python.exe -X utf8 eval_on_gold.py --engines rapid_v1 viet_seq2seq_cpu
Doc teams/team1_ocr/gold/gold_pages_todo.csv + teams/team1_ocr/gold/transcripts/<id>.txt (trang chua co file thi bo qua;
trang overlap co <id>.a.txt/<id>.b.txt: dung <id>.a.txt).  Ky hieu [?] [EMPTY] [ROTATED] bi bo truoc khi so.
Ket qua: gold_eval.csv (tung trang) + bang tom tat theo why_chosen.
"""
import argparse, re
from pathlib import Path
import pandas as pd
from ocrlib import *
from run_bakeoff import make_engine

GOLD = Path(__file__).resolve().parents[2] / "gold"
ap = argparse.ArgumentParser()
ap.add_argument("--engines", nargs="+", default=["viet_seq2seq_cpu"])
ap.add_argument("--dpi", type=int, default=200)
ap.add_argument("--gold-dir", type=Path, default=GOLD / "transcripts")
a = ap.parse_args()
todo = pd.read_csv(GOLD / "gold_pages_todo.csv", encoding="utf-8-sig")
CLEAN = re.compile(r"\[(\?|EMPTY|ROTATED)\]")
rows = []
for name in a.engines:
    eng = make_engine(name)
    for r in todo.itertuples():
        f = next((p for p in (a.gold_dir / f"{r.transcription_id}.txt", a.gold_dir / f"{r.transcription_id}.a.txt") if p.exists()), None)
        if f is None:
            continue
        gt = CLEAN.sub("", f.read_text(encoding="utf-8"))
        img = render_page(open_pdf(r.relative_path), int(r.page), a.dpi)
        hyp = result_to_text(eng(img))
        rows.append(dict(engine=name, id=r.transcription_id, why=r.why_chosen, **all_metrics(gt, hyp)))
d = pd.DataFrame(rows)
d.to_csv(Path(__file__).parent / "gold_eval.csv", index=False)
if len(d):
    print(d.groupby(["engine", "why"])[["cer", "wer", "cer_nodiac", "diac_recall"]].mean().round(3).to_string())
    print(d.groupby("engine")[["cer", "wer", "cer_nodiac", "diac_recall"]].mean().round(3).to_string())
else:
    print("chua co file dap an trong", a.gold_dir)
