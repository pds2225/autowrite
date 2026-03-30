#!/bin/bash
echo "[MarketGate 사업계획서 자동 주입기]"
pip install -r requirements.txt -q
python inject.py --template templates/사업계획서_원본양식.docx --content examples/content_marketgate.json --output output/사업계획서_완성.docx
echo "완료! output 폴더를 확인하세요."
