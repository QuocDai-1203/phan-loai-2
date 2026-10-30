"""freeze.py - Đóng băng cấu hình chọn trên DEV vào `dev_selection.json` TRƯỚC khi chạy TEST (Nhóm 4, T4).

    .venv\\Scripts\\python.exe -X utf8 .../freeze.py [--production-rule "regex=llm"]

Đọc `results_DEV_all.json` (quy tắc từ chối chọn trên DEV), ghi băm của: luật regex (src/extraction/field_rules.py), prompt LLM/VLM, bộ chuẩn hóa,
đáp án silver tại thời điểm đóng băng, và danh sách cấu hình sẽ chấm trên TEST. Từ chối ghi đè nếu tệp đã tồn tại (đóng băng là một lần).
`production.expiry_rule` là quy tắc mà `src/extraction/field_extractor.py` dùng mặc định (test kiểm tra khớp).
"""
import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEAM = HERE.parents[1]
REPO = TEAM.parents[1]
sys.path.insert(0, str(REPO))


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--production-rule", default=None, help="mặc định = quy tắc chọn trên DEV")
    ap.add_argument("--note", default="")
    a = ap.parse_args()
    out = HERE / "dev_selection.json"
    if out.exists():
        raise SystemExit("dev_selection.json đã tồn tại: đóng băng chỉ một lần (xóa chỉ khi chấp nhận TEST đã bị nhìn thấy).")
    dev = json.loads((HERE / "results_DEV_all.json").read_text(encoding="utf-8"))
    from src.extraction import field_llm
    from methods import local_vlm_json  # noqa: F401  (đảm bảo import được)
    rule = a.production_rule or dev["chosen_expiry_rule"]
    sel = {
        "frozen_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "note": a.note,
        "tuned_on": "DEV (76 đơn vị); luật/prompt/ngưỡng KHÔNG được chỉnh sau khi xem TEST",
        "silver_sha_at_freeze": sha(TEAM / "gold" / "fields_silver_v1.jsonl"),
        "code_hashes": {"regex_rules": sha(REPO / "src" / "extraction" / "field_rules.py"), "normalize": sha(REPO / "src" / "extraction" / "normalize.py"),
                        "expiry_rules": sha(REPO / "src" / "extraction" / "expiry_rules.py"), "llm_prompt_module": sha(REPO / "src" / "extraction" / "field_llm.py"),
                        "methods_vlm": sha(TEAM / "methods" / "local_vlm_json.py"), "methods_llm": sha(TEAM / "methods" / "local_llm_json.py")},
        "prompts": {"llm_variant": "v1", "vlm_variant": "v1", "llm_fingerprint": field_llm.prompt_fingerprint(), "model": field_llm.MODEL,
                    "options": {"temperature": 0, "num_ctx_llm": 6144, "num_ctx_vlm": 12288, "num_predict": 900}},
        "expiry_rule_dev_choice": dev["chosen_expiry_rule"],
        "expiry_rule_dev_table": [{k: r[k] for k in ("rule", "n_emitted", "n_correct", "n_wrong", "n_spurious", "wrong_upper95")} for r in dev["abstention"]],
        "expiry_rule": rule,
        "production": {"pipeline": "regex -> llm (cascade) + expiry auto-accept rule", "expiry_rule": rule},
        "test_configs": list(dev["configs"].keys()),
        "gold_variants_reported": ["all", "trusted"],
    }
    out.write_text(json.dumps(sel, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("đã ghi", out, "| quy tắc hạn:", rule)
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(TEAM))
    sys.exit(main())
