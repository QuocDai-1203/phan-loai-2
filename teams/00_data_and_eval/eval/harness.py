"""harness.py - Khung đánh giá dùng chung cho Nhóm 3 (phân loại) và Data & Eval.

Dùng:
    import sys; sys.path.insert(0, "<repo>/teams/00_data_and_eval/eval")
    from harness import *
    bench  = load_benchmark("data/labels_v2.csv")                 # tài liệu duy nhất, đã loại composite hỗn hợp
    splits = load_or_make_splits(bench)                           # data/splits/splits.csv
    dev    = load_documents(bench, splits, "haiku_p12", split="DEV")
    cv     = cross_validate(lambda: MyPredictor(), dev, bench.s_classes, track="S")
    # TEST chỉ mở bằng: load_documents(..., split="TEST", final_test=True)

Một Predictor mới (vd. LLM / embedding) chỉ cần kế thừa `Predictor`, cài `fit` và `predict`:
    class MyPredictor(Predictor):
        name = "my_method"; track = "S"
        def fit(self, train_docs): ...
        def predict(self, docs) -> Prediction: ...
rồi gọi `cross_validate`, `score_predictions`, `append_result_row`. Quy tắc đầy đủ: reports/03_evaluation_protocol.md.
"""

from __future__ import annotations

import csv
import datetime as _dt
import hashlib
import json
import time
import unicodedata
import uuid
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

from eval_metrics import *  # noqa: F401,F403
from eval_metrics import (BOOT_N, BOOT_SEED, accuracy_idx, bootstrap_metrics, encode, latency_summary,
                          macro_f1_idx, score_predictions)
from eval_splits import *  # noqa: F401,F403
from eval_splits import (DEFAULT_MAX_GROUP, FOLD_SEEDS, SPLIT_SEED, check_no_group_leak, make_splits)

REPO = Path(__file__).resolve().parents[3]
DATA = REPO / "data"
PDF_ROOT = REPO / "docs" / "_chot_samples_phanloaitailieu"
DEFAULT_LABELS = DATA / "labels_v2.csv"
MANIFEST = DATA / "manifest.csv"
SPLITS_DIR = DATA / "splits"
RESULTS_TABLE = REPO / "teams" / "team3_classification" / "results" / "results_table.csv"

POOL = "RARE_OR_OTHER"           # lớp gộp của Track S
UNKNOWN = "UNKNOWN"              # nhãn abstain của bộ luật
SEEDS = FOLD_SEEDS
FOLD_COLS = {0: "fold", 1: "fold_s1", 2: "fold_s2"}

# nguồn văn bản: tên -> (file, danh sách trang)
TEXT_SOURCES = {
    "legacy_p1": ("baseline_ocr_335.jsonl", [1]),
    "haiku_p1": ("ocr_llm_haiku.jsonl", [1]),
    "haiku_p12": ("ocr_llm_haiku.jsonl", [1, 2]),
    "ocr_v2_p1": ("ocr_v2.jsonl", [1]),
    "ocr_v2_p12": ("ocr_v2.jsonl", [1, 2]),
}


# ---------------------------------------------------------------------------
# Dữ liệu
# ---------------------------------------------------------------------------
@dataclass
class Doc:
    doc_id: str
    file_name: str
    relative_path: str
    label: str                      # loại nội dung đầy đủ (Track Z)
    label_s: str                    # nhãn Track S (loại có >= min_docs tài liệu, còn lại = RARE_OR_OTHER)
    group: str = ""
    template_group: str = ""
    split: str = ""
    fold: int = -1                  # seed 0
    folds: Dict[int, int] = field(default_factory=dict)   # seed -> fold
    is_scanned: bool = True
    page_count: int = 1
    text: str = ""
    pdf_path: Optional[Path] = None

    def target(self, track: str) -> str:
        return self.label_s if track == "S" else self.label


@dataclass
class Benchmark:
    files: pd.DataFrame              # mọi file (kể cả bản sao, composite)
    reps: pd.DataFrame               # tài liệu duy nhất, không composite hỗn hợp
    composites: pd.DataFrame
    dup_conflicts: List[str]
    s_classes: List[str]             # Track S: các loại >= min_docs + POOL
    pool_types: List[str]            # các loại bị gộp vào POOL
    type_counts: Dict[str, int]
    min_docs: int
    labels_path: Path
    labels_sha: str

    @property
    def z_classes(self) -> List[str]:
        return sorted(self.type_counts)

    def label_s(self, doc_type: str) -> str:
        return doc_type if doc_type in self.s_classes else POOL

    def summary(self) -> Dict:
        pooled = sum(self.type_counts[t] for t in self.pool_types)
        return {
            "files": int(len(self.files)),
            "unique_docs": int(self.files["is_rep"].sum()),
            "composites_mixed_unique": int(len(self.composites)),
            "benchmark_docs": int(len(self.reps)),
            "types_total": len(self.type_counts),
            "track_s_types": [(c, self.type_counts[c]) for c in self.s_classes if c != POOL],
            "pool_types": len(self.pool_types),
            "pool_docs": int(pooled),
            "dup_conflicts": self.dup_conflicts,
        }


_PDF_INDEX: Dict[str, Path] = {}


def _pdf_index() -> Dict[str, Path]:
    """NFC(relative path) -> đường dẫn thật trên đĩa (tên file trên đĩa có thể ở dạng Unicode khác NFC)."""
    if not _PDF_INDEX and PDF_ROOT.exists():
        for x in PDF_ROOT.rglob("*.pdf"):
            _PDF_INDEX[_nfc_rel(x.relative_to(PDF_ROOT).as_posix())] = x
    return _PDF_INDEX


def file_sha(path: Path) -> str:
    return hashlib.sha1(Path(path).read_bytes()).hexdigest()[:10]


def load_benchmark(labels_path: Path | str = DEFAULT_LABELS, min_docs: int = 10, manifest: Path | str = MANIFEST) -> Benchmark:
    """Gộp manifest + nhãn; thu về tài liệu duy nhất; loại composite hỗn hợp; kiểm tra bản sao cùng nhãn."""
    labels_path = Path(labels_path)
    lab = pd.read_csv(labels_path, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    man = pd.read_csv(manifest, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    df = man.merge(lab[[c for c in lab.columns if c not in ("page_count",)]], on="doc_id", how="inner", validate="1:1")
    if len(df) != len(man):
        raise ValueError(f"Nhãn thiếu {len(man) - len(df)} doc_id so với manifest")
    if "composite_mixed" in df.columns:
        df["composite_mixed"] = df["composite_mixed"].astype(str).str.strip() == "1"
    else:  # nhãn tạm của annotator A
        df["composite_mixed"] = df["note"].astype(str).str.contains("composite khác loại", case=False)

    # bản sao byte-giống-hệt: nhóm theo manifest.exact_dup_group; đại diện = dòng không có is_duplicate_of, else doc_id nhỏ nhất
    df["_ug"] = np.where(df["exact_dup_group"] != "", df["exact_dup_group"], df["doc_id"])
    rep = {}
    for ug, sub in df.groupby("_ug"):
        cands = sub["doc_id"].tolist()
        if "is_duplicate_of" in sub.columns:
            primary = sub.loc[sub["is_duplicate_of"] == "", "doc_id"].tolist()
            cands = primary or cands
        rep_id = sorted(cands)[0]
        for d in sub["doc_id"]:
            rep[d] = rep_id
    df["rep_doc_id"] = df["doc_id"].map(rep)
    df["is_rep"] = df["doc_id"] == df["rep_doc_id"]

    conflicts = []
    for ug, sub in df.groupby("_ug"):
        if sub["doc_type"].nunique() > 1 or sub["composite_mixed"].nunique() > 1:
            conflicts.append(f"{ug}: " + ", ".join(sorted(set(sub["doc_type"]))))

    reps_all = df[df["is_rep"]].copy()
    composites = reps_all[reps_all["composite_mixed"]]
    reps = reps_all[~reps_all["composite_mixed"]].copy()
    counts = reps["doc_type"].value_counts().to_dict()
    s_types = [t for t, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])) if n >= min_docs]
    pool_types = sorted(t for t in counts if t not in s_types)
    pdf_idx = _pdf_index()
    df["pdf_path"] = df["relative_path"].map(lambda p: pdf_idx.get(_nfc_rel(p), PDF_ROOT / p))
    df["is_scanned"] = df["is_scanned"].astype(str).str.lower() == "true"
    df["page_count"] = pd.to_numeric(df["page_count"], errors="coerce").fillna(1).astype(int)
    reps = df.loc[reps.index]
    composites = df.loc[composites.index]
    return Benchmark(df, reps, composites, conflicts, s_types + [POOL], pool_types, counts, min_docs, labels_path, file_sha(labels_path))


# ---------------------------------------------------------------------------
# Splits
# ---------------------------------------------------------------------------
def build_splits(bench: Benchmark, max_group_size: Optional[int] = DEFAULT_MAX_GROUP) -> pd.DataFrame:
    sp = make_splits(bench.reps, bench.files, max_group_size=max_group_size)
    bad = check_no_group_leak(sp)
    if bad:
        raise AssertionError("Rò rỉ nhóm trong splits: " + "; ".join(bad[:5]))
    return sp


def write_splits(bench: Benchmark, out_dir: Path = SPLITS_DIR) -> Dict[str, pd.DataFrame]:
    """Ghi splits.csv (chính), splits_strict.csv, excluded_composites.csv và splits_meta.json vào data/splits/."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    main = build_splits(bench, DEFAULT_MAX_GROUP)
    strict = build_splits(bench, None)
    main.to_csv(out_dir / "splits.csv", index=False, encoding="utf-8")
    strict.to_csv(out_dir / "splits_strict.csv", index=False, encoding="utf-8")
    comp = bench.composites[["doc_id", "file_name", "doc_type", "segments", "review_status"]
                            if "review_status" in bench.composites.columns else ["doc_id", "file_name", "doc_type", "segments"]]
    comp.to_csv(out_dir / "excluded_composites.csv", index=False, encoding="utf-8")
    meta = {
        "labels_file": str(bench.labels_path.relative_to(REPO)) if bench.labels_path.is_relative_to(REPO) else str(bench.labels_path),
        "labels_sha1_10": bench.labels_sha,
        "min_docs": bench.min_docs,
        "split_seed": SPLIT_SEED,
        "max_group_size_main": DEFAULT_MAX_GROUP,
        "n_dev": int(((main.split == "DEV") & (main.is_rep == 1)).sum()),
        "n_test": int(((main.split == "TEST") & (main.is_rep == 1)).sum()),
        "n_excluded_composite_unique": int(((main.split == "EXCLUDED_COMPOSITE") & (main.is_rep == 1)).sum()),
        "generated": _dt.datetime.now().isoformat(timespec="seconds"),
    }
    (out_dir / "splits_meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"main": main, "strict": strict}



def load_splits(path: Path | str = SPLITS_DIR / "splits.csv") -> pd.DataFrame:
    return pd.read_csv(path, dtype={"doc_id": str, "rep_doc_id": str, "group": str})


class SplitsOutOfDateError(RuntimeError):
    """data/splits/ (đã khóa) không còn phủ hết benchmark; phải chủ động sinh lại bằng rebuild=True."""


def unassigned_docs(bench: Benchmark, splits: pd.DataFrame) -> List[str]:
    """doc_id thuộc benchmark nhưng chưa được gán DEV/TEST trong splits đã khóa."""
    assigned = set(splits.loc[splits["split"].isin(["DEV", "TEST"]), "doc_id"])
    return sorted(set(bench.reps["doc_id"]) - assigned)


def load_or_make_splits(bench: Benchmark, strict: bool = False, rebuild: bool = False) -> pd.DataFrame:
    """Đọc data/splits/*.csv - tập chia ĐÃ KHÓA: thành viên DEV/TEST không đổi khi nhãn được sửa.

    - Chưa có splits (lần đầu) hoặc rebuild=True: sinh mới (tất định) và ghi data/splits/.
    - Nhãn đã đổi (sha khác) nhưng mọi tài liệu của benchmark vẫn có DEV/TEST: GIỮ NGUYÊN splits, chỉ cảnh báo.
      splits.csv không chứa nhãn nên sửa nhãn không làm tài liệu đổi tập; TEST cũ vẫn là TEST.
    - Có tài liệu của benchmark chưa được gán (thêm tài liệu mới, tệp ghép khác loại được sửa thành tài liệu đơn):
      báo SplitsOutOfDateError. Sinh lại là quyết định có chủ ý vì TEST mới khác TEST cũ: số TEST đã báo cáo
      không còn so sánh được và TEST cũ coi như đã bị nhìn thấy.
    """
    main_p, meta_p = SPLITS_DIR / "splits.csv", SPLITS_DIR / "splits_meta.json"
    if rebuild or not (main_p.exists() and meta_p.exists()):
        write_splits(bench, SPLITS_DIR)
    else:
        meta = json.loads(meta_p.read_text(encoding="utf-8"))
        missing = unassigned_docs(bench, load_splits(main_p))
        if missing:
            raise SplitsOutOfDateError(
                f"{len(missing)} tài liệu của benchmark chưa có trong tập chia đã khóa {SPLITS_DIR} "
                f"(ví dụ {', '.join(missing[:5])}). Nhãn lúc chia: {meta.get('labels_sha1_10')}, hiện tại: {bench.labels_sha}. "
                "Muốn chia lại: load_or_make_splits(bench, rebuild=True) - TEST sẽ đổi, mọi số TEST cũ phải chấm lại."
            )
        if meta.get("labels_sha1_10") != bench.labels_sha:
            warnings.warn(
                f"Nhãn đã đổi kể từ khi chia tập ({meta.get('labels_sha1_10')} -> {bench.labels_sha}); "
                "giữ nguyên thành viên DEV/TEST đã khóa.", stacklevel=2)
    return load_splits(SPLITS_DIR / ("splits_strict.csv" if strict else "splits.csv"))


# ---------------------------------------------------------------------------
# Văn bản
# ---------------------------------------------------------------------------
def _nfc_rel(p: str) -> str:
    return unicodedata.normalize("NFC", p.replace("\\", "/"))


def source_available(source: str) -> bool:
    return (DATA / TEXT_SOURCES[source][0]).exists()


def available_sources() -> List[str]:
    return [s for s in TEXT_SOURCES if source_available(s)]


def load_text_source(source: str, bench: Benchmark) -> Dict[str, str]:
    """doc_id -> văn bản (cho MỌI file; thiếu -> '')."""
    fname, pages = TEXT_SOURCES[source]
    path = DATA / fname
    rel2id = {_nfc_rel(r): d for r, d in zip(bench.files["relative_path"], bench.files["doc_id"])}
    out = {d: "" for d in bench.files["doc_id"]}
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            did = rec.get("doc_id") or rel2id.get(_nfc_rel(rec.get("relative_path", "")))
            if did not in out:
                continue
            if isinstance(rec.get("pages"), list) and rec["pages"]:
                ps = [p for p in rec["pages"] if int(p.get("page", 0)) in pages and (p.get("text") or "").strip()]
                ps.sort(key=lambda p: int(p["page"]))
                out[did] = "\n".join(p["text"] for p in ps)
            elif isinstance(rec.get("ocr_text"), str):
                out[did] = rec["ocr_text"]
    return out


def load_documents(
    bench: Benchmark,
    splits: pd.DataFrame,
    source: str,
    split: str = "DEV",
    final_test: bool = False,
    include_duplicates: bool = False,
) -> List[Doc]:
    """Tài liệu của một split. `split="TEST"` bị chặn trừ khi final_test=True (điều khoản khóa TEST)."""
    if split == "TEST" and not final_test:
        raise PermissionError("TEST bị khóa: chỉ lệnh --final-test mới được phép mở (final_test=True).")
    if split not in ("DEV", "TEST", "ALL"):
        raise ValueError(split)
    texts = load_text_source(source, bench)
    sp = splits.set_index("doc_id")
    docs: List[Doc] = []
    df = bench.files
    for _, r in df.sort_values("doc_id").iterrows():
        d = r["doc_id"]
        if d not in sp.index:
            continue
        s = sp.loc[d]
        # composite_mixed: tệp vừa được sửa nhãn thành ghép khác loại vẫn mang DEV/TEST trong splits đã khóa
        if s["split"] == "EXCLUDED_COMPOSITE" or bool(r["composite_mixed"]):
            continue
        if split != "ALL" and s["split"] != split:
            continue
        if not include_duplicates and not bool(r["is_rep"]):
            continue
        docs.append(Doc(
            doc_id=d, file_name=r["file_name"], relative_path=r["relative_path"], label=r["doc_type"],
            label_s=bench.label_s(r["doc_type"]), group=str(s["group"]),
            template_group=r["template_group"] or "", split=s["split"], fold=int(s["fold"]),
            folds={0: int(s["fold"]), 1: int(s["fold_s1"]), 2: int(s["fold_s2"])},
            is_scanned=bool(r["is_scanned"]), page_count=int(r["page_count"]), text=texts.get(d, ""),
            pdf_path=Path(r["pdf_path"]),
        ))
    return docs


def truncate_docs(docs: Sequence[Doc], n_chars: Optional[int]) -> List[Doc]:
    """Bản sao tài liệu với văn bản cắt còn n ký tự đầu (ablation độ dài đầu vào)."""
    import dataclasses

    if not n_chars:
        return list(docs)
    return [dataclasses.replace(d, text=d.text[:n_chars]) for d in docs]


# ---------------------------------------------------------------------------
# Predictor
# ---------------------------------------------------------------------------
@dataclass
class Prediction:
    labels: List[str]
    proba: Optional[np.ndarray] = None      # (n_docs, len(classes)) hoặc None
    classes: Optional[List[str]] = None     # tên cột của proba
    latency_ms: Optional[np.ndarray] = None  # mỗi tài liệu (nếu có đo)

    @property
    def confidence(self) -> Optional[np.ndarray]:
        return None if self.proba is None else self.proba.max(axis=1)


class Predictor:
    """Giao diện chung. `track` = 'S' hoặc 'Z' quyết định nhãn mục tiêu (Doc.target). `fit` có thể no-op (zero-shot)."""
    name: str = "predictor"
    track: str = "S"

    def fit(self, train_docs: Sequence[Doc]) -> "Predictor":
        return self

    def predict(self, docs: Sequence[Doc]) -> Prediction:  # pragma: no cover - giao diện
        raise NotImplementedError


def time_single_doc(predictor: Predictor, docs: Sequence[Doc]) -> np.ndarray:
    """Độ trễ (ms) khi dự đoán TỪNG tài liệu một (batch=1), gồm trích đặc trưng + suy luận, không gồm OCR."""
    out = []
    for d in docs:
        t0 = time.perf_counter()
        predictor.predict([d])
        out.append((time.perf_counter() - t0) * 1000)
    return np.array(out)


# ---------------------------------------------------------------------------
# Cross-validation trên DEV (đầu ra: dự đoán out-of-fold)
# ---------------------------------------------------------------------------
@dataclass
class CVResult:
    seed: int
    oof: pd.DataFrame                 # doc_id, fold, y_true, y_pred, conf
    proba: Optional[np.ndarray]       # (n, K) cùng thứ tự oof, hoặc None
    classes: Optional[List[str]]
    fold_scores: List[Dict]


def cross_validate(
    factory: Callable[[], Predictor],
    dev_docs: Sequence[Doc],
    classes: Sequence[str],
    track: str = "S",
    seed: int = 0,
    min_support: int = 1,
    abstain_label: Optional[str] = None,
    keep_proba: bool = True,
) -> CVResult:
    """CV 5-fold (cột fold của `seed`) trên DEV. Mỗi tài liệu được dự đoán đúng 1 lần (out-of-fold)."""
    folds = sorted({d.folds[seed] for d in dev_docs})
    rows, probas, fold_scores = [], [], []
    pred_classes = None
    for f in folds:
        tr = [d for d in dev_docs if d.folds[seed] != f]
        te = [d for d in dev_docs if d.folds[seed] == f]
        p = factory()
        p.fit(tr)
        pr = p.predict(te)
        yt = [d.target(track) for d in te]
        sc = score_predictions(yt, pr.labels, classes, pr.proba if pr.classes == list(classes) else None,
                               min_support=min_support, abstain_label=abstain_label)
        sc.pop("per_class")
        sc.update(fold=f, seed=seed)
        fold_scores.append(sc)
        conf = pr.confidence if pr.proba is not None else np.full(len(te), np.nan)
        for i, d in enumerate(te):
            rows.append(dict(doc_id=d.doc_id, fold=f, y_true=yt[i], y_pred=pr.labels[i], conf=float(conf[i])))
        if pr.proba is not None and keep_proba:
            probas.append(pr.proba)
            pred_classes = pr.classes
    oof = pd.DataFrame(rows)
    proba = np.vstack(probas) if probas and len(probas) == len(folds) else None
    return CVResult(seed, oof, proba, pred_classes, fold_scores)


def summarize_folds(fold_scores: Sequence[Dict], metrics=("accuracy", "macro_f1", "weighted_f1")) -> Dict[str, float]:
    out = {}
    for m in metrics:
        v = np.array([s[m] for s in fold_scores], dtype=float)
        out[f"{m}_mean"] = float(np.nanmean(v))
        out[f"{m}_std"] = float(np.nanstd(v, ddof=1)) if np.isfinite(v).sum() > 1 else float("nan")
    return out


# ---------------------------------------------------------------------------
# Bảng kết quả dùng chung
# ---------------------------------------------------------------------------
RESULT_COLUMNS = [
    "run_id", "timestamp", "method", "track", "text_source", "split", "n", "accuracy", "accuracy_ci_lo", "accuracy_ci_hi",
    "macro_f1", "macro_f1_ci_lo", "macro_f1_ci_hi", "macro_f1_std", "coverage", "acc_on_covered",
    "latency_ms_median", "latency_ms_p95", "labels_file", "labels_sha", "notes",
]


def new_run_id() -> str:
    """Id lần chạy không phụ thuộc git: thời gian UTC + 6 hex ngẫu nhiên."""
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:6]


def append_result_row(row: Dict, path: Path | str = RESULTS_TABLE) -> None:
    """Thêm MỘT dòng vào results_table.csv (tạo file + header nếu chưa có). Khóa không biết bị bỏ qua; thiếu -> rỗng."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    row = dict(row)
    row.setdefault("timestamp", _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"))
    for k in ("run_id", "method", "track", "text_source", "split", "labels_sha"):
        if k not in row:
            raise KeyError(f"Dòng kết quả thiếu '{k}'")
    new = not path.exists() or path.stat().st_size == 0
    with open(path, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=RESULT_COLUMNS, extrasaction="ignore")
        if new:
            w.writeheader()
        def cell(v):
            if isinstance(v, (float, np.floating)):
                return "" if np.isnan(v) else f"{float(v):.6g}"
            return "" if v is None else v

        w.writerow({c: cell(row.get(c, "")) for c in RESULT_COLUMNS})
