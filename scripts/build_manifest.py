#!/usr/bin/env python
"""Build data/manifest.csv + data/duplicate_groups.csv for the labelled sample PDFs.

Run (from the repo root):
    .venv\\Scripts\\python.exe -X utf8 scripts\\build_manifest.py

What it does (everything local, nothing leaves the machine):
  1. Walk <samples-dir> and fingerprint every PDF: sha256, size, page count, text-layer
     coverage, scanned/born-digital flag, PDF metadata, 64-bit difference hash (dHash) of
     page 1 and of the last page, plus a 200x283 grey render used for a pixel-difference check.
  2. Detect TRUE DUPLICATES (the same document filed twice) with union-find over three kinds
     of evidence: identical bytes / near-identical page images / near-identical page-1 text.
  3. Detect TEMPLATE GROUPS (different documents filled into the same form). They are NOT
     duplicates, but must stay together in one cross-validation fold.

Rules (thresholds are CLI options; the defaults were validated empirically, see
teams/00_data_and_eval/reports/01_duplicates.md):

  TRUE DUPLICATE edge between documents A and B (same document filed twice) if ANY of
    bytes : sha256(A) == sha256(B). Conclusive.
    image : page_count equal AND dHash(first page) and dHash(last page) Hamming <=
            --image-hamming AND pixel difference (fraction of pixels whose grey level differs
            by > 30 on a 200x283 blurred render) <= --pixel-dup on BOTH first and last page
            AND (if both have text) text similarity >= --text-dup-sim.
            Meaning "same scan/render, only re-encoded".
    text  : normalised page-1 text IDENTICAL (similarity >= --text-dup-sim) AND normalised
            length >= --text-min-len AND page_count equal AND pixel difference <=
            --text-dup-pixel on first and last page. Meaning "same document re-scanned".
  Why not "text similarity >= 0.95" as duplicate evidence: filled-in copies of one form
  routinely have 0.93-0.99 similarity (different date/amount/customer) while being different
  documents; see the report. Hence 0.95 only creates TEMPLATE edges.

  TEMPLATE edge (A and B are different documents but the same form / letterhead):
    normalised page-1 text similarity >= --template-sim, or
    similarity >= --template-loose-sim AND first-page pixel difference <= --template-pixel
    (same printed layout, different filled-in values).
  template_group = connected components of (true-duplicate edges + template edges); it is
  the group to use for GroupKFold. template_group_size counts every member.

is_scanned heuristic: fewer than half of the pages carry a text layer (>= 50 characters of
PyMuPDF text) AND at least one page contains a raster image. Everything else is
"born-digital".

Determinism: files are processed in sorted NFC relative-path order, no randomness, output
sorted by relative_path, group ids numbered by the smallest relative_path in the group.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

import cv2
import fitz  # PyMuPDF
import numpy as np
from PIL import Image
from rapidfuzz import fuzz, process

REPO = Path(__file__).resolve().parent.parent
DEFAULT_SAMPLES = REPO / "docs" / "_chot_samples_phanloaitailieu"
DEFAULT_OUT = REPO / "data" / "manifest.csv"
DEFAULT_GROUPS = REPO / "data" / "duplicate_groups.csv"
DEFAULT_BASELINE = REPO / "data" / "baseline_ocr_335.jsonl"
DEFAULT_STATS = REPO / "teams" / "00_data_and_eval" / "reports" / "01_duplicates_stats.json"

TEXT_LAYER_MIN_CHARS = 50
RENDER_WIDTH = 256  # px, page rendered at this width before hashing

MANIFEST_COLUMNS = [
    "doc_id", "relative_path", "file_name", "folder_label", "sha256", "size_bytes",
    "page_count", "pages_with_text_layer", "is_scanned", "created", "producer",
    "page1_dhash", "last_page_dhash", "exact_dup_group", "near_dup_group",
    "dup_group_size", "dup_cross_label", "template_group", "template_group_size",
]
GROUP_COLUMNS = [
    "near_dup_group", "doc_id", "relative_path", "folder_label", "group_size",
    "group_cross_label", "evidence", "nearest_doc_id", "page1_hamming", "page_pixel_diff",
    "text_similarity", "page_count",
]


# ----------------------------------------------------------------------------- basics
def norm_rel(path: Path, root: Path) -> str:
    """Path relative to root, forward slashes, Unicode NFC (the doc_id input)."""
    rel = path.relative_to(root).as_posix()
    return unicodedata.normalize("NFC", rel)


def make_doc_id(rel: str) -> str:
    return hashlib.sha1(rel.encode("utf-8")).hexdigest()[:12]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize_text(s: str) -> str:
    """Lower-case, strip Vietnamese diacritics, keep [a-z0-9] only (also drops spaces:
    OCR often glues or splits words, so spacing carries no information)."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("đ", "d").replace("Đ", "D").lower()
    return re.sub(r"[^a-z0-9]+", "", s)


def pdf_date(s: str) -> str:
    """'D:20220929210231-08'00'' -> '2022-09-29'. Empty if unparsable."""
    m = re.match(r"D:(\d{4})(\d{2})(\d{2})", s or "")
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else ""


# ----------------------------------------------------------------------------- images
def render_gray(page: "fitz.Page") -> Image.Image:
    zoom = RENDER_WIDTH / max(page.rect.width, 1.0)
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), colorspace=fitz.csGRAY, alpha=False)
    return Image.frombytes("L", (pix.width, pix.height), pix.samples)


def dhash64(img: Image.Image) -> int:
    """64-bit difference hash: 9x8 grey thumbnail, bit = left pixel > right pixel."""
    a = np.asarray(img.resize((9, 8), Image.BOX), dtype=np.int16)
    bits = (a[:, :-1] > a[:, 1:]).flatten()
    v = 0
    for b in bits:
        v = (v << 1) | int(b)
    return v


PIX_W, PIX_H = 200, 283


def pixel_ref(img: Image.Image) -> np.ndarray:
    """200x283 grey render, lightly blurred, int16 -- the reference for pixel-difference."""
    a = np.asarray(img.resize((PIX_W, PIX_H), Image.BOX), dtype=np.float32)
    return cv2.GaussianBlur(a, (0, 0), 1.0).astype(np.int16)


def pixel_diff(a: np.ndarray, b: np.ndarray) -> float:
    """Fraction of pixels whose grey level differs by more than 30 (0 = identical render)."""
    return float((np.abs(a - b) > 30).mean())


def hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


# ----------------------------------------------------------------------------- features
def fingerprint(path: Path) -> dict:
    rec = {
        "sha256": sha256_file(path), "size_bytes": path.stat().st_size,
        "page_count": 0, "pages_with_text_layer": 0, "pages_with_images": 0,
        "created": "", "producer": "", "page1_dhash": 0, "last_page_dhash": 0,
        "pix1": None, "pixN": None, "text_layer_p1": "", "error": "",
    }
    try:
        doc = fitz.open(path)
        rec["page_count"] = doc.page_count
        meta = doc.metadata or {}
        rec["created"] = pdf_date(meta.get("creationDate", ""))
        rec["producer"] = " ".join((meta.get("producer") or "").split())
        for i, page in enumerate(doc):
            txt = page.get_text()
            if len(txt.strip()) >= TEXT_LAYER_MIN_CHARS:
                rec["pages_with_text_layer"] += 1
            if page.get_images():
                rec["pages_with_images"] += 1
            if i == 0:
                rec["text_layer_p1"] = txt
        first = render_gray(doc[0])
        last = first if doc.page_count == 1 else render_gray(doc[doc.page_count - 1])
        rec["page1_dhash"], rec["last_page_dhash"] = dhash64(first), dhash64(last)
        rec["pix1"], rec["pixN"] = pixel_ref(first), pixel_ref(last)
        doc.close()
    except Exception as exc:  # corrupt / encrypted file: keep the row, flag it
        rec["error"] = f"{type(exc).__name__}: {exc}"
    pc, tl = rec["page_count"], rec["pages_with_text_layer"]
    rec["is_scanned"] = bool(pc and tl / pc < 0.5 and rec["pages_with_images"] > 0)
    return rec


def load_baseline_text(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if path.exists():
        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    r = json.loads(line)
                    out[unicodedata.normalize("NFC", r["relative_path"].replace("\\", "/"))] = r["ocr_text"]
    return out


# ----------------------------------------------------------------------------- grouping
class UnionFind:
    def __init__(self, n: int):
        self.p = list(range(n))

    def find(self, x: int) -> int:
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[max(ra, rb)] = min(ra, rb)  # deterministic: smaller index is the root


def hamming_matrix(vals: list[int]) -> np.ndarray:
    a = np.array(vals, dtype=np.uint64)
    x = (a[:, None] ^ a[None, :]).view(np.uint8).reshape(len(vals), len(vals), 8)
    return np.unpackbits(x, axis=2).sum(axis=2).astype(np.int16)


def text_similarity_matrix(texts: list[str]) -> np.ndarray:
    """fuzz.ratio/100 for every pair of non-empty texts; 0 if either text is empty."""
    n = len(texts)
    sim = np.zeros((n, n), np.float32)
    idx = [i for i, t in enumerate(texts) if t]
    if idx:
        m = process.cdist([texts[i] for i in idx], [texts[i] for i in idx],
                          scorer=fuzz.ratio, dtype=np.float32, workers=1) / 100.0
        sim[np.ix_(idx, idx)] = m
    np.fill_diagonal(sim, 0.0)
    return sim


class Metrics:
    """All pairwise evidence. Pixel differences are computed lazily and cached."""

    def __init__(self, recs: list[dict], texts: list[str]):
        self.recs, self.texts = recs, texts
        self.n = len(recs)
        self.h1 = hamming_matrix([r["page1_dhash"] for r in recs])
        self.hn = hamming_matrix([r["last_page_dhash"] for r in recs])
        self.sim = text_similarity_matrix(texts)
        self.tlen = np.array([len(t) for t in texts])
        self.pcs = np.array([r["page_count"] for r in recs])
        self._cache: dict[tuple[int, int, str], float] = {}

    def pix(self, i: int, j: int, which: str) -> float:
        """Pixel difference of the first ('1') or last ('N') page; 1.0 if a render is missing."""
        key = (i, j, which)
        if key not in self._cache:
            a, b = self.recs[i]["pix" + which], self.recs[j]["pix" + which]
            self._cache[key] = 1.0 if a is None or b is None else pixel_diff(a, b)
        return self._cache[key]

    def pix_max(self, i: int, j: int) -> float:
        """Worst of first/last page (last page == first page for 1-page documents)."""
        d1 = self.pix(i, j, "1")
        return d1 if self.pcs[i] == 1 else max(d1, self.pix(i, j, "N"))


def group_documents(recs, texts, args):
    n = len(recs)
    M = Metrics(recs, texts)
    dup_edges: dict[tuple[int, int], set[str]] = {}
    tmpl_edges: list[tuple[int, int]] = []
    for i in range(n):
        for j in range(i + 1, n):
            ev = set()
            same_pc = M.pcs[i] == M.pcs[j]
            if recs[i]["sha256"] == recs[j]["sha256"]:
                ev.add("bytes")
            both_text = M.tlen[i] > 0 and M.tlen[j] > 0
            text_ok = (not both_text) or M.sim[i, j] >= args.text_dup_sim
            if (same_pc and text_ok and M.h1[i, j] <= args.image_hamming
                    and (M.pcs[i] == 1 or M.hn[i, j] <= args.image_hamming)
                    and M.pix_max(i, j) <= args.pixel_dup):
                ev.add("image")
            if (same_pc and M.sim[i, j] >= args.text_dup_sim and min(M.tlen[i], M.tlen[j]) >= args.text_min_len
                    and M.pix_max(i, j) <= args.text_dup_pixel):
                ev.add("text")
            if ev:
                dup_edges[(i, j)] = ev
            elif M.sim[i, j] >= args.template_sim or (
                    M.sim[i, j] >= args.template_loose_sim and M.pix(i, j, "1") <= args.template_pixel):
                tmpl_edges.append((i, j))
    uf = UnionFind(n)  # true duplicates
    for (i, j) in dup_edges:
        uf.union(i, j)
    ex = UnionFind(n)  # identical bytes only
    for (i, j), ev in dup_edges.items():
        if "bytes" in ev:
            ex.union(i, j)
    tf = UnionFind(n)  # templates (includes duplicates)
    for (i, j) in dup_edges:
        tf.union(i, j)
    for (i, j) in tmpl_edges:
        tf.union(i, j)
    return uf, ex, tf, dup_edges, M


def label_groups(uf: UnionFind, rels: list[str], prefix: str) -> dict[int, str]:
    """root index -> 'PREFIXnnn' for components with >=2 members, ordered by smallest rel."""
    comp: dict[int, list[int]] = {}
    for i in range(len(rels)):
        comp.setdefault(uf.find(i), []).append(i)
    multi = sorted((min(rels[k] for k in m), r) for r, m in comp.items() if len(m) >= 2)
    return {r: f"{prefix}{k + 1:03d}" for k, (_, r) in enumerate(multi)}


# ----------------------------------------------------------------------------- stats
HAM_BINS = [0, 1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 65]
PIX_BINS = [0, 0.0005, 0.001, 0.002, 0.004, 0.008, 0.016, 0.03, 0.06, 0.12, 1.0001]


def distance_stats(M: Metrics, recs) -> dict:
    """Distributions used to choose/validate the thresholds (written to the stats json)."""
    n = M.n
    h_byte, h_other, p_byte, p_other, border = [], [], [], [], []
    for i in range(n):
        for j in range(i + 1, n):
            is_byte = recs[i]["sha256"] == recs[j]["sha256"]
            (h_byte if is_byte else h_other).append(int(M.h1[i, j]))
            if M.pcs[i] == M.pcs[j] and (M.h1[i, j] <= 8 or M.hn[i, j] <= 8 or M.sim[i, j] >= 0.75):
                d = M.pix_max(i, j)
                (p_byte if is_byte else p_other).append(d)
                if not is_byte:
                    border.append((d, i, j))
    border.sort()

    def hist(vals, bins):
        return [int(x) for x in np.histogram(vals, bins=bins)[0]]

    return {
        "hamming_bins": HAM_BINS,
        "page1_hamming_hist_byte_identical_pairs": hist(h_byte, HAM_BINS),
        "page1_hamming_hist_other_pairs": hist(h_other, HAM_BINS),
        "pixel_bins": PIX_BINS,
        "pixel_diff_hist_byte_identical_pairs": hist(p_byte, PIX_BINS),
        "pixel_diff_hist_candidate_other_pairs": hist(p_other, PIX_BINS),
        "n_pairs_total": n * (n - 1) // 2,
        "n_byte_identical_pairs": len(h_byte),
        "n_other_pairs_hamming_le_2": int(sum(1 for h in h_other if h <= 2)),
        "n_other_pairs_hamming_le_4": int(sum(1 for h in h_other if h <= 4)),
        "lowest_pixel_diff_non_byte_pairs": [
            {"pixel_diff": round(d, 5), "a": recs[i]["relative_path"], "b": recs[j]["relative_path"],
             "hamming_p1": int(M.h1[i, j]), "hamming_last": int(M.hn[i, j]),
             "text_sim": round(float(M.sim[i, j]), 3), "page_count": int(M.pcs[i])}
            for d, i, j in border[:25]],
    }


# ----------------------------------------------------------------------------- main
THRESHOLD_ARGS = ["image_hamming", "pixel_dup", "text_dup_sim", "text_min_len", "text_dup_pixel",
                  "template_sim", "template_loose_sim", "template_pixel"]


def build(args):
    root = Path(args.samples_dir)
    files = sorted(root.rglob("*.pdf"), key=lambda p: norm_rel(p, root))
    base = load_baseline_text(Path(args.baseline))
    recs, rels, texts = [], [], []
    for p in files:
        rel = norm_rel(p, root)
        rec = fingerprint(p)
        rec["relative_path"] = rel
        rec["file_name"] = unicodedata.normalize("NFC", p.name)
        rec["folder_label"] = unicodedata.normalize("NFC", rel.rsplit("/", 1)[0]) if "/" in rel else ""
        rec["doc_id"] = make_doc_id(rel)
        raw = base.get(rel) or rec["text_layer_p1"]  # root PDFs are not in the jsonl
        texts.append(normalize_text(raw))
        recs.append(rec)
        rels.append(rel)

    uf, ex, tf, edges, M = group_documents(recs, texts, args)
    near_ids = label_groups(uf, rels, "D")
    exact_ids = label_groups(ex, rels, "E")
    tmpl_ids = label_groups(tf, rels, "T")

    def members(u: UnionFind, i: int) -> list[int]:
        r = u.find(i)
        return [k for k in range(len(recs)) if u.find(k) == r]

    rows, grows = [], []
    for i, r in enumerate(recs):
        near = near_ids.get(uf.find(i), "")
        m = members(uf, i) if near else [i]
        labels = {recs[k]["folder_label"] for k in m}
        tm = members(tf, i) if tmpl_ids.get(tf.find(i)) else [i]
        rows.append({
            "doc_id": r["doc_id"], "relative_path": r["relative_path"], "file_name": r["file_name"],
            "folder_label": r["folder_label"], "sha256": r["sha256"], "size_bytes": r["size_bytes"],
            "page_count": r["page_count"], "pages_with_text_layer": r["pages_with_text_layer"],
            "is_scanned": str(r["is_scanned"]), "created": r["created"], "producer": r["producer"],
            "page1_dhash": f"{r['page1_dhash']:016x}", "last_page_dhash": f"{r['last_page_dhash']:016x}",
            "exact_dup_group": exact_ids.get(ex.find(i), ""), "near_dup_group": near,
            "dup_group_size": len(m), "dup_cross_label": str(bool(near) and len(labels) >= 2),
            "template_group": tmpl_ids.get(tf.find(i), ""), "template_group_size": len(tm),
        })
        if near:
            others = [k for k in m if k != i]
            best = min(others, key=lambda k: (int(M.h1[i, k]), M.pix_max(i, k), k))
            ev = set()
            for k in others:
                ev |= edges.get((min(i, k), max(i, k)), set())
            grows.append({
                "near_dup_group": near, "doc_id": r["doc_id"], "relative_path": r["relative_path"],
                "folder_label": r["folder_label"], "group_size": len(m),
                "group_cross_label": str(len(labels) >= 2),
                "evidence": "+".join(e for e in ("bytes", "image", "text") if e in ev) or "transitive",
                "nearest_doc_id": recs[best]["doc_id"], "page1_hamming": int(M.h1[i, best]),
                "page_pixel_diff": f"{M.pix_max(i, best):.4f}", "text_similarity": f"{float(M.sim[i, best]):.3f}",
                "page_count": r["page_count"],
            })
    grows.sort(key=lambda g: (g["near_dup_group"], g["relative_path"]))
    stats = distance_stats(M, recs)
    stats["thresholds"] = {k: getattr(args, k) for k in THRESHOLD_ARGS}
    return rows, grows, stats


def write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:  # BOM so Excel opens UTF-8
        w = csv.DictWriter(f, fieldnames=columns, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--samples-dir", default=str(DEFAULT_SAMPLES))
    ap.add_argument("--out", default=str(DEFAULT_OUT), help="manifest.csv path")
    ap.add_argument("--groups-out", default=str(DEFAULT_GROUPS), help="duplicate_groups.csv path")
    ap.add_argument("--stats-out", default=str(DEFAULT_STATS), help="distance-distribution json ('' to skip)")
    ap.add_argument("--baseline", default=str(DEFAULT_BASELINE), help="baseline OCR jsonl (page-1 text)")
    ap.add_argument("--image-hamming", type=int, default=4, help="max dHash Hamming distance (of 64), first and last page")
    ap.add_argument("--pixel-dup", type=float, default=0.0005, help="max pixel difference for image dup")
    ap.add_argument("--text-dup-sim", type=float, default=0.999, help="text similarity needed for text dup (identical)")
    ap.add_argument("--text-min-len", type=int, default=150, help="min normalised text length for text-only dup")
    ap.add_argument("--text-dup-pixel", type=float, default=0.02, help="max pixel difference for text dup")
    ap.add_argument("--template-sim", type=float, default=0.95, help="text similarity for a template edge")
    ap.add_argument("--template-loose-sim", type=float, default=0.75, help="looser text similarity, needs layout match")
    ap.add_argument("--template-pixel", type=float, default=0.03, help="max page-1 pixel difference for loose template edge")
    return ap.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    rows, grows, stats = build(args)
    write_csv(Path(args.out), MANIFEST_COLUMNS, rows)
    write_csv(Path(args.groups_out), GROUP_COLUMNS, grows)
    if args.stats_out:
        Path(args.stats_out).parent.mkdir(parents=True, exist_ok=True)
        with open(args.stats_out, "w", encoding="utf-8", newline="\n") as f:
            json.dump(stats, f, ensure_ascii=False, indent=1, sort_keys=True)
            f.write("\n")
    ndup = len({g["near_dup_group"] for g in grows})
    ntmpl = len({r["template_group"] for r in rows if r["template_group"]})
    print(f"manifest rows: {len(rows)} -> {args.out}")
    print(f"true-duplicate groups: {ndup}, documents involved: {len(grows)} -> {args.groups_out}")
    print(f"unique documents after de-duplication: {len(rows) - len(grows) + ndup}; template groups: {ntmpl}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
