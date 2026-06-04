@echo off
setlocal EnableExtensions
set "APP_DIR=%~dp0app"
if not exist "%APP_DIR%" (
  echo [ERROR] App folder not found: %APP_DIR%
  pause
  exit /b 1
)
cd /d "%APP_DIR%"

if exist ".env" (
  for /f "usebackq tokens=1,* delims==" %%A in (`findstr /R "^[A-Za-z_][A-Za-z0-9_]*=" ".env"`) do (
    set "%%A=%%B"
  )
) else (
  echo [INFO] .env file not found. Copy .env.example to .env and set OPENAI_API_KEY or ANTHROPIC_API_KEY.
)
if "%OPENAI_API_KEY%"=="" if "%ANTHROPIC_API_KEY%"=="" (
  echo [WARN] AI API key is empty. Template analysis and DOCX output work, but AI writing/search/image quality will be limited.
)

if "%AUTO_WRITE_HOST%"=="" set "AUTO_WRITE_HOST=127.0.0.1"
if "%AUTO_WRITE_PORT%"=="" set "AUTO_WRITE_PORT=8765"

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
  set "CANDIDATE=%%P"
  echo %%P | find /I "WindowsApps" >nul
  if errorlevel 1 (
    set "PYTHON_EXE=%%P"
    goto :python_found
  )
)

if not defined PYTHON_EXE (
  python --version >nul 2>nul
  if errorlevel 1 (
    echo [ERROR] Python 3.11+ executable not found.
    echo [INFO] Install Python from https://www.python.org/downloads/windows/ and check "Add python.exe to PATH".
    pause
    exit /b 1
  )
  for /f "delims=" %%P in ('python -c "import sys; print(sys.executable)" 2^>nul') do (
    set "PYTHON_EXE=%%P"
    goto :python_found
  )
  echo [INFO] Python: python PATH alias
  start "Auto Write Server" /D "%APP_DIR%" cmd /k "python -m uvicorn auto_write.main:app --host %AUTO_WRITE_HOST% --port %AUTO_WRITE_PORT%"
  timeout /t 2 >nul
  start "" http://%AUTO_WRITE_HOST%:%AUTO_WRITE_PORT%
  exit /b 0
)

:python_found
echo [INFO] Python: %PYTHON_EXE%
start "Auto Write Server" /D "%APP_DIR%" "%PYTHON_EXE%" -m uvicorn auto_write.main:app --host %AUTO_WRITE_HOST% --port %AUTO_WRITE_PORT%
timeout /t 2 >nul
start "" http://%AUTO_WRITE_HOST%:%AUTO_WRITE_PORT%
