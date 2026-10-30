r"""validate_batch.py - T6: kiem mot LO ban chep chu cua LLM (doc anh trang) truoc khi dung lam du lieu "bac".

Ly do (README nhom 1, T6): da xay ra mot dot phai lam lai vi tac nhan chep chu cho 12 trang ma anh cua chung nap loi. LLM khong bao
"khong thay anh", no bia. Vi vay moi lo phai tu chung minh la mo hinh THUC SU nhin thay anh bang cac trang da biet dap an:

  1. TRANG DA BIET (control_textlayer): trang born-digital tron vao lo; dap an = text layer cua PDF. Cham bag_recall (khong phu thuoc thu tu
     doc) va CER giong score_llm_transcripts.py. Moi trang phai dat `min_page_recall`, trung binh phai dat `min_mean_recall` va `max_mean_cer`.
  2. TRANG TRANG (control_blank): trang khong co chu. Neu ban chep co >= `max_blank_chars`+1 ky tu chu/so (sau khi bo ghi chu [..]) -> LO KHONG
     HOP LE (mo hinh dang bia ra chu cho trang no khong thay).
  3. SO ANH NAP DUOC: tac nhan chep phai ghi so anh nap duoc vao `_images_loaded.txt` (hoac --images-loaded N); phai bang so muc cua lo.
     Khong ghi, hoac khac -> khong hop le.  Moi muc phai co ban chep, khong co ban chep la muc thua.
  4. KIEM CHEO: voi trang that (real), 4-gram ky tu da bo dau/khoang trang cua ban chep phai phu duoc phan lon 4-gram cua OCR doc lap
     (mac dinh data/ocr_v2.jsonl) nhu data/ocr_llm_haiku/_check_vs_baseline.py. Trang < `suspect_recall` la nghi van; lo khong hop le neu
     trung vi recall < `min_median_recall` hoac ty le trang nghi van > `max_suspect_share`.  (Chi xet trang ma OCR co >= 44 ky tu chu so.)

Ket qua: `<batch>/_validation.json` (trang thai `valid`/`invalid`, ly do, so do, hash noi dung cac tep .txt) va ma thoat 0/1. scripts/assemble_llm_ocr.py
chi nhan lo co _validation.json `valid` VA hash khop noi dung hien tai (sua tep sau khi kiem -> tu choi).

Manifest (CSV UTF-8, mot dong/muc):  item_id,kind,relative_path,page0,doc_id,page
  kind = real | control_textlayer | control_blank;  item_id = ten tep .txt (khong duoi) trong thu muc lo.
  control_textlayer can relative_path + page0 (dem tu 0, nhu pages.csv); real can doc_id + page (dem tu 1, nhu ocr_v2.jsonl).
  Neu khong co manifest: moi `<doc_id>_p<N>.txt` la muc `real`; khi do lo thieu trang kiem nen KHONG hop le (khong the chung minh).

Chay:
  .venv\Scripts\python.exe -X utf8 teams\team1_ocr\experiments\03_llm_silver\validate_batch.py --batch-dir <thu muc .txt> --manifest <batch_manifest.csv> [--images-loaded N]
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import re
import sys
import unicodedata
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median
from typing import Callable, Dict, List, Optional

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO))

STAMP_NAME = "_validation.json"
IMAGES_FILE = "_images_loaded.txt"
_MARK = re.compile(r"\[[^\]\n]{0,200}\]")    # [dau: ...], [chu ky], [?], [trang trang]


@dataclass
class Thresholds:
    """Nguong dat sau khi xem so lieu hien co (xem `Hieu chuan` trong RESULTS.md cua 03_llm_silver):
    39 trang born-digital Haiku: bag_recall thap nhat 0.987, trung binh 0.995, CER 0.105; 477 trang that doi chieu voi ocr_v2: trung vi 0.93,
    phan vi 1% 0.27, 5% 0.60; trang ghep nham tai lieu: trung vi 0.19."""
    min_page_recall: float = 0.90        # moi trang da biet
    min_mean_recall: float = 0.95
    max_mean_cer: float = 0.25
    max_blank_chars: int = 4             # ky tu chu/so toi da cho phep trong ban chep cua trang trang
    min_known: int = 3                   # so trang da biet toi thieu moi lo
    min_blank: int = 1                   # so trang trang toi thieu moi lo
    suspect_recall: float = 0.30         # trang that co recall 4-gram < nguong nay la nghi van
    min_median_recall: float = 0.75
    max_suspect_share: float = 0.10
    min_ocr_chars: int = 44              # chi kiem cheo trang ma OCR doc lap co >= ngan nay ky tu chu/so (4-gram can du dai)
    max_recommended_items: int = 60      # lo lon hon: chi CANH BAO (khong loai). Mo phong (RESULTS.md): 12 trang bia/50 trang bi bat 99%, /100 trang chi 46%, /200 trang 0%


# ----------------------------------------------------------------------------------------------------- tien ich van ban
def strip_markers(text: str) -> str:
    return re.sub(r"[ \t]+", " ", _MARK.sub(" ", text).replace("|", " ")).strip()


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", nfc(s)).strip()


def fold(s: str) -> str:
    """Bo dau, 'd' gach -> d, chi giu a-z0-9 (giong _check_vs_baseline.py)."""
    s = unicodedata.normalize("NFD", s.replace("đ", "d").replace("Đ", "D"))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]+", "", s)


def grams(s: str, n: int = 4):
    return collections.Counter(s[i:i + n] for i in range(len(s) - n + 1))


def gram_recall(ref_text: str, hyp_text: str) -> Optional[Dict[str, float]]:
    """Ty le 4-gram cua `ref` (OCR doc lap) duoc `hyp` (ban chep) phu, va nguoc lai. None neu ref qua ngan."""
    a, b = fold(ref_text), fold(hyp_text)
    ga, gb = grams(a), grams(b)
    ov = sum((ga & gb).values())
    return dict(recall=ov / max(sum(ga.values()), 1), precision=ov / max(sum(gb.values()), 1), n_ref=len(a), n_hyp=len(b))


def bag_recall(gt: str, hyp: str) -> float:
    g = collections.Counter(nfc(norm_ws(gt).casefold()).split())
    h = collections.Counter(nfc(norm_ws(hyp).casefold()).split())
    return sum((g & h).values()) / max(sum(g.values()), 1)


def cer(gt: str, hyp: str) -> float:
    from rapidfuzz.distance import Levenshtein
    g, h = nfc(norm_ws(gt).casefold()), nfc(norm_ws(hyp).casefold())
    return Levenshtein.distance(g, h) / max(len(g), 1)


def alnum_count(text: str) -> int:
    return sum(1 for c in strip_markers(text) if c.isalnum())


def content_hash(batch_dir: Path) -> str:
    """sha1 theo (ten tep, noi dung) cua moi *.txt khong bat dau bang '_' trong thu muc lo. assemble_llm_ocr.py tinh y het."""
    h = hashlib.sha1()
    for p in sorted(Path(batch_dir).glob("*.txt")):
        if p.name.startswith("_"):
            continue
        h.update(p.name.encode("utf-8") + b"\0" + p.read_bytes() + b"\0")
    return h.hexdigest()


# ----------------------------------------------------------------------------------------------------- kiem
def validate_batch(batch_dir: Path, items: List[dict], th: Thresholds,
                   truth_textlayer: Callable[[dict], str], ocr_reference: Callable[[dict], Optional[str]],
                   images_loaded: Optional[int]) -> dict:
    """Thuan tuy (khong doc PDF/OCR truc tiep): `truth_textlayer(item)` tra text layer, `ocr_reference(item)` tra van ban OCR doc lap hoac None."""
    batch_dir = Path(batch_dir)
    reasons: List[str] = []
    rep: Dict[str, object] = dict(batch_dir=str(batch_dir), n_items=len(items), thresholds=asdict(th))
    texts: Dict[str, Optional[str]] = {}
    for it in items:
        f = batch_dir / f"{it['item_id']}.txt"
        texts[it["item_id"]] = f.read_text(encoding="utf-8") if f.exists() else None
    missing = [k for k, v in texts.items() if v is None]
    names = {p.stem for p in batch_dir.glob("*.txt") if not p.name.startswith("_")}
    extra = sorted(names - set(texts))
    rep["missing_transcripts"] = missing
    rep["extra_transcripts"] = extra
    if missing:
        reasons.append(f"thieu ban chep cho {len(missing)} muc (vd {missing[:3]})")
    if extra:
        reasons.append(f"{len(extra)} tep .txt khong co trong manifest (vd {extra[:3]})")

    # 3. so anh nap duoc
    rep["images_loaded"] = images_loaded
    rep["images_expected"] = len(items)
    if images_loaded is None:
        reasons.append(f"khong co so anh nap duoc ({IMAGES_FILE} hoac --images-loaded); khong the chung minh mo hinh thay anh")
    elif images_loaded != len(items):
        reasons.append(f"so anh nap duoc {images_loaded} != so muc cua lo {len(items)}")

    # 2. trang trang
    blanks = [it for it in items if it["kind"] == "control_blank"]
    blank_rows = []
    for it in blanks:
        t = texts.get(it["item_id"])
        n = alnum_count(t) if t is not None else None
        blank_rows.append(dict(item_id=it["item_id"], alnum_chars=n))
    rep["blank"] = blank_rows
    bad_blank = [r for r in blank_rows if r["alnum_chars"] is not None and r["alnum_chars"] > th.max_blank_chars]
    if len(blanks) < th.min_blank:
        reasons.append(f"lo chi co {len(blanks)} trang trang (can >= {th.min_blank})")
    if bad_blank:
        reasons.append(f"{len(bad_blank)}/{len(blanks)} trang TRANG ma ra chu (vd {[r['item_id'] for r in bad_blank[:3]]}): mo hinh bia chu cho anh khong thay")

    # 1. trang da biet
    known = [it for it in items if it["kind"] == "control_textlayer"]
    known_rows = []
    for it in known:
        t = texts.get(it["item_id"])
        if t is None:
            continue
        gt, hyp = truth_textlayer(it), strip_markers(t)
        known_rows.append(dict(item_id=it["item_id"], bag_recall=bag_recall(gt, hyp), cer=cer(gt, hyp), n_gt=len(gt), n_hyp=len(hyp)))
    rep["known"] = known_rows
    if len(known) < th.min_known:
        reasons.append(f"lo chi co {len(known)} trang da biet (can >= {th.min_known})")
    if known_rows:
        mr, mc = mean(r["bag_recall"] for r in known_rows), mean(r["cer"] for r in known_rows)
        worst = min(known_rows, key=lambda r: r["bag_recall"])
        rep["known_summary"] = dict(n=len(known_rows), mean_bag_recall=mr, min_bag_recall=worst["bag_recall"], mean_cer=mc)
        low = [r for r in known_rows if r["bag_recall"] < th.min_page_recall]
        if low:
            reasons.append(f"{len(low)}/{len(known_rows)} trang da biet co bag_recall < {th.min_page_recall} (thap nhat {worst['bag_recall']:.3f}, {worst['item_id']})")
        if mr < th.min_mean_recall:
            reasons.append(f"bag_recall trung binh trang da biet {mr:.3f} < {th.min_mean_recall}")
        if mc > th.max_mean_cer:
            reasons.append(f"CER trung binh trang da biet {mc:.3f} > {th.max_mean_cer}")

    # 4. kiem cheo
    real_rows, skipped = [], 0
    for it in items:
        if it["kind"] != "real" or texts.get(it["item_id"]) is None:
            continue
        ref = ocr_reference(it)
        if ref is None or len(fold(ref)) < th.min_ocr_chars:
            skipped += 1
            continue
        g = gram_recall(ref, strip_markers(texts[it["item_id"]]))
        real_rows.append(dict(item_id=it["item_id"], recall=g["recall"], precision=g["precision"], n_ocr=g["n_ref"], n_llm=g["n_hyp"]))
    rep["cross_check"] = real_rows
    rep["cross_check_skipped_short_or_missing_ocr"] = skipped
    if real_rows:
        med = median(r["recall"] for r in real_rows)
        susp = [r for r in real_rows if r["recall"] < th.suspect_recall]
        share = len(susp) / len(real_rows)
        rep["cross_check_summary"] = dict(n=len(real_rows), median_recall=med, suspect=len(susp), suspect_share=share,
                                          suspects=[r["item_id"] for r in susp][:30])
        if med < th.min_median_recall:
            reasons.append(f"kiem cheo: trung vi recall 4-gram {med:.3f} < {th.min_median_recall} tren {len(real_rows)} trang that")
        if share > th.max_suspect_share:
            reasons.append(f"kiem cheo: {len(susp)}/{len(real_rows)} trang that nghi van (recall < {th.suspect_recall}) = {share:.3f} > {th.max_suspect_share}")
    elif any(it["kind"] == "real" for it in items):
        rep["cross_check_summary"] = dict(n=0)

    rep["warnings"] = []
    if len(items) > th.max_recommended_items:
        rep["warnings"].append(f"lo {len(items)} muc > {th.max_recommended_items}: kiem cheo kem nhay voi mot nhom nho trang bia; nen chia lo <= {th.max_recommended_items} muc, moi lo co trang kiem rieng")
    rep["reasons"] = reasons
    rep["status"] = "valid" if not reasons else "invalid"
    rep["content_sha1"] = content_hash(batch_dir)
    rep["created_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return rep


# ----------------------------------------------------------------------------------------------------- doi tuong that
def read_manifest(path: Path) -> List[dict]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        return [dict(r) for r in csv.DictReader(f)]


def manifest_from_pages_csv(path: Path) -> List[dict]:
    """Doc pages.csv cua 03_llm_silver (page_id,kind,relative_path,page0): gold_textlayer -> control_textlayer, con lai -> real."""
    sys.path.insert(0, str(REPO / "scripts"))
    from build_ocr_dataset import make_doc_id
    items = []
    for r in read_manifest(path):
        rel = nfc(r["relative_path"])
        known = r["kind"] == "gold_textlayer"
        items.append(dict(item_id=r["page_id"], kind="control_textlayer" if known else "real", relative_path=rel, page0=r["page0"],
                          doc_id=make_doc_id(rel), page=str(int(r["page0"]) + 1)))
    return items


def manifest_from_dir(batch_dir: Path) -> List[dict]:
    items = []
    for p in sorted(Path(batch_dir).glob("*.txt")):
        m = re.match(r"^(?P<doc>[0-9a-f]{12})_p(?P<page>\d+)$", p.stem)
        if m and not p.name.startswith("_"):
            items.append(dict(item_id=p.stem, kind="real", relative_path="", page0="", doc_id=m["doc"], page=m["page"]))
    return items


def make_providers(ocr_jsonl: Path, corpus: Optional[Path] = None):
    """truth_textlayer: doc text layer bang PyMuPDF, sap theo dong nhu ocrlib.gt_words_text;  ocr_reference: tra cuu ocr_jsonl theo (doc_id, page)."""
    import fitz
    from src.ocr.vietocr_engine import boxes_to_text
    sys.path.insert(0, str(REPO / "scripts"))
    from build_ocr_dataset import CORPUS, list_pdfs
    pdfs = list_pdfs(corpus or CORPUS)
    ocr: Dict[tuple, str] = {}
    if ocr_jsonl and Path(ocr_jsonl).exists():
        for line in open(ocr_jsonl, encoding="utf-8"):
            j = json.loads(line)
            for pg in j["pages"]:
                if pg.get("source") in ("ocr", "embedded_ocr_layer+ocr"):          # chi OCR that, khong phai text layer/sao chep
                    ocr[(j["doc_id"], int(pg["page"]))] = pg.get("text") or ""

    def truth(it: dict) -> str:
        doc = fitz.open(str(pdfs[nfc(it["relative_path"])]))
        try:
            return boxes_to_text([(w[0], w[1], w[2], w[3], w[4]) for w in doc[int(it["page0"])].get_text("words")])
        finally:
            doc.close()

    def reference(it: dict) -> Optional[str]:
        try:
            return ocr.get((it["doc_id"], int(it["page"])))
        except (KeyError, ValueError):
            return None
    return truth, reference


def read_images_loaded(batch_dir: Path, cli: Optional[int]) -> Optional[int]:
    if cli is not None:
        return cli
    f = Path(batch_dir) / IMAGES_FILE
    if f.exists():
        m = re.search(r"\d+", f.read_text(encoding="utf-8"))
        return int(m.group()) if m else None
    return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--batch-dir", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, default=None)
    ap.add_argument("--pages-csv", type=Path, default=None, help="thay manifest: doc pages.csv cua 03_llm_silver (chi dung de hieu chuan/do thu)")
    ap.add_argument("--min-blank", type=int, default=None, help="ghi de nguong so trang trang toi thieu (chi de hieu chuan; lo that de mac dinh)")
    ap.add_argument("--min-known", type=int, default=None)
    ap.add_argument("--ocr-jsonl", type=Path, default=REPO / "data" / "ocr_v2.jsonl", help="OCR doc lap de kiem cheo")
    ap.add_argument("--images-loaded", type=int, default=None)
    ap.add_argument("--out", type=Path, default=None, help=f"mac dinh <batch-dir>/{STAMP_NAME}")
    a = ap.parse_args(argv)
    items = (read_manifest(a.manifest) if a.manifest else manifest_from_pages_csv(a.pages_csv) if a.pages_csv
             else manifest_from_dir(a.batch_dir))
    truth, ref = make_providers(a.ocr_jsonl)
    th = Thresholds()
    if a.min_blank is not None:
        th.min_blank = a.min_blank
    if a.min_known is not None:
        th.min_known = a.min_known
    rep = validate_batch(a.batch_dir, items, th, truth, ref, read_images_loaded(a.batch_dir, a.images_loaded))
    out = a.out or (a.batch_dir / STAMP_NAME)
    out.write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[{rep['status'].upper()}] {len(items)} muc; so anh nap {rep['images_loaded']}; ghi {out}")
    for k in ("known_summary", "cross_check_summary"):
        if k in rep:
            print(" ", k, json.dumps(rep[k], ensure_ascii=False))
    for r in rep["reasons"]:
        print("  - KHONG HOP LE:", r)
    for w in rep.get("warnings", []):
        print("  - canh bao:", w)
    return 0 if rep["status"] == "valid" else 1


if __name__ == "__main__":
    sys.exit(main())
