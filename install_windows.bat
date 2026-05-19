@echo off
:: OpenClaw Killswitch — Windows Installer
:: Run as Administrator

setlocal EnableDelayedExpansion

echo =========================================
echo  OpenClaw USB Killswitch — Windows Setup
echo =========================================
echo.

:: Check admin rights
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Please run this script as Administrator.
    pause & exit /b 1
)

:: Check Python
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Python is not installed. Install from https://python.org
    pause & exit /b 1
)

set INSTALL_DIR=%ProgramData%\OpenClawKillswitch
set SCRIPT_DIR=%~dp0

echo [1/4] Creating install directory: %INSTALL_DIR%
mkdir "%INSTALL_DIR%" 2>nul
copy "%SCRIPT_DIR%killswitch.py" "%INSTALL_DIR%\killswitch.py" >nul
echo      Done.

echo [2/4] Creating auto-start scheduled task...
schtasks /create /tn "OpenClawKillswitch" /tr "python \"%INSTALL_DIR%\killswitch.py\"" ^
    /sc ONLOGON /ru SYSTEM /rl HIGHEST /f >nul
echo      Done.

echo [3/4] Creating manual-fire shortcut on Desktop...
set SHORTCUT=%USERPROFILE%\Desktop\FIRE_KILLSWITCH.bat
(
echo @echo off
echo echo Firing OpenClaw killswitch manually...
echo python "%INSTALL_DIR%\killswitch.py" --fire-now
) > "%SHORTCUT%"
echo      Done.

echo [4/4] Starting killswitch now...
start /min python "%INSTALL_DIR%\killswitch.py"
echo      Done.

echo.
echo ✅ Killswitch installed and running!
echo    Log file: %%USERPROFILE%%\.openclaw_killswitch.log
echo.
pause
