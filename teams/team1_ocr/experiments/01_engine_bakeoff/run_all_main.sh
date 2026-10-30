#!/bin/bash
# Bake-off chinh (dpi 200), chay song song 5 chuoi. Resume duoc (chay lai se bo qua trang da xong).
# Engine cham chay tren tap con: --stride N = moi N trang lay 1. Cac stride long nhau (1, 2, 4) de luon co tap chung.
cd "$(dirname "$0")"
VENV_MAIN=../../../../.venv/Scripts/python.exe
VENV_PADDLE=_cache/venv_paddle/Scripts/python.exe   # PaddleOCR o venv rieng (xem RESULTS.md)
mkdir -p _cache/logs
R() { py=$1; e=$2; th=$3; st=$4; for s in gold scan; do $py -X utf8 run_bakeoff.py --engine $e --set $s --dpi 200 --threads $th --stride $st; done; }
chain_rapid()  { R $VENV_MAIN rapid_v1 8 1; R $VENV_MAIN rapid_v5_latin 8 2; R $VENV_MAIN rapid_v6_multi 8 2; }
chain_seq()    { R $VENV_MAIN viet_seq2seq_cpu 6 1; }
chain_trans()  { R $VENV_MAIN viet_transformer_cpu 12 2; }
chain_easy()   { R $VENV_MAIN easyocr_cpu 8 4; }
chain_paddle() { R $VENV_PADDLE paddle 8 8; }   # rat cham tren CPU (~5-9 phut/trang) nen chi 1/8 so trang
chain_rapid  > _cache/logs/chain_rapid.log 2>&1 &
chain_seq    > _cache/logs/chain_viet_s.log 2>&1 &
chain_trans  > _cache/logs/chain_viet_t.log 2>&1 &
chain_easy   > _cache/logs/chain_easy.log 2>&1 &
chain_paddle > _cache/logs/chain_paddle.log 2>&1 &
wait
