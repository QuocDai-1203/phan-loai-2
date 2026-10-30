"""build_results_md.py - Ghép RESULTS.md từ results_*.json và tables_*.md (mọi con số lấy từ JSON, không gõ tay). Chạy sau make_results.py + render_tables.py.

    .venv\\Scripts\\python.exe -X utf8 .../build_results_md.py
Lời văn nằm trong tệp này; đổi nhận định thì sửa ở đây rồi chạy lại để RESULTS.md luôn khớp số liệu.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
J = {(s, g): json.loads((HERE / f"results_{s}_{g}.json").read_text(encoding="utf-8")) for s in ("DEV", "TEST") for g in ("all", "trusted")}
CS = "cascade theo kiểu (văn bản: llm→luật; ngày/số/mã: luật→llm) @ocr_v2"
CR = "cascade + từ chối hạn [any-model=filename]"
SEL = json.loads((HERE / "dev_selection.json").read_text(encoding="utf-8"))
SILVER = (HERE.parents[1] / "gold" / "silver_report.md").read_text(encoding="utf-8")


def c(s, g, n):
    return J[(s, g)]["configs"][n]


def f2(x):
    return "n/a" if x is None or x != x else f"{x:.2f}"


def ci(r, k, lo=None, hi=None):
    return f"{r[k]:.2f} [{r[lo or k + '_ci_lo']:.2f}; {r[hi or k + '_ci_hi']:.2f}]"


def row(s, n, label=None, g="all"):
    x = c(s, g, n)
    a, l = x["normalized"], x["lenient"]
    e = a["expiry_all"]
    return (f"| {label or n} | {ci(a['overall'], 'f1')} | {ci(l['overall'], 'f1')} | {ci(l['doc_level'], 'rate', 'ci_lo', 'ci_hi')} | "
            f"{f2(e['correct_rate'])} / {f2(e['empty_rate'])} / **{f2(e['wrong_rate'])}** (n={e['n_gold_present']}) |")


def head(s, g="all"):
    return ["| phương pháp (văn bản OCR cục bộ `ocr_v2`, trừ khi ghi khác) | F1 chặt [CI 95%] | F1 mềm [CI] | đúng mọi trường bắt buộc, mềm [CI] | hạn: đúng / bỏ trống / **sai giá trị** |", "|---|---|---|---|---|"]


ROWS = [("regex@ocr_v2", "luật/regex"), ("gliner@ocr_v2", "GLiNER + gán trường"), ("llm@ocr_v2", "LLM cục bộ (văn bản OCR)"), ("vlm", "VLM cục bộ (ảnh trang; xem lưu ý 3)"),
        ("filename", "ngày trong tên tệp (chỉ trường hạn)"), (CS, "**ghép theo kiểu: LLM cho văn bản, luật cho ngày/số/mã**"),
        (CR, "**ghép theo kiểu + tự nhận hạn khi `any-model=filename`**")]
RF = [("llm@ocr_llm_haiku", "(tham chiếu, KHÔNG on-prem) LLM trên bản chép Haiku, chỉ trường ở trang <= 2")]


def block(s, g="all"):
    out = head(s)
    out += [row(s, n, lab, g) for n, lab in ROWS]
    out += [row(s, n, lab, g) for n, lab in RF]
    return out


def ab(s, rule):
    return next(r for r in J[(s, "all")]["abstention"] if r["rule"] == rule)


dv, ts = ab("DEV", SEL["expiry_rule"]), ab("TEST", SEL["expiry_rule"])
rq_d, rq_t = J[("DEV", "all")]["review_queue"], J[("TEST", "all")]["review_queue"]
from importlib import import_module  # noqa: E402
import sys  # noqa: E402
sys.path.insert(0, str(HERE))
C = import_module("combine")


def ink(s, n, k):
    b = c(s, "all", n)["by_ink"]["lenient"].get(k)
    return None if not b else (b["n"], b.get("correct", 0) / b["n"], b.get("wrong", 0) / b["n"])


def inkrow(label, n_ocr, n_ref):
    out = []
    for k in ("printed", "handwritten", "under_stamp"):
        a, b = ink("DEV", n_ocr, k), ink("DEV", n_ref, k)
        if a and b:
            out.append(f"| {label} | {k} | {a[0]} | {a[1]:.2f} / {a[2]:.2f} | {b[1]:.2f} / {b[2]:.2f} | {b[1] - a[1]:+.2f} |")
    return out


def cost_row(m):
    a, b = c("DEV", "all", f"{m}@ocr_v2"), c("DEV", "all", f"{m}@ocr_llm_haiku")
    t = []
    for ty in ("date", "id", "text", "number"):
        x, y = a["lenient"]["per_type"][ty]["f1"], b["lenient"]["per_type"][ty]["f1"]
        t.append(f"{f2(x)} → {f2(y)}" if (x == x and y == y) else "n/a")
    return f"| {m} | {f2(a['lenient']['overall']['f1'])} → {f2(b['lenient']['overall']['f1'])} | " + " | ".join(t) + " |"


def adjud():
    i = SILVER.index("## 6.")
    return SILVER[i:].replace("## 6.", "### ", 1)


L = []
L += ["# Kết quả so sánh các phương pháp trích xuất trường (Nhóm 4, T4)", "",
      "> Bản tự sinh bởi `build_results_md.py` từ `results_*.json` (số liệu) — đừng sửa tay các con số. Tiếng Việt, viết cho sinh viên năm cuối ngành AI.", "",
      "## 0. Tóm tắt", "",
      "**Câu hỏi.** Trong 4 loại tài liệu đã có schema (`GCN_DDK_BAN_LE_XD`, `CC_TAP_HUAN_VC_HNH`, `HD_MUA_BAN`, `PHIEU_XUAT_KHO`), phương pháp nào trích đúng các trường, "
      "đặc biệt **ngày hết hạn** (làm lịch nhắc), và có thể tự động nhận kết quả mà không để lọt ngày sai không?", "",
      f"**Kết quả chính trên TEST ({J[('TEST', 'all')]['n_units']} đơn vị, chấm MỘT lần với cấu hình đã đóng băng trên DEV; đáp án = silver do mô hình đọc, KHÔNG phải người kiểm):**", ""]
L += block("TEST")
L += ["", f"*DEV ({J[('DEV', 'all')]['n_units']} đơn vị; luật và quy tắc từ chối được chỉnh trên chính các đơn vị này nên số DEV lạc quan):*", ""]
L += block("DEV")
L += ["",
      f"* **Tốt nhất khi chỉ dùng OCR cục bộ:** ghép theo kiểu (F1 mềm TEST {ci(c('TEST', 'all', CS)['lenient']['overall'], 'f1')}, DEV {ci(c('DEV', 'all', CS)['lenient']['overall'], 'f1')}). "
      f"LLM đứng một mình gần bằng; luật mạnh ở ngày/mã/số nhưng yếu ở văn bản; GLiNER yếu (F1 mềm {f2(c('TEST', 'all', 'gliner@ocr_v2')['lenient']['overall']['f1'])}): chỉ đáng tin ở ngày.",
      f"* **VLM đọc ảnh** là phương pháp đơn lẻ mạnh nhất (F1 mềm TEST {f2(c('TEST', 'all', 'vlm')['lenient']['overall']['f1'])}, hạn đúng "
      f"{f2(c('TEST', 'all', 'vlm')['normalized']['expiry_all']['correct_rate'])}) nhưng **con số này bị thổi phồng** (lưu ý 3) và cần ảnh trang.",
      f"* **Ngày hết hạn không thể tin vào một nguồn đơn lẻ:** các phương pháp dựa OCR ra SAI giá trị ở {f2(c('DEV', 'all', 'regex@ocr_v2')['normalized']['expiry_all']['wrong_rate'])} (DEV) "
      f"và {f2(c('TEST', 'all', 'regex@ocr_v2')['normalized']['expiry_all']['wrong_rate'])} (TEST) số trường hạn có đáp án (đọc sai chữ số, chữ viết tay). Hai nguồn cùng đọc từ MỘT bản OCR "
      "sai chung lỗi, nên đồng thuận giữa luật và LLM không cứu được.",
      f"* **Quy tắc tự nhận `{SEL['expiry_rule']}`** (chỉ nhận ngày khi một mô hình đọc trùng ngày trong tên tệp; chọn trên DEV vì không sai trường nào): "
      f"DEV nhận {dv['n_emitted']}/{dv['n_gold_present']} trường hạn thật ({dv['automation']:.0%}), **sai {dv['n_wrong']}**, cận trên 95% của tỉ lệ sai {dv['wrong_upper95']:.0%}; "
      f"TEST nhận {ts['n_emitted']}/{ts['n_gold_present']} ({ts['automation']:.0%}), **sai {ts['n_wrong']}**, cận trên 95% {ts['wrong_upper95']:.0%}. "
      f"Phần còn lại ({rq_d['n_review']} trường ở DEV, {rq_t['n_review']} ở TEST) chuyển người duyệt kèm ngày gợi ý (gợi ý đúng {rq_d['n_suggestion_correct']}/{rq_d['n_with_suggestion']} ở DEV, "
      f"{rq_t['n_suggestion_correct']}/{rq_t['n_with_suggestion']} ở TEST). **Chưa chứng minh được 'sai <= 1%'**: với 0 lỗi cần tối thiểu {C.n_needed(0.01, 0)} lần tự nhận đúng "
      f"(<= 2%: {C.n_needed(0.02, 0)}; <= 5%: {C.n_needed(0.05, 0)}); ta mới có {dv['n_emitted'] + ts['n_emitted']} (DEV+TEST).",
      f"* **Độ tin cậy của đáp án:** người chú thích chính (Haiku) bị người phân xử (Opus) coi là sai ở ~17% số mục bất đồng/rủi ro (xem mục 6), nên mọi con số ở đây có sai số do đáp án.", ""]

L += ["## 1. Thiết lập", "",
      "* **Đơn vị chấm** = `(doc_id, segment)`; 4 loại, 104 đơn vị duy nhất: DEV 76, TEST 22 (+6 đơn vị phiếu xuất kho từ tệp ghép bị loại khỏi chấm). Chia DEV/TEST đóng băng của nhóm 00.",
      "* **Đáp án (silver)**: `gold/fields_silver_v1.jsonl`. Haiku đọc ảnh cả 104 đơn vị, Sonnet đọc độc lập 40 đơn vị, Opus phân xử 58 trường bất đồng/rủi ro (ngày hết hạn lệch tên tệp, "
      "chữ viết tay/dưới dấu, bất đồng hai người). Chỉ `agreed_unverified` (hai mô hình giống nhau) hoặc `model_adjudicated`; **không có trường nào `human_verified`**. "
      "`--gold all` = mọi trường (phần lớn chỉ một người đọc: Haiku); `--gold trusted` = chỉ trường hai người đồng thuận hoặc đã phân xử (ít hơn nhiều: ở TEST chỉ "
      f"{J[('TEST', 'trusted')]['configs']['regex@ocr_v2']['normalized']['expiry_all']['n_gold_present']} trường hạn).",
      "* **Chuẩn hóa/so sánh**: `eval/normalize.py`; **chặt** = sau chuẩn hóa ngày/số/mã/văn bản (NFC, hoa-thường, khoảng trắng); **mềm** = văn bản bỏ dấu tiếng Việt và dấu câu, chuỗi ngắn nằm trọn trong chuỗi dài, "
      "'tên + mã số thuế' khớp theo tên (hai mã số thuế khác nhau thì KHÔNG khớp). Hai cột luôn đi cạnh nhau; ngày/số/mã giống nhau ở hai chế độ. Trường PII (số định danh, ngày sinh, họ tên) **không được chấm**.",
      "* **Quy ước TP/FP/FN** theo README T3 (đúng = TP; sai giá trị = FP+FN; bỏ trống = FN; thừa = FP; null-null không tính). Đơn vị phương pháp lỗi/không có văn bản chấm như dự đoán toàn null và đếm riêng (`n_failed`: 0 ở mọi cấu hình chính). "
      "CI 95% = bootstrap percentile 1000 lần theo đơn vị; khi một tỉ lệ là 0 hoặc 1 thì CI bootstrap suy biến, dùng cận nhị thức ở bảng E.",
      "* **Đóng băng**: `dev_selection.json` (băm của luật regex, prompt, bộ chuẩn hóa, silver; quy tắc từ chối chọn trên DEV) được ghi TRƯỚC khi chạy TEST; TEST chạy một lần (`run_methods.py --final-test`). "
      "Đáp án ở DEV/TEST dùng bản silver SAU phân xử (thay đổi so với lúc phát triển: 58 trường).",
      "* **Phương pháp**: luật (`src/extraction/field_rules.py`), ngày trong tên tệp, GLiNER `belumind/barb-1-ie-vi` + gán trường theo từ khóa bên trái (CPU), LLM `qwen3.5:4b` qua Ollama với đầu ra ràng buộc JSON Schema (prompt `v1`), "
      "VLM cùng mô hình đọc ảnh trang (4 ảnh đầu), và các cách ghép. Nguồn văn bản: `ocr_v2` (OCR cục bộ, **nguồn sản xuất**), `ocr_llm_haiku` (chỉ 2 trang đầu; không on-prem), `text_layer`.", ""]

L += ["### Lưu ý bắt buộc (đọc trước khi dùng con số)", "",
      "1. **Đáp án là silver do mô hình LLM đọc, chưa có người kiểm.** Khi phương pháp và đáp án cùng sai thì được tính là đúng.",
      "2. **Các mô hình họ Claude có thể chung lỗi** (cùng đọc ảnh theo cùng hướng dẫn); độ đồng thuận giữa Haiku và Sonnet không chứng minh đúng.",
      "3. **VLM và người chú thích đều đọc ẢNH** nên độ khớp VLM-silver có thể cao hơn so với phương pháp dựa OCR (chung kiểu lỗi/đọc); đừng đọc 'VLM hơn OCR' thành lợi thế thật 1:1.",
      "4. **Trường nằm ở trang không được cho annotator xem** (đơn vị > 4 trang chỉ cho xem tối đa 6 trang) có thể bị ghi `not_present`; phương pháp tìm thấy giá trị ở đó bị tính 'thừa'. Ảnh hưởng chủ yếu `HD_MUA_BAN` dài.",
      "5. **Một biểu mẫu, nhiều tài liệu**: `CC_TAP_HUAN_VC_HNH` (23/24 cùng mẫu) và `PHIEU_XUAT_KHO` (biểu mẫu BSR số hóa) cho điểm cao giả tạo; chỉ `GCN_DDK_BAN_LE_XD` và `HD_MUA_BAN` có nhiều biến thể.",
      "6. **Cỡ mẫu nhỏ**: TEST 22 đơn vị, 16 trường hạn có đáp án — CI rộng; nhiều so sánh giữa phương pháp 'không tách được'.",
      "7. Luật và quy tắc từ chối được chỉnh trên DEV: số DEV là 'đã chỉnh trên chính các đơn vị này'; chỉ số TEST mới là ước lượng ngoài mẫu (và vẫn chỉ 22 đơn vị).", ""]

L += ["## 2. Theo loại tài liệu", "", "Bảng B của từng tập (cuối tệp) có chi tiết. Tóm tắt F1 mềm của phương pháp ghép theo kiểu:", "",
      "| loại | DEV (n) | TEST (n) | ghi chú |", "|---|---|---|---|"]
notes = {"CC_TAP_HUAN_VC_HNH": "một biểu mẫu thẻ duy nhất (23/24): lạc quan", "GCN_DDK_BAN_LE_XD": "bản quét, con dấu chứng thực đè lên hạn, chữ viết tay: khó nhất",
         "HD_MUA_BAN": "nhiều biến thể; hạn nằm trong điều khoản cuối, có hợp đồng không ghi hạn", "PHIEU_XUAT_KHO": "bản số hóa BSR (chữ thật): gần như hoàn hảo, một mẫu"}
for t in J[("DEV", "all")]["units_by_type"]:
    d_, t_ = c("DEV", "all", CS)["by_doc_type"][t]["lenient"], c("TEST", "all", CS)["by_doc_type"][t]["lenient"]
    L.append(f"| {t} | {f2(d_['overall']['f1'])} ({d_['n_units']}) | {f2(t_['overall']['f1'])} ({t_['n_units']}) | {notes[t]} |")
L.append("")

L += ["## 3. Cái giá của OCR (DEV)", "",
      "So CÙNG phương pháp trên `ocr_v2` (OCR cục bộ) và trên bản chép của Haiku (LLM đọc ảnh: gần như 'OCR hoàn hảo'; **không có on-prem**, là cận trên). "
      "Chỉ chấm trường có đáp án ở trang <= 2. F1 mềm; mũi tên = ocr_v2 → bản chép Haiku.", "",
      "| phương pháp | tất cả | ngày | mã | văn bản | số |", "|---|---|---|---|---|---|", cost_row("regex"), cost_row("llm"), "",
      "Theo mực viết của đáp án (silver; so sánh mềm), `đúng / sai giá trị`:", "",
      "| phương pháp | mực | n trường | OCR cục bộ | bản chép Haiku | Δ đúng |", "|---|---|---|---|---|---|"]
L += inkrow("luật", "regex@ocr_v2", "regex@ocr_llm_haiku") + inkrow("LLM", "llm@ocr_v2", "llm@ocr_llm_haiku")
L += ["", "VLM đọc ảnh (không qua OCR), cùng bảng: " + "; ".join(f"{k}: {ink('DEV', 'vlm', k)[1]:.2f} đúng / {ink('DEV', 'vlm', k)[2]:.2f} sai (n={ink('DEV', 'vlm', k)[0]})" for k in ("printed", "handwritten", "under_stamp")) + ".", "",
      "* OCR cục bộ mất nhiều nhất ở chữ **viết tay** và **dưới con dấu** (đúng thấp hơn rõ so với bản chép), còn chữ in chỉ mất ít. Đây là nơi cần đọc ảnh (VLM) hoặc người duyệt.",
      "* **Text layer**: các trang số hóa (chủ yếu phiếu xuất kho) đã nằm trong `ocr_v2` với `source = text_layer`, nên so `text_layer` với `ocr_v2` trên các đơn vị đó cho kết quả GIỐNG HỆT (xem bảng C của từng tập); "
      "không thể đo 'OCR vs chữ thật' trên bộ này. Trên các đơn vị có chữ thật (DEV 10, TEST 5; đều là phiếu xuất kho) mọi phương pháp tốt hơn hẳn trên nguồn sạch này (LLM F1 mềm ~0,98-1,00).",
      "* Dòng 'ORACLE' ở bảng D chỉ để minh họa: định tuyến VLM theo mực của đáp án (không triển khai được vì sản xuất không biết trước ô nào viết tay); lợi ích nhỏ so với dùng VLM toàn phần.", ""]

L += ["## 4. Ngày hết hạn: tự nhận hay từ chối", "",
      f"Chọn trên DEV trong {len(J[('DEV', 'all')]['abstention'])} quy tắc đồng thuận giữa 4 nguồn {{luật, LLM, VLM, tên tệp}}: quy tắc **không sai trường nào trên DEV** và tự nhận nhiều nhất = "
      f"**`{SEL['expiry_rule']}`**. Bảng E của DEV/TEST liệt kê mọi quy tắc kèm cận trên Clopper-Pearson 95% một phía.", "",
      "* Không quy tắc nào chỉ dựa vào văn bản OCR (luật=LLM) đạt 0 sai trên DEV, vì hai phương pháp đọc cùng một bản OCR nên cùng sai (ví dụ '22' thay vì '12', '24' thay vì '21' khi chữ viết tay).",
      "* Mô hình đọc ảnh (VLM) là nguồn độc lập với OCR nhưng cũng đọc nhầm chữ viết tay (một trường DEV: luật, LLM và VLM cùng đọc 24, đáp án và tên tệp là 21): "
      "ngày trong tên tệp là tín hiệu độc lập hữu ích, **nhưng quy ước đặt tên chưa được công ty xác nhận** (câu hỏi 16) và đứng một mình nó sai ở 3/15 trường TEST. Quy tắc chỉ nhận khi một MÔ HÌNH đọc trùng tên tệp.",
      f"* Cái giá của an toàn: tự động hóa {dv['automation']:.0%} (DEV) / {ts['automation']:.0%} (TEST) số trường hạn thật; phần còn lại vào hàng duyệt tay, kèm ngày gợi ý.",
      f"* Để khẳng định tỉ lệ sai <= 1% (một phía 95%) với 0 lỗi quan sát cần ít nhất **{C.n_needed(0.01, 0)}** lần tự nhận (ta có {dv['n_emitted']} + {ts['n_emitted']}); với <= 5%: {C.n_needed(0.05, 0)}. "
      "Nếu quan sát 1 lỗi thì cần nhiều hơn nữa (xem `combine.n_needed`).", ""]

L += ["## 5. Độ trễ và VRAM", "",
      "Đo khi GPU và Ollama đang được các việc khác dùng chung ('shared GPU load'): Ollama nhiều lần bị đẩy mô hình ra rồi nạp lại (30-45 s mỗi lần) nên độ trễ 'toàn bộ' có đuôi dài; cột 'chỉ suy luận' trừ thời gian nạp. "
      "VRAM lấy từ `ollama ps` (nvidia-smi toàn GPU không tách riêng được). Chi tiết ở bảng F.", "",
      "| phương pháp | trung vị toàn bộ (ms) | trung vị chỉ suy luận (ms) | VRAM Ollama | ghi chú |", "|---|---|---|---|---|"]
for n, lab, vram, note in (("regex@ocr_v2", "luật", "0", "CPU, vài ms"), ("gliner@ocr_v2", "GLiNER (CPU)", "0 (CPU)", "~10-15 s/đơn vị trên CPU dùng chung; nạp mô hình ~40 s một lần"),
                           ("llm@ocr_v2", "LLM văn bản", "~3,1 GB (ctx 6144)", "qwen3.5:4b Q4_K_M"), ("vlm", "VLM ảnh", "~3,3 GB (ctx 12288)", "4 ảnh/đơn vị")):
    lt = c("TEST", "all", n)["latency"]
    L.append(f"| {lab} (TEST) | {f2(lt['wall_median_ms']) if lt['wall_median_ms'] is None else f'{lt['wall_median_ms']:.0f}'} | "
             f"{'n/a' if lt['inference_only_median_ms'] is None else f'{lt['inference_only_median_ms']:.0f}'} | {vram} | {note} |")
L += ["", "Toàn bộ quy trình đề xuất (luật + LLM + tùy chọn VLM cho hạn) ~ 5-16 giây/đơn vị khi mô hình đã nạp.", ""]

L += ["## 6. Độ tin cậy của đáp án: phân xử và ước lượng sai của người chú thích", "", adjud(), ""]

L += ["## 7. Khuyến nghị cho sản xuất (chỉ on-premise) và điều CHƯA chứng minh", "",
      "**Khuyến nghị.** Dùng `src/extraction/field_extractor.py::extract_fields` (đã thăng cấp từ thí nghiệm này):",
      "1. luật/regex trên văn bản OCR cục bộ; 2. LLM cục bộ `qwen3.5:4b` (JSON Schema) ghép theo kiểu (văn bản ưu tiên LLM; ngày/số/mã ưu tiên luật); "
      "3. trường hạn: **tự nhận chỉ khi một mô hình đọc trùng ngày trong tên tệp** (`any-model=filename`; nếu có ảnh trang thì thêm VLM làm nguồn thứ ba), còn lại để null + `needs_review` + ngày gợi ý; "
      "4. PII: mặc định bỏ số định danh và ngày sinh (T5). Không dùng GLiNER làm bộ trích trường (F1 thấp); không dùng ngày trong tên tệp một mình.", "",
      "**Chưa chứng minh:**",
      "* độ chính xác so với **đáp án do người kiểm** (mọi con số là so với silver LLM); tỉ lệ sai thật của hạn tự nhận (cần >= 299 mẫu đúng liên tiếp cho <= 1%);",
      "* hiệu năng trên **biểu mẫu mới** ngoài 4 biểu mẫu hiện có (đặc biệt thẻ tập huấn, phiếu xuất kho một mẫu) và trên tài liệu viết tay nhiều;",
      "* quy ước **ngày trong tên tệp = ngày hết hạn** (chưa được công ty xác nhận; rule sản xuất phụ thuộc vào nó — nếu không có tên tệp hợp lệ thì hầu hết hạn sẽ vào hàng duyệt tay);",
      "* các trường nằm ở trang không được annotator xem; trường PII (không chấm); bảng hàng hóa (`dong_hang`, T6); định dạng ERP;",
      "* độ trễ/VRAM trên máy không dùng chung (số ở đây đo khi GPU đang tải); thông lượng khi chạy hàng loạt;",
      "* VLM có thực sự độc lập với OCR hơn là 'chung kiểu đọc ảnh với annotator' (lưu ý 3).", ""]

L += ["## 8. Bẫy đã gặp khi làm", "",
      "* **Ollama thrash**: tiến trình khác dùng Ollama làm mô hình bị đẩy ra; mỗi lời gọi mất 30-45 s nạp lại. Đo độ trễ phải tách 'nạp' và 'suy luận'; chạy tuần tự có cache đĩa (`_cache/ollama`).",
      "* **Cột bảng bị lệch**: LLM 4B đọc bảng số lượng của phiếu xuất kho trên bản chép Haiku bị dịch một cột (gán số thùng cho m3). Luật theo thứ tự cột không bị. Vì vậy ghép theo kiểu: số/mã/ngày ưu tiên luật.",
      "* **LLM chép nguyên văn rác** khi OCR hỏng ('ngày 09 tháng dưng ...'): ngày/số không phân tích được bị chuyển thành null thay vì giá trị sai.",
      "* **Hạn sai do chữ số OCR**: '22' thay '12', '24' thay '21' (viết tay), tháng '15'. Tháng không hợp lệ bị lọc; hai lỗi còn lại cần nguồn độc lập (ảnh/tên tệp).",
      "* **Đáp án có chỗ không phải ngày** ('từ ngày ký', cụm thời hạn, '[?]'): được quy ước ở `lib.load_gold` (quy về ngày ký / không có ngày cụ thể / loại khỏi điểm) và áp dụng như nhau cho DEV và TEST.",
      "* **Luật gần như đúng từng trường nhưng 'từ khóa không dấu' vẫn nhầm vào phần căn cứ pháp lý** ('hiệu lực từ ngày' của luật, số quyết định): phải neo vào cụm 'Hợp đồng ... có hiệu lực', 'GCN/SCT', 'Bên ... :' ở đầu.",
      "* Một lỗi vặt tốn thời gian: chuỗi regex trong tệp bị chèn ký tự điều khiển `\\x08` (backspace) khi vá bằng heredoc không-raw; đã quét toàn bộ mã.", ""]

L += ["## 9. Chạy lại", "",
      "```powershell",
      "# từ gốc repo; chạy tuần tự, có cache; DEV trước, TEST chỉ sau khi đã freeze",
      ".venv\\Scripts\\python.exe -X utf8 teams\\team4_extraction\\experiments\\02_methods\\run_methods.py --split DEV --configs regex@ocr_v2,llm@ocr_v2,vlm,filename,gliner@ocr_v2",
      ".venv\\Scripts\\python.exe -X utf8 teams\\team4_extraction\\experiments\\02_methods\\make_results.py --split DEV --gold all",
      ".venv\\Scripts\\python.exe -X utf8 teams\\team4_extraction\\experiments\\02_methods\\freeze.py            # ghi dev_selection.json (một lần)",
      ".venv\\Scripts\\python.exe -X utf8 teams\\team4_extraction\\experiments\\02_methods\\run_methods.py --split TEST --final-test --configs ...",
      ".venv\\Scripts\\python.exe -X utf8 teams\\team4_extraction\\experiments\\02_methods\\make_results.py --split TEST --gold all --final-test",
      ".venv\\Scripts\\python.exe -X utf8 teams\\team4_extraction\\experiments\\02_methods\\render_tables.py TEST all   # rồi build_results_md.py",
      "```", ""]

for s in ("TEST", "DEV"):
    for g in ("all", "trusted"):
        L += [f"## Phụ lục {s} / {g}", "", (HERE / f"tables_{s}_{g}.md").read_text(encoding="utf-8").replace("### ", "### ", 1), ""]

(HERE / "RESULTS.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print("đã ghi", HERE / "RESULTS.md")
