@echo off
cd /d "%~dp0"
set "PY=%~dp0runtime\python\python.exe"
if not exist "%PY%" set "PY=python"
set PYTHONUTF8=1

"%PY%" -c "import onnxruntime" >nul 2>&1
if errorlevel 1 (
  echo [First run] Installing system runtime, please click YES if a popup appears...
  "%~dp0runtime\vc_redist.x64.exe" /passive /norestart
  echo Runtime installed. Starting program...
)

"%PY%" -m tower2model run inputs -o outputs %*
pause