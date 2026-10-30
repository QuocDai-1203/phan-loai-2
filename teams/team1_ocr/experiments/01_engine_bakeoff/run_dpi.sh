#!/bin/bash
# So sanh 150 / 200 / 300 dpi cho engine tot nhat (VietOCR seq2seq). 200 dpi da co trong luot chinh.
cd "$(dirname "$0")"
PY=../../../../.venv/Scripts/python.exe
D() { d=$1; $PY -X utf8 run_bakeoff.py --engine viet_seq2seq_cpu --set gold --dpi $d --threads 6 --stride 4; $PY -X utf8 run_bakeoff.py --engine viet_seq2seq_cpu --set scan --dpi $d --threads 6 --stride 2; }
D 150 > _cache/logs/dpi150.log 2>&1 &
D 300 > _cache/logs/dpi300.log 2>&1 &
wait
