#!/bin/bash
# Bien the cau hinh cua VietOCR seq2seq (pad hop, chuan hoa nen, max_width). Chay tap con: gold stride 4, scan stride 2.
cd "$(dirname "$0")"
PY=../../../../.venv/Scripts/python.exe
V() { e=$1; $PY -X utf8 run_bakeoff.py --engine $e --set gold --dpi 200 --threads 6 --stride 4; $PY -X utf8 run_bakeoff.py --engine $e --set scan --dpi 200 --threads 6 --stride 2; }
V viet_seq2seq_pad > _cache/logs/var_pad.log 2>&1 &
V viet_seq2seq_pad_bg > _cache/logs/var_pad_bg.log 2>&1 &
wait
