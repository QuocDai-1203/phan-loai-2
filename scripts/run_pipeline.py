"""run_pipeline.py - Chạy toàn bộ pipeline trên một tệp PDF: OCR -> tách -> phân loại (cascade) -> trích xuất (tùy chọn).

  .venv\\Scripts\\python.exe -X utf8 scripts\\run_pipeline.py <tệp.pdf> [--out thư_mục] [--max-pages N] [--no-llm] [--no-extract]

Ghi `<out>/<tên tệp>.pipeline.json` (DocumentProcessingPipelineResult: văn bản OCR, lát cắt, phân loại, trích xuất, quyết định xử lý
từng lát cắt, thời gian từng giai đoạn) và in bản tóm tắt. Kết quả chứa NỘI DUNG tài liệu: không đưa lên nơi công khai.

  --out        thư mục đầu ra (mặc định ./output/pipeline, đã nằm trong .gitignore). Script KHÔNG ghi cạnh tệp PDF.
  --max-pages  số trang OCR tối đa (mặc định 30).
  --no-llm     tắt tầng LLM: chỉ luật + TF-IDF; tài liệu chưa nhận -> người (không cần Ollama/Kev).
  --no-extract tắt trích xuất thực thể (không nạp GLiNER).
  --no-vlm     không dựng ảnh trang (PyMuPDF, 200 dpi, thư mục tạm, xóa ngay) cho nguồn VLM đối chiếu ngày hết hạn. Mặc định BẬT cho lát cắt thuộc loại có
               trường hạn; cần LLM; tốn thêm thời gian dựng ảnh (`stage_timings_ms.render`) và một lời gọi VLM mỗi lát cắt.
  --device     OCR: cpu | cuda:0 | auto (auto = GPU nếu còn >= 2 GB trống, ngược lại CPU). Mặc định auto.
  --llm        ollama (Qwen3.5-4B, mặc định, đã đo) | kev (chỉ tên loại; xem models/README.md và teams/team3_classification/README.md).
  --splitter   chính sách tách trang: model+merge (MẶC ĐỊNH, S10, thí nghiệm 01; quy tắc "bản khác" chạy ở chế độ bóng: không tách, chỉ chuyển người) | model+merge+id (thêm quy tắc "bản khác", KHÔNG mặc định: báo cáo 04 N1) | none (không tách) | rule (hành vi cũ) |
               rule_v2 | model |
               triage (không tách; tệp nghi là composite thì chuyển người). Xem src/splitting/policy.py.
  --title-tiebreak / --no-title-tiebreak   gỡ mơ hồ (MẶC ĐỊNH TẮT; khi tắt vẫn ghi nhãn "bóng" ở routing[i].shadow) của cổng luật theo vị trí tiêu đề (tùy chọn của bộ phân loại; xem teams/team3_classification/experiments/05_composite_slices).
  --auto-accept-expiry / --no-auto-accept-expiry   cho quy tắc hạn TỰ NHẬN ngày hết hạn (MẶC ĐỊNH TẮT: mọi hạn là needs_review; quy tắc vẫn ghi "sẽ nhận" ở routing[i].shadow).
  --llm-timeout / --llm-file-budget   giây hết giờ MỖI lời gọi LLM (mặc định 45) / tổng thời gian chờ LLM tối đa cho MỘT tệp (mặc định 90).

Mã thoát: 0 chạy xong; 2 thiếu mô hình / cấu hình (thông báo nêu rõ cần đặt gì ở đâu).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.pipeline import DEFAULT_AUTO_ACCEPT_EXPIRY, DEFAULT_TITLE_TIEBREAK, DEFAULT_LLM_FILE_BUDGET_S, DEFAULT_LLM_TIMEOUT_S, DocumentPipeline, resolve_device  # noqa: E402
from src.splitting.policy import DEFAULT_PRESET, PRESETS  # noqa: E402


def summarize(res) -> str:
    lines = [f"Tệp: {res.file_name} | {res.total_pages} trang (đã OCR {len(res.ocr_result.pages)}) | {len(res.split_result.slices)} lát cắt"
             f" | ghép nhiều tài liệu: {res.is_composite_bundle}",
             "Thời gian (ms, đo lúc chạy, phụ thuộc tải máy): " + ", ".join(f"{k}={v:.0f}" for k, v in res.stage_timings_ms.items())
             + f", tổng={res.total_processing_time_ms:.0f}"]
    for sl, c, r in zip(res.split_result.slices, res.classifications, res.routing):
        ex = next((e for e in res.extractions if e.slice_id == sl.slice_id), None)
        lines.append(f"  {sl.slice_id} trang {sl.start_page}-{sl.end_page}: tầng={c.tier} nhãn={c.predicted_category} "
                     f"conf={c.confidence:.3f} model={c.model_name} -> {r.decision}"
                     + (f" ({', '.join(r.reasons)})" if r.reasons else "")
                     + (f" gợi ý={r.suggested_category}" if r.suggested_category else "")
                     + (f" | trích xuất={ex.status}, {len(ex.entities)} thực thể" if ex else ""))
    fr = res.file_routing
    if fr is not None:
        lines.append(f"Định tuyến cấp tệp: {fr.decision} | chính sách tách={fr.splitter} | lát cắt {fr.n_slices_before_merge}->{fr.n_slices} "
                     f"(tự xếp {fr.n_auto}, cần người {fr.n_needs_human}) | lời gọi LLM={fr.n_llm_calls} ({fr.llm_ms:.0f} ms)"
                     + (f" | lý do: {', '.join(fr.reasons)}" if fr.reasons else ""))
    for w in res.warnings:
        lines.append(f"  CẢNH BÁO: {w}")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("pdf", type=Path)
    ap.add_argument("--out", type=Path, default=REPO / "output" / "pipeline")
    ap.add_argument("--max-pages", type=int, default=30)
    ap.add_argument("--no-llm", action="store_true")
    ap.add_argument("--no-extract", action="store_true")
    ap.add_argument("--no-vlm", action="store_true", help="không dựng ảnh trang cho nguồn VLM của ngày hết hạn (mặc định: dựng, trong thư mục tạm)")
    ap.add_argument("--device", default="auto")
    ap.add_argument("--dpi", type=int, default=200)
    ap.add_argument("--llm", choices=["ollama", "kev"], default="ollama")
    ap.add_argument("--splitter", choices=sorted(PRESETS), default=DEFAULT_PRESET, help="chính sách tách trang (mặc định: %(default)s)")
    ap.add_argument("--title-tiebreak", action=argparse.BooleanOptionalAction, default=DEFAULT_TITLE_TIEBREAK, help="gỡ mơ hồ của cổng luật theo vị trí tiêu đề (DocumentClassifier.rule_title_tiebreak); mặc định: %(default)s; --no-title-tiebreak để tắt")
    ap.add_argument("--auto-accept-expiry", action=argparse.BooleanOptionalAction, default=DEFAULT_AUTO_ACCEPT_EXPIRY, help="cho quy tắc hạn TỰ NHẬN ngày hết hạn (mặc định: %(default)s = mọi hạn là needs_review, quy tắc vẫn ghi 'sẽ nhận' để đo)")
    ap.add_argument("--llm-timeout", type=float, default=DEFAULT_LLM_TIMEOUT_S, help="giây hết giờ MỖI lời gọi LLM")
    ap.add_argument("--llm-file-budget", type=float, default=DEFAULT_LLM_FILE_BUDGET_S, help="tổng giây chờ LLM tối đa cho MỘT tệp")
    ap.add_argument("--cache-dir", type=Path, default=None, help="cache lời gọi LLM (mặc định cache/llm)")
    a = ap.parse_args(argv)

    if not a.pdf.is_file():
        print(f"Không thấy tệp: {a.pdf}", file=sys.stderr)
        return 2
    out_dir = a.out.resolve()
    if a.pdf.resolve().parent == out_dir:
        print("--out trùng thư mục chứa PDF: chọn thư mục khác (script không ghi cạnh tệp nguồn)", file=sys.stderr)
        return 2
    out_dir.mkdir(parents=True, exist_ok=True)

    from src.ocr.vietocr_engine import OcrModelsMissingError
    from src.classification.tfidf_classifier import TfidfModelError
    pipe = DocumentPipeline(run_extraction=not a.no_extract, max_pages=a.max_pages, dpi=a.dpi, device=a.device, use_llm=not a.no_llm,
                            llm_backend=a.llm, cache_dir=a.cache_dir, split_policy=a.splitter, llm_timeout_s=a.llm_timeout,
                            llm_file_budget_s=a.llm_file_budget, use_vlm=not a.no_vlm, title_tiebreak=a.title_tiebreak,
                            auto_accept_expiry=a.auto_accept_expiry)
    print(f"[*] OCR thiết bị: {resolve_device(a.device)}; LLM: {'tắt' if a.no_llm else a.llm}; trích xuất: {'tắt' if a.no_extract else 'bật'}; "
          f"tách trang: {a.splitter}; ảnh trang cho VLM: {'tắt' if a.no_vlm else 'bật'}; gỡ mơ hồ theo tiêu đề: {'bật' if a.title_tiebreak else 'tắt (bóng)'}; tự nhận hạn: {'bật' if a.auto_accept_expiry else 'tắt'}", flush=True)
    try:
        res = pipe.run(a.pdf)
    except OcrModelsMissingError as e:
        print(e, file=sys.stderr)
        return 2
    except TfidfModelError as e:
        print(e, file=sys.stderr)
        return 2
    target = out_dir / (a.pdf.stem + ".pipeline.json")
    target.write_text(res.model_dump_json(indent=1), encoding="utf-8")
    print(summarize(res))
    print(f"[*] đã ghi {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
