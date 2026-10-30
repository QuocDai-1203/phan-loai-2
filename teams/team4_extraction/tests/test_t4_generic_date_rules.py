"""Test luật ngày chung cho loại chưa có luật riêng (giai đoạn 3, `methods/generic_date_rules.py`) trên văn bản giả (không PII).

Giữ hành vi v1: `RegexRules(generic=False)` (mặc định) không đổi; với `generic=True` loại có luật riêng (4 loại cũ) cũng không đổi.
"""

from __future__ import annotations

import sys
from pathlib import Path

TEAM = Path(__file__).resolve().parents[1]
REPO = TEAM.parents[1]
for p in (str(TEAM), str(REPO)):
    if p not in sys.path:
        sys.path.insert(0, p)

from methods.common import Unit  # noqa: E402
from methods.generic_date_rules import generic_rules  # noqa: E402
from methods.regex_rules import RegexRules  # noqa: E402
from src.extraction.field_rules import Doc  # noqa: E402

EXP = ["ngay_het_han"]


def hit(text: str, names=EXP):
    return generic_rules(names, Doc({1: text}))


def test_expiry_co_gia_tri_den_voi_nhan_tieng_anh():
    assert hit("Hạng/Class: C Có giá trị đến Expires: 12/08/2026 Họ tên")["ngay_het_han"][0] == "12/08/2026"
    assert hit("Có gia trị đến-01/06/2035 Date of expiry")["ngay_het_han"][0] == "01/06/2035"


def test_expiry_hop_dong_tu_ngay_ky_den():
    names = ["hieu_luc_den", "hieu_luc_tu"]
    r = hit("5.3 Hợp đồng này có hiệu lực từ ngày ký đến ngày 31/12/2022 hoặc hai bên hoàn tất", names)
    assert r["hieu_luc_den"][0] == "31/12/2022"
    r = hit("Hiệu lực từ ngày 01/01/2024 đến hết ngày 31/12/2026", names)
    assert r["hieu_luc_tu"][0] == "01/01/2024" and r["hieu_luc_den"][0] == "31/12/2026"


def test_expiry_bao_hiem_can_gio_di_kem():
    r = hit("Từ: 16 giờ 00, ngày 26/11/2023 Đến: 16 giờ 00, ngày 26/11/2024 Phạm vi", ["ngay_het_han", "hieu_luc_tu"])
    assert r["ngay_het_han"][0] == "26/11/2024" and r["hieu_luc_tu"][0] == "26/11/2023"


def test_khong_nhan_ky_hoc_la_han():
    # "từ ngày ... đến ngày ..." của khóa học (không có giờ) KHÔNG phải hạn
    assert hit("Thời gian học: Từ ngày 28/5/2022 Đến ngày 02/6/2022 Kết quả")["ngay_het_han"][0] is None


def test_khong_thoi_han_khong_bia_ngay():
    # "Không thời hạn" đứng giữa nhãn và một ngày khác: không được nhảy sang ngày cấp
    assert hit("Có giá trị đến: Không thời hạn Ngày cấp: 05/05/2019")["ngay_het_han"][0] is None


def test_ngay_ky_va_ngay_cap():
    r = hit("Hôm nay, ngày 21 tháng 11 năm 2023, tại", ["ngay_ky"])
    assert r["ngay_ky"][0] == "21 tháng 11 năm 2023"
    r = hit("Nội dung\nBình Định, ngày 06 tháng 04 năm 2021\nGiám đốc", ["ngay_cap"])
    assert r["ngay_cap"][0] == "06 tháng 04 năm 2021"


def _unit(doc_type: str) -> Unit:
    return Unit(unit_id="x_0", doc_id="x", doc_type=doc_type, split="DEV", pages=[1], shown_pages=[1])


def test_generic_flag_chi_ap_dung_cho_loai_chua_co_luat(monkeypatch):
    text = {1: "Có giá trị đến hết ngày 12 tháng 01 năm 2028. Bình Định, ngày 01 tháng 01 năm 2020"}
    m_default, m_generic = RegexRules(generic=False), RegexRules(generic=True)
    u_old, u_new = _unit("GCN_DDK_BAN_LE_XD"), _unit("GPLX")
    # loại cũ: hai chế độ cho cùng kết quả
    assert m_default._extract(u_old, text) == m_generic._extract(u_old, text)
    # loại mới: mặc định (v1) toàn null; generic=True điền hạn
    off = m_default._extract(u_new, text)
    on = m_generic._extract(u_new, text)
    assert all(v["value"] is None for v in off.values())
    assert on["ngay_het_han"]["normalized"] == "2028-01-12"
