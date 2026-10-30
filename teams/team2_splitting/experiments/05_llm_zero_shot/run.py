r"""Thí nghiệm 05 (tùy chọn) - zero-shot "trang B có mở một tài liệu mới không?" bằng Qwen3.5-4B chạy cục bộ qua Ollama (127.0.0.1:11434).

Không gửi gì ra ngoài máy. Không huấn luyện gì. Dùng OllamaClient + DiskCache của src/classification/zero_shot.py (chạy lại miễn phí).
num_ctx được đặt = 32768, đúng bằng cấu hình mô hình đang nạp sẵn trên Ollama, để KHÔNG buộc Ollama nạp lại mô hình của agent khác.

    .venv\Scripts\python.exe -X utf8 teams/team2_splitting/experiments/05_llm_zero_shot/run.py --probe          # đo độ trễ một tệp rồi thoát
    .venv\Scripts\python.exe -X utf8 teams/team2_splitting/experiments/05_llm_zero_shot/run.py                  # chạy toàn bộ cặp (đã bật cache)
    .venv\Scripts\python.exe -X utf8 teams/team2_splitting/experiments/05_llm_zero_shot/run.py --neg-files 60   # chỉ 60 tệp âm (seed cố định) nếu chậm
"""
import json
import random
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
import expcommon as ec  # noqa: E402
import splitlib as sl  # noqa: E402
from src.classification.llm_cache import DiskCache  # noqa: E402
from src.classification.zero_shot import OllamaClient  # noqa: E402
from src.splitting.learned import BLANK_CHARS  # noqa: E402

MODEL = "qwen3.5:4b"
NUM_CTX = 32768
LABELS = ["NEW_DOCUMENT", "SAME_DOCUMENT"]
SYSTEMS = {
    # "rules": prompt thứ nhất, viết một lần theo mục 7.2 của hướng dẫn gán nhãn
    "rules": (
        "Bạn là trợ lý tách tài liệu quét. Bạn nhận hai trang LIÊN TIẾP của cùng một tệp PDF (văn bản OCR, có thể sai chính tả, mất dấu). "
        "Hãy quyết định trang B có MỞ ĐẦU MỘT TÀI LIỆU MỚI (NEW_DOCUMENT) hay là phần tiếp theo của tài liệu chứa trang A (SAME_DOCUMENT).\n"
        "Quy tắc: các trường hợp sau là SAME_DOCUMENT: trang chỉ có chữ ký/con dấu, trang trắng, mặt sau, trang đánh số '2/2', phụ lục/bảng kê/danh mục "
        "đính kèm, các điều khoản hoặc phần con bên trong cùng một hợp đồng hoặc hồ sơ (kể cả khi trang đó lặp lại tiêu đề hay quốc hiệu). "
        "NEW_DOCUMENT khi trang B là một giấy tờ riêng: khác loại với trang A, hoặc cùng loại nhưng là BẢN KHÁC (khác số, khác ngày, khác người hoặc khác xe)."
    ),
    # "neutral": prompt thứ hai, định thử vì prompt thứ nhất cho kết quả gần như luôn SAME_DOCUMENT. CHƯA CHẠY XONG, không có số đo (xem notes.md, mục 2)
    "neutral": (
        "Hai trang liên tiếp của một tệp PDF quét (văn bản OCR). Trang B có phải là trang đầu của một giấy tờ KHÁC với giấy tờ ở trang A không? "
        "Trả lời NEW_DOCUMENT nếu trang B mở đầu một giấy tờ khác (khác loại, hoặc cùng loại nhưng là một bản/biểu mẫu khác đã điền riêng). "
        "Trả lời SAME_DOCUMENT nếu trang B là phần tiếp theo của chính giấy tờ ở trang A."
    ),
}
SYSTEM = SYSTEMS["rules"]


def user_prompt(a: str, b: str) -> str:
    a = " ".join(a.split())[-700:]
    b = "\n".join(b.split("\n")[:25])[:1200]
    return f"TRANG A (phần cuối):\n{a}\n\nTRANG B (phần đầu):\n{b}\n\nTrang B là NEW_DOCUMENT hay SAME_DOCUMENT?"


def ollama_loaded() -> str:
    try:
        d = json.loads(urllib.request.urlopen("http://127.0.0.1:11434/api/ps", timeout=5).read())
        return ", ".join(f"{m['name']} (context {m.get('context_length')})" for m in d.get("models", [])) or "(không có mô hình nào)"
    except Exception as e:  # noqa: BLE001
        return f"không kết nối được Ollama: {e}"


def main():
    ap = ec.common_args(__doc__)
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--prompt", default="rules", choices=list(SYSTEMS))
    ap.add_argument("--probe-idx", type=int, default=0)
    ap.add_argument("--neg-files", type=int, default=0, help="0 = mọi tệp âm; >0 = lấy mẫu ngẫu nhiên (seed 7) từng ấy tệp âm")
    args = ap.parse_args()
    gold, ids, docs = ec.setup(args)
    meta = gold.drop_duplicates("doc_id").set_index("doc_id")
    pos_ids = [d for d in ids if meta.loc[d, "eval_group"] in ("mixed", "same_other", "same_bb")]
    all_neg = [d for d in ids if meta.loc[d, "eval_group"] == "negative"]
    neg_ids = sorted(random.Random(7).sample(all_neg, min(args.neg_files, len(all_neg)))) if args.neg_files else all_neg
    use = pos_ids + neg_ids
    client = OllamaClient(DiskCache(HERE / "_cache"), timeout=300.0)
    loaded = ollama_loaded()
    print("Ollama đang nạp:", loaded, flush=True)

    lat_first, preds = [], {}
    stats = dict(errors=0, calls=0)

    def decide(d, doc):
        texts = [p.full_text for p in doc.pages]
        starts, last = set(), None
        for i, t in enumerate(texts):
            if len(t.strip()) < BLANK_CHARS:
                continue
            if last is not None:
                ans = client.choose(MODEL, SYSTEMS[args.prompt], user_prompt(texts[last], t), LABELS, num_ctx=NUM_CTX)
                stats["calls"] += 1
                lat_first.append(ans.latency_ms)     # độ trễ ghi trong bản ghi cache lúc gọi thật (chạy lại từ cache vẫn đọc được)
                if not ans.parse_ok:
                    stats["errors"] += 1
                elif ans.label == "NEW_DOCUMENT":
                    starts.add(doc.pages[i].page_number)
            last = i
        return starts

    if args.probe:
        d = pos_ids[args.probe_idx]
        t0 = time.perf_counter()
        decide(d, docs[d])
        print(f"probe: {stats['calls']} cặp trong {time.perf_counter() - t0:.1f} s; độ trễ lần đầu (ms): {[round(x) for x in lat_first]}; lỗi phân tích: {stats['errors']}")
        return
    t0 = time.perf_counter()
    for k, d in enumerate(use):
        preds[d] = decide(d, docs[d])
        if k % 20 == 0:
            print(f"  {k}/{len(use)} tệp, {stats['calls']} cặp, {time.perf_counter() - t0:.0f} s", flush=True)
    dt = time.perf_counter() - t0
    df, _ = sl.evaluate_method(None, use, docs, gold, prediction_cache=preds)
    base_df, _ = sl.evaluate_method(ec.baseline_starts, use, docs, gold)
    v2_df, _ = sl.evaluate_method(ec.rule_v2_starts, use, docs, gold)
    per = {"rule cũ (01)": base_df, "rule v2 (02)": v2_df, f"d Qwen3.5-4B zero-shot (prompt {args.prompt})": df}
    lat = np.array(lat_first) if lat_first else np.array([float("nan")])
    print(sl.summary_table_md(per, args.boot))
    if args.no_write:
        return
    scope = args.scope
    ec.save_per_file(HERE, "qwen" + ("" if args.prompt == "rules" else "_" + args.prompt), df, preds, scope)
    run_id = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + "-05"
    for r in ec.results_rows("05_qwen35_4b_zero_shot" + ("" if args.prompt == "rules" else "_" + args.prompt), df, scope, run_id, f"zero-shot Ollama {MODEL}; negatives: {len(neg_ids)} tệp"):
        ec.append_results_table(r)
    cmd = (r".venv\Scripts\python.exe -X utf8 teams/team2_splitting/experiments/05_llm_zero_shot/run.py"
           + (f" --neg-files {args.neg_files}" if args.neg_files else "") + (f" --prompt {args.prompt}" if args.prompt != "rules" else "") + (" --scope all --final-test" if scope == "all" else ""))
    neg_note = f" (lấy mẫu ngẫu nhiên seed 7 từ {len(all_neg)})" if args.neg_files else " (tất cả)"
    out = [f"# 05 - Zero-shot 'trang này có mở tài liệu mới không?' bằng {MODEL} cục bộ - phạm vi `{scope}`", "",
           ec.reproduce_header(HERE, cmd, args, {
               "mô hình": f"`{MODEL}` qua Ollama `http://127.0.0.1:11434` (đang nạp: {loaded}); `think=False`, temperature 0, seed 0, đầu ra bị ràng buộc theo JSON schema enum {LABELS}; `num_ctx={NUM_CTX}`. Chạy on-premise, không gửi gì ra ngoài.",
               "tệp được chấm": f"{len(pos_ids)} tệp composite + {len(neg_ids)} tệp âm" + neg_note,
               "độ trễ (NHIỄU: GPU/CPU dùng chung với agent khác)": f"{stats['calls']} cặp; độ trễ mỗi cặp (đo lúc gọi thật, lưu trong cache): n={len(lat_first)}, median {np.nanmedian(lat):.0f} ms, p95 {np.nanpercentile(lat, 95):.0f} ms; tổng {dt:.0f} s",
               "lỗi phân tích đầu ra": f"{stats['errors']} cặp (tính là SAME_DOCUMENT)"}),
           "", "## Kết quả theo nhóm (cùng tập tệp cho cả ba phương pháp)", "",
           f"Không có huấn luyện nên không cần cross-fitting. Prompt `{args.prompt}`:", "",
           "> " + SYSTEMS[args.prompt].replace("\n", "\n> "), "",
           sl.summary_table_md(per, args.boot), "",
           "## So sánh ghép cặp với rule cũ và rule v2", "", sl.paired_table_md(df, base_df, "Qwen", "rule cũ", args.boot), "",
           sl.paired_table_md(df, v2_df, "Qwen", "rule v2", args.boot), ""]
    notes = HERE / "notes.md"
    if notes.exists() and scope == "dev":
        out.append(notes.read_text(encoding="utf-8"))
    ec.results_path(HERE, scope).write_text("\n".join(out), encoding="utf-8")
    print("đã ghi", ec.results_path(HERE, scope))


if __name__ == "__main__":
    main()
