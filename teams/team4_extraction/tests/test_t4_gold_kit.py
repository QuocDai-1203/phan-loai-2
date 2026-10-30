"""Kiểm thử bộ công cụ chú thích silver: chọn trang, chia lô, và (nếu đã sinh) tính toàn vẹn của units.csv, ảnh, lô."""
import csv
import json
import random
from collections import Counter
from pathlib import Path

import pytest

from gold import build_units as BU

GOLD = Path(__file__).resolve().parents[1] / "gold"
TYPES = ["GCN_DDK_BAN_LE_XD", "CC_TAP_HUAN_VC_HNH", "HD_MUA_BAN", "PHIEU_XUAT_KHO"]
HAVE = (GOLD / "units.csv").exists() and (GOLD / "batches_second_annotator.json").exists()
needs_kit = pytest.mark.skipif(not HAVE, reason="chưa chạy gold/build_units.py")


def test_parse_segments():
    assert BU.parse_segments("1-2:PHIEU_XUAT_KHO;3:CHUNG_THU_CHAT_LUONG;5:BB_LAY_MAU") == [
        ([1, 2], "PHIEU_XUAT_KHO"), ([3], "CHUNG_THU_CHAT_LUONG"), ([5], "BB_LAY_MAU")]
    assert BU.parse_segments("") == []


def test_choose_pages_short_units_show_everything():
    assert BU.choose_pages([1, 2, 3, 4], {}) == [1, 2, 3, 4]
    assert BU.choose_pages([7], {}) == [7]


def test_choose_pages_long_unit_first2_keywords_last_cap6():
    pages = list(range(1, 11))
    texts = {p: "nội dung không liên quan" for p in pages}
    texts[5] = "Hợp đồng CÓ HIỆU LỰC từ ngày ký"          # khớp không phân biệt hoa/thường
    texts[7] = "Thời han của giấy"                           # 'han' không dấu + lỗi dấu OCR vẫn khớp 'thoi han'
    assert BU.choose_pages(pages, texts) == [1, 2, 5, 7, 10]
    many = {p: "có giá trị đến hết ngày " * p for p in pages}   # rất nhiều trang khớp: vẫn tối đa 6, ưu tiên trang nhiều lần khớp nhất
    chosen = BU.choose_pages(pages, many)
    assert len(chosen) == 6 and chosen[:2] == [1, 2] and 10 in chosen and 9 in chosen


def test_interleave_batches_respects_limit_and_mixes_types():
    units = [{"unit_id": f"{t}{i}", "doc_type": t, "n_images": 4 + (i % 3)} for t in TYPES for i in range(10)]
    batches = BU.interleave_batches(units, random.Random(1), limit=24)
    assert sum(len(b) for b in batches) == len(units)
    assert all(sum(u["n_images"] for u in b) <= 24 for b in batches)
    assert all(len({u["doc_type"] for u in b}) >= 2 for b in batches[:-1])


# --------------------------------------------------------------------------- sản phẩm thật
def read_units():
    with open(GOLD / "units.csv", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


@needs_kit
def test_units_cover_every_unique_doc_of_the_four_types():
    rows = read_units()
    assert len(rows) == len({r["unit_id"] for r in rows})
    per_type = Counter(r["doc_type"] for r in rows)
    assert per_type == {"GCN_DDK_BAN_LE_XD": 27, "CC_TAP_HUAN_VC_HNH": 24, "HD_MUA_BAN": 32, "PHIEU_XUAT_KHO": 21}
    assert Counter(r["split"] for r in rows if r["composite"] == "1") == {"EXCLUDED": 6}      # đơn vị từ tệp ghép
    assert {r["split"] for r in rows if r["composite"] == "0"} <= {"DEV", "TEST"}
    # không có bản sao (is_duplicate_of) lọt vào
    labels = {r["doc_id"]: r for r in csv.DictReader(open(BU.DATA / "labels_v2.csv", encoding="utf-8-sig", newline=""))}
    assert all(labels[r["doc_id"]]["is_duplicate_of"] == "" for r in rows)


@needs_kit
def test_shown_pages_rule_and_images_exist():
    have_images = (GOLD / "pages").is_dir()     # ảnh trang không commit (sinh lại bằng build_units.py)
    for r in read_units():
        pages = [int(x) for x in r["pages"].split(";")]
        shown = [int(x) for x in r["shown_pages"].split(";")]
        assert set(shown) <= set(pages) and shown == sorted(shown)
        if len(pages) <= 4:
            assert shown == pages
        else:
            assert len(shown) <= 6 and shown[:2] == pages[:2] and pages[-1] in shown
        if not have_images:
            continue
        imgs = sorted((GOLD / "pages" / r["unit_id"]).glob("p*.png"))
        assert len(imgs) == int(r["n_images"]) >= len(shown)
        got_pages = {int(p.name[1:3]) for p in imgs}
        assert got_pages == set(shown)


@needs_kit
def test_images_are_not_larger_than_1600px():
    from PIL import Image
    for p in list((GOLD / "pages").glob("*/p*.png"))[:60]:
        assert max(Image.open(p).size) <= 1600


def load_batches(path):
    j = json.loads(path.read_text(encoding="utf-8"))
    return j["batches"] if "batches" in j else [j]


@needs_kit
def test_first_annotator_batches_cover_all_units_once_with_at_most_24_images():
    seen = Counter()
    for p in sorted((GOLD / "batches").glob("batch_*.json")):
        (b,) = load_batches(p)
        assert b["n_images"] == sum(len(u["images"]) for u in b["units"]) <= 24
        for u in b["units"]:
            seen[u["unit_id"]] += 1
            assert Path(u["schema_path"]).exists() and Path(u["schema_path"]).is_absolute()
            assert all(Path(i["path"]).is_absolute() and Path(i["path"]).exists() for i in u["images"])
    assert set(seen) == {r["unit_id"] for r in read_units()} and set(seen.values()) == {1}


@needs_kit
def test_batches_mix_types():
    for p in sorted((GOLD / "batches").glob("batch_*.json"))[:-1]:
        (b,) = load_batches(p)
        assert len({u["doc_type"] for u in b["units"]}) >= 2


@needs_kit
def test_second_annotator_sample_is_stratified_and_covers_dev_and_test():
    rows = {r["unit_id"]: r for r in read_units()}
    batches = load_batches(GOLD / "batches_second_annotator.json")
    ids = [u["unit_id"] for b in batches for u in b["units"]]
    assert len(ids) == len(set(ids)) == 40
    assert Counter(rows[i]["doc_type"] for i in ids) == {t: 10 for t in TYPES}
    for t in TYPES:
        splits = {rows[i]["split"] for i in ids if rows[i]["doc_type"] == t}
        assert splits == {"DEV", "TEST"}, (t, splits)
    assert all(b["n_images"] <= 24 for b in batches)


def test_silver_prompt_has_the_hard_rules():
    t = (GOLD / "SILVER_PROMPT.md").read_text(encoding="utf-8")
    for must in ("QUY TẮC DỪNG", "Không bao giờ đoán", "tên tệp", "tối đa 12 từ", "silver_raw/<annotator>/<unit_id>.json",
                 "DONE units=", "withhold_value", "illegible", "under_stamp", "Read"):
        assert must in t, must
