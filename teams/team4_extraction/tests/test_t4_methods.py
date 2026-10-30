"""Kiểm thử các phương pháp trích xuất (luật, tên tệp, GLiNER, LLM/VLM cục bộ) bằng dữ liệu tổng hợp và mô hình giả.
Không gọi Ollama thật, không tải GLiNER; không đọc nội dung TEST."""
import re

import pytest

from methods import common, gliner_fields, local_llm_json, local_vlm_json, ollama_client
from methods.common import MethodUnavailable, Unit
from methods.filename_date import FilenameDate, filename_date
from methods.gliner_fields import GlinerFields
from methods.local_llm_json import LocalLlmJson, fields_for, json_schema
from methods.regex_rules import RegexRules

GCN_TEXT = """UBND TỈNH KHÁNH HÒA CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
SỞ CÔNG THƯƠNG
Số: 83/GCNĐĐK-SCT Khánh Hoà, ngày 10 tháng 4 năm 2019
Cấp lần thứ nhất: ngày 10 tháng 4 năm 2019
GIÁM ĐỐC SỞ CÔNG THƯƠNG TỈNH KHÁNH HÒA
1. Tên cửa hàng bán lẻ xăng dầu: Tàu dầu Mẫu 01;
Địa chỉ: Cảng cá Mẫu, tỉnh Khánh Hòa.
Thuộc sở hữu doanh nghiệp: Công ty TNHH Xăng dầu Mẫu.
Mã số thuế: 4201578020
Điều 3. Giấy chứng nhận này có giá trị đến
hết ngày 09 tháng 4 năm 2024.
"""
CC_TEXT = """GIẤY CHỨNG NHẬN
Họ và tên: Nguyen Van Secret
Ngày Sinh: 22/01/1981
Nghề nghiệp: Thủ kho
Số: 51/2022-GCN
Bình Định, ngày 12 tháng 05 năm 2022
Tổ chức từ ngày: 06/05/2022 đến ngày 07/05/2022
Từ ngày 12 tháng 05 năm 2022 đến ngày 12 tháng 05 năm 2024
"""
HD_TEXT = """HỢP ĐỒNG MUA BÁN
Số: 04/2020/HĐMB-HH
Hôm nay, ngày 01 tháng 01 năm 2020, chúng tôi gồm:
BÊN A: CÔNG TY CỔ PHẦN BÁN HÀNG MẪU
Mã số thuế: 4100668616
BÊN B: CÔNG TY TNHH MUA HÀNG MẪU
Mã số thuế: 4101517546
Điều 1. Mặt hàng: xăng dầu các loại
Căn cứ Luật X có hiệu lực từ ngày 01/01/2017;
5.3 Hợp đồng này có hiệu lực từ ngày ký đến ngày 31/12/2020 hoặc hai bên hoàn thành
"""
PXK_TEXT = """PHIẾU XUẤT KHO THÀNH PHẨM
Ngày: 05/01/2026
Ký hiệu: BSR/PXK/DO
Số: 2600493
Bên nhận: Công ty Mẫu
Phương tiện: 77R-01942(77C-10179)
Tên thành phẩm - Quy cách
M3 thực tế
Nhiên liệu điêzen (DO 0,05S)
mức 2
241,746
38,415
31,743
39,020
"""


def unit(doc_type, **kw):
    return Unit(unit_id="u_0", doc_id="u", doc_type=doc_type, split="DEV", pages=[1], shown_pages=[1], relative_path="x/y.pdf", **kw)


class FakeText(RegexRules):
    """RegexRules với văn bản cho sẵn thay vì đọc data/ocr_v2.jsonl."""
    def __init__(self, text, **kw):
        super().__init__("ocr_v2", **kw)
        self._t = text

    def pages(self, u):
        return {1: self._t}


def val(res, name):
    return res[name]["normalized"]


def test_regex_gcn_fields_and_expiry_split_across_lines():
    r = FakeText(GCN_TEXT).extract(unit("GCN_DDK_BAN_LE_XD"))
    assert val(r, "ngay_het_han") == "2024-04-09"
    assert val(r, "ngay_cap") == "2019-04-10"
    assert val(r, "so_giay") == "83/GCNDDK-SCT"
    assert r["ten_cua_hang"]["value"] == "Tàu dầu Mẫu 01"
    assert "4201578020" in r["thuong_nhan_chu_so_huu"]["value"]
    assert set(r) == {f["name"] for f in common.field_specs("GCN_DDK_BAN_LE_XD")}      # đủ mọi trường, có khóa null


def test_regex_survives_ocr_diacritic_damage():
    damaged = GCN_TEXT.replace("hết ngày", "hêt ngay").replace("tháng", "thang").replace("năm", "nam")
    assert val(FakeText(damaged).extract(unit("GCN_DDK_BAN_LE_XD")), "ngay_het_han") == "2024-04-09"


def test_regex_does_not_invent_a_date_when_year_is_missing():
    cut = GCN_TEXT.replace("hết ngày 09 tháng 4 năm 2024.", "hết ngày 09 tháng 4 năm")
    r = FakeText(cut).extract(unit("GCN_DDK_BAN_LE_XD"))
    assert r["ngay_het_han"]["value"] is None          # null (not_found), không đoán năm


def test_regex_cc_picks_validity_range_not_course_dates_and_hides_birthdate():
    r = FakeText(CC_TEXT).extract(unit("CC_TAP_HUAN_VC_HNH"))
    assert val(r, "ngay_het_han") == "2024-05-12" and val(r, "hieu_luc_tu") == "2022-05-12"
    assert val(r, "ngay_cap") == "2022-05-12" and val(r, "so_gcn") == "51/2022-GCN"
    assert "nam_sinh" not in r                         # T5: ngày sinh bị bỏ khỏi đầu ra mặc định
    assert r["ho_ten"]["value"] == "Nguyen Van Secret"
    on = FakeText(CC_TEXT, store_personal_ids=True).extract(unit("CC_TAP_HUAN_VC_HNH"))
    assert val(on, "nam_sinh") == "1981-01-22"


def test_regex_hd_ignores_law_effective_date_and_maps_parties():
    r = FakeText(HD_TEXT).extract(unit("HD_MUA_BAN"))
    assert val(r, "hieu_luc_den") == "2020-12-31"
    assert val(r, "ngay_ky") == "2020-01-01" and val(r, "so_hop_dong") == "04/2020/HDMB-HH"
    assert "4100668616" in r["ben_ban"]["value"] and "4101517546" in r["ben_mua"]["value"]
    assert val(r, "hieu_luc_tu") == "2020-01-01"        # "có hiệu lực từ ngày ký" -> bằng ngày ký; "luật ... có hiệu lực từ ngày 01/01/2017" bị bỏ qua


def test_regex_hd_without_expiry_clause_gives_null():
    r = FakeText(HD_TEXT.replace("5.3 Hợp đồng này có hiệu lực từ ngày ký đến ngày 31/12/2020", "5.3 Các điều khoản khác")).extract(unit("HD_MUA_BAN"))
    assert r["hieu_luc_den"]["value"] is None


def test_regex_phieu_xuat_kho_table_quantities_use_vietnamese_decimal_comma():
    r = FakeText(PXK_TEXT).extract(unit("PHIEU_XUAT_KHO"))
    assert val(r, "so_phieu") == "2600493" and val(r, "ngay_xuat") == "2026-01-05"
    assert val(r, "so_luong_m3_15c") == "38.415" and val(r, "so_luong_tan") == "31.743" and val(r, "so_luong_m3_thuc_te") == "39.02"
    assert val(r, "bien_so_phuong_tien") == "77R0194277C10179"
    assert r["mat_hang"]["value"].startswith("Nhiên liệu điêzen")


def test_filename_date_baseline():
    assert filename_date("DDK-ABC-12.1.28.pdf") == "2028-01-12"
    assert filename_date("15. GCN VC HNH X (BC-12-5-24).pdf") == "2024-05-12"
    assert filename_date("10. Hop dong ABC.pdf") is None
    assert filename_date("GCN 8-2022.pdf") is None      # ngày không đầy đủ không được nhận
    u = Unit("a_0", "a", "GCN_DDK_BAN_LE_XD", "DEV", [1], [1], relative_path="d/DDK-X-12.1.28.pdf")
    r = FilenameDate().extract(u)
    assert r["ngay_het_han"]["normalized"] == "2028-01-12" and r["ngay_cap"]["value"] is None


def test_missing_text_is_skipped_not_empty_success():
    class NoText(RegexRules):
        def pages(self, u):
            return {}
    res = NoText("ocr_v2").run(unit("HD_MUA_BAN"))
    assert res.status == "skipped" and res.error and res.fields == {}


def test_invalid_source_rejected():
    with pytest.raises(ValueError):
        RegexRules("pdf_text_layer_typo")


# ---------------------------------------------------------------------------------------------- LLM cục bộ
class FakeChat:
    def __init__(self, data):
        self.data, self.calls = data, []

    def __call__(self, model, system, user, schema, images=None, options=None, **kw):
        self.calls.append({"model": model, "schema": schema, "user": user, "images": images})
        return {"data": self.data, "raw": "{}", "latency_ms": 1.0, "stats": {}, "cached": False}


def test_llm_schema_has_no_personal_ids_by_default_and_result_is_filtered(monkeypatch):
    fake = FakeChat({"so_gcn": "51/2022-GCN", "ho_ten": "Nguyen Van Secret", "nam_sinh": "1981", "nghe_nghiep": "Thủ kho",
                     "don_vi_cong_tac": None, "don_vi_cap": None, "ngay_cap": "ngày 12 tháng 05 năm 2022", "hieu_luc_tu": None,
                     "ngay_het_han": "12/5/24"})
    monkeypatch.setattr(local_llm_json, "chat_json", fake)

    class M(LocalLlmJson):
        def pages(self, u):
            return {1: CC_TEXT}

    u = unit("CC_TAP_HUAN_VC_HNH")
    res = M("ocr_v2").extract(u)
    sent = fake.calls[0]["schema"]
    assert "nam_sinh" not in sent["properties"] and "ho_ten" in sent["properties"]      # không hỏi thì không trích
    assert "nam_sinh" not in res                                                        # và lọc thêm một lần nữa
    assert res["ngay_het_han"]["normalized"] == "2024-05-12" and res["ngay_cap"]["normalized"] == "2022-05-12"
    assert sent["additionalProperties"] is False and sent["required"] == list(sent["properties"])
    # bật cờ thì mới hỏi/giữ
    fake2 = FakeChat({**fake.data})
    monkeypatch.setattr(local_llm_json, "chat_json", fake2)
    res2 = M("ocr_v2", store_personal_ids=True).extract(u)
    assert "nam_sinh" in fake2.calls[0]["schema"]["properties"] and res2["nam_sinh"]["normalized"] == "1981"


def test_llm_prompt_contains_schema_field_descriptions_and_text(monkeypatch):
    fake = FakeChat({f["name"]: None for f in common.field_specs("HD_MUA_BAN")})
    monkeypatch.setattr(local_llm_json, "chat_json", fake)

    class M(LocalLlmJson):
        def pages(self, u):
            return {1: HD_TEXT}

    M("ocr_v2").extract(unit("HD_MUA_BAN"))
    p = fake.calls[0]["user"]
    assert "hieu_luc_den" in p and "04/2020/HĐMB-HH" in p and "vai_tro_cong_ty" not in p      # trường dẫn xuất không được hỏi


def test_llm_json_schema_builder():
    s = json_schema(fields_for(unit("PHIEU_XUAT_KHO"), False))
    assert len(s["properties"]) == 14 and all(v["type"] == ["string", "null"] for v in s["properties"].values())


def test_ollama_down_is_an_explicit_error_not_empty_success(monkeypatch):
    import requests

    def boom(*a, **k):
        raise requests.ConnectionError("từ chối kết nối")

    monkeypatch.setattr(ollama_client.requests, "post", boom)
    monkeypatch.setattr(ollama_client, "CACHE", ollama_client.DiskCache(ollama_client.TEAM / "_cache" / "test_unused"))

    class M(LocalLlmJson):
        def pages(self, u):
            return {1: "văn bản riêng cho test lỗi kết nối 1234"}

    res = M("ocr_v2").run(unit("HD_MUA_BAN"))
    assert res.status == "error" and "Ollama" in res.error and res.fields == {}


def test_vlm_requires_rendered_images(monkeypatch):
    u = Unit("khong_co_anh_0", "khong_co_anh", "HD_MUA_BAN", "DEV", [1], [1])
    res = local_vlm_json.LocalVlmJson().run(u)
    assert res.status == "error" and "ảnh" in res.error


def test_vlm_sends_images_and_schema(monkeypatch, tmp_path):
    (tmp_path / "x_0").mkdir()
    for n in ("p01_a.png", "p01_b.png"):
        (tmp_path / "x_0" / n).write_bytes(b"\x89PNG fake")
    monkeypatch.setattr(local_vlm_json, "PAGES_DIR", tmp_path)
    fake = FakeChat({f["name"]: None for f in common.field_specs("HD_MUA_BAN")} | {"so_hop_dong": "04/2020"})
    monkeypatch.setattr(local_vlm_json, "chat_json", fake)
    r = local_vlm_json.LocalVlmJson().extract(Unit("x_0", "x", "HD_MUA_BAN", "DEV", [1], [1]))
    assert len(fake.calls[0]["images"]) == 2 and r["so_hop_dong"]["value"] == "04/2020"


# ---------------------------------------------------------------------------------------------- GLiNER
class FakeGliner:
    """Giả lập GLiNER: nhận các chuỗi 'ngày D tháng M năm Y' làm thực thể 'ngày'; ghi lại văn bản đã nhận."""
    def __init__(self):
        self.seen = []

    def predict_entities(self, text, labels, threshold):
        self.seen.append(text)
        out = []
        for m in re.finditer(r"ngày \d{1,2} tháng \d{1,2} năm \d{4}", text):
            out.append({"label": "ngày", "text": m.group(0), "start": m.start(), "end": m.end(), "score": 0.8})
        return out


def test_gliner_assigns_date_by_left_keyword_and_reads_beyond_first_4000_chars():
    filler = "Điều khoản chung không liên quan. " * 300          # ~10 000 ký tự
    text = GCN_TEXT.split("Điều 3.")[0] + filler + "Điều 3. Giấy chứng nhận này có giá trị đến\nhết ngày 09 tháng 4 năm 2024.\n"
    fake = FakeGliner()

    class M(GlinerFields):
        def pages(self, u):
            return {1: text}

    r = M("ocr_v2", model=fake).extract(unit("GCN_DDK_BAN_LE_XD"))
    assert r["ngay_het_han"]["normalized"] == "2024-04-09"         # nằm sau ký tự 10 000: bản gốc "4000 ký tự đầu" bỏ sót
    assert r["ngay_cap"]["normalized"] == "2019-04-10"             # ngày cấp có dấu phẩy ngay trước, KHÔNG bị nhầm là hạn
    assert all(len(t) <= 900 for t in fake.seen) and len(fake.seen) <= common.MAX_WINDOWS
    assert r["so_giay"]["value"] is None                           # GLiNER không có nhãn số hiệu: null có chủ ý


def test_gliner_model_load_failure_is_explicit(monkeypatch):
    def fail(name=gliner_fields.MODEL_NAME):
        raise MethodUnavailable("Không nạp được GLiNER 'x': OSError: không có mạng")

    monkeypatch.setattr(gliner_fields, "load_gliner_cpu", fail)

    class M(GlinerFields):
        def pages(self, u):
            return {1: GCN_TEXT}

    res = M("ocr_v2").run(unit("GCN_DDK_BAN_LE_XD"))
    assert res.status == "error" and "Không nạp được GLiNER" in res.error


def test_build_windows_caps_and_centres_on_anchors():
    t = "x " * 6000 + "có giá trị đến hết ngày 01/01/2030" + " y" * 6000
    wins = common.build_windows({3: t})
    assert any(p == 3 and a <= t.index("hết ngày") < b for p, a, b in wins)
    assert all(b - a <= common.WIN_MAX for _p, a, b in wins) and len(wins) <= common.MAX_WINDOWS
