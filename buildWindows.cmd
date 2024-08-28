@echo off
REM Exit the script if any command fails
setlocal enabledelayedexpansion
set "ERRORLEVEL=0"

REM 1. Create a .venv folder in the current folder
echo Creating .venv folder...
if not exist ".venv" mkdir ".venv"

REM 2. Create a Python virtual environment in that .venv folder
echo Creating virtual environment...
python -m venv .venv

REM 3. Activate the virtual environment
echo Activating virtual environment...
call .venv\Scripts\activate.bat

REM 4. Install PyInstaller in that virtual environment
echo Installing PyInstaller...
pip install pyinstaller

REM 5. Run PyInstaller with the specified .spec file
REM To handle prompts automatically, use `yes` if needed
echo Running PyInstaller...
if exist "dist\mybible-cli" (
    rmdir /S /Q "dist\mybible-cli"
)
if exist "build\mybible-cli" (
    rmdir /S /Q "build\mybible-cli"
)
echo Y | pyinstaller mybible-cli.spec

REM 6. Copy 'myfile.cmd' to .\dest\myscript\
echo Copying files to .\dist\mybible-cli\...
copy clip2bible.* dist\mybible-cli\

REM Deactivate the virtual environment
echo Deactivating virtual environment...
call .venv\Scripts\deactivate.bat

echo Script completed successfully.

REM Exit with the status of the last command
exit /b %ERRORLEVEL%