#!/bin/bash
# Do toc do RIENG (khong chay song song voi viec khac): moi engine tren 5 trang scan (stride 7), 200 dpi, 16 luong.
# Luu y: GPU duoc tien trinh khac cua may dung chung (~70-80% util) nen so GPU la "duoi tai ngoai".
cd "$(dirname "$0")"
PY=../../../../.venv/Scripts/python.exe
mkdir -p _cache/logs
T() { py=$1; e=$2; st=${3:-7}; $py -X utf8 run_bakeoff.py --engine $e --set scan --dpi 200 --threads 16 --stride $st --tag timing; }
for e in rapid_v1 rapid_v5_latin rapid_v6_multi viet_seq2seq_cpu viet_seq2seq_bgauto viet_seq2seq viet_transformer_cpu viet_transformer easyocr_cpu easyocr; do
  T $PY $e
done > _cache/logs/timing.log 2>&1
T _cache/venv_paddle/Scripts/python.exe paddle 30 >> _cache/logs/timing.log 2>&1
echo TIMING_DONE >> _cache/logs/timing.log
