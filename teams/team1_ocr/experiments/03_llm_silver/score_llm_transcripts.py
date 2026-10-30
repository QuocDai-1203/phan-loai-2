r"""Cham diem ban chep cua LLM (Haiku/Sonnet doc anh trang) de biet co dung lam "chuan bac" duoc khong.

1) Tren cac trang born-digital (kind=gold_textlayer): so voi text layer (dap an that) bang CUNG metric voi bake-off
   (ocrlib.all_metrics) -> so sanh truc tiep voi cac engine OCR local tren cung trang.
2) Tren cac trang scan that: do muc bat dong giua hai nguoi chep doc lap (Haiku vs Sonnet),
   va cham cac engine local theo ban chep cua LLM.

Chay:  .venv\Scripts\python -X utf8 teams\team1_ocr\experiments\03_llm_silver\score_llm_transcripts.py
"""
import csv, json, re, sys, unicodedata
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
T1 = HERE.parents[1]
sys.path.insert(0, str(HERE.parent / "01_engine_bakeoff"))
import ocrlib  # noqa: E402

SILVER = T1 / "gold" / "silver_llm"
_MARK = re.compile(r"\[[^\]\n]{0,200}\]")  # [dấu: ...], [chữ ký], [?], [trang trắng]


def clean_llm(text: str) -> str:
    """Bo ky hieu chu thich cua nguoi chep va dau phan cach o bang truoc khi cham."""
    return _MARK.sub(" ", text).replace("|", " ")


def bag_pr(gt: str, hyp: str) -> dict:
    """Precision/recall theo tui tu (khong phu thuoc thu tu doc) - metric chinh de so LLM voi engine,
    vi CER/WER bi phat nang khi thu tu doc khac text layer (bo cuc 2 cot, bang)."""
    from collections import Counter
    g = Counter(ocrlib.nfc(ocrlib.norm(gt).casefold()).split()); h = Counter(ocrlib.nfc(ocrlib.norm(hyp).casefold()).split())
    ov = sum((g & h).values())
    return dict(bag_recall=ov / max(sum(g.values()), 1), bag_precision=ov / max(sum(h.values()), 1))


def read_llm(model: str, pid: str):
    p = SILVER / model / f"{pid}.txt"
    return p.read_text(encoding="utf-8") if p.exists() else None


def main():
    pages = list(csv.DictReader(open(HERE / "pages.csv", encoding="utf-8")))
    bake = pd.read_csv(HERE.parent / "01_engine_bakeoff" / "results_pages.csv")
    bake = bake[(bake["variant"] == "clean") & (bake["dpi"] == 200) & (bake["set"] == "gold")]
    bake["relative_path"] = bake["relative_path"].map(lambda s: unicodedata.normalize("NFC", s))
    LOCAL = {}
    for f in sorted((HERE.parent / "01_engine_bakeoff" / "_cache" / "raw").glob("*__gold__200__main.jsonl")):
        d = {}
        for line in open(f, encoding="utf-8"):
            j = json.loads(line)
            if j.get("variant", "clean") == "clean" and not j.get("error"):
                d[(unicodedata.normalize("NFC", j["relative_path"]), int(j["page"]))] = j.get("text") or ""
        LOCAL[f.name.split("__")[0]] = d
    rows, loc_rows = [], []
    for r in pages:
        if r["kind"] != "gold_textlayer":
            continue
        doc = ocrlib.open_pdf(r["relative_path"])
        gt = ocrlib.gt_words_text(doc[int(r["page0"])])
        for model in ("haiku", "sonnet"):
            hyp = read_llm(model, r["page_id"])
            if hyp is None:
                continue
            m = ocrlib.all_metrics(gt, clean_llm(hyp))
            rows.append(dict(page_id=r["page_id"], relative_path=r["relative_path"], page=int(r["page0"]), engine=f"llm_{model}", **m, **bag_pr(gt, clean_llm(hyp))))
        key = (r["relative_path"], int(r["page0"]))
        for eng, texts in LOCAL.items():
            if key in texts:
                loc_rows.append(dict(page_id=r["page_id"], engine=eng, **bag_pr(gt, texts[key]), cer=ocrlib.all_metrics(gt, texts[key])["cer"]))
    llm = pd.DataFrame(rows)
    llm.to_csv(HERE / "llm_vs_textlayer_pages.csv", index=False, encoding="utf-8-sig")
    cols = ["cer", "wer", "cer_nodiac", "diac_recall", "bag_f1"]
    out = []
    for model, g in llm.groupby("engine"):
        out.append(dict(engine=model, n_pages=len(g), **{c: g[c].mean() for c in cols}, cer_median=g["cer"].median(), cer_max=g["cer"].max()))
        # so sanh ghep cap voi tung engine local tren dung nhung trang ca hai cung co
        for eng, b in bake.groupby("engine"):
            j = g.merge(b, on=["relative_path", "page"], suffixes=("_llm", "_loc"))
            if len(j) >= 5:
                out.append(dict(engine=f"  {eng} (cung {len(j)} trang voi {model})", n_pages=len(j),
                                **{c: j[f"{c}_loc"].mean() for c in cols}, cer_median=j["cer_loc"].median(), cer_max=j["cer_loc"].max(),
                                llm_cer_same_pages=j["cer_llm"].mean()))
    summ = pd.DataFrame(out)
    summ.to_csv(HERE / "llm_vs_textlayer_summary.csv", index=False, encoding="utf-8-sig")
    pd.set_option("display.width", 220); pd.set_option("display.max_colwidth", 60)
    print("== Trang born-digital: LLM va engine local so voi text layer ==")
    print(summ.round(4).to_string(index=False))
    allp = pd.concat([llm[["page_id", "engine", "bag_recall", "bag_precision", "cer"]], pd.DataFrame(loc_rows)])
    hp = set(llm[llm.engine == "llm_haiku"].page_id)
    t = []
    for eng, g in allp.groupby("engine"):
        g = g[g.page_id.isin(hp)]
        h = llm[(llm.engine == "llm_haiku") & llm.page_id.isin(set(g.page_id))]
        t.append(dict(engine=eng, n_pages=len(g), bag_recall=g.bag_recall.mean(), bag_precision=g.bag_precision.mean(),
                      recall_min=g.bag_recall.min(), haiku_recall_same_pages=h.bag_recall.mean()))
    t = pd.DataFrame(t).sort_values("bag_recall", ascending=False)
    t.to_csv(HERE / "bag_recall_summary.csv", index=False, encoding="utf-8-sig")
    print("\n== Ti le tu cua dap an duoc chep dung (bag recall, khong phu thuoc thu tu) ==")
    print(t.round(4).to_string(index=False))
    if len(llm):
        print("\n5 trang LLM te nhat:")
        print(llm.sort_values("bag_recall").head(6)[["engine", "page_id", "bag_recall", "bag_precision", "cer", "n_gt", "n_hyp"]].round(3).to_string(index=False))

    # Haiku vs Sonnet tren cac trang ca hai cung chep
    rows = []
    for r in pages:
        a, b = read_llm("haiku", r["page_id"]), read_llm("sonnet", r["page_id"])
        if a is None or b is None:
            continue
        m = ocrlib.all_metrics(clean_llm(b), clean_llm(a))  # coi Sonnet la tham chieu
        rows.append(dict(page_id=r["page_id"], kind=r["kind"], q_haiku=a.count("[?]"), q_sonnet=b.count("[?]"), **m))
    hs = pd.DataFrame(rows)
    if len(hs):
        hs.to_csv(HERE / "haiku_vs_sonnet_pages.csv", index=False, encoding="utf-8-sig")
        print("\n== Bat dong Haiku vs Sonnet (CER cua Haiku khi coi Sonnet la tham chieu) ==")
        print(hs.groupby("kind")[["cer", "wer", "bag_f1", "q_haiku", "q_sonnet"]].mean().round(4).to_string())
        print(hs[["page_id", "kind", "cer", "bag_f1", "q_haiku", "q_sonnet"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
