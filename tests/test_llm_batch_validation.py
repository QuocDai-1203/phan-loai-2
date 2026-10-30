"""Kiểm thử T6: teams/team1_ocr/experiments/03_llm_silver/validate_batch.py và cổng kiểm lô của scripts/assemble_llm_ocr.py.

Không PDF, không OCR thật: truy cập text layer và OCR độc lập được thay bằng từ điển trong bộ nhớ."""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


vb = _load("validate_batch_under_test", ROOT / "teams/team1_ocr/experiments/03_llm_silver/validate_batch.py")
asm = _load("assemble_llm_ocr_under_test", ROOT / "scripts/assemble_llm_ocr.py")

KNOWN = ["Công ty cổ phần thương mại dịch vụ Hiệp Hòa phiếu xuất kho số {i} hàng hóa xăng dầu diezen {i}",
         "Giấy chứng nhận đủ điều kiện bán lẻ xăng dầu cấp lần thứ {i} tại tỉnh Bình Định ngày {i}",
         "Biên bản giao nhận hàng hóa giữa bên A và bên B lập thành hai bản số {i}"]
REAL = ["Hợp đồng mua bán hàng hóa số {i} giữa công ty thương mại dịch vụ và công ty vận tải điều khoản thanh toán giao hàng bên bán bên mua",
        "Quyết định thành lập tổ phòng cháy chữa cháy tại cửa hàng xăng dầu số {i} gồm các thành viên sau đây tổ trưởng tổ viên",
        "Giấy phép vận chuyển hàng nguy hiểm về cháy nổ cho phương tiện biển kiểm soát số {i} có giá trị đến ngày"]


def build(tmp, n_known=4, n_blank=2, n_real=8, blank_text="[trang trắng]", images="auto", corrupt_real=False, corrupt_known=False):
    """Dựng thư mục lô + manifest + từ điển truth/ocr. Trả về (batch_dir, items, truth, ref)."""
    items, truth, ocr = [], {}, {}
    for i in range(n_known):
        t = KNOWN[i % 3].format(i=i)
        iid = f"K{i}"
        items.append(dict(item_id=iid, kind="control_textlayer"))
        truth[iid] = t
        (tmp / f"{iid}.txt").write_text("không liên quan gì cả " * 5 if corrupt_known and i == 0 else t, encoding="utf-8")
    for i in range(n_blank):
        iid = f"B{i}"
        items.append(dict(item_id=iid, kind="control_blank"))
        (tmp / f"{iid}.txt").write_text(blank_text, encoding="utf-8")
    for i in range(n_real):
        t = REAL[i % 3].format(i=i)
        iid = f"{i:012x}_p1"
        items.append(dict(item_id=iid, kind="real", doc_id=f"{i:012x}", page="1"))
        ocr[iid] = t
        wrong = REAL[(i + 1) % 3].format(i=i + 50) if corrupt_real else t
        (tmp / f"{iid}.txt").write_text(wrong.replace("Hợp đồng", "[dấu: đỏ] Hợp đồng"), encoding="utf-8")
    if images == "auto":
        (tmp / vb.IMAGES_FILE).write_text(f"{len(items)}\n", encoding="utf-8")
    return tmp, items, (lambda it: truth[it["item_id"]]), (lambda it: ocr.get(it["item_id"]))


def run(tmp, items, truth, ref, images=None, **build_kw):
    n = images if images is not None else vb.read_images_loaded(tmp, None)
    return vb.validate_batch(tmp, items, vb.Thresholds(), truth, ref, n)


def test_good_batch_is_valid(tmp_path):
    d, items, truth, ref = build(tmp_path)
    rep = run(d, items, truth, ref)
    assert rep["status"] == "valid", rep["reasons"]
    assert rep["images_loaded"] == rep["images_expected"] == len(items)
    assert rep["known_summary"]["mean_bag_recall"] == pytest.approx(1.0)
    assert rep["cross_check_summary"]["median_recall"] > 0.9


def test_blank_page_that_comes_back_with_text_makes_the_batch_invalid(tmp_path):
    d, items, truth, ref = build(tmp_path)
    (d / "B1.txt").write_text("CÔNG TY CỔ PHẦN THƯƠNG MẠI DỊCH VỤ HIỆP HÒA phiếu giao hàng", encoding="utf-8")   # bịa chữ cho trang trắng
    rep = run(d, items, truth, ref)
    assert rep["status"] == "invalid"
    assert any("TRANG ma ra chu" in r for r in rep["reasons"])
    assert rep["blank"][1]["alnum_chars"] > vb.Thresholds().max_blank_chars


def test_markers_and_a_few_chars_do_not_count_as_text_on_blank_pages(tmp_path):
    d, items, truth, ref = build(tmp_path, blank_text="[trang trắng] [dấu: không] ...")
    assert run(d, items, truth, ref)["status"] == "valid"
    (d / "B0.txt").write_text("abcde", encoding="utf-8")        # 5 ký tự chữ > ngưỡng 4
    assert run(d, items, truth, ref)["status"] == "invalid"


def test_missing_or_wrong_image_count_makes_it_invalid(tmp_path):
    d, items, truth, ref = build(tmp_path, images=None)
    rep = run(d, items, truth, ref)
    assert rep["status"] == "invalid" and any("so anh nap duoc" in r for r in rep["reasons"])
    rep = run(d, items, truth, ref, images=len(items) - 3)       # nạp 3 ảnh ít hơn số mục: 3 mục không thể có thật
    assert rep["status"] == "invalid" and any("!=" in r for r in rep["reasons"])


def test_known_page_with_wrong_text_makes_it_invalid(tmp_path):
    d, items, truth, ref = build(tmp_path, corrupt_known=True)
    rep = run(d, items, truth, ref)
    assert rep["status"] == "invalid"
    assert any("trang da biet" in r for r in rep["reasons"]) and rep["known_summary"]["min_bag_recall"] < 0.5


def test_transcripts_that_do_not_match_the_independent_ocr_are_flagged(tmp_path):
    d, items, truth, ref = build(tmp_path, corrupt_real=True)
    rep = run(d, items, truth, ref)
    assert rep["status"] == "invalid"
    assert rep["cross_check_summary"]["median_recall"] < 0.75 and any("kiem cheo" in r for r in rep["reasons"])


def test_missing_transcript_and_extra_file_are_reported(tmp_path):
    d, items, truth, ref = build(tmp_path)
    (d / "K0.txt").unlink()
    (d / "Z9.txt").write_text("thừa", encoding="utf-8")
    rep = run(d, items, truth, ref)
    assert rep["status"] == "invalid" and rep["missing_transcripts"] == ["K0"] and rep["extra_transcripts"] == ["Z9"]


def test_batch_without_control_pages_cannot_be_valid(tmp_path):
    d, items, truth, ref = build(tmp_path, n_known=0, n_blank=0)
    rep = run(d, items, truth, ref)
    assert rep["status"] == "invalid"
    assert any("trang trang" in r for r in rep["reasons"]) and any("trang da biet" in r for r in rep["reasons"])


def test_large_batch_only_warns(tmp_path):
    d, items, truth, ref = build(tmp_path, n_real=62)
    rep = run(d, items, truth, ref)
    assert rep["status"] == "valid" and rep["warnings"]


def test_content_hash_is_identical_in_validator_and_assembler_and_ignores_underscore_files(tmp_path):
    d, *_ = build(tmp_path)
    h = vb.content_hash(d)
    assert h == asm.content_hash(d)
    (d / "_validation.json").write_text("{}", encoding="utf-8")
    assert vb.content_hash(d) == h
    (d / "K1.txt").write_text("sửa", encoding="utf-8")
    assert vb.content_hash(d) != h


def stamp(d, rep):
    (d / vb.STAMP_NAME).write_text(json.dumps(rep, ensure_ascii=False), encoding="utf-8")


def test_assembler_gate_refuses_unvalidated_invalid_and_modified_batches_and_accepts_valid(tmp_path):
    d, items, truth, ref = build(tmp_path)
    assert "chưa kiểm" in asm.check_batch_validated(d)                       # chưa có _validation.json
    bad = run(d, items, truth, ref, images=1)
    stamp(d, bad)
    assert "KHÔNG HỢP LỆ" in asm.check_batch_validated(d)
    good = run(d, items, truth, ref)
    stamp(d, good)
    assert asm.check_batch_validated(d) == ""
    (d / "K2.txt").write_text("đã sửa sau khi kiểm", encoding="utf-8")
    assert "đã đổi" in asm.check_batch_validated(d)


def _manifest(tmp_path):
    m = tmp_path / "manifest.csv"
    m.write_text("doc_id,relative_path,file_name,folder_label,page_count,exact_dup_group\n"
                 "aaaaaaaaaaaa,x/a.pdf,a.pdf,x,1,\n", encoding="utf-8")
    return m


def test_assembler_main_refuses_with_exit_2_and_writes_nothing(tmp_path, monkeypatch, capsys):
    pages = tmp_path / "pages"
    pages.mkdir()
    (pages / "aaaaaaaaaaaa_p1.txt").write_text("nội dung", encoding="utf-8")
    out = tmp_path / "out.jsonl"
    monkeypatch.setattr(sys, "argv", ["assemble", "--pages-dir", str(pages), "--manifest", str(_manifest(tmp_path)), "--out", str(out)])
    assert asm.main() == 2
    assert not out.exists() and "TỪ CHỐI" in capsys.readouterr().err


def test_assembler_skip_flag_needs_a_reason_and_is_logged(tmp_path, monkeypatch, capsys):
    pages = tmp_path / "pages"
    pages.mkdir()
    (pages / "aaaaaaaaaaaa_p1.txt").write_text("nội dung", encoding="utf-8")
    out = tmp_path / "out.jsonl"
    base = ["assemble", "--pages-dir", str(pages), "--manifest", str(_manifest(tmp_path)), "--out", str(out)]
    monkeypatch.setattr(sys, "argv", base + ["--skip-validation", "  "])
    assert asm.main() == 2 and not out.exists()                                      # lý do rỗng: vẫn từ chối
    monkeypatch.setattr(sys, "argv", base + ["--skip-validation", "lô cũ trước khi có validate_batch"])
    assert asm.main() == 0 and out.exists()
    log = (tmp_path / "_validation_skipped.log").read_text(encoding="utf-8").strip().splitlines()
    rec = json.loads(log[-1])
    assert rec["reason"] == "lô cũ trước khi có validate_batch" and rec["content_sha1"] == asm.content_hash(pages)
    assert "CẢNH BÁO" in capsys.readouterr().err


def test_assembler_main_accepts_a_validated_batch(tmp_path, monkeypatch):
    pages = tmp_path / "pages"
    pages.mkdir()
    (pages / "aaaaaaaaaaaa_p1.txt").write_text("nội dung", encoding="utf-8")
    stamp(pages, dict(status="valid", reasons=[], content_sha1=asm.content_hash(pages)))
    out = tmp_path / "out.jsonl"
    monkeypatch.setattr(sys, "argv", ["assemble", "--pages-dir", str(pages), "--manifest", str(_manifest(tmp_path)), "--out", str(out)])
    assert asm.main() == 0 and out.exists() and not (tmp_path / "_validation_skipped.log").exists()
