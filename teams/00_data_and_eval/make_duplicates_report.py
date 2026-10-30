#!/usr/bin/env python
"""Generate teams/00_data_and_eval/reports/01_duplicates.md from the build_manifest outputs.

    .venv\\Scripts\\python.exe -X utf8 teams\\00_data_and_eval\\make_duplicates_report.py

All numeric tables are computed from data/manifest.csv, data/duplicate_groups.csv and
teams/00_data_and_eval/reports/01_duplicates_stats.json (written by scripts/build_manifest.py).
The sections marked "viet tay" (validation by eye, label implications) are written by the
analyst and live in this file as constants: they describe what was SEEN when the pairs were
rendered and viewed, and must be re-checked if the data or thresholds change.
"""
from __future__ import annotations

import argparse
import csv
import itertools
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
ROOT_LABEL = "(gốc, không nhãn)"


def read_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def md_table(header: list[str], rows: list[list]) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c).replace("|", "\\|") for c in r) + " |")
    return "\n".join(out)


def lab(x: str) -> str:
    return x if x else ROOT_LABEL


def fm(x) -> str:
    """Number with a decimal comma (Vietnamese convention)."""
    return format(x, "g").replace(".", ",")


def median(v: list[int]) -> float:
    s = sorted(v)
    n = len(s)
    return fm(s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2)


def bin_labels(edges: list[float], last_closed: str = "") -> list[str]:
    out = []
    for a, b in zip(edges[:-1], edges[1:]):
        out.append(f"{a:g}–{b:g}")
    return out


# ------------------------------------------------------------------ viet tay (static) text
VALIDATION_TABLE = [
    # (cap, so lieu do duoc, nhin thay gi, ket luan)
    ("don-hang_2604-0034 ↔ don-hang_2605-0004", "Hamming 0, pixel 0,0010, text 0,93",
     "Cùng mẫu «Đơn đặt hàng»; khác ngày, số lượng, thành tiền, bên nhận.", "Mẫu chung, KHÔNG trùng"),
    ("don-hang_2606-0019 ↔ don-hang_2606-0024", "Hamming 0, pixel 0,0010, text 0,95",
     "Cùng mẫu; khác số PO, ngày, loại dầu và thành tiền. Text 0,95 vẫn là hai tài liệu khác nhau.",
     "Mẫu chung, KHÔNG trùng (lý do không dùng text ≥ 0,95 làm bằng chứng trùng)"),
    ("bbgn-260206-10 ↔ bbgn-260220-1", "Hamming 5, pixel 0,0054, text 0,93",
     "Cùng mẫu «Biên bản giao hàng», chữ viết tay khác nhau (khách hàng, số lượng, chữ ký).", "Mẫu chung, KHÔNG trùng"),
    ("BHDS 13420 ↔ BHDS 173.10 (hồ sơ xe)", "Hamming 3/1, pixel 0,0019, text 0,91",
     "Cùng mẫu giấy chứng nhận bảo hiểm TNDS; số giấy chứng nhận khác nhau chỉ ở chữ số cuối.",
     "Mẫu chung, KHÔNG trùng"),
    ("PCCC CH12-22 ↔ PCCC G1-22 (50 trang)", "Hamming 16/11, trang cuối pixel 0,0000, trang 1 pixel 0,0045",
     "Cùng mẫu «Hồ sơ quản lý công tác PCCC», tên cơ sở khác nhau (một cửa hàng, một phương tiện thủy).",
     "Mẫu chung, KHÔNG trùng. Trang cuối giống hệt nên bắt buộc phải so cả trang đầu lẫn trang cuối"),
    ("NQ-18.2021-DUC TRONG ↔ THÀNH LIÊN (31-12-2026)", "Hamming 2/16, trang cuối pixel 0,0000, trang 1 pixel 0,029",
     "Cùng mẫu bìa «Hợp đồng nhượng quyền bán lẻ xăng dầu», khác bên nhận nhượng quyền, số hợp đồng và ngày ký.",
     "Mẫu chung, KHÔNG trùng. Cũng chứng minh phải so cả trang đầu và cuối"),
    ("HDMBCD-02.2020-TRUONG HUNG (thư mục MUON BON) ↔ HDMBCD-04.2020-PHUC VINH (thư mục THUE KHO)",
     "Hamming 1/1, pixel 0,011, text 0,89",
     "Cùng mẫu «Hợp đồng mượn bồn chứa dầu», khác bên B (tên công ty, mã số thuế, người đại diện).",
     "Mẫu chung, KHÔNG trùng; nhưng đây là bằng chứng hai thư mục cùng một loại tài liệu"),
    ("65. GCN VC HNH Nhieu ↔ 72. GCN VC HNH Nhan (trang 2)", "Hamming trang cuối thấp, pixel 0,0099",
     "Cùng mẫu thẻ chứng nhận tập huấn; ảnh chân dung, họ tên, ngày sinh, số giấy chứng nhận khác nhau.",
     "Mẫu chung, KHÔNG trùng"),
    ("10. GCN VC HNH/38 (Nguyen) ↔ 9. TỔNG HỢP HỒ SƠ CỬA HÀNG/38 (Tấn) (trang 2)", "pixel 0,065",
     "Hai người khác nhau trên cùng mẫu thẻ (dù tên tệp cùng số 38).", "KHÔNG trùng"),
    ("15. GCN VC HNH Dong (12-5-24) ↔ 62. GCN VC HNH Huy (trang 1)", "Hamming trang 1 = 4; text giống hệt (98 ký tự)",
     "Trang 1 chỉ là bìa trống in sẵn (tên công ty + tiêu đề), giống nhau giữa mọi người.",
     "Khác tài liệu nhưng trang 1 không phân biệt được. Bằng chứng text/ảnh của trang 1 vô giá trị với nhóm này; phải so trang cuối"),
    ("58. GCN VC HNH Tuan ↔ 59. GCN VC HNH Thong (trang 2)", "pixel trang cuối > 0,01",
     "Trang 2 là thẻ có ảnh chân dung, họ tên, số giấy chứng nhận; hai người khác nhau, cùng mẫu thẻ.", "KHÔNG trùng"),
    ("GPKD-AN PHAT LAND (thư mục HOP DONG DAI LY) ↔ GPKD-AN PHÁT LAND (thư mục Giay DKKD)",
     "Hamming 0, pixel 0,0000, cùng sha256", "Đối chứng dương: cùng một giấy phép kinh doanh, nội dung từng chữ giống nhau.",
     "TRÙNG THẬT (bytes)"),
]

IMPLICATIONS = """\
### 6.1. Các thư mục có vẻ là CÙNG MỘT loại tài liệu (nhãn bị tách đôi)

| Cặp thư mục | Dấu hiệu đo được | Nhận định (suy luận) |
|---|---|---|
| `10. GCN VC HNH` và `8. GCN Lop dao tao van chuyen hang chay no` | 15 nhóm trùng byte giữa hai thư mục; cả hai đều là thẻ chứng nhận tập huấn vận chuyển hàng hóa nguy hiểm (cùng ngày cấp 12-05-2022) | Là một loại tài liệu; nên gộp thành một lớp (hoặc coi là bí danh của nhau). Nếu giữ hai lớp, cùng một tệp mang hai nhãn nên chắc chắn có một nhãn bị tính sai |
| `8. CUA HANG - TU K.TRA PCCC- VÂN` và `TU K.TRA PCCC- VÂN` | 2 nhóm trùng byte (GHE 3-T1+T2, PCCC G1-22); cùng mẫu «Hồ sơ quản lý công tác PCCC» | Một loại tài liệu; nên gộp |
| `6. HOP DONG MUON BON` và `6. HOP DONG THUE KHO- Vi` | 2 nhóm trùng byte (HDMBCD-05.2016, HDMBCD-05.2020); các tệp HDMBCD-* ở cả hai thư mục cùng mẫu «Hợp đồng mượn bồn chứa dầu» | Tên thư mục «thuê kho» nhưng nội dung là hợp đồng mượn bồn. Nên gộp, hoặc hỏi khách hàng ranh giới giữa «mượn bồn» và «thuê kho» |

### 6.2. Các thư mục là «gói hồ sơ» (bundle) gồm nhiều loại tài liệu

Dựa trên tên tệp (suy luận từ tên, chưa đọc nội dung từng tệp):

- `5. TỔNG HỢP HỒ SƠ XE`: bảo hiểm xe (BHVC/BHDS), PCCC xe, barem, giấy tờ người lái... trộn trong một thư mục.
- `9. TỔNG HỢP HỒ SƠ CỬA HÀNG`: GCN đăng ký doanh nghiệp, GCN vận chuyển hàng nguy hiểm (trùng với hai thư mục GCN ở trên),
  bằng/GCN BVMT, PCCC, giấy phép xây dựng, bảo hiểm, ảnh CamScanner...
- `_1. HOP DONG DAI LY NHUONG QUYEN`: chỉ ~5/25 tệp là hợp đồng nhượng quyền (NQ-*, 10 trang); phần lớn là giấy phép kinh doanh
  (GPKD-*, GĐKKD-*) và giấy đủ điều kiện (DDK-*), tức đúng loại tài liệu của `_1. Giay DKKD khach hang` và `_2. Giay Du Dieu Kien Khach hang`.
- `_3. HOP DONG DAU VAO-Diem`: hợp đồng, giấy ủy quyền, giấy phép kinh doanh, thanh lý... trộn.
- `6. CUA HANG - BB MAU- VÂN`: tệp dài (đến 93 trang), có thể gồm nhiều biên bản; cần tách trang trước khi phân loại.

Hệ quả: (1) nhãn «thư mục» ≠ nhãn «loại tài liệu» ở các bundle; (2) bài toán tách tài liệu (Team 2) phải chạy trước phân loại;
(3) các lớp bundle nên được định nghĩa lại hoặc loại khỏi tập đánh giá cho đến khi có nhãn ở mức trang/tài liệu con.

### 6.3. Hai hiện tượng phải xử lý khác nhau

- **Trùng thật** (cùng một tài liệu nộp hai lần, ở đây luôn là cùng byte): phải gộp thành MỘT mẫu và luôn nằm cùng một fold.
  Nếu hai bản mang hai nhãn khác nhau thì nhãn đang mâu thuẫn: chọn một nhãn (hoặc gộp lớp) rồi mới đánh giá.
- **Cùng mẫu** (khác khách hàng/ngày): vẫn là các mẫu riêng, nhưng phải cùng fold khi chia cross-validation
  (`GroupKFold(groups=template_group)`), nếu không điểm số sẽ lạc quan vì mô hình chỉ cần nhớ mẫu.
  Chú ý: với bài toán phân loại, hai bản trong cùng mẫu thường cùng lớp nên điểm trong-fold cao không chứng minh được khả năng tổng quát hóa;
  hãy báo cáo thêm điểm theo `GroupKFold`.
"""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=str(REPO / "data" / "manifest.csv"))
    ap.add_argument("--groups", default=str(REPO / "data" / "duplicate_groups.csv"))
    ap.add_argument("--stats", default=str(HERE / "reports" / "01_duplicates_stats.json"))
    ap.add_argument("--out", default=str(HERE / "reports" / "01_duplicates.md"))
    args = ap.parse_args(argv)

    man = read_csv(Path(args.manifest))
    grp = read_csv(Path(args.groups))
    stats = json.loads(Path(args.stats).read_text(encoding="utf-8"))
    th = stats["thresholds"]
    n = len(man)
    for r in man:
        r["pc"] = int(r["page_count"])
        r["scan"] = r["is_scanned"] == "True"
    by_label: dict[str, list[dict]] = defaultdict(list)
    for r in man:
        by_label[r["folder_label"]].append(r)
    labels = sorted(by_label, key=lambda s: (s == "", s))

    # components
    comp_of = {r["doc_id"]: (r["near_dup_group"] or "S:" + r["doc_id"]) for r in man}
    comp_members: dict[str, list[dict]] = defaultdict(list)
    for r in man:
        comp_members[comp_of[r["doc_id"]]].append(r)
    unique_total = len(comp_members)
    dup_groups = sorted(c for c in comp_members if not c.startswith("S:"))
    dup_docs = sum(len(comp_members[c]) for c in dup_groups)
    cross = [c for c in dup_groups if len({m["folder_label"] for m in comp_members[c]}) >= 2]
    within = [c for c in dup_groups if c not in cross]
    ev = Counter(g["evidence"] for g in grp)

    # per-folder before / after
    rows_fold = []
    for L in labels:
        comps = {comp_of[r["doc_id"]] for r in by_label[L]}
        shared = [c for c in comps if len({m["folder_label"] for m in comp_members[c]}) >= 2]
        rows_fold.append([lab(L), len(by_label[L]), len(comps), len(shared), len(comps) - len(shared)])
    tot = ["**Tổng**", n, "—", "—", "—"]

    # folder pair table
    pair_groups: dict[tuple[str, str], list[str]] = defaultdict(list)
    for c in cross:
        ls = sorted({m["folder_label"] for m in comp_members[c]})
        for a, b in itertools.combinations(ls, 2):
            pair_groups[(a, b)].append(c)
    pair_rows = [[f"`{lab(a)}`", f"`{lab(b)}`", len(v), ", ".join(v)] for (a, b), v in
                 sorted(pair_groups.items(), key=lambda kv: (-len(kv[1]), kv[0]))]

    # cross-label groups list
    grp_rows = []
    for c in cross:
        ms = sorted(comp_members[c], key=lambda m: m["relative_path"])
        grp_rows.append([c, len(ms), "<br>".join(f"`{m['folder_label']}/{m['file_name']}`" for m in ms)])
    within_rows = []
    for c in within:
        ms = sorted(comp_members[c], key=lambda m: m["relative_path"])
        within_rows.append([c, len(ms), "<br>".join(f"`{m['folder_label']}/{m['file_name']}`" for m in ms)])

    # page counts
    pbins = [(1, 1, "1"), (2, 2, "2"), (3, 5, "3–5"), (6, 10, "6–10"), (11, 30, "11–30"), (31, 10**9, ">30")]
    page_rows = []
    for L in labels:
        pcs = [r["pc"] for r in by_label[L]]
        page_rows.append([lab(L), len(pcs)] + [sum(1 for p in pcs if a <= p <= b) for a, b, _ in pbins]
                         + [median(pcs), max(pcs)])
    allpc = [r["pc"] for r in man]
    page_rows.append(["**Tổng**", n] + [sum(1 for p in allpc if a <= p <= b) for a, b, _ in pbins]
                     + [median(allpc), max(allpc)])
    multi = sum(1 for p in allpc if p > 1)
    over10 = sum(1 for p in allpc if p > 10)

    # scanned vs digital
    scan_rows = []
    for L in labels:
        s = sum(1 for r in by_label[L] if r["scan"])
        scan_rows.append([lab(L), len(by_label[L]), s, len(by_label[L]) - s,
                          f"{100 * s / len(by_label[L]):.0f}%"])
    S = sum(1 for r in man if r["scan"])
    scan_rows.append(["**Tổng**", n, S, n - S, f"{100 * S / n:.0f}%"])
    prod = Counter((r["producer"] or "(trống)", r["scan"]) for r in man)
    prod_tot = Counter(r["producer"] or "(trống)" for r in man)
    prod_rows = [[p, c, prod[(p, True)], prod[(p, False)]] for p, c in prod_tot.most_common(8)]

    # templates
    tmpl = defaultdict(list)
    for r in man:
        if r["template_group"]:
            tmpl[r["template_group"]].append(r)
    tmpl_docs = sum(len(v) for v in tmpl.values())
    top_t = sorted(tmpl.items(), key=lambda kv: (-len(kv[1]), kv[0]))[:6]
    tmpl_rows = [[k, len(v), len({m["folder_label"] for m in v}),
                  "; ".join(sorted({m["folder_label"] for m in v}))[:90]] for k, v in top_t]
    tmpl_fold_rows = []
    for L in labels:
        c = sum(1 for r in by_label[L] if r["template_group"])
        tmpl_fold_rows.append([lab(L), len(by_label[L]), c, f"{100 * c / len(by_label[L]):.0f}%"])

    hb = stats["hamming_bins"]
    hlab = [f"{a}" if b - a == 1 else f"{a}–{b - 1}" for a, b in zip(hb[:-1], hb[1:])]
    hlab[-1] = f"≥{hb[-2]}"
    ham_rows = [[hl, x, y] for hl, x, y in zip(hlab, stats["page1_hamming_hist_byte_identical_pairs"],
                                              stats["page1_hamming_hist_other_pairs"])]
    pb = stats["pixel_bins"]
    plab = [f"[{a:g}; {b:g})".replace(".", ",") for a, b in zip(pb[:-1], pb[1:])]
    pix_rows = [[pl, x, y] for pl, x, y in zip(plab, stats["pixel_diff_hist_byte_identical_pairs"],
                                              stats["pixel_diff_hist_candidate_other_pairs"])]
    low_rows = [[f"`{d['a'].split('/')[-1]}`", f"`{d['b'].split('/')[-1]}`", d["pixel_diff"], d["hamming_p1"],
                 d["text_sim"]] for d in stats["lowest_pixel_diff_non_byte_pairs"][:10]]

    out = []
    w = out.append
    w("# Báo cáo 01 — Tài liệu trùng lặp và nhóm cùng mẫu trong tập mẫu 336 PDF\n")
    w("> Dành cho sinh viên. Mọi số liệu trong các bảng tự sinh được tính lại từ `data/manifest.csv`, "
      "`data/duplicate_groups.csv` và `01_duplicates_stats.json`. Các mục ghi «viết tay» là nhận định của người phân tích sau khi "
      "mở từng cặp ảnh trang để xem; hãy kiểm tra lại nếu dữ liệu hoặc ngưỡng thay đổi. Toàn bộ xử lý chạy cục bộ, "
      "không gửi dữ liệu ra ngoài.\n")
    w("## 1. Tóm tắt\n")
    w(f"- Tập mẫu: **{n}** PDF ({n - len(by_label[''])} nằm trong {len(labels) - 1} thư mục có nhãn, {len(by_label[''])} tệp nằm rời ở gốc, không nhãn).")
    w(f"- **Trùng thật** (cùng một tài liệu được lưu hai lần): **{len(dup_groups)} nhóm**, gồm **{dup_docs} tài liệu**; "
      f"sau khi gộp còn **{unique_total} tài liệu duy nhất** (loại bỏ {n - unique_total} bản thừa).")
    w(f"- Trong {len(dup_groups)} nhóm đó, **{len(cross)} nhóm nằm ở ≥ 2 thư mục khác nhau** (cùng một tệp, hai nhãn → nhãn mâu thuẫn và rò rỉ train/test); "
      f"{len(within)} nhóm nằm trong cùng một thư mục.")
    n_bytes = sum(1 for c in dup_groups if all(m["exact_dup_group"] for m in comp_members[c]))
    w(f"- Bằng chứng của các nhóm trùng (theo tài liệu): {', '.join(f'{k}: {v}' for k, v in sorted(ev.items()))}. "
      f"{n_bytes}/{len(dup_groups)} nhóm có **cùng sha256** (byte giống hệt); không tìm thấy cặp nào «cùng ảnh nhưng khác byte» (xem mục 3).")
    w(f"- **Nhóm cùng mẫu** (khác tài liệu nhưng cùng biểu mẫu): **{len(tmpl)} nhóm** gồm {tmpl_docs} tài liệu (đã bao gồm các nhóm trùng thật). "
      "Dùng cột `template_group` làm `groups` cho `GroupKFold`.")
    w(f"- Số tài liệu nhiều trang: {multi}; hơn 10 trang: {over10}. Quét (scan) {S}/{n}, born-digital {n - S}/{n}.\n")

    w("## 2. Tạo lại toàn bộ kết quả\n")
    w("Chạy từ thư mục gốc của repo (kết quả xác định, chạy lại cho đúng cùng byte đầu ra; mất khoảng 20–30 giây):\n")
    w("```powershell")
    w(r".venv\Scripts\python.exe -X utf8 scripts\build_manifest.py")
    w(r".venv\Scripts\python.exe -X utf8 teams\00_data_and_eval\make_duplicates_report.py")
    w(r".venv\Scripts\python.exe -X utf8 teams\00_data_and_eval\tests\test_manifest.py")
    w("```\n")
    w("Tham số của `build_manifest.py`: `--samples-dir`, `--out` (mặc định `data/manifest.csv`), `--groups-out`, `--stats-out`, `--baseline` "
      "và các ngưỡng ở mục 3. Đầu ra: `data/manifest.csv`, `data/duplicate_groups.csv`, `reports/01_duplicates_stats.json`. "
      "`doc_id = sha1(đường dẫn tương đối, NFC, dấu «/»).hexdigest()[:12]`. Không bao giờ ghi vào thư mục mẫu.\n")

    w("## 3. Cách phát hiện và cách kiểm chứng ngưỡng\n")
    w("### 3.1. Hai hiện tượng, hai quy tắc\n")
    w("**(a) Trùng thật** — cùng một tài liệu được lưu hai lần. Hai tệp là trùng nếu thỏa MỘT trong ba bằng chứng "
      "(gộp bằng union-find, nhóm là thành phần liên thông):\n")
    w("1. `bytes`: sha256 giống nhau (kết luận chắc chắn).")
    w(f"2. `image`: cùng số trang; dHash 64-bit của trang đầu **và** trang cuối cách nhau ≤ {th['image_hamming']} bit; "
      f"tỉ lệ điểm ảnh khác nhau (chênh mức xám > 30 trên ảnh 200×283 đã làm mờ nhẹ) ≤ {fm(th['pixel_dup'])} ở cả trang đầu và trang cuối; "
      "và nếu cả hai có text thì text phải giống nhau. Ý nghĩa: «cùng một bản quét, chỉ nén lại».")
    w(f"3. `text`: text trang 1 (chuẩn hóa: bỏ dấu, chữ thường, chỉ giữ a–z0–9) **giống hệt** (độ tương đồng ≥ {fm(th['text_dup_sim'])}), "
      f"dài ≥ {th['text_min_len']} ký tự, cùng số trang và pixel ≤ {fm(th['text_dup_pixel'])} ở trang đầu/cuối. Ý nghĩa: «cùng tài liệu quét lại».\n")
    w("Lý do so cả trang đầu và trang cuối: với thẻ chứng nhận 2 trang, trang 1 chỉ là bìa in sẵn giống hệt giữa mọi người, "
      "còn với hồ sơ PCCC/hợp đồng nhiều trang thì trang cuối có thể giống hệt giữa các tài liệu khác nhau (đã gặp cả hai trường hợp, mục 3.4).\n")
    w("Vì sao KHÔNG dùng «text tương đồng ≥ 0,95» làm bằng chứng trùng như đề xuất ban đầu: các bản điền khác nhau của cùng một biểu mẫu "
      "(đơn đặt hàng, phiếu xuất kho, biên bản giao hàng) thường có tương đồng 0,93–0,99 dù là các tài liệu khác nhau "
      "(đã xem ảnh các cặp 0,93 và 0,95 ở mục 3.4: khác ngày, số lượng, tiền). Mức 0,95 chỉ được dùng để tạo cạnh «cùng mẫu».\n")
    w("**(b) Cùng mẫu** — khác tài liệu, cùng biểu mẫu/đầu thư, khác khách hàng hoặc ngày. Đây không phải trùng lặp nên có cột riêng "
      f"`template_group`. Cạnh «cùng mẫu» khi text trang 1 tương đồng ≥ {fm(th['template_sim'])}, hoặc tương đồng ≥ {fm(th['template_loose_sim'])} "
      f"**và** bố cục trang 1 khớp (pixel ≤ {fm(th['template_pixel'])}). `template_group` là thành phần liên thông của (cạnh trùng thật + cạnh cùng mẫu).")
    w("Giới hạn (đo được, xem mục 7): text lấy từ OCR trang 1 của `baseline_ocr_335.jsonl` (và text layer cho 2 tệp ở gốc), "
      "nên nhóm cùng mẫu chỉ là nỗ lực tốt nhất; biểu mẫu quét lệch vị trí hoặc OCR kém sẽ không được nối. "
      "Đừng coi «không có template_group» là «chắc chắn không cùng mẫu».\n")

    w("### 3.2. Phân bố khoảng cách dHash (trang 1) trên mọi cặp\n")
    w(f"Có {stats['n_pairs_total']} cặp; {stats['n_byte_identical_pairs']} cặp trùng byte. Số cặp khác byte nhưng Hamming ≤ 2: "
      f"**{stats['n_other_pairs_hamming_le_2']}**; ≤ 4: **{stats['n_other_pairs_hamming_le_4']}**.\n")
    w(md_table(["Hamming trang 1", "Cặp trùng byte", "Cặp khác byte"], ham_rows) + "\n")
    w("Đọc bảng: các cặp trùng byte luôn có Hamming 0 (đúng như dự kiến), nhưng hàng trăm cặp KHÁC tài liệu cũng có Hamming ≤ 4, vì "
      "trang giấy A4 có chữ đen trên nền trắng cùng biểu mẫu thì rất giống nhau ở độ phân giải 9×8. "
      f"**Kết luận: dHash chỉ là bộ lọc thô, không đủ để kết luận trùng**; ngưỡng chọn là ≤ {th['image_hamming']} (đủ rộng cho bản nén lại, đủ chặt để lọc cặp ứng viên) "
      "và quyết định thật sự nằm ở phép so điểm ảnh bên dưới.\n")
    w("### 3.3. Phân bố chênh lệch điểm ảnh (cặp ứng viên cùng số trang; lấy trang xấu nhất trong trang đầu/cuối)\n")
    w(md_table(["Tỉ lệ điểm ảnh khác", "Cặp trùng byte", "Cặp khác byte (ứng viên)"], pix_rows) + "\n")
    w(f"Đọc bảng: cặp trùng byte có chênh lệch đúng 0; cặp khác byte thấp nhất là 0,0010 (gấp đôi ngưỡng {fm(th['pixel_dup'])}) và 10 cặp thấp nhất như dưới đây "
      "đều là biểu mẫu điền khác nhau (đã xem ảnh 2 trong số đó và nhiều cặp biên khác, mục 3.4; các cặp còn lại có số đơn/số phiếu khác nhau). Ngưỡng điểm ảnh được đặt ngay trên mức của bản sao giống hệt và dưới mọi cặp khác tài liệu quan sát được. "
      "Hệ quả đo được: **trong tập này không tồn tại cặp «cùng ảnh nhưng khác byte»**, nên các quy tắc `image`/`text` chưa từng là bằng chứng "
      "duy nhất của nhóm nào; chúng được giữ để chạy trên dữ liệu mới. Chúng chưa được kiểm chứng bằng ví dụ dương nào ngoài các cặp trùng byte.\n")
    w(md_table(["Tệp A", "Tệp B", "Pixel", "Hamming p1", "Text"], low_rows) + "\n")
    w("### 3.4. Các cặp biên đã xem bằng mắt (viết tay)\n")
    w("Mỗi cặp được kết xuất thành PNG (thư mục scratch, ngoài repo), ghép cạnh nhau và mở xem. "
      "Ảnh thẻ, họ tên, số giấy tờ cá nhân xuất hiện trong ảnh nhưng KHÔNG được ghi lại trong báo cáo.\n")
    w(md_table(["Cặp", "Số đo", "Nhìn thấy", "Kết luận"], [list(r) for r in VALIDATION_TABLE]) + "\n")
    w("Tổng cộng đã xem 12 cặp (11 cặp biên + 1 đối chứng dương). Cặp nào cũng cho cùng một bài học: **hai tài liệu khác nhau trên cùng "
      "một biểu mẫu trông gần như giống hệt ở mức trang**; chỉ các chi tiết nhỏ (ngày, số, tên, ảnh chân dung) mới khác. "
      "Vì vậy ngưỡng Hamming/độ tương đồng nới lỏng sẽ gộp nhầm tài liệu khác nhau, và sẽ làm mất mẫu hợp lệ.\n")

    w("## 4. Số tài liệu trước/sau khi loại trùng, theo thư mục\n")
    w(f"Trước: {n}. Sau khi gộp các nhóm trùng thật: **{unique_total}** tài liệu duy nhất. Cột «sau» đếm tài liệu duy nhất có mặt trong thư mục "
      "(bản trùng trong cùng thư mục chỉ tính một). «Dùng chung» là số tài liệu duy nhất của thư mục cũng có bản ở thư mục khác "
      "(một tài liệu dùng chung được đếm ở mỗi thư mục có bản, nên tổng cột «sau» lớn hơn số duy nhất toàn cục).\n")
    w(md_table(["Thư mục", "Trước", "Sau", "Dùng chung với thư mục khác", "Chỉ riêng thư mục"], rows_fold + [tot]) + "\n")

    w("## 5. Cặp thư mục chia sẻ tài liệu\n")
    w(f"{len(cross)} nhóm trùng thật nằm ở ≥ 2 thư mục. Mỗi nhóm được đếm một lần cho mỗi cặp thư mục mà nó bắc cầu.\n")
    w(md_table(["Thư mục A", "Thư mục B", "Số nhóm dùng chung", "Nhóm"], pair_rows) + "\n")
    w("### Danh sách nhóm trùng khác nhãn (tên tệp)\n")
    w(md_table(["Nhóm", "Số bản", "Tệp (thư mục/tên)"], grp_rows) + "\n")
    w("### Danh sách nhóm trùng trong cùng một thư mục\n")
    w(md_table(["Nhóm", "Số bản", "Tệp (thư mục/tên)"], within_rows) + "\n")

    w("## 6. Hệ quả cho bộ nhãn (viết tay, dựa trên số liệu và ảnh đã xem)\n")
    w(IMPLICATIONS)

    w("## 7. Nhóm cùng mẫu (`template_group`)\n")
    w(f"{len(tmpl)} nhóm, {tmpl_docs}/{n} tài liệu. Nhóm lớn nhất:\n")
    w(md_table(["Nhóm", "Số tài liệu", "Số thư mục", "Thư mục"], tmpl_rows) + "\n")
    w("Nhóm `T001` gồm các thẻ chứng nhận tập huấn: trang 1 chỉ là bìa in sẵn nên text giống hệt nhau giữa mọi người, "
      "và kéo ba thư mục vào cùng một nhóm. Tỉ lệ tài liệu có `template_group` theo thư mục "
      "(thấp = có thể do OCR/bố cục, không có nghĩa là không cùng mẫu):\n")
    w(md_table(["Thư mục", "Số tài liệu", "Có template_group", "Tỉ lệ"], tmpl_fold_rows) + "\n")

    w("## 8. Số trang theo thư mục\n")
    w(f"Tài liệu > 1 trang: **{multi}/{n}**; > 10 trang: **{over10}/{n}** (tính trên {n} PDF trước khi loại trùng).\n")
    w(md_table(["Thư mục", "Số tài liệu"] + [b[2] for b in pbins] + ["Trung vị", "Tối đa"], page_rows) + "\n")
    w("Các tệp > 10 trang (ứng viên cần tách trang): " + ", ".join(
        f"`{r['relative_path']}` ({r['pc']})" for r in sorted((r for r in man if r["pc"] > 10), key=lambda r: (-r["pc"], r["relative_path"]))) + "\n")

    w("## 9. Quét (scan) hay born-digital\n")
    w("Định nghĩa `is_scanned` (heuristic): ít hơn một nửa số trang có text layer (≥ 50 ký tự PyMuPDF) VÀ ít nhất một trang chứa ảnh raster. "
      "Còn lại là born-digital. Nơi có nhiều bản quét là nơi chất lượng OCR quyết định kết quả.\n")
    w(md_table(["Thư mục", "Số tài liệu", "Quét", "Born-digital", "% quét"], scan_rows) + "\n")
    w("Phần mềm tạo PDF (`producer`) phổ biến nhất:\n")
    w(md_table(["Producer", "Tổng", "Quét", "Born-digital"], prod_rows) + "\n")
    w("Dấu hiệu CamScanner/ảnh chụp điện thoại có thể tìm bằng `producer` chứa `intsig` (CamScanner) và trường `created`.\n")

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
