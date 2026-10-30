r"""build_boundary_gold.py - Dựng đáp án ranh giới mức TRANG (phiên bản máy `v0`) từ `data/labels_v2.csv`.

Chạy từ gốc repo:
    .venv\Scripts\python.exe -X utf8 teams/team2_splitting/gold/build_boundary_gold.py

Sinh ra:
    teams/team2_splitting/gold/boundary_gold_v0.csv       (1113 dòng = 1113 trang của 304 tài liệu duy nhất)
    teams/team2_splitting/gold/boundary_gold_v0.meta.json (sha nhãn, sha manifest, số đếm)

CẢNH BÁO: ranh giới do MỘT annotator AI (đã xem đủ trang) gán, CHƯA có người kiểm. Đây là `v0`, không phải `v1`.
Script chỉ ĐỌC data/ (không ghi gì vào data/).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]

BB = "BB_LAY_MAU"
EXPECTED = dict(pages=1113, positions=809, boundaries=145)
# Nhóm đánh giá (theo README nhóm 2). `single_page` không có vị trí nào để chấm.
GROUPS = ["mixed", "same_other", "same_bb", "negative", "single_page"]


def sha10(path: Path) -> str:
    return hashlib.sha1(Path(path).read_bytes()).hexdigest()[:10]


def parse_segments(segments: str):
    segs = []
    for s in segments.split(";"):
        rng, typ = s.split(":")
        a, _, b = rng.partition("-")
        segs.append((int(a), int(b or a), typ))
    return segs


def eval_group(is_composite: str, mixed: str, seg_types: set, n_pages: int) -> str:
    if is_composite == "1":
        if mixed == "1":
            return "mixed"
        return "same_bb" if seg_types == {BB} else "same_other"
    return "negative" if n_pages >= 2 else "single_page"


def build(labels: Path, manifest: Path, splits: Path, ocr: Path | None) -> pd.DataFrame:
    lab = pd.read_csv(labels, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    man = pd.read_csv(manifest, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    sp = pd.read_csv(splits, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    u = lab[lab.is_duplicate_of == ""].merge(man[["doc_id", "relative_path", "page_count", "template_group"]], on="doc_id")
    u = u.merge(sp[["doc_id", "split"]], on="doc_id", how="left")
    avail = {}
    if ocr is not None and ocr.exists():
        for line in ocr.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            avail[r["doc_id"]] = int(r["pages_processed"])
    rows = []
    for r in u.itertuples():
        n = int(r.page_count)
        if r.is_composite == "1":
            segs = parse_segments(r.segments)
            assert segs[0][0] == 1 and segs[-1][1] == n and all(segs[k][1] + 1 == segs[k + 1][0] for k in range(len(segs) - 1)), r.doc_id
        else:
            segs = [(1, n, r.doc_type)]
        kind = "mixed" if r.composite_mixed == "1" else "same_type" if r.is_composite == "1" else "single"
        grp = eval_group(r.is_composite, r.composite_mixed, {t for _, _, t in segs}, n)
        for k, (a, b, typ) in enumerate(segs):
            for p in range(a, b + 1):
                rows.append(dict(
                    doc_id=r.doc_id, page=p, is_start=int(p == a), segment_idx=k, page_doc_type=typ, n_pages=n, kind=kind,
                    eval_group=grp, split=r.split, template_group=r.template_group or r.doc_id, review_status=r.review_status,
                    ocr_available=(int(p <= avail[r.doc_id]) if r.doc_id in avail else ""),
                ))
    return pd.DataFrame(rows)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--labels", default=str(REPO / "data" / "labels_v2.csv"))
    ap.add_argument("--manifest", default=str(REPO / "data" / "manifest.csv"))
    ap.add_argument("--splits", default=str(REPO / "data" / "splits" / "splits.csv"))
    ap.add_argument("--ocr", default=str(REPO / "data" / "ocr_v2.jsonl"), help="chỉ để đánh dấu trang nào có văn bản (cột ocr_available)")
    ap.add_argument("--out", default=str(HERE / "boundary_gold_v0.csv"))
    a = ap.parse_args(argv)

    g = build(Path(a.labels), Path(a.manifest), Path(a.splits), Path(a.ocr))
    pos = g[g.page >= 2]
    got = dict(pages=len(g), positions=len(pos), boundaries=int(pos.is_start.sum()))
    print("pages/positions/boundaries:", got["pages"], got["positions"], got["boundaries"])
    if got != EXPECTED:
        print(f"CẢNH BÁO: kỳ vọng {EXPECTED} (nhãn đã đổi?)", file=sys.stderr)
    per_group = {}
    for grp in GROUPS:
        sub = g[g.eval_group == grp]
        sp = sub[sub.page >= 2]
        per_group[grp] = dict(files=int(sub.doc_id.nunique()), pages=len(sub), positions=len(sp), boundaries=int(sp.is_start.sum()))
        print(f"  {grp:12s}", per_group[grp])
    out = Path(a.out)
    g.to_csv(out, index=False, encoding="utf-8-sig")
    meta = dict(
        version="v0 (machine, NOT human verified)", labels_file=Path(a.labels).name, labels_sha1_10=sha10(Path(a.labels)),
        manifest_sha1_10=sha10(Path(a.manifest)), splits_sha1_10=sha10(Path(a.splits)), totals=got, expected=EXPECTED,
        per_group=per_group, check_composite_files=sorted(g[g.review_status == "check_composite"].doc_id.unique().tolist()),
    )
    out.with_suffix(".meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print("đã ghi", out)


if __name__ == "__main__":
    main()
