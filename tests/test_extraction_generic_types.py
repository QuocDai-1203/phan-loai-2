"""17 loại giai đoạn 3 trong `src/extraction`: schema đồng nhất, luật ngày chung làm phương án dự phòng, quy tắc hạn theo loại,
"không thời hạn", PII. Dùng văn bản giả (không có định danh thật) và LLM giả: không cần GPU/mạng."""
import re
from pathlib import Path

import pytest

from src.common.contracts import DocumentSlice
from src.extraction import field_extractor as FE
from src.extraction import generic_date_rules as GR
from src.extraction.field_extractor import ExtractConfig, expiry_rule_for, extract_fields
from src.extraction.field_rules import RULES, apply_rules
from src.extraction.generic_date_rules import apply_rules_with_fallback
from src.extraction.schemas import PHASE2_TYPES, PHASE3_TYPES, SCHEMA_DIR, SUPPORTED_TYPES, field_specs

REPO = Path(__file__).resolve().parents[1]
TEAM_SCHEMA = REPO / "teams" / "team4_extraction" / "schema"

HDVC = """HỢP ĐỒNG VẬN CHUYỂN
Số: 01/2024/HĐVC
Hôm nay, ngày 05 tháng 03 năm 2024, tại Hà Nội
Hợp đồng này có hiệu lực kể từ ngày ký đến hết ngày 31 tháng 12 năm 2025.
"""
GPLX_NO_EXPIRY = """GIẤY PHÉP LÁI XE
Hạng: A1
Có giá trị không thời hạn
"""


def sl(text):
    return DocumentSlice(slice_id="s1", start_page=1, end_page=1, page_count=1, combined_text=text)


class FakeLlm:
    def __init__(self, **values):
        self.values, self.calls = values, []

    def __call__(self, system, user, schema):
        self.calls.append(schema)
        return {k: self.values.get(k) for k in schema["properties"]}


# ------------------------------------------------------------------ loại và schema
def test_supported_types_cover_all_21_types_and_all_schema_files():
    assert len(PHASE2_TYPES) == 4 and len(PHASE3_TYPES) == 17 and len(set(SUPPORTED_TYPES)) == 21
    on_disk = {p.stem for p in SCHEMA_DIR.glob("*.json")} - {"pii_fields"}
    assert on_disk == set(SUPPORTED_TYPES)
    for dt in SUPPORTED_TYPES:
        assert field_specs(dt)                                       # không còn UnsupportedDocType


def test_team_schema_dir_is_fully_mirrored():
    if not TEAM_SCHEMA.exists():
        pytest.skip("không có thư mục teams/")
    team = {p.stem for p in TEAM_SCHEMA.glob("*.json")} - {"pii_fields"}
    assert team == set(SUPPORTED_TYPES)                              # 21 loại nhóm 4 = 21 loại sản phẩm
    for dt in SUPPORTED_TYPES:
        assert (SCHEMA_DIR / f"{dt}.json").read_bytes() == (TEAM_SCHEMA / f"{dt}.json").read_bytes()


def test_product_generic_rules_equal_team_frozen_copy():
    team = REPO / "teams" / "team4_extraction" / "methods" / "generic_date_rules.py"
    if not team.exists():
        pytest.skip("không có thư mục teams/")
    def patterns(src):
        return {k: re.findall(rf"^{k}[^=]*=.*?^\]", src, flags=re.S | re.M) for k in ("EXPIRY_PATTERNS", "FROM_PATTERNS", "SIGN_PATTERNS")}
    assert patterns(team.read_text(encoding="utf-8")) == patterns(Path(GR.__file__).read_text(encoding="utf-8"))


# ------------------------------------------------------------------ luật dự phòng
def test_generic_fallback_only_for_types_without_own_rules():
    hits = apply_rules_with_fallback("HD_VAN_CHUYEN", {1: HDVC})
    assert "HD_VAN_CHUYEN" not in RULES
    assert hits["hieu_luc_den"][0] == "31 tháng 12 năm 2025" and hits["ngay_ky"][0] == "05 tháng 03 năm 2024"
    assert apply_rules("HD_VAN_CHUYEN", {1: HDVC}) == {}                    # luật giai đoạn 2 (đóng băng) vẫn rỗng cho loại mới
    assert apply_rules_with_fallback("HD_VAN_CHUYEN", {1: HDVC}, generic=False) == {}
    assert apply_rules_with_fallback("LOAI_KHONG_CO", {1: HDVC}) == {}                   # loại không có schema: rỗng, không ném lỗi


def test_old_types_never_touch_generic_rules():
    for dt in PHASE2_TYPES:
        assert dt in RULES
        assert apply_rules_with_fallback(dt, {1: HDVC}) == apply_rules(dt, {1: HDVC})


def test_generic_rules_refuse_no_expiry_phrase():
    assert apply_rules_with_fallback("GPLX", {1: "Có giá trị không thời hạn, cấp ngày 01/02/2020"}).get("ngay_het_han", (None, None))[0] is None


# ------------------------------------------------------------------ quy tắc hạn theo loại
def test_expiry_rule_by_type():
    assert FE.DEFAULT_EXPIRY_RULE == "any-model=filename" and FE.GENERIC_EXPIRY_RULE == "regex=llm"
    assert all(expiry_rule_for(t) == "any-model=filename" for t in PHASE2_TYPES)
    assert all(expiry_rule_for(t) == "regex=llm" for t in PHASE3_TYPES)
    assert expiry_rule_for("HD_VAN_CHUYEN", "regex") == "regex"          # đặt tường minh thì ép mọi loại


def test_new_type_accepts_expiry_when_regex_and_llm_agree_and_records_rule():
    r = extract_fields(sl(HDVC), "HD_VAN_CHUYEN", config=ExtractConfig(auto_accept_expiry=True), llm_client=FakeLlm(hieu_luc_den="31/12/2025"))
    assert r.status == "ok"
    assert r.entity_dict["hieu_luc_den"] == "2025-12-31"
    assert r.entity_dict["_expiry"] == {"hieu_luc_den": "accepted"} and r.entity_dict["_expiry_rule"] == "regex=llm"
    assert r.entity_dict["hieu_luc_tu"] is None or isinstance(r.entity_dict["hieu_luc_tu"], str)


def test_new_type_refuses_on_disagreement_and_ignores_lone_filename():
    r = extract_fields(sl(HDVC), "HD_VAN_CHUYEN", config=ExtractConfig(auto_accept_expiry=True), llm_client=FakeLlm(hieu_luc_den="30/12/2025"), filename="HD-31.12.25.pdf")
    assert r.entity_dict["hieu_luc_den"] is None and r.entity_dict["_expiry"] == {"hieu_luc_den": "needs_review"}
    assert r.entity_dict["_expiry_suggestion"] == {"hieu_luc_den": "2025-12-31"}
    # quy tắc giai đoạn 2 trên loại cũ không đổi: tên tệp + một nguồn đồng thuận
    old = extract_fields(sl("Giấy chứng nhận này có giá trị đến hết ngày 09 tháng 4 năm 2024."), "GCN_DDK_BAN_LE_XD",
                         config=ExtractConfig(auto_accept_expiry=True), llm_client=FakeLlm(), filename="DDK-09.4.24.pdf")
    assert old.entity_dict["_expiry_rule"] == "any-model=filename" and old.entity_dict["ngay_het_han"] == "2024-04-09"


def test_no_expiry_is_reported_and_no_date_invented():
    r = extract_fields(sl(GPLX_NO_EXPIRY), "GPLX", llm_client=FakeLlm())
    assert r.entity_dict["ngay_het_han"] is None and r.entity_dict["_expiry"] == {"ngay_het_han": "no_expiry"}
    assert r.entity_dict["_expiry_suggestion"] == {}
    plain = extract_fields(sl("GIẤY PHÉP LÁI XE Hạng B2"), "GPLX", llm_client=FakeLlm())
    assert plain.entity_dict["_expiry"] == {"ngay_het_han": "not_found"}          # không ghi gì: not_found, khác no_expiry


# ------------------------------------------------------------------ PII
PII_BY_TYPE = {"GPLX": ("so_gplx", "ngay_sinh"), "CCCD": ("so_dinh_danh", "ngay_sinh")}


@pytest.mark.parametrize("dt,fields", PII_BY_TYPE.items())
def test_personal_ids_dropped_by_default_for_new_types(dt, fields):
    fake_num, fake_dob = "000000000001", "02/03/1980"
    llm = FakeLlm(**{fields[0]: fake_num, fields[1]: fake_dob, "ho_ten": "Nguyen Van Gia", "ngay_het_han": "01/01/2030"})
    text = f"{fake_num} sinh {fake_dob} giá trị đến 01/01/2030"
    res = extract_fields(sl(text), dt, llm_client=llm)
    assert not (set(fields) & set(llm.calls[0]["properties"]))                 # không hỏi LLM
    assert not (set(fields) & set(res.entity_dict))                            # không trả về
    assert res.entity_dict["dropped_pii_fields"] == sorted(fields)
    blob = res.model_dump_json()
    assert fake_num not in blob and "1980" not in blob
    on = extract_fields(sl(text), dt, config=ExtractConfig(auto_accept_expiry=True, store_personal_ids=True),
                        llm_client=FakeLlm(**{fields[0]: fake_num, fields[1]: fake_dob}))
    assert on.entity_dict[fields[1]] == "1980-03-02" and fields[0] in on.entity_dict


def test_pii_fields_of_every_new_type_follow_pii_file():
    from src.extraction.field_result import pii_category
    for dt in PHASE3_TYPES:
        names = {f["name"] for f in field_specs(dt)}
        for n in names:
            if pii_category(n) in ("personal_id", "birth_date"):
                llm = FakeLlm()
                res = extract_fields(sl("văn bản"), dt, llm_client=llm)
                assert n not in llm.calls[0]["properties"] and n in res.entity_dict["dropped_pii_fields"], (dt, n)
