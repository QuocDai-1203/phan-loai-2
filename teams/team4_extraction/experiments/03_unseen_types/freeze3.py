"""freeze3.py - Đóng băng cấu hình sau vòng cải tiến DEV, TRƯỚC khi chạy TEST+EXCLUDED (ghi `dev_selection3.json`, chỉ một lần).

    .venv\\Scripts\\python.exe -X utf8 teams\\team4_extraction\\experiments\\03_unseen_types\\freeze3.py

Ghi băm sha1 (10 ký tự) của: luật chung (`methods/generic_date_rules.py`), bộ bọc (`methods/regex_rules.py`), luật loại cũ
(`src/extraction/field_rules.py`), quy tắc hạn (`src/extraction/expiry_rules.py`), silver v2, nhãn `labels_v2.csv`; quy tắc tự nhận hạn
(chọn trên DEV v2: regex=llm; quy tắc giai đoạn 2 ghi kèm để so sánh). Từ chối ghi đè nếu tệp đã có (tránh chỉnh sau khi đã xem TEST).
"""

from __future__ import annotations

import datetime
import hashlib
import json

import common3 as C

OUT = C.HERE / "dev_selection3.json"


def sha(p) -> str:
    return hashlib.sha1(p.read_bytes()).hexdigest()[:10]


def main() -> int:
    if OUT.exists():
        raise SystemExit(f"{OUT.name} đã tồn tại: không ghi đè (cấu hình đã đóng băng).")
    sel = json.loads((C.M2 / "dev_selection.json").read_text(encoding="utf-8"))
    rec = {
        "frozen_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "note": "Một vòng cải tiến chung chỉ chỉnh trên DEV v2: luật ngày chung cho loại chưa có luật riêng (methods/generic_date_rules.py). "
                "LLM/VLM/prompt/quy tắc tự nhận hạn giữ nguyên như giai đoạn 2.",
        "expiry_rule": "regex=llm",
        "expiry_rule_phase2": sel["expiry_rule"],
        "expiry_rule_selection": "Chọn trên DEV v2 sau khi có luật chung: trong các quy tắc cần >= 2 nguồn đồng thuận (giữ tinh thần giai đoạn 2: không bao giờ một nguồn đơn), "
                                 "lấy quy tắc KHÔNG sai trường nào trên DEV và tự nhận nhiều nhất = regex=llm (35/45 đúng, 0 sai trên DEV). "
                                 "Quy tắc giai đoạn 2 (any-model=filename) vẫn được báo cạnh để so sánh.",
        "hashes": {
            "generic_date_rules.py": sha(C.TEAM / "methods" / "generic_date_rules.py"),
            "regex_rules.py": sha(C.TEAM / "methods" / "regex_rules.py"),
            "src/extraction/field_rules.py": sha(C.REPO / "src" / "extraction" / "field_rules.py"),
            "src/extraction/expiry_rules.py": sha(C.REPO / "src" / "extraction" / "expiry_rules.py"),
            "fields_silver_v2.jsonl": sha(C.GOLD_V2),
            "labels_v2.csv": sha(C.REPO / "data" / "labels_v2.csv"),
        },
        "dev_units": len(C.units_v2("DEV")),
    }
    OUT.write_text(json.dumps(rec, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("đã ghi", OUT, rec["hashes"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
