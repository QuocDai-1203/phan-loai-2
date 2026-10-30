r"""demo_blank_trap.py - T6: dot thu "trang trang ra chu" voi du lieu that (khong ve anh nao, khong goi LLM).

Dung 39 trang born-digital + 12 trang scan co ban chep Haiku san (gold/silver_llm/haiku) lam lo, them 2 trang TRANG (muc gia, khong co anh that).
  A) ban chep trang trang = "[trang trang]"           -> ky vong: HOP LE
  B) mot trang trang duoc "chep" ra chu (mo phong tac nhan bia khi anh khong nap duoc) -> ky vong: KHONG HOP LE
  C) nhu A nhung khai bao so anh nap duoc it hon so muc (nap loi 2 anh) -> ky vong: KHONG HOP LE
Ghi ra _scratch/ (khong commit). Chay:  .venv\Scripts\python.exe -X utf8 teams\team1_ocr\experiments\03_llm_silver\demo_blank_trap.py
"""
import csv
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
SILVER = REPO / "teams" / "team1_ocr" / "gold" / "silver_llm" / "haiku"
OUT = HERE / "_scratch" / "demo_blank_trap"
PY = REPO / ".venv" / "Scripts" / "python.exe"
VB = HERE / "validate_batch.py"


def main() -> int:
    pages = list(csv.DictReader(open(HERE / "pages.csv", encoding="utf-8")))
    known = [r for r in pages if r["kind"] == "gold_textlayer"]
    real = [r for r in pages if r["kind"] != "gold_textlayer"][:12]
    rows = []
    for variant in ("A", "B", "C"):
        d = OUT / variant
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
        man = [["item_id", "kind", "relative_path", "page0", "doc_id", "page"]]
        sys.path.insert(0, str(REPO / "scripts"))
        from build_ocr_dataset import make_doc_id
        for r in known + real:
            src = SILVER / f"{r['page_id']}.txt"
            if not src.exists():
                continue
            shutil.copy(src, d / f"{r['page_id']}.txt")
            k = "control_textlayer" if r["kind"] == "gold_textlayer" else "real"
            man.append([r["page_id"], k, r["relative_path"], r["page0"], make_doc_id(r["relative_path"]), int(r["page0"]) + 1])
        for b in ("BLANK1", "BLANK2"):
            man.append([b, "control_blank", "", "", "", ""])
            (d / f"{b}.txt").write_text("[trang trang]", encoding="utf-8")
        if variant == "B":
            (d / "BLANK2.txt").write_text("CONG TY CO PHAN THUONG MAI DICH VU HIEP HOA\nPHIEU GIAO HANG so 123\nDia chi: 112 Hai Ba Trung, Quy Nhon", encoding="utf-8")
        n = len(man) - 1
        (d / "_images_loaded.txt").write_text(str(n - 2 if variant == "C" else n), encoding="utf-8")
        with open(d / "_manifest.csv", "w", encoding="utf-8", newline="") as f:
            csv.writer(f).writerows(man)
        p = subprocess.run([str(PY), "-X", "utf8", str(VB), "--batch-dir", str(d), "--manifest", str(d / "_manifest.csv")],
                           capture_output=True, text=True, encoding="utf-8", cwd=REPO)
        print(f"=== lo {variant} ({n} muc) -> ma thoat {p.returncode}")
        print(p.stdout.strip())
        rows.append((variant, p.returncode))
    exp = {"A": 0, "B": 1, "C": 1}
    ok = all(exp[v] == rc for v, rc in rows)
    print("\nket qua dung ky vong:", ok)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
