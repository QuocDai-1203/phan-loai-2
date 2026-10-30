"""pipeline.py - Bộ điều phối đầu-cuối: PDF -> OCR -> tách tài liệu -> phân loại từng lát cắt -> (tùy chọn) trích xuất.

Trả về `DocumentProcessingPipelineResult` (src/common/contracts.py) kèm thời gian từng giai đoạn, QUYẾT ĐỊNH XỬ LÝ của từng lát cắt
(`auto_file` hoặc `needs_human`, kèm lý do và gợi ý) và TÓM TẮT ĐỊNH TUYẾN CẤP TỆP (`file_routing`).

Các giai đoạn gọi qua giao diện hẹp để nhóm khác sửa bên trong mà không vỡ ở đây:
  * OCR      : `src.ocr.pdf_ocr.ocr_pdf(path, engine, dpi, max_pages) -> OCRDocumentResult`
  * tách     : `src.splitting.policy.split_with_policy(doc, policy) -> SplitResult` (chính sách `SplitPolicy`; mặc định `model+merge`, xem dưới)
  * phân loại: `DocumentClassifier.classify_slice(slice) -> ClassificationResult`
  * gộp      : `src.splitting.type_merge.merge_same_type` - gộp lát cắt liền kề mà bộ phân loại gán CÙNG loại (trừ loại "một tờ = một tài liệu")
  * trích xuất: HOOK `DocumentPipeline.extract_fields(slice, category, filename) -> ExtractionResult` (mặc định `src.extraction.field_extractor.FieldExtractor`:
                luật/regex + LLM cục bộ ghép theo kiểu trường; nạp lười). Chỉ 4 loại có schema; loại khác -> `skipped` + `extraction_note="no_schema..."` (không phải lỗi).
                MẶC ĐỊNH KHÔNG tự nhận ngày hết hạn nào (`auto_accept_expiry=False`, báo cáo 04 N2/N3): mọi hạn là `needs_review` + ngày gợi ý, quy tắc đã khớp và
                trạng thái "sẽ nhận" được ghi để đo (`SliceRouting.shadow["expiry_would_accept"]`). Với `auto_accept_expiry=True` hạn chỉ được tự nhận theo quy tắc theo loại
                (4 loại cũ: `any-model=filename`, phụ thuộc quy ước đặt tên tệp; 17 loại mới: `regex=llm`). Phản ánh ở `SliceRouting.expiry / expiry_suggestion / field_review`. PII tắt mặc định.
Mọi thành phần có thể thay bằng đối tượng giả khi dựng `DocumentPipeline(...)` (xem tests/test_pipeline.py: không GPU, không mạng).

CHÍNH SÁCH TÁCH MẶC ĐỊNH = `model+merge` (S10: bộ phân loại cặp trang, ngưỡng 0,7, gộp lát cắt liền kề cùng loại trừ ranh giới điểm >= 0,99), chọn trên DEV bằng
thí nghiệm end-to-end `teams/00_data_and_eval/experiments/01_end_to_end/` (đáp án máy, chưa người kiểm). `title_tiebreak` mặc định TẮT. Hai tùy chọn của thí nghiệm
03_end_to_end_v2 (`--splitter model+merge+id`, `--title-tiebreak`) vẫn dùng được nhưng KHÔNG là mặc định (báo cáo 04 N1: bằng chứng nằm trong mẫu thiết kế). Khi tắt, chúng chạy ở CHẾ ĐỘ BÓNG:
  * `id` -> ranh giới mà quy tắc "bản khác" sẽ thêm ghi ở `file_routing.shadow["id_rule_extra_boundaries"]` và cả tệp chuyển người (lý do `id_rule_boundary`), KHÔNG tách;
  * `tiebreak` -> nhãn nó sẽ chọn ghi ở `routing[i].shadow["title_tiebreak_label"]` (chỉ luật từ khóa, không gọi thêm LLM), không đổi quyết định.
Các chế độ khác: `none` (không tách), `rule`, `rule_v2`, `model`, `triage` (không tách; tệp nghi là composite thì chuyển người). Muốn hành vi cũ: `split_policy="rule"` / `--splitter rule`.
Tệp dài hơn `max_pages` (30): phần trang không xử lý được ghi ở `warnings` + `file_routing.shadow["truncated_pages"]` và cả tệp chuyển người (lý do `truncated_pages`).

Quy tắc trung thực:
  * lỗi OCR cấp trang nằm trong `OCRPageResult.error` và đẩy lát cắt sang `needs_human` (lý do `ocr_error`);
  * phân loại lỗi/ném ngoại lệ/hết giờ -> `needs_human` với lý do nêu rõ (`classifier_error`, `llm_timeout`, `llm_skipped`), không có nhãn thay thế;
  * một lời gọi LLM bị kẹt không được làm tệp đứng hàng phút: mỗi lời gọi có hết giờ riêng, mỗi TỆP có ngân sách thời gian LLM, và sau một lần hết giờ các
    lát cắt còn lại của tệp đó KHÔNG gọi LLM nữa (về người, lý do `llm_skipped`); hết giờ liên tiếp ở nhiều tệp mở "mạch ngắt" một lúc (`GuardedLlm`);
  * trích xuất chỉ chạy cho lát cắt `auto_file`; thất bại -> `ExtractionResult.status="error"` + dòng trong `warnings`, quyết định xếp hồ sơ giữ nguyên;
  * thiếu mô hình OCR là lỗi cấu hình: ném `OcrModelsMissingError` (không âm thầm đổi engine); thiếu mô hình tách (`model`) cũng là lỗi cấu hình, không quay về luật.
"""
from __future__ import annotations

import inspect
import logging
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Collection, List, Optional, Union

from src.common.contracts import (UNKNOWN_CATEGORY, ClassificationResult, DocumentProcessingPipelineResult, DocumentSlice, ExtractionResult,
                                  FileRoutingSummary, OCRDocumentResult, SliceRouting, SplitResult)
from src.splitting.policy import SplitPolicy, resolve_policy, split_with_policy
from src.splitting.type_merge import load_one_sheet_types, merge_same_type

logger = logging.getLogger(__name__)

AUTO_FILE = "auto_file"
NEEDS_HUMAN = "needs_human"
REASON_POSSIBLE_COMPOSITE = "possible_composite"   # chính sách `triage`: tệp có điểm ranh giới cao => nghi là composite => người xử lý
REASON_ID_BOUNDARY = "id_rule_boundary"            # quy tắc `id` (đang ở chế độ bóng) muốn thêm ranh giới => người kiểm ranh giới
REASON_TRUNCATED = "truncated_pages"               # tệp dài hơn max_pages: các trang sau không được xử lý => người
DEFAULT_LLM_TIMEOUT_S = 45.0                       # mỗi lời gọi (lời gọi bình thường ~1 s; nạp lại mô hình ~20 s)
DEFAULT_LLM_FILE_BUDGET_S = 90.0                   # tổng thời gian chờ LLM tối đa cho MỘT tệp
DEFAULT_EXTRACT_TIMEOUT_S = 120.0                  # mỗi lời gọi LLM trích xuất trường (prompt dài hơn và đầu ra dài hơn phân loại)
DEFAULT_LLM_COOLDOWN_S = 60.0                      # mạch ngắt mở bao lâu sau 2 tệp liên tiếp bị hết giờ


DEFAULT_TITLE_TIEBREAK = False                    # TẮT mặc định (báo cáo 04 N1: chỉ có bằng chứng trong mẫu thiết kế); vẫn ghi nhãn "bóng" ở SliceRouting.shadow
DEFAULT_AUTO_ACCEPT_EXPIRY = False                # KHÔNG tự nhận ngày hết hạn (báo cáo 04 N2/N3); ngày vẫn được gợi ý và quy tắc vẫn ghi "sẽ nhận"
DEFAULT_USE_VLM = True                             # đưa ảnh trang cho nguồn VLM của trường hạn (kết quả đo: experiments/02_chain_with_images/RESULTS.md)
VLM_MAX_SHOWN_PAGES = 6                            # như gold/build_units.py (trang cho xem), sau đó FieldExtractor chỉ gửi `max_vlm_images` (4) ảnh đầu
VLM_EXPIRY_KEYWORDS = ("hieu luc", "thoi han", "co gia tri den", "het han", "den het ngay", "hieu luc den", "het hieu luc")


def choose_vlm_pages(pages: List[int], texts: dict) -> List[int]:
    """Chọn trang đưa vào VLM, đúng quy tắc `teams/team4_extraction/gold/build_units.py:choose_pages` (cách VLM đã được đo):
    <= 4 trang -> tất cả; ngược lại 2 trang đầu + trang cuối + các trang có từ khóa hiệu lực/hạn (nhiều từ khóa trước), tối đa 6."""
    if len(pages) <= 4:
        return list(pages)
    from src.extraction.normalize import fold_text
    keep = list(pages[:2])
    if pages[-1] not in keep:
        keep.append(pages[-1])
    hits = []
    for p in pages[2:-1]:
        t = fold_text(texts.get(p, ""))
        n = sum(t.count(k) for k in VLM_EXPIRY_KEYWORDS)
        if n:
            hits.append((-n, p))
    for _, p in sorted(hits):
        if len(keep) >= VLM_MAX_SHOWN_PAGES:
            break
        keep.append(p)
    return sorted(keep)


def default_page_renderer(pdf_path: Path, pages: List[int], out_dir: Path) -> List[Path]:
    """Dựng ảnh trang như lúc VLM được đo (200 dpi, trang dọc cắt đôi, cạnh dài <= 1600 px); ghi vào `out_dir` (thư mục tạm của pipeline)."""
    from src.extraction.field_vlm import render_pages_for_vlm
    return render_pages_for_vlm(pdf_path, pages, out_dir)


def is_llm_timeout(error: Optional[str]) -> bool:
    e = (error or "")
    return e.startswith(("ReadTimeout", "ConnectTimeout", "Timeout", "TimeoutError"))


def is_llm_skipped(error: Optional[str]) -> bool:
    return (error or "").startswith("llm_skipped")


def route_slice(sl: DocumentSlice, cls: ClassificationResult) -> SliceRouting:
    """Quyết định xử lý tiếp theo của MỘT lát cắt. `auto_file` chỉ khi bộ phân loại tự nhận, không đòi người xem và OCR sạch lỗi."""
    reasons: List[str] = []
    if cls.tier == "human" or cls.predicted_category == UNKNOWN_CATEGORY:
        reasons.append(f"classification:{cls.abstain_reason or 'unknown'}")
    elif cls.requires_human_review:
        reasons.append("classification:requires_review")
    if cls.error:
        reasons.append("classifier_error")
        if is_llm_timeout(cls.error):
            reasons.append("llm_timeout")
        elif is_llm_skipped(cls.error):
            reasons.append("llm_skipped")
    if sl.ocr_errors:
        reasons.append("ocr_error")
    decision = NEEDS_HUMAN if reasons else AUTO_FILE
    return SliceRouting(slice_id=sl.slice_id, decision=decision,
                        category=cls.predicted_category if decision == AUTO_FILE else UNKNOWN_CATEGORY, reasons=reasons,
                        suggested_category=cls.suggested_category if decision == NEEDS_HUMAN else None)


class GuardedLlm:
    """Bọc backend LLM của bộ phân loại để một lời gọi kẹt không làm tệp đứng hàng phút. Lời gọi bị bỏ qua trả `Answer(parse_ok=False)` với
    `error` bắt đầu bằng 'llm_skipped' -> DocumentClassifier chuyển lát cắt cho người (abstain_reason='llm_error') kèm lý do rõ.

    * hết giờ MỘT lời gọi (error 'ReadTimeout...'): các lát cắt còn lại của TỆP đó không gọi LLM nữa;
    * tổng thời gian chờ LLM của một tệp vượt `file_budget_s`: như trên;
    * hết giờ ở 2 tệp liên tiếp: mạch ngắt mở `cooldown_s` giây, mọi tệp trong thời gian đó bỏ qua LLM (Ollama coi như đang kẹt);
    * lỗi kết nối (Ollama vừa khởi động lại) được thử lại đúng 1 lần.
    Truy cập thuộc tính (spec, tier_name, model_name, ...) chuyển thẳng cho backend gốc."""

    def __init__(self, inner: Any, file_budget_s: float = DEFAULT_LLM_FILE_BUDGET_S, cooldown_s: float = DEFAULT_LLM_COOLDOWN_S,
                 connection_retries: int = 1, clock: Callable[[], float] = time.monotonic):
        self.inner, self.file_budget_s, self.cooldown_s = inner, file_budget_s, cooldown_s
        self.connection_retries, self.clock = connection_retries, clock
        self._open_until = 0.0
        self._consecutive_bad_files = 0
        self.start_file()

    def __getattr__(self, name):          # spec, tier_name, model_name, client, ...
        return getattr(self.inner, name)

    def start_file(self) -> None:
        self.calls = 0
        self.llm_ms = 0.0
        self.timeouts = 0
        self.skipped = 0
        self._spent_s = 0.0
        self._file_broken: Optional[str] = None

    def end_file(self) -> None:
        """Gọi sau khi xong một tệp: cập nhật mạch ngắt (2 tệp liên tiếp có hết giờ -> mở)."""
        if self.timeouts:
            self._consecutive_bad_files += 1
            if self._consecutive_bad_files >= 2:
                self._open_until = self.clock() + self.cooldown_s
        else:
            self._consecutive_bad_files = 0

    def _skip(self, why: str):
        from src.classification.zero_shot import NO_ANSWER, Answer
        self.skipped += 1
        return Answer(NO_ANSWER, None, None, 0.0, False, f"llm_skipped: {why}")

    def answer(self, text: str):
        if self.clock() < self._open_until:
            return self._skip("mạch ngắt đang mở (LLM hết giờ ở các tệp liền trước)")
        if self._file_broken:
            return self._skip(self._file_broken)
        if self._spent_s >= self.file_budget_s:
            return self._skip(f"hết ngân sách {self.file_budget_s:.0f} s LLM của tệp")
        ans = None
        for attempt in range(1 + max(0, self.connection_retries)):
            t0 = self.clock()
            ans = self.inner.answer(text)
            dt = self.clock() - t0
            self.calls += 1
            self.llm_ms += dt * 1000
            self._spent_s += dt
            if ans.parse_ok or not str(ans.error).startswith("ConnectionError"):
                break
        if not ans.parse_ok and is_llm_timeout(ans.error):
            self.timeouts += 1
            self._file_broken = "lời gọi LLM trước đó của tệp này đã hết giờ"
        return ans


def _set_timeout(llm: Any, seconds: float) -> None:
    """Đặt hết giờ cho backend thật (Ollama: .client.timeout; Kev: .timeout). Backend giả không có thì bỏ qua."""
    client = getattr(llm, "client", None)
    if client is not None and hasattr(client, "timeout"):
        client.timeout = seconds
    elif hasattr(llm, "timeout"):
        llm.timeout = seconds


class DocumentPipeline:
    def __init__(self, *, ocr: Optional[Callable[[Path], OCRDocumentResult]] = None,
                 splitter: Optional[Callable[[OCRDocumentResult], SplitResult]] = None,
                 classifier: Optional[Any] = None, extractor: Optional[Any] = None,
                 classifier_factory: Optional[Callable[[], Any]] = None, extractor_factory: Optional[Callable[[], Any]] = None,
                 run_extraction: bool = True, max_pages: int = 30, dpi: int = 200, device: str = "cpu", use_llm: bool = True,
                 llm_backend: str = "ollama", cache_dir: Optional[Path] = None,
                 split_policy: Union[None, str, SplitPolicy] = None, split_model: Optional[Any] = None,
                 one_sheet_types: Optional[Collection[str]] = None,
                 llm_timeout_s: float = DEFAULT_LLM_TIMEOUT_S, llm_file_budget_s: float = DEFAULT_LLM_FILE_BUDGET_S,
                 llm_cooldown_s: float = DEFAULT_LLM_COOLDOWN_S, extract_timeout_s: float = DEFAULT_EXTRACT_TIMEOUT_S,
                 clock: Callable[[], float] = time.monotonic, use_vlm: bool = DEFAULT_USE_VLM,
                 page_renderer: Optional[Callable[[Path, List[int], Path], List[Path]]] = None, title_tiebreak: bool = DEFAULT_TITLE_TIEBREAK,
                 auto_accept_expiry: bool = DEFAULT_AUTO_ACCEPT_EXPIRY):
        """`auto_accept_expiry`: cho quy tắc hạn tự nhận ngày (False: mọi hạn `needs_review`; chỉ áp cho FieldExtractor do pipeline dựng). `title_tiebreak`: bật `DocumentClassifier.rule_title_tiebreak` (gỡ mơ hồ của cổng luật theo vị trí tiêu đề; teams/team3_classification/experiments/05_composite_slices);
        chỉ áp cho bộ phân loại do pipeline dựng (hoặc bộ phân loại truyền vào có thuộc tính này). `use_vlm`: dựng ảnh trang (trong thư mục tạm, xóa ngay sau khi trích xuất lát cắt; không lưu vào repo) cho lát cắt thuộc loại có trường hạn
        để nguồn VLM đối chiếu ngày hết hạn; cần `use_llm`. `page_renderer(pdf, pages, out_dir) -> [ảnh]` thay được khi kiểm thử.
        Truyền `ocr`/`splitter`/`classifier`/`extractor` để thay thành phần (kiểm thử); bỏ trống -> dùng thành phần thật, nạp lười.
        `splitter` (hàm tùy ý) ghi đè mọi chính sách tách (không gộp, không đánh dấu). `split_policy`: tên preset (`src.splitting.policy.PRESETS`) hoặc
        `SplitPolicy`; None = mặc định `model+merge` (`DEFAULT_PRESET`). `split_model`: PairBoundaryModel đã nạp (mặc định nạp từ teams/team2_splitting/models/)."""
        self._ocr, self._splitter = ocr, splitter
        self._classifier, self._extractor = classifier, extractor
        self._classifier_factory, self._extractor_factory = classifier_factory, extractor_factory
        self.run_extraction = run_extraction
        self.max_pages, self.dpi, self.device = max_pages, dpi, device
        self.use_llm, self.llm_backend, self.cache_dir = use_llm, llm_backend, cache_dir
        self.policy = SplitPolicy("custom", "rule") if splitter is not None else resolve_policy(split_policy)
        self._split_model, self._one_sheet = split_model, one_sheet_types
        self.llm_timeout_s, self.llm_file_budget_s, self.llm_cooldown_s, self._clock = llm_timeout_s, llm_file_budget_s, llm_cooldown_s, clock
        self.extract_timeout_s = extract_timeout_s
        self.use_vlm, self._page_renderer = use_vlm, page_renderer or default_page_renderer
        self.title_tiebreak = bool(title_tiebreak)
        self.auto_accept_expiry = bool(auto_accept_expiry)
        self._guard: Optional[GuardedLlm] = None
        self._engine = None
        self._load_ms = 0.0

    # --- dựng thành phần thật (lười)
    def _do_ocr(self, path: Path) -> OCRDocumentResult:
        if self._ocr is not None:
            return self._ocr(path)
        from src.ocr.pdf_ocr import ocr_pdf
        from src.ocr.vietocr_engine import VietOCREngine
        if self._engine is None:
            t = time.perf_counter()
            self._engine = VietOCREngine("vgg_seq2seq", resolve_device(self.device))
            self._load_ms = (time.perf_counter() - t) * 1000          # nạp mô hình tính riêng, không lẫn vào thời gian OCR
        return ocr_pdf(path, self._engine, dpi=self.dpi, max_pages=self.max_pages)

    def _do_split(self, doc: OCRDocumentResult):
        """-> (SplitResult, PolicyInfo|None). `splitter` tùy ý thắng chính sách."""
        if self._splitter is not None:
            return self._splitter(doc), None
        res, info = split_with_policy(doc, self.policy, self._split_model)
        return res, info

    def _get_classifier(self):
        if self._classifier is None:
            if self._classifier_factory is not None:
                self._classifier = self._classifier_factory()
            else:
                from src.classification.doc_classifier import DocumentClassifier
                self._classifier = DocumentClassifier.from_defaults(use_llm=self.use_llm, llm_backend=self.llm_backend,
                                                                    cache_dir=self.cache_dir)
        if self.title_tiebreak and hasattr(self._classifier, "rule_title_tiebreak"):
            self._classifier.rule_title_tiebreak = True
        llm = getattr(self._classifier, "llm", None)
        if llm is not None and not isinstance(llm, GuardedLlm):
            _set_timeout(llm, self.llm_timeout_s)
            self._guard = GuardedLlm(llm, self.llm_file_budget_s, self.llm_cooldown_s, clock=self._clock)
            self._classifier.llm = self._guard
        elif isinstance(llm, GuardedLlm):
            self._guard = llm
        return self._classifier

    def _get_extractor(self):
        if self._extractor is None:
            if self._extractor_factory is not None:
                self._extractor = self._extractor_factory()
            else:
                from src.extraction.field_extractor import ExtractConfig, FieldExtractor
                cache = Path(self.cache_dir) / "extraction" if self.cache_dir else None
                self._extractor = FieldExtractor(ExtractConfig(use_llm=self.use_llm, timeout_s=self.extract_timeout_s, cache_dir=cache,
                                                                auto_accept_expiry=self.auto_accept_expiry))
        return self._extractor

    def _one_sheet_types(self) -> Collection[str]:
        if self._one_sheet is None:
            self._one_sheet = load_one_sheet_types()
        return self._one_sheet

    # ======================================================================================
    # HOOK TRÍCH XUẤT TRƯỜNG: nơi nhóm 4 cắm vào. Pipeline gọi đúng một lần cho MỖI lát cắt `auto_file` (sau khi đã tách, phân loại và gộp), với nhãn đã được nhận.
    # Giữ nguyên chữ ký `extract_fields(slice, category) -> ExtractionResult`. Mặc định gọi BarbEntityExtractor.extract (nạp lười); ngoại lệ được `run` bắt và ghi nhận.
    # ======================================================================================
    def extract_fields(self, sl: DocumentSlice, category: str, filename: Optional[str] = None, page_images: Optional[Any] = None) -> ExtractionResult:
        """`filename` = tên tệp PDF gốc (nguồn độc lập của ngày hết hạn); `page_images` tùy chọn (ảnh trang cho VLM; `run` dựng trong thư mục tạm khi `use_vlm`)."""
        ex = self._get_extractor()
        from src.extraction.field_extractor import FieldExtractor
        if isinstance(ex, FieldExtractor):
            from src.extraction.schemas import SUPPORTED_TYPES
            if category not in SUPPORTED_TYPES:
                return ExtractionResult(slice_id=sl.slice_id, document_type=category, status="skipped",
                                        error=f"no_schema: chưa có schema trích xuất cho loại {category} (có: {', '.join(SUPPORTED_TYPES)})")
            return ex.extract(sl, category, filename=filename, page_images=page_images)
        try:
            takes_filename = "filename" in inspect.signature(ex.extract).parameters
        except (TypeError, ValueError):
            takes_filename = False
        return ex.extract(sl, category, filename=filename) if takes_filename else ex.extract(sl, category)

    def _wants_page_images(self, category: str) -> bool:
        """Chỉ dựng ảnh khi sẽ có người dùng: VLM bật, LLM bật, bộ trích xuất thật (FieldExtractor) và loại có trường hạn (VLM chỉ đối chiếu trường hạn)."""
        if not (self.use_vlm and self.use_llm):
            return False
        from src.extraction.field_extractor import FieldExtractor
        if not isinstance(self._get_extractor(), FieldExtractor):
            return False
        from src.extraction.schemas import SUPPORTED_TYPES, field_specs
        return category in SUPPORTED_TYPES and any(f.get("is_expiry") for f in field_specs(category))

    def _render_slice_images(self, path: Path, sl: DocumentSlice, tmp_root: Path) -> List[Path]:
        pages = sorted({p.page_number for p in sl.pages}) or list(range(sl.start_page, sl.end_page + 1))
        texts = {p.page_number: p.full_text or "" for p in sl.pages}
        shown = choose_vlm_pages(pages, texts)
        return self._page_renderer(path, shown, tmp_root / sl.slice_id)

    @staticmethod
    def _escalate(routing: List[SliceRouting], reason: str) -> None:
        """Cả tệp về người (giữ nhãn đã nhận làm gợi ý) với lý do cấp tệp `reason`."""
        for r in routing:
            if r.decision == AUTO_FILE:
                r.suggested_category, r.category, r.decision = r.category, UNKNOWN_CATEGORY, NEEDS_HUMAN
            if reason not in r.reasons:
                r.reasons.append(reason)

    @staticmethod
    def _file_sha256(path: Path) -> str:
        """Định danh tệp cho khóa kiểm mẫu: sha256 nội dung; không đọc được -> tên tệp."""
        import hashlib
        try:
            h = hashlib.sha256()
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(1 << 20), b""):
                    h.update(chunk)
            return h.hexdigest()
        except OSError:
            return f"name:{path.name}"

    # --- chạy
    def run(self, pdf_path: str | Path) -> DocumentProcessingPipelineResult:
        t_start = time.perf_counter()
        path = Path(pdf_path)
        timings = {"ocr": 0.0, "split": 0.0, "classify": 0.0, "extract": 0.0}
        warnings: List[str] = []

        t = time.perf_counter()
        self._load_ms = 0.0
        ocr_doc = self._do_ocr(path)
        timings["ocr"] = (time.perf_counter() - t) * 1000 - self._load_ms
        if self._load_ms:
            timings["ocr_model_load"] = self._load_ms          # chỉ có ở lần chạy đầu của tiến trình
        if ocr_doc.error:
            warnings.append(f"ocr: {ocr_doc.error}")
        truncated_pages: List[int] = []
        if ocr_doc.total_pages > len(ocr_doc.pages) and ocr_doc.pages:
            n_done = len(ocr_doc.pages)
            truncated_pages = list(range(n_done + 1, ocr_doc.total_pages + 1))
            warnings.append(f"ocr: chỉ xử lý {n_done}/{ocr_doc.total_pages} trang (giới hạn --max-pages); trang {n_done + 1}-{ocr_doc.total_pages} "
                            f"KHÔNG được tách/phân loại/trích xuất: cả tệp chuyển người (lý do {REASON_TRUNCATED})")

        t = time.perf_counter()
        split, pinfo = self._do_split(ocr_doc)
        timings["split"] = (time.perf_counter() - t) * 1000
        n_before_merge = len(split.slices)

        classifications: List[ClassificationResult] = []
        clf_error = None
        try:
            clf = self._get_classifier()
        except Exception as e:  # noqa: BLE001  - thiếu mô hình TF-IDF, v.v.: nêu rõ, mọi lát cắt sang người
            clf, clf_error = None, f"{type(e).__name__}: {e}"
            warnings.append(f"classify: không dựng được bộ phân loại: {clf_error}")
        if not self.use_llm:
            warnings.append("classify: tầng LLM đang TẮT (--no-llm): tài liệu luật và TF-IDF không nhận được sẽ chuyển cho người")
        if clf is not None and hasattr(clf, "set_file_key"):
            clf.set_file_key(self._file_sha256(path))          # khóa kiểm mẫu = tệp + lát cắt (slice_id một mình lặp lại ở mọi tệp)
        if self._guard is not None:
            self._guard.start_file()
        for sl in split.slices:
            t = time.perf_counter()
            if clf is None:
                cls = ClassificationResult(slice_id=sl.slice_id, predicted_category=UNKNOWN_CATEGORY, tier="human", requires_human_review=True,
                                           abstain_reason="classifier_unavailable", error=clf_error)
            else:
                try:
                    cls = clf.classify_slice(sl)
                except Exception as e:  # noqa: BLE001
                    logger.exception("Phân loại %s lỗi", sl.slice_id)
                    cls = ClassificationResult(slice_id=sl.slice_id, predicted_category=UNKNOWN_CATEGORY, tier="human", requires_human_review=True,
                                               abstain_reason="classifier_exception", error=f"{type(e).__name__}: {e}")
            timings["classify"] += (time.perf_counter() - t) * 1000
            classifications.append(cls)

        # --- hiệu chỉnh nhận biết loại: gộp lát cắt liền kề được gán cùng loại (trừ loại một-tờ); lát cắt bị từ chối không bao giờ bị gộp
        if self.policy.merge_same_type and len(split.slices) > 1:
            t = time.perf_counter()
            labels = [c.predicted_category if (c.tier != "human" and c.predicted_category != UNKNOWN_CATEGORY) else None for c in classifications]
            split, groups = merge_same_type(split, labels, self._one_sheet_types(), self.policy.keep_above)
            if len(split.slices) < n_before_merge:
                classifications = [classifications[g[0]].model_copy(update={"slice_id": s.slice_id}) for g, s in zip(groups, split.slices)]
                warnings.append(f"split: gộp {n_before_merge} -> {len(split.slices)} lát cắt (liền kề cùng loại)")
            timings["split"] += (time.perf_counter() - t) * 1000
        for sl, cls in zip(split.slices, classifications):
            if cls.error:
                warnings.append(f"classify {sl.slice_id}: {cls.error}")
        if self._guard is not None:
            self._guard.end_file()

        routing: List[SliceRouting] = [route_slice(sl, cls) for sl, cls in zip(split.slices, classifications)]
        flagged = bool(pinfo is not None and pinfo.flagged)
        if flagged:        # chính sách `triage`: tệp nghi là composite => cả tệp về người, giữ nhãn đã nhận làm gợi ý
            warnings.append(f"split: điểm ranh giới cao nhất {pinfo.max_score:.3f} >= {self.policy.flag_min}: nghi tệp ghép nhiều tài liệu, chuyển người")
            self._escalate(routing, REASON_POSSIBLE_COMPOSITE)
        file_shadow: dict = {}
        if pinfo is not None and pinfo.id_extra_pages:        # chế độ bóng của quy tắc `id` (chính sách hiện tại không tự thêm ranh giới): không tách, chuyển người kiểm
            file_shadow["id_rule_extra_boundaries"] = list(pinfo.id_extra_pages)
            warnings.append(f"split: quy tắc `id` (bóng) muốn thêm ranh giới ở trang {pinfo.id_extra_pages}: không tách, chuyển người kiểm ranh giới")
            self._escalate(routing, REASON_ID_BOUNDARY)
        if truncated_pages:
            file_shadow["truncated_pages"] = truncated_pages
            self._escalate(routing, REASON_TRUNCATED)
        if clf is not None and not self.title_tiebreak and hasattr(clf, "shadow_title_tiebreak"):
            from src.classification.doc_classifier import text_for_classification
            for sl, cls, r in zip(split.slices, classifications, routing):          # bóng của tiebreak: chỉ luật từ khóa, không gọi LLM
                try:
                    lab = clf.shadow_title_tiebreak(text_for_classification(sl))
                except Exception:  # noqa: BLE001 - chỉ là số liệu đo, không được làm hỏng tệp
                    logger.exception("shadow tiebreak %s lỗi", sl.slice_id)
                    lab = None
                if lab:
                    r.shadow["title_tiebreak_label"] = lab
                    r.shadow["title_tiebreak_differs"] = bool(lab != cls.predicted_category)

        extractions: List[ExtractionResult] = []
        tmp_ctx = tempfile.TemporaryDirectory(prefix="pipeline_vlm_") if (self.run_extraction and self.use_vlm) else None
        try:
            for sl, route in zip(split.slices, routing):
                if not self.run_extraction or route.decision != AUTO_FILE:
                    continue
                images: Optional[List[Path]] = None
                if tmp_ctx is not None:
                    t = time.perf_counter()
                    try:
                        if self._wants_page_images(route.category):
                            timings.setdefault("render", 0.0)          # chỉ có khi thật sự dựng ảnh (tách khỏi 'extract')
                            images = self._render_slice_images(path, sl, Path(tmp_ctx.name)) or None
                    except Exception as e:  # noqa: BLE001  - không dựng được ảnh: trích xuất tiếp không có VLM, nêu rõ
                        logger.exception("Dựng ảnh trang %s lỗi", sl.slice_id)
                        warnings.append(f"render {sl.slice_id}: không dựng được ảnh trang, bỏ nguồn VLM: {type(e).__name__}: {e}")
                    if "render" in timings:
                        timings["render"] += (time.perf_counter() - t) * 1000
                t = time.perf_counter()
                try:
                    kw = {"page_images": images} if images else {}
                    ex = self.extract_fields(sl, route.category, filename=path.name, **kw)          # <-- HOOK trích xuất trường
                except Exception as e:  # noqa: BLE001  - trích xuất không bao giờ làm hỏng cả pipeline
                    logger.exception("Trích xuất %s lỗi", sl.slice_id)
                    ex = ExtractionResult(slice_id=sl.slice_id, document_type=route.category, status="error",
                                          error=f"{type(e).__name__}: {e}")
                finally:
                    if images:                              # ảnh giấy tờ không được nằm lại trên đĩa
                        shutil.rmtree(Path(tmp_ctx.name) / sl.slice_id, ignore_errors=True)
                timings["extract"] += (time.perf_counter() - t) * 1000
                extractions.append(ex)
                route.extraction_status = ex.status
                ed = ex.entity_dict or {}
                route.expiry = dict(ed.get("_expiry") or {})
                route.expiry_suggestion = dict(ed.get("_expiry_suggestion") or {})
                route.field_review = any(v == "needs_review" for v in route.expiry.values())
                if ed.get("_expiry_would_accept") is not None:
                    route.shadow["expiry_would_accept"] = dict(ed["_expiry_would_accept"])
                    route.shadow["expiry_rule"] = ed.get("_expiry_rule")
                if ex.status == "skipped" and (ex.error or "").startswith("no_schema"):
                    route.extraction_note = ex.error            # loại chưa có schema: "chưa trích xuất", không phải lỗi, không cảnh báo
                elif ex.status != "ok":
                    route.extraction_note = ex.error
                    warnings.append(f"extract {sl.slice_id}: {ex.status}: {ex.error}")
        finally:
            if tmp_ctx is not None:
                tmp_ctx.cleanup()

        reasons: List[str] = []
        for r in routing:
            for x in r.reasons:
                if x not in reasons:
                    reasons.append(x)
        n_auto = sum(r.decision == AUTO_FILE for r in routing)
        summary = FileRoutingSummary(
            decision=AUTO_FILE if (routing and n_auto == len(routing)) else NEEDS_HUMAN, n_slices=len(routing), n_auto=n_auto,
            n_needs_human=len(routing) - n_auto, n_field_review=sum(r.field_review for r in routing), reasons=reasons, splitter=self.policy.name, n_slices_before_merge=n_before_merge,
            n_llm_calls=self._guard.calls if self._guard is not None else 0, llm_ms=round(self._guard.llm_ms, 1) if self._guard is not None else 0.0,
            shadow=file_shadow)
        if truncated_pages and REASON_TRUNCATED not in summary.reasons:
            summary.reasons.append(REASON_TRUNCATED)
        if not routing:
            summary.reasons = ["no_slices"] + ([REASON_TRUNCATED] if truncated_pages else [])
        return DocumentProcessingPipelineResult(
            file_name=ocr_doc.file_name or path.name, total_pages=ocr_doc.total_pages, is_composite_bundle=len(split.slices) > 1,
            ocr_result=ocr_doc, split_result=split, classifications=classifications, extractions=extractions,
            total_processing_time_ms=(time.perf_counter() - t_start) * 1000, routing=routing,
            stage_timings_ms={k: round(v, 1) for k, v in timings.items()}, warnings=warnings, file_routing=summary)


    def summarize(self, result: "DocumentProcessingPipelineResult") -> str:
        """Trả về một dòng tóm tắt ngắn gọn về kết quả chạy pipeline."""
        routing = result.file_routing
        warn_part = f" | warnings: {len(result.warnings)}" if result.warnings else ""
        return (
            f"[{result.file_name}] {result.total_pages} trang → "
            f"{routing.decision.upper()} ({routing.n_auto}/{routing.n_slices} auto){warn_part}"
        )


def resolve_device(device: str) -> str:
    """'auto' -> 'cuda:0' nếu có GPU còn >= 2 GB trống, ngược lại 'cpu' (GPU dùng chung với việc khác). Giá trị khác giữ nguyên."""
    if device != "auto":
        return device
    try:
        import torch
        if torch.cuda.is_available():
            free, _ = torch.cuda.mem_get_info(0)
            if free >= 2 * 1024 ** 3:
                return "cuda:0"
    except Exception:  # noqa: BLE001
        pass
    return "cpu"
