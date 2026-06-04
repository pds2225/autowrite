@echo off
chcp 65001 >nul
setlocal EnableExtensions

echo ========================================
echo Auto Write 실행환경 점검
echo ========================================
echo.

set "ROOT_DIR=%~dp0"
set "APP_DIR=%ROOT_DIR%app"
set "REQ_FILE=%APP_DIR%\requirements.txt"

if not exist "%APP_DIR%" (
  echo [FAIL] app 폴더 없음: %APP_DIR%
  pause
  exit /b 1
) else (
  echo [OK] app 폴더 확인: %APP_DIR%
)

if not exist "%REQ_FILE%" (
  echo [FAIL] requirements.txt 없음: %REQ_FILE%
  pause
  exit /b 1
) else (
  echo [OK] requirements.txt 확인
)

set "PYTHON_EXE="
for %%P in (
  "%LocalAppData%\Programs\Python\Python313\python.exe"
  "%LocalAppData%\Programs\Python\Python312\python.exe"
  "%LocalAppData%\Programs\Python\Python311\python.exe"
  "%ProgramFiles%\Python313\python.exe"
  "%ProgramFiles%\Python312\python.exe"
  "%ProgramFiles%\Python311\python.exe"
) do (
  if exist "%%~fP" (
    set "PYTHON_EXE=%%~fP"
    goto :python_found
  )
)

for /f "delims=" %%P in ('where python 2^>nul') do (
  echo %%P | find /I "WindowsApps" >nul
  if errorlevel 1 (
    set "PYTHON_EXE=%%P"
    goto :python_found
  )
)

if not defined PYTHON_EXE (
  python --version >nul 2>nul
  if not errorlevel 1 (
    for /f "delims=" %%P in ('python -c "import sys; print(sys.executable)" 2^>nul') do (
      set "PYTHON_EXE=%%P"
      goto :python_found
    )
  )
  echo [FAIL] Python을 찾지 못했습니다.
  echo [조치] Python 3.11 이상 설치 후 setup.bat를 다시 실행하세요.
  pause
  exit /b 1
)

:python_found
echo [OK] Python 발견: %PYTHON_EXE%
"%PYTHON_EXE%" --version

echo.
echo [패키지 점검]
"%PYTHON_EXE%" -c "import fastapi, uvicorn, jinja2, docx, openai, httpx, pydantic, PIL, pypdf, olefile; print('[OK] 핵심 패키지 import 성공')"
if errorlevel 1 (
  echo [FAIL] 일부 패키지가 설치되지 않았습니다.
  echo [조치] setup.bat를 먼저 실행하세요.
  pause
  exit /b 1
)

echo.
echo [앱 import 점검]
cd /d "%APP_DIR%"
"%PYTHON_EXE%" -c "from auto_write.main import app; print('[OK] auto_write.main import 성공')"
if errorlevel 1 (
  echo [FAIL] Auto Write 앱 import 실패
  echo [조치] 위 오류 메시지를 복사해서 AI에게 전달하세요.
  pause
  exit /b 1
)

echo.
echo [포트 안내]
echo 기본 접속 주소: http://127.0.0.1:8765
echo 만약 실행 후 접속이 안 되면 다른 프로그램이 8765 포트를 사용 중일 수 있습니다.

echo.
echo ========================================
echo 점검 완료: launch.bat 실행 가능 상태로 보입니다.
echo ========================================
echo.
pause
