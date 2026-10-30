"""smoke_test.py - Chạy thử từng phương pháp trên vài đơn vị DEV và báo có chạy được không (Nhóm 4).

    .venv\\Scripts\\python.exe -X utf8 teams\\team4_extraction\\methods\\smoke_test.py [--methods regex,filename,gliner,llm,vlm] [--source ocr_v2]
                                                                                  [--units id1,id2,id3]

Chỉ dùng đơn vị DEV (TEST không bao giờ được nạp ở đây). In: trạng thái, độ trễ, số trường khác null, giá trị chuẩn hóa của TRƯỜNG HẠN
(không phải dữ liệu cá nhân) — KHÔNG in giá trị của trường PII hay trường văn bản.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

TEAM = Path(__file__).resolve().parents[1]
REPO = TEAM.parents[1]
for _p in (str(TEAM), str(REPO)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from methods.common import Unit, load_units  # noqa: E402

# 3 đơn vị DEV mặc định, mỗi loại khác nhau (chọn cố định để so sánh được giữa các lần chạy)
DEFAULT_UNITS = ["73d0edb4d618_0", "dfc6b34476ae_0", "240854950618_0"]


def make(name: str, source: str):
    if name == "regex":
        from methods.regex_rules import RegexRules
        return RegexRules(source)
    if name == "filename":
        from methods.filename_date import FilenameDate
        return FilenameDate()
    if name == "gliner":
        from methods.gliner_fields import GlinerFields
        return GlinerFields(source)
    if name == "llm":
        from methods.local_llm_json import LocalLlmJson
        return LocalLlmJson(source)
    if name == "vlm":
        from methods.local_vlm_json import LocalVlmJson
        return LocalVlmJson()
    raise SystemExit(f"phương pháp không biết: {name}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--methods", default="regex,filename,gliner,llm,vlm")
    ap.add_argument("--source", default="ocr_v2")
    ap.add_argument("--units", default=",".join(DEFAULT_UNITS))
    a = ap.parse_args()
    dev = {u.unit_id: u for u in load_units("DEV")}
    units = [dev[x] for x in a.units.split(",") if x in dev]
    if len(units) != len(a.units.split(",")):
        raise SystemExit("có đơn vị không thuộc DEV hoặc không tồn tại — smoke test chỉ chạy trên DEV")
    ok_all = True
    for name in a.methods.split(","):
        try:
            m = make(name, a.source)
        except Exception as e:  # noqa: BLE001
            print(f"[{name}] KHÔNG KHỞI TẠO ĐƯỢC: {type(e).__name__}: {e}")
            ok_all = False
            continue
        for u in units:
            r = m.run(u)
            filled = sum(1 for v in r.fields.values() if v.get("value"))
            exp = {k: v["normalized"] for k, v in r.fields.items()
                   if v.get("value") and k in ("ngay_het_han", "hieu_luc_den")}
            print(f"[{name}] {u.unit_id} {u.doc_type}: status={r.status} latency={r.latency_ms:.0f}ms "
                  f"fields_filled={filled}/{len(r.fields)} expiry={exp or '-'}" + (f" ERROR={r.error[:300]}" if r.error else ""))
            ok_all &= r.status == "ok"
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
