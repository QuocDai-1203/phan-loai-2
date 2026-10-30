"""render_tables.py - Biến results_<split>_<gold>.json thành bảng Markdown (tables_<split>_<gold>.md). Chỉ số tổng hợp, không có giá trị trường.

    .venv\\Scripts\\python.exe -X utf8 .../render_tables.py DEV all
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from combine import n_needed  # noqa: E402

HERE = Path(__file__).resolve().parent
split, gold = (sys.argv[1], sys.argv[2]) if len(sys.argv) > 2 else ("DEV", "all")
d = json.loads((HERE / f"results_{split}_{gold}.json").read_text(encoding="utf-8"))
RES = HERE / "_cache" / "resources.jsonl"


def p(x, lo=None, hi=None, nd=2):
    if x is None or x != x:
        return "n/a"
    s = f"{x:.{nd}f}"
    if lo is not None and lo == lo:
        s += f" [{lo:.2f}; {hi:.2f}]"
    return s


def ci(r, k):
    return p(r[k], r.get(k + "_ci_lo"), r.get(k + "_ci_hi"))


L = [f"### Kết quả {split} (đáp án: `{gold}`)", "",
     f"Số đơn vị: {d['n_units']} ({', '.join(f'{k} {v}' for k, v in d['units_by_type'].items())}). Khoảng tin cậy 95%: bootstrap percentile theo đơn vị. "
     "`F1 chặt` = so sánh sau chuẩn hóa; `F1 mềm` = như chặt nhưng văn bản bỏ dấu/dấu câu, chứa nhau, 'tên + MST' khớp theo tên. "
     + (f"Cấu hình chưa chạy đủ: {d['incomplete']}." if d["incomplete"] else ""), ""]

L += ["#### A. Tổng quan theo phương pháp × nguồn văn bản", "",
      "| cấu hình | n | F1 chặt (toàn bộ trường) | F1 mềm | F1 ngày | F1 số | F1 mã | F1 văn bản chặt | F1 văn bản mềm | đúng mọi trường bắt buộc (chặt) | (mềm) | hạn: đúng | hạn: bỏ trống | hạn: **sai giá trị** | n hạn |",
      "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
for n, c in d["configs"].items():
    s, l = c["normalized"], c["lenient"]
    pt, pl, e = s["per_type"], l["per_type"], s["expiry_all"]
    L.append(f"| {n} | {c['units']}{' (+' + str(s['n_failed']) + ' lỗi)' if s['n_failed'] else ''} | {ci(s['overall'], 'f1')} | {ci(l['overall'], 'f1')} | {p(pt['date']['f1'])} | {p(pt['number']['f1'])} | "
             f"{p(pt['id']['f1'])} | {p(pt['text']['f1'])} | {p(pl['text']['f1'])} | {ci(s['doc_level'], 'rate')} ({s['doc_level']['n_all_required_correct']}/{s['doc_level']['n_evaluated']}) | "
             f"{ci(l['doc_level'], 'rate')} | {ci(e, 'correct_rate')} | {ci(e, 'empty_rate')} | {ci(e, 'wrong_rate')} | {e['n_gold_present']} |")
L += ["", "Ghi chú: `F1 ngày` gộp mọi trường kiểu ngày (hạn, ngày cấp, ngày ký...). `n hạn` = số trường hạn có đáp án. `đúng mọi trường bắt buộc` dùng so sánh chặt.", ""]

pick = [n for n in ("regex@ocr_v2", "gliner@ocr_v2", "llm@ocr_v2", "vlm") if n in d["configs"]] + [n for n in d["configs"] if n.startswith("cascade")]
L += ["#### B. Theo loại tài liệu (so sánh chặt; trong ngoặc: F1 mềm)", "",
      "> `CC_TAP_HUAN_VC_HNH` và `PHIEU_XUAT_KHO` gần như MỘT biểu mẫu duy nhất (và phiếu xuất kho là bản số hóa sạch): điểm cao ở hai loại này lạc quan, không suy ra cho biểu mẫu mới.", "",
      "| loại | cấu hình | n | F1 chặt (mềm) | đúng mọi trường bắt buộc | hạn: đúng / bỏ trống / **sai** (n) |", "|---|---|---|---|---|---|"]
for t in d["units_by_type"]:
    for n in pick:
        bt = d["configs"][n]["by_doc_type"].get(t)
        if not bt:
            continue
        s, l = bt["normalized"], bt["lenient"]
        e = s["expiry_all"]
        ex = f"{p(e['correct_rate'])} / {p(e['empty_rate'])} / {p(e['wrong_rate'])} ({e['n_gold_present']})" if e["n_gold_present"] else "(không có trường hạn)"
        L.append(f"| {t} | {n} | {s['n_units']} | {p(s['overall']['f1'])} ({p(l['overall']['f1'])}) | {p(s['doc_level']['rate'])} ({s['doc_level']['n_all_required_correct']}/{s['doc_level']['n_evaluated']}); mềm {p(l['doc_level']['rate'])} | {ex} |")
L.append("")

L += ["#### C. Cái giá của OCR: cùng phương pháp, khác nguồn văn bản", "",
      "`ocr_llm_haiku` chỉ có 2 trang đầu của tệp và đáp án ở trang > 2 bị loại khỏi điểm (cho công bằng); nguồn này KHÔNG chạy được on-premise (cận trên). "
      "`text_layer` chỉ có ở trang số hóa nên chấm trên tập con các đơn vị có chữ thật; cột cuối là chính phương pháp đó trên OCR cục bộ ở CÙNG tập con.", "",
      "| phương pháp | nguồn | n | F1 chặt | F1 mềm | F1 ngày | F1 mã | F1 văn bản mềm | hạn đúng / **sai** (n) |", "|---|---|---|---|---|---|---|---|---|"]
for m in ("regex", "gliner", "llm"):
    for src in ("ocr_v2", "ocr_llm_haiku", "text_layer", "ocr_v2 (cùng tập đơn vị với text_layer)"):
        n = f"{m}@{src}"
        if n not in d["configs"]:
            continue
        c = d["configs"][n]
        s, l = c["normalized"], c["lenient"]
        e = s["expiry_all"]
        L.append(f"| {m} | {src} | {c['units']} | {ci(s['overall'], 'f1')} | {ci(l['overall'], 'f1')} | {p(s['per_type']['date']['f1'])} | {p(s['per_type']['id']['f1'])} | "
                 f"{p(l['per_type']['text']['f1'])} | {p(e['correct_rate'])} / {p(e['wrong_rate'])} ({e['n_gold_present']}) |")
L.append("")

L += ["#### D. Theo mực viết của đáp án silver (trường có đáp án; so sánh mềm)", "",
      "Mực do người chú thích ghi (Haiku là chính), nên có thể sai. Chỉ tính trường có giá trị trong đáp án.", "",
      "| cấu hình | mực | n trường | đúng | bỏ trống | **sai giá trị** |", "|---|---|---|---|---|---|"]
for n in pick + [x for x in d["configs"] if x.startswith("ORACLE")]:
    for ink in ("printed", "handwritten", "under_stamp"):
        b = d["configs"][n]["by_ink"]["lenient"].get(ink)
        if not b or not b.get("n"):
            continue
        L.append(f"| {n} | {ink} | {b['n']} | {p(b.get('correct', 0) / b['n'])} | {p(b.get('empty', 0) / b['n'])} | {p(b.get('wrong', 0) / b['n'])} |")
L.append("")

L += ["#### E. Trường hạn: quy tắc tự nhận / từ chối", "",
      "Mỗi quy tắc chỉ TỰ NHẬN một ngày khi các nguồn đồng thuận, ngược lại từ chối (chuyển người duyệt). `sai` gồm cả trường hợp giấy không ghi hạn mà quy tắc vẫn ra ngày. "
      "Cận trên là Clopper-Pearson MỘT PHÍA 95% của tỉ lệ sai trong số đã tự nhận. "
      f"Để KHẲNG ĐỊNH tỉ lệ sai <= 1% với 0 lỗi quan sát cần tối thiểu {n_needed(0.01, 0)} lần tự nhận đúng (<= 2%: {n_needed(0.02, 0)}; <= 5%: {n_needed(0.05, 0)}).", "",
      f"Quy tắc được chọn trên DEV: **{d['chosen_expiry_rule']}**.", "",
      "| quy tắc | tự nhận | đúng | sai | trong đó 'giấy không có hạn' | tự động hóa (đúng / có hạn thật) | tỉ lệ sai | cận trên 95% |", "|---|---|---|---|---|---|---|---|"]
for r in d["abstention"]:
    if r["n_emitted"] == 0:
        L.append(f"| {r['rule']} | 0 | 0 | 0 | 0 | 0.00 | n/a | n/a |")
        continue
    L.append(f"| {'**' + r['rule'] + '**' if r['rule'] == d['chosen_expiry_rule'] else r['rule']} | {r['n_emitted']} | {r['n_correct']} | {r['n_wrong']} | {r['n_spurious']} | "
             f"{p(r['automation'])} ({r['n_correct']}/{r['n_gold_present']}) | {p(r['wrong_rate'])} | {p(r['wrong_upper95'])} |")
L.append("")

rq = d.get("review_queue") or {}
if rq:
    L += [f"Chuyển người duyệt theo quy tắc đã chọn: {rq['n_review']} trường hạn (trong đó {rq['n_review_gold_present']} có hạn thật); có gợi ý (luật, rồi LLM, rồi VLM): {rq['n_with_suggestion']}, "
          f"gợi ý đúng {rq['n_suggestion_correct']}; gợi ý ra ngày dù giấy không ghi hạn: {rq['n_suggestion_where_no_expiry']}. Người duyệt chỉ cần xác nhận/sửa chứ không phải đọc từ đầu.", ""]

L += ["#### F. Độ trễ mỗi đơn vị (đo khi GPU/Ollama đang dùng chung với việc khác)", "",
      "`toàn bộ` gồm cả thời gian Ollama nạp lại mô hình (bị đẩy ra khi tiến trình khác dùng Ollama); `chỉ suy luận` = tổng - nạp mô hình (nếu có ghi).", "",
      "| cấu hình | n | toàn bộ: trung vị (ms) | p95 (ms) | chỉ suy luận: trung vị (ms) | p95 (ms) |", "|---|---|---|---|---|---|"]
for n, c in d["configs"].items():
    lt = c.get("latency") or {}
    if not lt.get("n"):
        continue
    f0 = lambda x: "n/a" if x is None else f"{x:.0f}"  # noqa: E731
    L.append(f"| {n} | {lt['n']} | {f0(lt['wall_median_ms'])} | {f0(lt['wall_p95_ms'])} | {f0(lt['inference_only_median_ms'])} | {f0(lt['inference_only_p95_ms'])} |")
L.append("")
if RES.exists():
    L += ["VRAM (nvidia-smi toàn GPU, `ollama ps`), đo sau mỗi cấu hình; GPU còn chạy việc của nhóm khác nên số 'toàn GPU' không phải của riêng phương pháp:", ""]
    for line in open(RES, encoding="utf-8"):
        r = json.loads(line)
        if not r["config"].startswith(("llm", "vlm", "gliner")) or r["split"] != split:
            continue
        L.append(f"* `{r['config']}` ({r['split']}): GPU dùng {r['gpu_used_mib_before']} -> {r['gpu_used_mib_after']} MiB; ollama ps: {json.dumps(r['ollama_ps'], ensure_ascii=False)}")
(HERE / f"tables_{split}_{gold}.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print("đã ghi", HERE / f"tables_{split}_{gold}.md")
