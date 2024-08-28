@echo off
if not "%COMSPEC%"=="%SystemRoot%\system32\cmd.exe" (
    REM Re-run the script in cmd.exe
    "%SystemRoot%\system32\cmd.exe" /c "%~f0" %*
    exit /b
)
cd /d "%~dp0"
for /f "usebackq tokens=*" %%a in (`powershell -command "Get-Clipboard"`) do set clipboard_content=%%a

start /min cmd /c mybible-cli.exe -r "%clipboard_content%" --gui