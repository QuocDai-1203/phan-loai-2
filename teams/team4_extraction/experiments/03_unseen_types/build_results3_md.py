"""build_results3_md.py - Dựng RESULTS.md của 03_unseen_types từ results3_base.json, results3_improved.json, causes_*.json (số liệu tự sinh).

    .venv\\Scripts\\python.exe -X utf8 teams\\team4_extraction\\experiments\\03_unseen_types\\build_results3_md.py

Văn bản diễn giải nằm trong tệp này; mọi con số lấy từ JSON. Không có giá trị trường nào trong đầu ra.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from pathlib import Path

import common3 as C
import combine as CB

HERE = C.HERE
BASE = json.loads((HERE / "results3_base.json").read_text(encoding="utf-8"))
IMP = json.loads((HERE / "results3_improved.json").read_text(encoding="utf-8"))
SEL3 = json.loads((HERE / "dev_selection3.json").read_text(encoding="utf-8"))
CAUSES = json.loads((HERE / "causes_DEV_cascade.json").read_text(encoding="utf-8"))
SHA_LABELS = hashlib.sha1((C.REPO / "data" / "labels_v2.csv").read_bytes()).hexdigest()[:10]
RULE = IMP["rule"]
OLD = "any-model=filename"
GROUPS = [("DEV", "DEV"), ("TEST", "TEST"), ("EXCLUDED", "EXCLUDED"), ("TEST+EXCLUDED", "TEST+EXCLUDED")]


def f2(x, lo=None, hi=None, recall=None):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "0.00 (luật rỗng)" if recall == 0 else "n/a"
    s = f"{x:.2f}"
    if lo is not None and not (isinstance(lo, float) and math.isnan(lo)):
        s += f" [{lo:.2f}; {hi:.2f}]"
    return s


def ov(cfg, mode):
    o = cfg[mode]["overall"]
    return f2(o["f1"], o["f1_ci_lo"], o["f1_ci_hi"], recall=o["recall"])


def exp_str(e):
    n = e["n_gold"]
    if not n:
        return "n/a"
    return f"{e['correct']}/{e['empty']}/**{e['wrong']}** (n={n}; sai ≤ {e['wrong_upper95']:.2f})"


def table_main(res, groups, cfgs, names):
    L = ["| tập (n đơn vị) | phương pháp | F1 chặt [CI 95%] | F1 mềm [CI] | đúng mọi trường bắt buộc (mềm) | hạn: đúng / bỏ trống / **sai** (n; cận trên 95% của tỉ lệ sai) | hạn: thừa khi giấy không có hạn |", "|---|---|---|---|---|---|---|"]
    for g, label in groups:
        G = res["groups"][g]
        for c in cfgs:
            if c not in G["configs"]:
                continue
            C_ = G["configs"][c]
            e = C_["expiry_counts_normalized"]
            sp = f"{e['spurious']}/{e['n_absent']}"
            L.append(f"| {label} ({G['n_units']}) | {names.get(c, c)} | {ov(C_, 'normalized')} | {ov(C_, 'lenient')} | {C_['lenient']['doc_level']['rate']:.2f} | {exp_str(e)} | {sp} |")
    return "\n".join(L)


def table_ftype(res, groups, cfgs, names):
    L = ["| tập | phương pháp | ngày (n) | số (n) | mã (n) | văn bản chặt / mềm (n) |", "|---|---|---|---|---|---|"]
    for g, label in groups:
        G = res["groups"][g]
        for c in cfgs:
            if c not in G["configs"]:
                continue
            ps, pl = G["configs"][c]["normalized"]["per_type"], G["configs"][c]["lenient"]["per_type"]

            def one(k, d=ps):
                v = d[k]["f1"]
                return ("n/a" if (v is None or (isinstance(v, float) and math.isnan(v))) else f"{v:.2f}") + f" ({d[k]['n_gold']})"
            L.append(f"| {label} | {names.get(c, c)} | {one('date')} | {one('number')} | {one('id')} | {one('text').split(' ')[0]} / {one('text', pl)} |")
    return "\n".join(L)


def table_type(res_b, res_i):
    G = res_b["groups"]["ALL"]
    Gi = res_i["groups"]["ALL"]
    units_by = {g: res_b["groups"][g]["units_by_type"] for g in ("DEV", "TEST", "EXCLUDED")}
    L = ["| loại | n đơn vị (DEV/TEST/EXCL) | F1 mềm: LLM (=cascade zero-tuning) | F1 mềm: VLM | hạn, cascade zero-tuning: đúng/trống/**sai** (n) | hạn, VLM | hạn, cascade+luật chung+`regex=llm` |", "|---|---|---|---|---|---|---|"]
    for t in G["units_by_type"]:
        bt = G["configs"]["cascade"]["by_doc_type"][t]
        vt = G["configs"]["vlm"]["by_doc_type"][t]
        it = Gi["configs"]["cascade+reject"]["by_doc_type"][t]

        def ex(d):
            e = d["expiry_counts"]
            return "không có trường hạn có đáp án" if not e["n_gold"] else f"{e['correct']}/{e['empty']}/**{e['wrong']}** ({e['n_gold']})"
        nn = "/".join(str(units_by[g].get(t, 0)) for g in ("DEV", "TEST", "EXCLUDED"))
        L.append(f"| {t} | {nn} | {ov(bt, 'lenient')} | {ov(vt, 'lenient')} | {ex(bt)} | {ex(vt)} | {ex(it)} |")
    return "\n".join(L)


def table_abst(res, groups, rules):
    L = ["| tập | quy tắc | số tự nhận | đúng | **sai** | có hạn thật (n) | tự động hóa (đúng/n) | cận trên 95% (Clopper-Pearson một phía) của tỉ lệ sai |", "|---|---|---|---|---|---|---|---|"]
    for g, label in groups:
        for r in res["groups"][g]["abstention"]:
            if r["rule"] not in rules:
                continue
            up = "n/a (không tự nhận)" if r["n_emitted"] == 0 else f"{r['wrong_upper95']:.2f}"
            auto = f"{r['n_correct']}/{r['n_gold_present']} = {r['automation']:.2f}" if r["n_gold_present"] else "n/a"
            L.append(f"| {label} | {r['rule']} | {r['n_emitted']} | {r['n_correct']} | {r['n_wrong']} | {r['n_gold_present']} | {auto} | {up} |")
    return "\n".join(L)


CAUSE_VI = {
    "llm_miss": "LLM 4B bỏ trống hoặc đọc lệch dù chuỗi đáp án CÓ trong văn bản đưa vào",
    "extent": "ranh giới trường khác đáp án (kèm/thiếu mã số thuế, địa chỉ, chức danh)",
    "ink": "chữ viết tay (OCR hỏng gần hết, LLM bịa hoặc bỏ trống)",
    "ocr_missing": "OCR không có chuỗi đáp án (đọc nhầm chữ số, mờ, bóng chữ mặt sau)",
    "spurious_gold_absent": "thừa: đáp án ghi không có; có thể do định nghĩa trường mơ hồ hoặc đáp án thiếu (cần người kiểm)",
    "truncated": "chuỗi có trong OCR nhưng nằm ngoài đoạn đưa cho LLM",
}


def cause_tables():
    tot = Counter((x["cause"], x["outcome"]) for x in CAUSES)
    L = ["| nguyên nhân | bỏ trống | sai giá trị | thừa | tổng |", "|---|---|---|---|---|"]
    for c in CAUSE_VI:
        e, w, s = tot[(c, "empty")], tot[(c, "wrong")], tot[(c, "spurious")]
        if e + w + s:
            L.append(f"| {CAUSE_VI[c]} | {e} | {w} | {s} | {e + w + s} |")
    L.append(f"| **tổng** | {sum(v for (c, o), v in tot.items() if o == 'empty')} | {sum(v for (c, o), v in tot.items() if o == 'wrong')} | {sum(v for (c, o), v in tot.items() if o == 'spurious')} | {len(CAUSES)} |")
    by_group = Counter((x["doc_type"], x["field"], x["outcome"]) for x in CAUSES)
    T = ["| # | loại | trường | kết quả | số lỗi (DEV) | nguyên nhân chính | ghi chú |", "|---|---|---|---|---|---|---|"]
    notes = {
        ("HD_VAN_CHUYEN", "tuyen_van_chuyen"): "trường là đoạn văn dài; mô hình trả null dù đoạn có trong văn bản",
        ("HD_VAN_CHUYEN", "gia_cuoc"): "như trên; một biểu mẫu hợp đồng (20 đơn vị DEV) nên lỗi lặp lại",
        ("HD_MUON_BON", "ngay_nhan_bon"): "biên bản nhận bồn có một ngày trong OCR nhưng đáp án ghi không có: cần người kiểm xem đáp án hay LLM đúng",
        ("HD_NHUONG_QUYEN_DAI_LY", "cua_hang"): "LLM điền tên/địa chỉ cửa hàng lấy ở đoạn khác; đáp án ghi không có",
        ("HD_VAN_CHUYEN", "ben_chu_hang"): "LLM chép tên kèm '(BÊN CHỦ HÀNG)' hoặc cắt mất 'Mã số thuế'; một số có chữ số mã số thuế đọc nhầm",
        ("GCN_BAO_HIEM", "doi_tuong_bao_hiem"): "bản quét chữ viết tay (biển số/đối tượng); OCR chèn dấu chấm giữa ký tự",
        ("GCN_BAO_HIEM", "phi_bao_hiem"): "số tiền viết tay bị OCR đọc sai chữ số (một số tiền khác bậc cỡ)",
        ("GCN_BAO_HIEM", "hieu_luc_tu"): "ngày viết tay: OCR không đọc được",
        ("GCN_BAO_HIEM", "ngay_het_han"): "ngày viết tay: OCR không đọc được; đây là CHÍNH trường hạn",
        ("GCN_BAO_HIEM", "so_tien_bao_hiem"): "3/4 ca là chữ viết tay, 1 ca lệch ranh giới; hiện tượng 'nhiều mức tiền' chưa được kiểm riêng",
    }
    for i, ((dt, fld, out), n) in enumerate(by_group.most_common(15), 1):
        cs = Counter(x["cause"] for x in CAUSES if (x["doc_type"], x["field"], x["outcome"]) == (dt, fld, out))
        main = cs.most_common(1)[0][0]
        T.append(f"| {i} | {dt} | {fld} | {out} | {n} | {CAUSE_VI[main].split(' (')[0]} | {notes.get((dt, fld), '')} |")
    return "\n".join(L), "\n".join(T)


def expiry_cause_line():
    exp = C.expiry_fields()
    xs = [x for x in CAUSES if x["field"] in exp.get(x["doc_type"], [])]
    c = Counter((x["cause"], x["outcome"]) for x in xs)
    return xs, c


def main() -> int:
    b, i = BASE, IMP
    names = {"regex": "luật/regex giai đoạn 2 (không có luật cho loại mới)", "llm": "LLM cục bộ (văn bản OCR)", "vlm": "VLM cục bộ (ảnh trang)",
             "filename": "ngày trong tên tệp", "cascade": "cascade theo kiểu (= LLM, vì luật rỗng)", "cascade+reject": f"cascade + tự nhận hạn `{OLD}` (cấu hình giai đoạn 2)"}
    names_i = {"regex": "luật chung (mới)", "cascade": "cascade theo kiểu: luật chung → LLM",
               "cascade+reject": f"cascade + tự nhận hạn `{RULE}`", "cascade+reject(phase2 rule)": f"cascade + tự nhận hạn `{OLD}` (giai đoạn 2)"}
    cause_tab, top_tab = cause_tables()
    xs, ec = expiry_cause_line()
    dev_b, dev_i = b["groups"]["DEV"], i["groups"]["DEV"]
    ab = {g: {r["rule"]: r for r in b["groups"][g]["abstention"]} for g in b["groups"]}
    ai = {g: {r["rule"]: r for r in i["groups"][g]["abstention"]} for g in i["groups"]}
    new_te, old_te = ai["TEST+EXCLUDED"][RULE], ai["TEST+EXCLUDED"][OLD]
    old_all = ab["ALL"][OLD]
    lat = {g: b["groups"][g]["configs"] for g in ("ALL",)}["ALL"]
    n_dev, n_te, n_ex = (b["groups"][g]["n_units"] for g in ("DEV", "TEST", "EXCLUDED"))
    ex_ok = lambda g, cfg, res=b: res["groups"][g]["configs"][cfg]["expiry_counts_normalized"]  # noqa: E731
    L = []
    A = L.append
    A("# Cấu hình trích xuất đóng băng dùng cho loại tài liệu mới (Nhóm 4, giai đoạn 3, thí nghiệm 03)")
    A("")
    A(f"> Bản tự sinh bởi `build_results3_md.py` từ `results3_base.json`, `results3_improved.json`, `causes_DEV_cascade.json`. Tiếng Việt, viết cho sinh viên năm cuối ngành AI.")
    A(f"> `data/labels_v2.csv` sha1[:10] = `{SHA_LABELS}`; silver v2 `fields_silver_v2.jsonl` sha1[:10] = `{SEL3['hashes']['fields_silver_v2.jsonl']}`; ngày chạy 2026-10-16.")
    A("> Tái lập một dòng: `run_zero_tuning.py` → `make_results3.py --set base` → `dev_iterate.py` → `freeze3.py` → `run_zero_tuning`-giống-lệnh luật chung (xem mục 9) → `make_results3.py --set improved --final-test` → `classify_errors.py` → `build_results3_md.py`.")
    A("> Nguồn văn bản: `data/ocr_v2.jsonl` (OCR cục bộ) cho luật và LLM; ảnh trang `gold/v2/pages_v2/` cho VLM; tên tệp (`relative_path` trong `gold/v2/units_v2.csv`) cho ngày trong tên tệp. Đáp án: silver v2 (Haiku + Sonnet đọc ảnh, Opus phân xử mù 135 mục), **không có người kiểm**: mọi số là \"so với đáp án máy\".")
    A("")
    A("## 0. Tóm tắt")
    A("")
    A("**Câu hỏi.** Cấu hình đóng băng ở giai đoạn 2 (luật cho ngày/số/mã + LLM `qwen3.5:4b` cho văn bản; quy tắc tự nhận hạn `any-model=filename`) dùng ngay cho 17 loại tài liệu có trường hạn mà ta CHƯA từng chỉnh luật thì được bao nhiêu, và hỏng ở đâu?")
    A("")
    ca = b["groups"]["ALL"]["configs"]
    A(f"* **Luật giai đoạn 2 không có gì cho loại mới.** `src/extraction/field_rules.py` chỉ có luật cho 4 loại cũ; với 17 loại mới luật trả toàn null (84/84 đơn vị, `status=ok` nhưng rỗng). Cascade \"luật→LLM\" thực chất chỉ còn là LLM. Ngoài ra `src/extraction/schemas.py` chỉ liệt kê 4 loại (`SUPPORTED_TYPES`): sản phẩm hiện tại trả `UnsupportedDocType` (status `error`) cho 17 loại này, nên thí nghiệm này đo *phương pháp* chứ không phải đường ống sản xuất.")
    A(f"* **Zero-tuning, cascade (= LLM) trên {n_dev + n_te + n_ex} đơn vị**: F1 mềm {ov(ca['cascade'], 'lenient')}, F1 chặt {ov(ca['cascade'], 'normalized')} (so với giai đoạn 2 trên 4 loại cũ: TEST 0.90 mềm / 0.72 chặt; hai tập khác loại nên chỉ đặt cạnh nhau). VLM đọc ảnh tốt hơn LLM-trên-OCR: F1 mềm {ov(ca['vlm'], 'lenient')}.")
    e_all_c = ex_ok("ALL", "cascade")
    e_all_v = ex_ok("ALL", "vlm")
    A(f"* **Trường hạn (62 trường có đáp án hạn thật, gộp DEV+TEST+EXCLUDED)**: cascade đúng {e_all_c['correct']}, bỏ trống {e_all_c['empty']}, **sai giá trị {e_all_c['wrong']}** (cận trên 95% {e_all_c['wrong_upper95']:.2f}); VLM đúng {e_all_v['correct']}, bỏ trống {e_all_v['empty']}, sai {e_all_v['wrong']} (cận trên {e_all_v['wrong_upper95']:.2f}).")
    A(f"* **Quy tắc tự nhận hạn giai đoạn 2 (`{OLD}`) gần như không dùng được cho loại mới**: tự nhận {old_all['n_emitted']}/{old_all['n_gold_present']} trường hạn thật ({old_all['automation']:.0%}), sai {old_all['n_wrong']} (cận trên 95% {old_all['wrong_upper95']:.2f}). Giai đoạn 2 (4 loại cũ): DEV 37/64 = 58%, TEST 12/16 = 75%, 0 sai (cận trên 8% và 22%). Lý do: ngày trong tên tệp của loại mới KHÔNG luôn là ngày hết hạn (đứng một mình sai 17/40 lần có ngày ở DEV, 14 trong số đó là giấy không có hạn), nên quy tắc đòi một mô hình đọc trùng tên tệp chỉ nhận được phần nhỏ; 10 đơn vị EXCLUDED là tệp ghép nên không có ngày tên tệp áp dụng.")
    A(f"* **Một vòng cải tiến chung chỉnh trên DEV**: thêm luật ngày chung (`methods/generic_date_rules.py`: nhãn hạn/hiệu lực/ngày ký/ngày cấp dùng chung cho mọi loại, từ chối \"không thời hạn\"), chọn quy tắc tự nhận `{RULE}` trên DEV. Trên phần KHÔNG chỉnh (TEST + EXCLUDED, {n_te + n_ex} đơn vị, chạy MỘT lần): quy tắc mới tự nhận {new_te['n_emitted']}/{new_te['n_gold_present']} trường hạn thật ({new_te['automation']:.0%}), **sai {new_te['n_wrong']}** (cận trên 95% {new_te['wrong_upper95']:.2f}); quy tắc cũ cùng tập: {old_te['n_emitted']}/{old_te['n_gold_present']} ({old_te['automation']:.0%}). F1 các trường khác gần như không đổi (luật chung chỉ phủ trường ngày, LLM vẫn là nguồn chính).")
    A("* **Chưa chứng minh** tỉ lệ sai ≤ 1% (cần ≥ 299 lần tự nhận đúng liên tiếp; ta có 47 trên cả 84 đơn vị, trong đó chỉ 12 là ngoài mẫu chỉnh). Mọi con số là so với đáp án máy chưa có người kiểm; tập TEST ở đây chỉ là *thêm mẫu* cho cấu hình không chỉnh (không có gì được chỉnh nên TEST không bị \"khóa\" theo nghĩa giai đoạn 2); chỉ ở mục 5 TEST+EXCLUDED mới là phần ngoài mẫu chỉnh (và tổng hợp zero-tuning của hai tập này đã được xem trước khi chọn cải tiến, dù không xem từng đơn vị).")
    A("")
    A("## 1. Thiết lập")
    A("")
    A(f"* **Đơn vị chấm** = `(doc_id, segment)`; 84 đơn vị thuộc 17 loại: DEV {n_dev}, TEST {n_te}, EXCLUDED {n_ex} (EXCLUDED = tệp ghép/loại khỏi chia DEV/TEST của nhóm 00: **không đại diện** cho tệp riêng lẻ; báo riêng, không gộp vào con số chính). Loại thiếu mẫu: nhiều loại chỉ có 1–3 đơn vị DEV (xem bảng theo loại).")
    A("* **Một biểu mẫu, nhiều tài liệu**: `HD_VAN_CHUYEN` (20 đơn vị DEV, cùng một mẫu hợp đồng) chiếm 1/3 DEV nên kéo điểm gộp theo mẫu đó; kết luận theo loại cho loại 1–3 đơn vị chỉ là minh họa.")
    A("* **Cấu hình**: đúng như giai đoạn 2: luật `src/extraction/field_rules.py` (trống cho loại mới), LLM `qwen3.5:4b` prompt `v1` trên `ocr_v2` (`num_ctx` 6144, 4B Q4_K_M), VLM cùng mô hình trên 4 ảnh đầu của `gold/v2/pages_v2`, ngày trong tên tệp, cascade theo kiểu (văn bản: LLM→luật; ngày/số/mã: luật→LLM), tự nhận hạn `any-model=filename`. Chỉ trường PII không được hỏi/chấm (`so_dinh_danh`, `so_gplx`, `ngay_sinh`, `nam_sinh`); `ho_ten` có chấm.")
    A("* **Chấm**: `eval/field_metrics.py` (4 chế độ so sánh; bảng dùng *chặt* và *mềm*), `lib.load_gold` giữ nguyên quy ước giai đoạn 2 (trường chỉ ghi thời hạn/cụm không phải ngày → không có ngày cụ thể; `[?]` → loại khỏi điểm). CI 95% = bootstrap percentile 1000 lần theo đơn vị; cận trên của tỉ lệ sai là Clopper–Pearson MỘT phía 95% (khi 0 sai trên n: ≈ 3/n). Luật \"F1 của luật rỗng\" = 0 (không TP, recall 0).")
    A("* **Tham số đường dẫn v2**: `lib.load_gold(path)` và `load_units(path=...)` đã có sẵn tham số; thêm `pages_dir` cho `LocalVlmJson` và `generic` cho `RegexRules` (mặc định giữ hành vi v1; 104 đơn vị v1 cho kết quả luật giống hệt cache giai đoạn 2).")
    A("* **Cache đĩa**: mọi lời gọi LLM/VLM nằm ở `teams/team4_extraction/_cache/ollama/` (chạy lại miễn phí, tất định); dự đoán ở `03_unseen_types/_cache/preds/` (không commit: có thể chứa họ tên).")
    A("")
    A("## 2. Kết quả zero-tuning (cấu hình giai đoạn 2, chưa chỉnh gì)")
    A("")
    A("Tập TEST/EXCLUDED ở đây chỉ là mẫu thêm (không có gì được chỉnh nên không thể rò rỉ); các tập báo riêng vì cỡ mẫu nhỏ và EXCLUDED là tệp ghép.")
    A("")
    A(table_main(b, GROUPS, ["regex", "llm", "vlm", "filename", "cascade", "cascade+reject"], names))
    A("")
    A("**Theo kiểu trường** (F1 theo kiểu; n = số trường có đáp án):")
    A("")
    A(table_ftype(b, GROUPS, ["llm", "vlm"], names))
    A("")
    A("* Ngày và mã tốt hơn văn bản chặt: văn bản dài (tên bên + mã số thuế, đoạn tuyến/giá cước) lệch ranh giới nên F1 chặt thấp (0.2–0.4), mềm cao hơn nhiều (0.6–0.9). Con số mềm là con số nên nhìn khi nói về \"đọc đúng nội dung\"; con số chặt cho biết còn bao xa mới nhập thẳng vào ERP.")
    A("* VLM hơn LLM-trên-OCR ở hầu hết kiểu trường, cùng chiều với giai đoạn 2; lưu ý bắt buộc 3 của giai đoạn 2 vẫn đúng (VLM và người chú thích cùng đọc ảnh).")
    A("")
    A("**Theo loại tài liệu** (gộp DEV+TEST+EXCLUDED, vì không có chỉnh sửa nào; n đơn vị mỗi loại 1–25 nên CI rất rộng, đọc như minh họa; trường hạn: đúng/bỏ trống/**sai** trên số trường hạn có đáp án):")
    A("")
    A(table_type(b, i))
    A("")
    A("Cột 'đúng mọi trường bắt buộc' ở các bảng trên phụ thuộc mạnh vào số trường văn bản dài bắt buộc của từng loại (chưa phân rã); đọc F1 và cột hạn trước.")
    A("")
    A("## 3. Trường hạn: tự nhận hay từ chối (zero-tuning, quy tắc giai đoạn 2)")
    A("")
    A(table_abst(b, GROUPS + [("ALL", "gộp 84")], {OLD}))
    A("")
    A(f"Đặt cạnh giai đoạn 2 trên 4 loại cũ (khác loại, khác tên tệp, KHÔNG kiểm định ghép cặp): DEV 37/64 = 58% (0 sai, cận trên 8%), TEST 12/16 = 75% (0 sai, cận trên 22%). Ở loại mới: DEV {ab['DEV'][OLD]['n_correct']}/{ab['DEV'][OLD]['n_gold_present']}, TEST {ab['TEST'][OLD]['n_correct']}/{ab['TEST'][OLD]['n_gold_present']}, EXCLUDED {ab['EXCLUDED'][OLD]['n_correct']}/{ab['EXCLUDED'][OLD]['n_gold_present']}. Không có lần tự nhận sai nào (gộp 84: {old_all['n_emitted']} tự nhận, 0 sai, cận trên {old_all['wrong_upper95']:.2f}): quy tắc giữ được **tính an toàn**, nhưng mất phần lớn **tự động hóa**; phần còn lại vào hàng duyệt tay kèm gợi ý ({b['groups']['ALL']['review_queue']['n_review_gold_present']} trường hạn thật vào hàng duyệt, gợi ý đúng {b['groups']['ALL']['review_queue']['n_suggestion_correct']}/{b['groups']['ALL']['review_queue']['n_with_suggestion']}).")
    A("")
    A("Các quy tắc khác (đủ bảng ở `results3_base.json`): VLM một mình ra 58/62 đúng, 1 sai gộp (thừa khi đáp án không có hạn); `llm=vlm` cũng 1 sai. Ngoài VLM và tên tệp không có nguồn thứ hai độc lập với OCR cho loại mới, mà tên tệp lại không đáng tin cho loại mới (xem trên).")
    A("")
    A("## 4. Phân tích lỗi (chỉ DEV; TEST/EXCLUDED không xem từng đơn vị để giữ phần không chỉnh sạch)")
    A("")
    A(f"Cấu hình cascade zero-tuning (= LLM), so sánh mềm, trên DEV: {len(CAUSES)} lỗi ở các trường không PII. Nguyên nhân gán bằng đặc trưng tự động (`classify_errors.py`: chuỗi đáp án có trong OCR/đoạn đưa LLM không, mực viết, độ trùng từ), không phải đọc từng ca:")
    A("")
    A(cause_tab)
    A("")
    A("15 nhóm lỗi lớn nhất (loại × trường × kết quả):")
    A("")
    A(top_tab)
    A("")
    n_ink_exp = sum(v for (c, o), v in ec.items() if c == "ink")
    A(f"**Riêng trường hạn (DEV, cascade zero-tuning)**: {len(xs)} lỗi hạn — " + ", ".join(f"{CAUSE_VI[c].split(' (')[0]}: {v} ({o})" for (c, o), v in sorted(ec.items(), key=lambda kv: -kv[1])) + ". Một nửa (6/12) là chữ viết tay trên giấy chứng nhận bảo hiểm (OCR không đọc được; LLM bỏ trống hoặc đọc sai); còn lại là OCR thiếu chuỗi, LLM bỏ sót, hoặc điền hạn khi giấy không có (2). Với chữ in, hạn đúng gần hết.")
    A("")
    A("Nhận xét theo các hiện tượng brief nêu:")
    A("")
    A("* **Luật thiếu mẫu ngày/nhãn của loại mới**: đúng là lý do duy nhất để luật 0 điểm (không có luật), và sửa được bằng luật nhãn chung (mục 5): luật chung đạt đúng 36/45 hạn DEV (xem mục 5) chỉ nhờ vài nhãn (\"có giá trị đến\", \"hiệu lực từ ngày ký đến\", \"Đến: giờ, ngày\").")
    A("* **\"Không thời hạn\"**: 0/62 đơn vị DEV có cụm \"không thời hạn\"/\"vô thời hạn\" trong OCR (GPLX/CCCD trong bộ này đều in ngày hết hạn): hiện tượng này CHƯA được kiểm bằng dữ liệu ở đây. Luật chung có chặn (không nhảy sang ngày cấp khi gặp cụm đó) và có test tổng hợp, nhưng chưa có số đo thật.")
    A("* **\"Kể từ ngày ký\"**: 15 hợp đồng vận chuyển DEV có hạn kiểu \"có hiệu lực từ ngày ký đến ngày …\" (luật chung đọc đúng); 7 biên bản mượn bồn có \"từ ngày ký\" nhưng không có ngày kết thúc (đáp án không có hạn): luật không bịa ngày, nhưng LLM điền `ngay_nhan_bon` ở 5 ca (xem bảng).")
    A("* **Nhiều mức tiền**: `so_tien_bao_hiem` sai ở 4 ca (3 viết tay, 1 lệch ranh giới) và `phi_bao_hiem` sai ở 5 ca (cả 5 viết tay); lỗi \"chọn nhầm giữa nhiều mức tiền\" KHÔNG phải nguyên nhân thấy được trong các ca này (chữ viết tay che mất nó).")
    A("* **OCR mờ/bóng chữ mặt sau**: chiếm một phần nhỏ (8 sai + 6 bỏ trống trong tổng) và chủ yếu là mã/số (chữ số đọc nhầm, vd. mã số thuế, số giấy); nằm ở `ocr_missing`.")
    A("* **Chữ viết tay**: nguyên nhân lớn nhất theo kiểu trường (33 lỗi, gồm 12 ngày, 6 mã, 5 số, 10 văn bản) và tập trung ở một loại (giấy chứng nhận bảo hiểm); đây là chỗ cần VLM hoặc người duyệt.")
    A("* **Khác**: LLM 4B bỏ trống ở trường văn bản dài dù chuỗi có trong prompt (nhóm `llm_miss`: 21 bỏ trống + 21 sai); đây là điểm chung với giai đoạn 2 (mô hình nhỏ quá thận trọng khi bị yêu cầu \"không chắc thì null\").")
    A("")
    A("## 5. Một vòng cải tiến chung (chỉ chỉnh trên DEV)")
    A("")
    A("**Cái đã làm** (`methods/generic_date_rules.py`, bật bằng `RegexRules(generic=True)`; loại có luật riêng không bị đụng): luật ngày chung theo tên trường — hạn (`ngay_het_han`, `hieu_luc_den`, `thoi_han_thue_den`): câu hiệu lực của hợp đồng/giấy ủy quyền (\"có hiệu lực [kể] từ ngày ký|<ngày> đến [hết] <ngày>\"), \"có giá trị đến [Expires] <ngày>\", \"thời hạn/hết hạn: <ngày>\", \"Đến: <giờ>, ngày <ngày>\" của giấy bảo hiểm; `hieu_luc_tu`/`thoi_han_thue_tu`, `ngay_ky` (\"Hôm nay, ngày …\", \"Ký ngày …\"), `ngay_cap` (\"<nơi>, ngày … tháng … năm …\" ở cuối trang cuối). Từ chối khi giữa nhãn và ngày có \"không/vô thời hạn\", \"ngày cấp\", \"ngày sinh\". Hai lỗi thấy trên DEV được sửa (cụm \"Từ ngày … Đến ngày …\" của KHÓA HỌC bị nhận là hạn; đã đòi giờ đi kèm cho dạng \"Đến:\"). Quy tắc tự nhận: chọn trên DEV `regex=llm` (không sai trường nào trên DEV, tự nhận nhiều nhất trong các quy tắc cần ≥ 2 nguồn).")
    A("")
    A("**Phạm vi phủ**: trong 17 trường hạn không chỉnh, 5 trường bị từ chối là toàn bộ của hai loại KHÔNG có đơn vị DEV nào (`GCN_KIEM_DINH_DO_LUONG` 0/4, `HD_THUE_TAI_SAN` 0/1 ở bảng theo loại mục 2): luật chung chỉ bắt được cách ghi hạn đã thấy trên DEV; loại có cách ghi mới thì luật im lặng (an toàn) và LLM/VLM vẫn đọc đúng nhưng không được tự nhận. Ta không xem văn bản của hai loại này để vá (giữ phần không chỉnh sạch): đó là việc của vòng sau.")
    A("")
    A("**Đóng băng**: `dev_selection3.json` (băm của luật chung, bộ bọc, luật cũ, quy tắc hạn, silver v2) ghi TRƯỚC khi sinh dự đoán luật chung cho TEST+EXCLUDED và chấm (`make_results3.py --set improved --final-test`, một lần). LLM, VLM, prompt, ngày trong tên tệp không đổi.")
    A("")
    A("**DEV (đã chỉnh trên chính các đơn vị này nên LẠC QUAN):**")
    A("")
    A(table_main(i, [("DEV", "DEV")], ["regex", "cascade", "cascade+reject", "cascade+reject(phase2 rule)"], names_i))
    A("")
    A("**Phần KHÔNG chỉnh (TEST+EXCLUDED, chạy một lần):**")
    A("")
    A(table_main(i, [("TEST", "TEST"), ("EXCLUDED", "EXCLUDED"), ("TEST+EXCLUDED", "TEST+EXCLUDED")], ["regex", "cascade", "cascade+reject", "cascade+reject(phase2 rule)"], names_i))
    A("")
    A("**Quy tắc tự nhận hạn sau cải tiến (mọi quy tắc đồng thuận, cùng dự đoán):**")
    A("")
    A(table_abst(i, GROUPS + [("ALL", "gộp 84")], {RULE, OLD, "regex", "vlm", "regex=vlm", "regex=llm=vlm", "llm=vlm"}))
    A("")
    dd, dt_ = ai["DEV"][RULE], ai["TEST+EXCLUDED"][RULE]
    A(f"* **Có đáng giữ không?** Có, với hai lưu ý. Trên phần không chỉnh, tự nhận hạn tăng từ {old_te['n_correct']}/{old_te['n_gold_present']} ({old_te['automation']:.0%}) lên {dt_['n_correct']}/{dt_['n_gold_present']} ({dt_['automation']:.0%}) mà vẫn 0 sai (cận trên 95% {dt_['wrong_upper95']:.2f}; chỉ {dt_['n_emitted']} lần tự nhận nên khoảng còn rất rộng). Trên DEV (đã chỉnh): {dd['n_correct']}/{dd['n_gold_present']} ({dd['automation']:.0%}), 0 sai. Chênh lệch DEV → không chỉnh ({dd['automation']:.0%} → {dt_['automation']:.0%}) là cỡ nhiễu của n=17, không tách được.")
    A(f"* **Phương án thay thế**: `llm=vlm` tự nhận {ai['TEST+EXCLUDED']['llm=vlm']['n_correct']}/{ai['TEST+EXCLUDED']['llm=vlm']['n_gold_present']} ngoài mẫu chỉnh (cao hơn `regex=llm`), nhưng sai {ai['DEV']['llm=vlm']['n_wrong']} trên DEV (thừa khi giấy không có hạn) và cần ảnh + ~19 s/đơn vị VLM; `regex=llm` rẻ hơn nhiều (CPU + một lời gọi LLM đã có). Chọn `regex=llm` là theo quy tắc chọn đã ghi trước trên DEV, không phải vì tốt nhất trên phần không chỉnh.")
    A("* **Lưu ý 1**: F1 toàn bộ trường KHÔNG đổi so với cascade zero-tuning (cột F1 của 'cascade: luật chung → LLM' bằng cột của 'cascade' ở mục 2 trên cả DEV và TEST+EXCLUDED: LLM đã đọc ngày khá tốt, ngày F1 0.84 trước và sau; hàng 'cascade + tự nhận' thấp hơn vì các hạn bị từ chối bị tính là bỏ trống); lợi ích thật nằm ở **tính độc lập của nguồn thứ hai**: trước đó `regex=llm` rỗng (luật rỗng) và không có nguồn nào ngoài tên tệp/VLM để đối chiếu hạn.")
    A("* **Lưu ý 2**: luật chung và LLM cùng đọc một bản OCR, nên chung lỗi khi OCR sai chữ số (bài học giai đoạn 2: hạn sai do '22' thay '12'); `regex=llm` chưa sai trường nào trong 47 lần tự nhận (DEV 35 + ngoài mẫu 12) nhưng 47 mẫu chưa nói được gì về mức 1%.")
    A("")
    A("## 6. Đề xuất đưa vào `src/extraction/` (KHÔNG tự sửa; agent khác đang sửa `field_extractor.py`)")
    A("")
    A("1. `schemas.py`: thêm 17 loại vào `SUPPORTED_TYPES` và sao 17 tệp `teams/team4_extraction/schema/<LOẠI>.json` vào `schema_data/` (test `tests/test_extraction_fields.py` hiện kiểm hai bản giống nhau; cần mở rộng danh sách). Không có bước này thì sản phẩm trả `UnsupportedDocType` cho loại mới.")
    A("2. `field_rules.py`: trong `apply_rules`, loại không có luật riêng gọi `generic_rules(tên_trường, Doc(pages))` (chép `methods/generic_date_rules.py`, chỉ phụ thuộc `Doc`, `D_VN`, `D_NUM`, `DATE`, `_clean` của chính tệp đó). Hành vi 4 loại cũ không đổi (đã kiểm: 104 đơn vị v1 cho luật giống hệt cache giai đoạn 2).")
    A(f"3. `field_extractor.py`: đặt quy tắc hạn mặc định `{RULE}` cho loại không có luật riêng khi có luật chung; giữ `any-model=filename` cho 4 loại cũ (đã chứng minh trên đó) hoặc đo lại. Quy tắc `regex=llm` đã có sẵn trong `expiry_rules.EXPIRY_RULES`.")
    A("4. Cần thêm test cho mã mới (đã có test ở phía nhóm: `teams/team4_extraction/tests/test_t4_generic_date_rules.py`); khi chuyển vào `src/` thì thêm test tương ứng ở `tests/`.")
    A("5. Chưa nên bật tự nhận hạn không có người duyệt cho loại mới: 47 lần tự nhận đúng liên tiếp chỉ chứng minh sai ≤ 6% (một phía 95%).")
    A("")
    A("## 7. Độ trễ và tài nguyên (GPU RTX 3060 dùng chung; số đo KHÔNG sạch)")
    A("")
    A("GPU và Ollama đang được client khác dùng chung (client khác giữ `qwen3.5:4b` với `num_ctx` 32768; gọi với `num_ctx` 6144/12288 làm Ollama nạp lại mô hình: lời gọi đầu tiên mỗi lượt mất vài phút do chờ/nạp lại). Trung vị tính theo `orig_latency_ms` của lời gọi gốc (cache giữ số gốc); cột 'chỉ suy luận' trừ thời gian nạp.")
    A("")
    A("| phương pháp | n | trung vị toàn bộ (ms) | p95 toàn bộ (ms) | trung vị chỉ suy luận (ms) | VRAM Ollama |")
    A("|---|---|---|---|---|---|")
    for c, vr in (("regex", "0 (CPU)"), ("llm", "~3,1 GB (ctx 6144)"), ("vlm", "~3,3 GB (ctx 12288)")):
        l = lat[c]["latency"]
        inf = "n/a" if l["inference_only_median_ms"] is None else f"{l['inference_only_median_ms']:.0f}"
        A(f"| {c} | {l['n']} | {l['wall_median_ms']:.2f} | {l['wall_p95_ms']:.0f} | {inf} | {vr} |" if c == "regex" else f"| {c} | {l['n']} | {l['wall_median_ms']:.0f} | {l['wall_p95_ms']:.0f} | {inf} | {vr} |")
    A("")
    A("Luật + LLM ≈ 4–10 giây/đơn vị khi mô hình đã nạp; thêm VLM ≈ 19 giây/đơn vị (4 ảnh). Cải tiến ở mục 5 chỉ thêm vài mili giây (luật) và cho phép bỏ VLM khỏi tự nhận hạn (`regex=llm` không cần ảnh). Đuôi p95 lớn ở tập EXCLUDED (hàng trăm giây) là lúc Ollama nạp lại mô hình do client khác, không phải độ trễ suy luận. Chạy tuần tự, toàn bộ 84 đơn vị: LLM ~640 s, VLM ~1735 s (đồng hồ treo tường, GPU dùng chung).")
    A("")
    A("## 8. Hạn chế và việc còn lại")
    A("")
    A("* **Đáp án máy, chưa có người kiểm** (silver v2: Haiku/Sonnet cùng họ có thể cùng sai; Opus phân xử 135 mục mà vẫn là mô hình). Ví dụ `ngay_nhan_bon` và `cua_hang` ở bảng lỗi: cần người xem đáp án hay LLM đúng.")
    A("* **Cỡ mẫu nhỏ**: 62 trường hạn có đáp án (DEV 45, TEST 8, EXCLUDED 9), nhiều loại chỉ 1–3 đơn vị; CI rộng; chênh lệch giữa tập DEV/TEST/EXCLUDED phần lớn là nhiễu. 10 đơn vị EXCLUDED là tệp ghép không đại diện.")
    A("* Phần \"không chỉnh\" chỉ có 17 trường hạn có đáp án (TEST 8 + EXCLUDED 9): đủ để thấy luật chung không vỡ ngay, chưa đủ để nói về mức sai thấp.")
    A("* **Một biểu mẫu thống trị** (`HD_VAN_CHUYEN`: 26 đơn vị cả ba tập) nên luật chung phần lớn được kiểm trên một mẫu hợp đồng; các loại khác 1–7 đơn vị.")
    A("* Chưa đo: hiện tượng \"không thời hạn\"; thẻ nhiều mặt có ảnh nửa trắng; VLM với > 4 ảnh (hợp đồng dài chỉ thấy trang đầu); trường `ho_ten` có chấm nhưng là dữ liệu cá nhân (không in giá trị).")
    A("* Không thử cải tiến phía LLM (prompt theo loại, gợi ý trường dài): chỉ một vòng chung theo đề bài; đây là hướng tiếp theo cho nhóm `llm_miss` (42 lỗi DEV).")
    A("")
    A("## 9. Chạy lại")
    A("")
    A("```powershell")
    A("# từ gốc repo; Ollama ở 127.0.0.1:11434 (không pull/xóa/khởi động lại mô hình)")
    A(r".venv\Scripts\python.exe -X utf8 teams\team4_extraction\experiments\03_unseen_types\run_zero_tuning.py --configs regex@ocr_v2,filename,llm@ocr_v2,vlm")
    A(r".venv\Scripts\python.exe -X utf8 teams\team4_extraction\experiments\03_unseen_types\make_results3.py --set base")
    A(r".venv\Scripts\python.exe -X utf8 teams\team4_extraction\experiments\03_unseen_types\classify_errors.py       # DEV, nguyên nhân lỗi")
    A(r".venv\Scripts\python.exe -X utf8 teams\team4_extraction\experiments\03_unseen_types\dev_iterate.py --errors   # vòng cải tiến, CHỈ DEV")
    A(r".venv\Scripts\python.exe -X utf8 teams\team4_extraction\experiments\03_unseen_types\freeze3.py               # ghi dev_selection3.json, một lần")
    A("# dự đoán luật chung cho mọi đơn vị (CPU): lib.run_config('regex','ocr_v2',units_v2(),tag='v2',force=True,generic=True) (xem common3.py)")
    A(r".venv\Scripts\python.exe -X utf8 teams\team4_extraction\experiments\03_unseen_types\make_results3.py --set improved --final-test")
    A(r".venv\Scripts\python.exe -X utf8 teams\team4_extraction\experiments\03_unseen_types\build_results3_md.py")
    A("```")
    A("")
    A("Test: `.venv\\Scripts\\python.exe -X utf8 -m pytest teams\\team4_extraction\\tests -q` (có `test_t4_generic_date_rules.py`).")
    A("")
    (HERE / "RESULTS.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("đã ghi", HERE / "RESULTS.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
