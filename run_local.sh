#!/bin/bash
# 내 컴퓨터에서 한 번 돌려보기: ./run_local.sh  →  site/index.html 을 브라우저로 열기
set -e
cd "$(dirname "$0")"
python3 argon/fetch.py
python3 argon/build.py
echo "완료 → site/index.html"
