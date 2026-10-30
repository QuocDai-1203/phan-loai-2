"""Bộ trích xuất TRƯỜNG (src/extraction/field_extractor.py): dùng LLM giả, không cần GPU/mạng. Mọi lỗi phải hiện ra ở status/error."""
import json
import logging
from pathlib import Path

import pytest

from src.common.contracts import DocumentSlice, OCRPageResult
from src.extraction import field_extractor as FE
from src.extraction import field_llm
from src.extraction.field_extractor import ExtractConfig, FieldExtractor, extract_fields
from src.extraction.schemas import SCHEMA_DIR, SUPPORTED_TYPES, load_schema

REPO = Path(__file__).resolve().parents[1]

GCN = """UBND TỈNH KHÁNH HÒA CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
Số: 83/GCNĐĐK-SCT Khánh Hoà, ngày 10 tháng 4 năm 2019
1. Tên cửa hàng bán lẻ xăng dầu: Tàu dầu Mẫu 01;
Điều 3. Giấy chứng nhận này có giá trị đến
hết ngày 09 tháng 4 năm 2024.
"""
CC = """GIẤY CHỨNG NHẬN
Họ và tên: Nguyen Van Bimat
Ngày Sinh: 22/01/1981
Số: 51/2022-GCN
Bình Định, ngày 12 tháng 05 năm 2022
Từ ngày 12 tháng 05 năm 2022 đến ngày 12 tháng 05 năm 2024
"""
CFG = ExtractConfig(auto_accept_expiry=True, expiry_rule="regex=llm")


def sl(text, **kw):
    return DocumentSlice(slice_id="s1", start_page=1, end_page=1, page_count=1, combined_text=text, **kw)


class FakeLlm:
    def __init__(self, **values):
        self.values, self.calls = values, []

    def __call__(self, system, user, schema):
        self.calls.append({"system": system, "user": user, "schema": schema})
        return {k: self.values.get(k) for k in schema["properties"]}


def test_cascade_fills_regex_nulls_from_llm_and_keeps_regex_values():
    llm = FakeLlm(ngay_het_han="09 tháng 4 năm 2024", co_quan_cap="Sở Công Thương tỉnh Khánh Hòa", so_giay="KHAC/XXX")
    res = extract_fields(sl(GCN), "GCN_DDK_BAN_LE_XD", config=CFG, llm_client=llm)
    d = res.entity_dict
    assert res.status == "ok" and res.error is None
    assert d["so_giay"] == "83/GCNDDK-SCT"                             # luật thắng khi có giá trị
    assert d["co_quan_cap"] == "Sở Công Thương tỉnh Khánh Hòa"         # LLM điền chỗ luật bỏ trống
    assert d["_sources"]["so_giay"] == "regex" and d["_sources"]["co_quan_cap"] == "llm"
    assert d["ngay_cap"] == "2019-04-10"


def test_expiry_is_auto_accepted_only_when_sources_agree():
    ok = extract_fields(sl(GCN), "GCN_DDK_BAN_LE_XD", config=CFG, llm_client=FakeLlm(ngay_het_han="09/04/2024"))
    assert ok.entity_dict["ngay_het_han"] == "2024-04-09" and ok.entity_dict["_expiry"] == {"ngay_het_han": "accepted"}
    bad = extract_fields(sl(GCN), "GCN_DDK_BAN_LE_XD", config=CFG, llm_client=FakeLlm(ngay_het_han="09/04/2025"))
    assert bad.entity_dict["ngay_het_han"] is None and bad.entity_dict["_expiry"] == {"ngay_het_han": "needs_review"}   # bất đồng: từ chối, không đoán
    none = extract_fields(sl("Giấy chứng nhận không có hạn"), "GCN_DDK_BAN_LE_XD", config=CFG, llm_client=FakeLlm())
    assert none.entity_dict["_expiry"] == {"ngay_het_han": "not_found"}


def test_filename_can_serve_as_independent_expiry_source():
    cfg = ExtractConfig(auto_accept_expiry=True, expiry_rule="regex=filename")
    r = extract_fields(sl(GCN), "GCN_DDK_BAN_LE_XD", config=cfg, llm_client=FakeLlm(), filename="DDK-Cua hang-09.4.24.pdf")
    assert r.entity_dict["ngay_het_han"] == "2024-04-09"
    r2 = extract_fields(sl(GCN), "GCN_DDK_BAN_LE_XD", config=cfg, llm_client=FakeLlm(), filename="DDK-Cua hang-10.4.24.pdf")
    assert r2.entity_dict["ngay_het_han"] is None and r2.entity_dict["_expiry"]["ngay_het_han"] == "needs_review"


class FakeVlm:
    def __init__(self, **values):
        self.values, self.calls = values, []

    def __call__(self, system, user, schema, images):
        self.calls.append({"system": system, "user": user, "schema": schema, "images": list(images)})
        return {k: self.values.get(k) for k in schema["properties"]}


def test_vlm_is_an_independent_expiry_source_used_only_with_images():
    cfg = ExtractConfig(auto_accept_expiry=True, expiry_rule="regex=vlm")
    imgs = [Path(f"p01_{s}.png") for s in "ab"] + [Path(f"p02_{s}.png") for s in "ab"] + [Path("p03.png")]
    vlm = FakeVlm(ngay_het_han="ngày 09 tháng 04 năm 2024", so_giay="SAI/KHAC")
    r = extract_fields(sl(GCN), "GCN_DDK_BAN_LE_XD", config=cfg, llm_client=FakeLlm(), page_images=imgs, vlm_client=vlm)
    assert r.entity_dict["ngay_het_han"] == "2024-04-09" and r.entity_dict["_expiry"]["ngay_het_han"] == "accepted"
    assert len(vlm.calls[0]["images"]) == 4                       # như lúc chấm: 4 ảnh đầu
    assert r.entity_dict["so_giay"] == "83/GCNDDK-SCT"             # VLM chỉ để đối chiếu hạn, không ghi đè trường khác
    no_img = extract_fields(sl(GCN), "GCN_DDK_BAN_LE_XD", config=cfg, llm_client=FakeLlm())
    assert no_img.entity_dict["_expiry"]["ngay_het_han"] == "needs_review" and not vlm.calls[1:]
    disagree = extract_fields(sl(GCN), "GCN_DDK_BAN_LE_XD", config=cfg, llm_client=FakeLlm(), page_images=imgs, vlm_client=FakeVlm(ngay_het_han="24/04/2024"))
    assert disagree.entity_dict["ngay_het_han"] is None


def test_vlm_failure_is_explicit():
    def boom(*a):
        raise field_llm.LlmError("hết bộ nhớ GPU")
    r = extract_fields(sl(GCN), "GCN_DDK_BAN_LE_XD", config=ExtractConfig(auto_accept_expiry=True, expiry_rule="regex=vlm"), llm_client=FakeLlm(),
                       page_images=[Path("p01.png")], vlm_client=boom)
    assert r.status == "error" and "VLM" in r.error and r.entity_dict["so_giay"] == "83/GCNDDK-SCT"


def test_default_rule_is_any_model_equals_filename():
    assert FE.DEFAULT_EXPIRY_RULE == "any-model=filename"
    ON = ExtractConfig(auto_accept_expiry=True)
    r = extract_fields(sl(GCN), "GCN_DDK_BAN_LE_XD", config=ON, llm_client=FakeLlm(ngay_het_han="01/01/2030"), filename="DDK-Mau-09.4.24.pdf")
    assert r.entity_dict["ngay_het_han"] == "2024-04-09"          # luật = tên tệp; LLM đọc khác -> vẫn nhận vì có HAI nguồn đồng thuận (luật + tên tệp)
    r2 = extract_fields(sl(GCN), "GCN_DDK_BAN_LE_XD", config=ON, llm_client=FakeLlm(ngay_het_han="09/04/2024"))
    assert r2.entity_dict["ngay_het_han"] is None and r2.entity_dict["_expiry"]["ngay_het_han"] == "needs_review"   # không có tên tệp/ảnh: không tự nhận
    assert r2.entity_dict["_expiry_suggestion"] == {"ngay_het_han": "2024-04-09"}      # nhưng gợi ý cho người duyệt


def test_unparseable_dates_become_null_not_garbage():
    llm = FakeLlm(ngay_cap="ngày … tháng … năm …", ngay_het_han="có giá trị đến hết ngày 09 tháng dưng")
    r = extract_fields(sl("Giấy chứng nhận"), "GCN_DDK_BAN_LE_XD", config=CFG, llm_client=llm)
    assert r.entity_dict["ngay_cap"] is None and r.entity_dict["ngay_het_han"] is None


def test_pii_birth_date_is_neither_asked_nor_returned_by_default():
    llm = FakeLlm(so_gcn="51/2022-GCN", ho_ten="Nguyen Van Bimat", nam_sinh="22/01/1981")
    res = extract_fields(sl(CC), "CC_TAP_HUAN_VC_HNH", config=CFG, llm_client=llm)
    assert "nam_sinh" not in llm.calls[0]["schema"]["properties"]                # không hỏi thì không trích
    assert "22/01/1981" not in llm.calls[0]["user"].split("<<<")[0]               # (văn bản OCR có thể chứa; phần chỉ dẫn thì không)
    blob = res.model_dump_json()
    assert "1981" not in blob and "nam_sinh" not in res.entity_dict
    assert res.entity_dict["dropped_pii_fields"] == ["nam_sinh"]
    on = extract_fields(sl(CC), "CC_TAP_HUAN_VC_HNH", config=ExtractConfig(auto_accept_expiry=True, expiry_rule="regex=llm", store_personal_ids=True),
                        llm_client=FakeLlm(nam_sinh="22/01/1981"))
    assert on.entity_dict["nam_sinh"] == "1981-01-22"


def test_logs_never_contain_field_values(caplog):
    class Boom:
        def __call__(self, *a):
            raise field_llm.LlmError("Ollama tắt")
    with caplog.at_level(logging.DEBUG):
        res = extract_fields(sl(CC), "CC_TAP_HUAN_VC_HNH", config=CFG, llm_client=Boom())
    assert res.status == "error"
    assert "Nguyen Van Bimat" not in caplog.text and "1981" not in caplog.text and "51/2022" not in caplog.text


def test_llm_failure_is_explicit_status_error_with_partial_regex_fields():
    class Boom:
        def __call__(self, *a):
            raise field_llm.LlmError("không gọi được Ollama tại http://127.0.0.1:11434: ConnectionError")
    res = extract_fields(sl(GCN), "GCN_DDK_BAN_LE_XD", config=CFG, llm_client=Boom())
    assert res.status == "error" and "LLM" in res.error and "Ollama" in res.error and "một phần" in res.error
    assert res.entity_dict["so_giay"] == "83/GCNDDK-SCT"                         # phần luật vẫn còn
    assert res.entity_dict["_expiry"]["ngay_het_han"] == "needs_review"          # không có nguồn thứ hai: từ chối, không tự nhận


def test_use_llm_false_never_calls_the_model():
    def never(*a):
        raise AssertionError("không được gọi LLM")
    res = extract_fields(sl(GCN), "GCN_DDK_BAN_LE_XD", config=ExtractConfig(auto_accept_expiry=True, use_llm=False, expiry_rule="regex"), llm_client=never)
    assert res.status == "ok" and res.entity_dict["ngay_het_han"] == "2024-04-09"


def test_empty_text_unsupported_type_and_page_errors():
    assert extract_fields(sl("   "), "HD_MUA_BAN", config=CFG, llm_client=FakeLlm()).status == "skipped"
    r = extract_fields(sl("văn bản"), "LOAI_KHONG_CO", config=CFG, llm_client=FakeLlm())      # (GPLX đã được hỗ trợ từ giai đoạn 3)
    assert r.status == "error" and "LOAI_KHONG_CO" in r.error
    bad_page = OCRPageResult(page_number=1, width=1, height=1, full_text="", error="OCR hỏng")
    assert extract_fields(sl("", pages=[bad_page]), "HD_MUA_BAN", config=CFG, llm_client=FakeLlm()).status == "skipped"


def test_pages_are_used_when_available_and_pageno_is_kept():
    pages = [OCRPageResult(page_number=2, width=1, height=1, full_text=GCN)]
    res = extract_fields(DocumentSlice(slice_id="s", start_page=2, end_page=2, page_count=1, combined_text="", pages=pages), "GCN_DDK_BAN_LE_XD",
                         config=ExtractConfig(auto_accept_expiry=True, use_llm=False, expiry_rule="regex"))
    assert res.status == "ok" and res.entity_dict["ngay_cap"] == "2019-04-10"


def test_field_extractor_has_barb_compatible_signature(monkeypatch):
    ex = FieldExtractor(CFG, llm_client=FakeLlm())
    res = ex.extract(sl(GCN), "GCN_DDK_BAN_LE_XD")                              # đúng chữ ký extract(slice, label)
    assert res.document_type == "GCN_DDK_BAN_LE_XD" and res.status == "ok" and res.processing_time_ms >= 0
    from src.extraction.barb_extractor import BarbEntityExtractor              # lớp cũ giữ nguyên
    assert BarbEntityExtractor().model is None


def test_no_network_calls_on_import_or_with_fake_client(monkeypatch):
    import requests
    monkeypatch.setattr(requests, "post", lambda *a, **k: (_ for _ in ()).throw(AssertionError("không được gọi mạng")))
    extract_fields(sl(GCN), "GCN_DDK_BAN_LE_XD", config=CFG, llm_client=FakeLlm())


def test_ollama_client_only_targets_localhost_and_reports_connection_errors(monkeypatch):
    import requests
    assert field_llm.OLLAMA_URL.startswith("http://127.0.0.1")
    monkeypatch.setattr(requests, "post", lambda *a, **k: (_ for _ in ()).throw(requests.ConnectionError("từ chối")))
    client = field_llm.ollama_client()
    with pytest.raises(field_llm.LlmError, match="Ollama"):
        client("s", "u", {"type": "object", "properties": {}})


# ---------------------------------------------------------------- đồng bộ với thí nghiệm
@pytest.mark.parametrize("dt", SUPPORTED_TYPES)
def test_schema_copy_identical_to_team_schema(dt):
    team = REPO / "teams" / "team4_extraction" / "schema" / f"{dt}.json"
    if not team.exists():
        pytest.skip("không có thư mục teams/")
    assert (SCHEMA_DIR / f"{dt}.json").read_bytes() == team.read_bytes()
    assert (SCHEMA_DIR / "pii_fields.json").read_bytes() == (team.parent / "pii_fields.json").read_bytes()


def test_default_expiry_rule_matches_frozen_dev_selection():
    sel = REPO / "teams" / "team4_extraction" / "experiments" / "02_methods" / "dev_selection.json"
    if not sel.exists():
        pytest.skip("chưa đóng băng cấu hình")
    s = json.loads(sel.read_text(encoding="utf-8"))
    assert FE.DEFAULT_EXPIRY_RULE == s["production"]["expiry_rule"]
    assert field_llm.prompt_fingerprint() == s["prompts"]["llm_fingerprint"]



def test_auto_accept_expiry_is_off_by_default_but_records_suggestion_rule_and_would_accept():
    assert ExtractConfig().auto_accept_expiry is False
    kw = dict(llm_client=FakeLlm(ngay_het_han="01/01/2030"), filename="DDK-Mau-09.4.24.pdf")
    off = extract_fields(sl(GCN), "GCN_DDK_BAN_LE_XD", **kw)
    ed = off.entity_dict
    assert ed["ngay_het_han"] is None and ed["_expiry"] == {"ngay_het_han": "needs_review"}      # không tự nhận dù quy tắc sẽ nhận
    assert ed["_expiry_rule"] == "any-model=filename" and ed["_expiry_would_accept"] == {"ngay_het_han": True}
    assert ed["_expiry_suggestion"] == {"ngay_het_han": "2024-04-09"}
    on = extract_fields(sl(GCN), "GCN_DDK_BAN_LE_XD", config=ExtractConfig(auto_accept_expiry=True), **kw)
    assert on.entity_dict["ngay_het_han"] == "2024-04-09" and on.entity_dict["_expiry"] == {"ngay_het_han": "accepted"}
    assert on.entity_dict["_expiry_would_accept"] == {"ngay_het_han": True}
    # quy tắc không nhận -> would_accept False
    no = extract_fields(sl(GCN), "GCN_DDK_BAN_LE_XD", llm_client=FakeLlm(ngay_het_han="09/04/2024"))
    assert no.entity_dict["_expiry_would_accept"] == {"ngay_het_han": False}
