@echo off
chcp 65001 >nul
echo [MarketGate 사업계획서 자동 주입기]
echo.

:: Python 설치 확인
python --version >nul 2>&1
if errorlevel 1 (
    echo Python이 설치되어 있지 않습니다. https://python.org 에서 설치하세요.
    pause
    exit /b 1
)

:: 패키지 설치
echo 필요 패키지 설치 중...
pip install -r requirements.txt -q

:: 주입 실행
echo.
echo 사업계획서 생성 중...
python inject.py --template templates/사업계획서_원본양식.docx --content examples/content_marketgate.json --output output/사업계획서_완성.docx

echo.
echo 완료! output 폴더를 확인하세요.
pause
