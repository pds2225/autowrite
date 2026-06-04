@echo off
setlocal EnableExtensions
cd /d "%~dp0"
git add app\auto_write\main.py app\auto_write\services\project_service.py app\auto_write\services\render_service.py app\auto_write\templates\index.html app\auto_write\templates\template_detail.html app\auto_write\templates\project_detail.html app\tests\test_psst_mapping.py
git commit -m "fix: block generate when template DOCX missing; show DOCX status on home"
git push -u origin HEAD
echo [INFO] EXIT_CODE=%ERRORLEVEL%
exit /b %ERRORLEVEL%
