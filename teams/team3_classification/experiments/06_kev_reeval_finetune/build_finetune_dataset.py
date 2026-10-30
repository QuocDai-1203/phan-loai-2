"""build_finetune_dataset.py - CHUẨN BỊ (không huấn luyện) dữ liệu tinh chỉnh Kev-0.8B cho phân loại loại tài liệu.

Nguồn: DEV (237 tài liệu duy nhất, nguồn OCR `ocr_v2_p12`) từ `data/splits/splits.csv`. `data/splits/` chỉ ĐỌC. TEST tuyệt đối không vào
(có assert). Không có tập TRAIN riêng trong repo (chỉ DEV/TEST/EXCLUDED_COMPOSITE) nên train/held-out đều sinh từ DEV bằng group k-fold.

Đầu ra (dưới `_data/`, được .gitignore vì chứa văn bản OCR):
  neutral.jsonl            mỗi dòng: id, doc_id, text, choices{ma:ten}, label, fold, group, kind, source_doc_id, n_tokens_est (định dạng trung tính)
  kev/fold{k}/train.jsonl  định dạng huấn luyện CỦA KEV (kev/data.py, skills/kev-finetune/references/data-format.md): {"state","questions":{"category":{type,instructions,criteria,label}}}
  kev/fold{k}/heldout.jsonl  chỉ tài liệu GỐC của fold k (không tăng mẫu, không hard-negative)
  folds.csv                doc_id -> fold, nhóm gộp, cờ chia sẻ nhóm với TEST
Manifest chỉ có số đếm (không văn bản) ghi ở `dataset_manifest.json` cạnh tệp này (được commit).
Tái lập (gốc repo): .venv\\Scripts\\python.exe -X utf8 teams\\team3_classification\\experiments\\06_kev_reeval_finetune\\build_finetune_dataset.py
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
EXP02 = HERE.parent / "02_llm_and_cascade"
for p in (REPO, EXP02):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import pandas as pd  # noqa: E402

from common import Data, load_taxonomy_json  # noqa: E402
from src.classification.zero_shot import INSTR_VI, build_label_set, clean_prompt_text  # noqa: E402

SOURCE = "ocr_v2_p12"
CHARS = 2000                 # đúng cách cắt lúc suy luận (system_one_classifier.KEV_TEXT_CHARS)
K_FOLDS = 5
RARE_TARGET = 6              # loại hiếm: đủ bản (gốc + tăng mẫu) tới mức này, nhưng KHÔNG quá 3 bản tăng mẫu/tài liệu gốc
MAX_AUG_PER_DOC = 3
HARDNEG_MIN_PAIR = 1         # mọi cặp nhầm đo được ở 06 (chỉ 9 lỗi, nên không lọc theo số lần lặp) sinh hard-negative, đối xứng hai chiều
QID = "category"
DATA = HERE / "_data"
RESULTS = REPO / "teams" / "team3_classification" / "results" / "06_kev_reeval_finetune"


class UF:
    def __init__(self):
        self.p = {}

    def find(self, x):
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        self.p[self.find(a)] = self.find(b)


def load_pages() -> dict:
    out = {}
    for line in open(REPO / "data" / "ocr_v2.jsonl", encoding="utf-8"):
        r = json.loads(line)
        out[r["doc_id"]] = {p["page"]: (p.get("text") or "") for p in r["pages"]}
    return out


def build_groups(docs, test_ids: set):
    """Nhóm gộp = hợp của (group không cắt ở splits_strict.csv) và template_group của manifest, tính trên MỌI tài liệu (cả TEST) để thấy chia sẻ."""
    strict = pd.read_csv(REPO / "data" / "splits" / "splits_strict.csv", dtype=str).set_index("doc_id")["group"].to_dict()
    uf = UF()
    allm = pd.read_csv(REPO / "data" / "manifest.csv", dtype=str, keep_default_na=False)
    tg = dict(zip(allm.doc_id, allm.template_group))
    members = defaultdict(list)
    for did, g in strict.items():
        members[("s", g)].append(did)
    for did, g in tg.items():
        if g:
            members[("t", g)].append(did)
    for key, ms in members.items():
        for m in ms[1:]:
            uf.union(ms[0], m)
        uf.find(ms[0])
    comp = {d: uf.find(d) for d in set(strict) | set(tg)}
    shares_test = defaultdict(bool)
    by_comp = defaultdict(list)
    for d, c in comp.items():
        by_comp[c].append(d)
    for c, ms in by_comp.items():
        if any(m in test_ids for m in ms):
            for m in ms:
                shares_test[m] = True
    return comp, shares_test


def assign_folds(docs, comp, k: int, seed: int):
    """Group k-fold tham lam: nhóm lớn trước, vào fold đang có ít tài liệu nhất (hòa: ít tài liệu cùng loại nhất) - cân bằng loại hiếm."""
    rng = random.Random(seed)
    groups = defaultdict(list)
    for d in docs:
        groups[comp.get(d.doc_id, d.doc_id)].append(d)
    order = sorted(groups.items(), key=lambda kv: (-len(kv[1]), rng.random()))
    n_in = [0] * k
    cls_in = [Counter() for _ in range(k)]
    fold_of = {}
    for g, ds in order:
        labs = Counter(d.label for d in ds)
        best = min(range(k), key=lambda f: (sum(cls_in[f][c] * n for c, n in labs.items()), n_in[f], rng.random()))
        for d in ds:
            fold_of[d.doc_id] = best
        n_in[best] += len(ds)
        cls_in[best].update(labs)
    return fold_of, [len(v) for v in groups.values()]


def kev_record(text: str, criteria: dict, label: str) -> dict:
    return {"state": text, "questions": {QID: {"type": "choice", "instructions": INSTR_VI, "criteria": criteria, "label": label}}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--confusions", default=str(RESULTS / "tables" / "dev_confusion_pairs_name.csv"), help="CSV true,name,n (cặp nhầm đo ở 06); thiếu thì chỉ dùng taxonomy.confusable_with")
    a = ap.parse_args()
    rng = random.Random(a.seed)
    D = Data()
    docs = D.docs(SOURCE, "DEV")
    assert docs and all(d.split == "DEV" for d in docs), "chỉ DEV"
    test_ids = {r.doc_id for r in pd.read_csv(REPO / "data" / "splits" / "splits.csv", dtype=str).itertuples() if r.split == "TEST"}
    assert not ({d.doc_id for d in docs} & test_ids), "TEST không được vào dữ liệu tinh chỉnh"
    tax = load_taxonomy_json()
    ls = build_label_set(tax, "name")
    criteria_all = {i: ls.desc[i] for i in ls.ids}
    conf_tax = {c["id"]: [x for x in (c.get("confusable_with") or []) if x in criteria_all] for c in tax["classes"]}
    pairs = Counter()
    cp = Path(a.confusions)
    if cp.exists():
        for r in pd.read_csv(cp).itertuples():
            if r.n >= HARDNEG_MIN_PAIR and r.true in criteria_all and r.name in criteria_all:
                pairs[(r.true, r.name)] += int(r.n)
    pages = load_pages()
    comp, shares_test = build_groups(docs, test_ids)
    fold_of, gsizes = assign_folds(docs, comp, K_FOLDS, a.seed)
    rare = set(D.bench.pool_types)
    # token ước lượng bằng bộ tách từ Qwen3.5 nếu có trong cache cục bộ
    try:
        from transformers import AutoTokenizer

        tok = AutoTokenizer.from_pretrained("Qwen/Qwen3.5-0.8B-Base", local_files_only=True)
        ntok = lambda s: len(tok(s)["input_ids"])
    except Exception:
        ntok = lambda s: int(len(s) / 2.6)
    crit_tokens = ntok(json.dumps(criteria_all, ensure_ascii=False))

    rows = []
    by_label = defaultdict(list)
    for d in docs:
        text = clean_prompt_text(d.text, CHARS)
        if len(text) < 25 or d.label not in criteria_all:
            continue
        by_label[d.label].append(d.doc_id)
        rows.append(dict(kind="orig", doc_id=d.doc_id, source_doc_id=d.doc_id, text=text, label=d.label, fold=fold_of[d.doc_id], criteria=criteria_all))
    n_orig = len(rows)
    text_of = {r["doc_id"]: r["text"] for r in rows}
    # --- tăng mẫu loại hiếm bằng cắt đoạn từ CHÍNH tài liệu (cùng fold với bản gốc) ---
    for did, text in list(text_of.items()):
        d = next(x for x in docs if x.doc_id == did)
        if d.label not in rare:
            continue
        n_have = len(by_label[d.label])
        n_need = max(0, RARE_TARGET - n_have)
        if n_need == 0:
            continue
        per_doc = min(MAX_AUG_PER_DOC, -(-n_need // n_have))
        raw_p1 = pages.get(did, {}).get(1, "")
        cands = []
        p1 = clean_prompt_text(raw_p1, CHARS)
        if len(p1) >= 200 and abs(len(p1) - len(text)) > 150:
            cands.append(("aug_page1", p1))
        if len(text) >= 1000:
            cands.append(("aug_prefix1000", text[:1000]))
        if len(text) >= 1400:
            cands.append(("aug_body", clean_prompt_text(d.text, CHARS + 600)[500:CHARS + 500]))   # bỏ phần đầu (tiêu đề): ép đọc thân văn bản
        for kind, t in cands[:per_doc]:
            order = list(criteria_all)
            rng.shuffle(order)
            rows.append(dict(kind=kind, doc_id=f"{did}+{kind}", source_doc_id=did, text=t, label=d.label, fold=fold_of[did],
                             criteria={k: criteria_all[k] for k in order}))
    n_aug = len(rows) - n_orig
    # --- hard negative: lựa chọn rút gọn gồm nhãn đúng + các loại hay nhầm + vài loại gây nhiễu, thứ tự ngẫu nhiên ---
    confus = defaultdict(set)
    for (t, p), _n in pairs.items():
        confus[t].add(p)
        confus[p].add(t)
    for t, lst in conf_tax.items():
        if t in confus:
            confus[t].update(lst)
    n_hn = 0
    for r in list(rows):
        if r["kind"] != "orig" or r["label"] not in confus:
            continue
        neg = sorted(confus[r["label"]])
        pool = [c for c in criteria_all if c != r["label"] and c not in neg]
        sub = [r["label"]] + neg[:5] + rng.sample(pool, min(3, len(pool)))
        rng.shuffle(sub)
        rows.append(dict(kind="hardneg_subset", doc_id=f'{r["doc_id"]}+hn', source_doc_id=r["doc_id"], text=r["text"], label=r["label"], fold=r["fold"],
                         criteria={k: criteria_all[k] for k in sub}))
        n_hn += 1
    # --- ghi ---
    (DATA / "kev").mkdir(parents=True, exist_ok=True)
    over = 0
    with open(DATA / "neutral.jsonl", "w", encoding="utf-8") as f:
        for i, r in enumerate(rows):
            r["n_tokens_est"] = ntok(r["text"]) + (crit_tokens if len(r["criteria"]) == len(criteria_all) else ntok(json.dumps(r["criteria"], ensure_ascii=False)))
            over += r["n_tokens_est"] > 2048
            f.write(json.dumps(dict(id=i, doc_id=r["doc_id"], source_doc_id=r["source_doc_id"], kind=r["kind"], fold=r["fold"], text=r["text"],
                                    choices=r["criteria"], label=r["label"], n_tokens_est=r["n_tokens_est"],
                                    group=comp.get(r["source_doc_id"], r["source_doc_id"]), shares_group_with_test=bool(shares_test[r["source_doc_id"]])),
                               ensure_ascii=False) + "\n")
    for k in range(K_FOLDS):
        d = DATA / "kev" / f"fold{k}"
        d.mkdir(parents=True, exist_ok=True)
        with open(d / "train.jsonl", "w", encoding="utf-8") as ft, open(d / "heldout.jsonl", "w", encoding="utf-8") as fh:
            for r in rows:
                rec = json.dumps(kev_record(r["text"], r["criteria"], r["label"]), ensure_ascii=False)
                if r["fold"] != k:
                    ft.write(rec + "\n")
                elif r["kind"] == "orig":
                    fh.write(rec + "\n")
    pd.DataFrame([dict(doc_id=r["doc_id"], fold=r["fold"], group=comp.get(r["doc_id"], r["doc_id"]), shares_group_with_test=bool(shares_test[r["doc_id"]]),
                       label=r["label"]) for r in rows if r["kind"] == "orig"]).to_csv(DATA / "folds.csv", index=False)
    # --- kiểm tra không rò rỉ nhóm ---
    leak = 0
    grp_fold = defaultdict(set)
    for r in rows:
        grp_fold[comp.get(r["source_doc_id"], r["source_doc_id"])].add(r["fold"])
    leak = sum(len(v) > 1 for v in grp_fold.values())
    folds_orig = Counter(r["fold"] for r in rows if r["kind"] == "orig")
    rare_per_fold = Counter(r["fold"] for r in rows if r["kind"] == "orig" and r["label"] in rare)
    manifest = dict(
        source=SOURCE, chars=CHARS, n_docs_dev=len(docs), n_orig=n_orig, n_aug=n_aug, n_hardneg=n_hn, n_total=len(rows),
        n_types=len(by_label), n_rare_types_present=len([c for c in by_label if c in rare]), k_folds=K_FOLDS,
        orig_per_fold=dict(sorted(folds_orig.items())), rare_orig_per_fold=dict(sorted(rare_per_fold.items())),
        n_groups=len(gsizes), max_group_size=max(gsizes), groups_split_across_folds=leak,
        dev_docs_sharing_group_with_test=int(sum(shares_test[d.doc_id] for d in docs)),
        rows_over_2048_tokens_est=int(over), criteria_tokens_all_choices=crit_tokens,
        max_n_tokens_est=int(max(r["n_tokens_est"] for r in rows)), mean_n_tokens_est=float(sum(r["n_tokens_est"] for r in rows) / len(rows)),
        confusion_pairs_used=[f"{t}->{p}" for (t, p) in pairs], seed=a.seed, includes_test=False,
        note="Dữ liệu văn bản nằm ở _data/ (gitignore). Nhãn là nhãn máy (labels_v2.csv), chưa người kiểm.",
    )
    (HERE / "dataset_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
