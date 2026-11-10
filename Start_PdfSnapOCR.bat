@echo off
title PdfSnapOCR
cd /d "%~dp0"

echo ==================================================
echo   PdfSnapOCR - automatische Installation und Start
echo ==================================================
echo.

where py >nul 2>nul
if %errorlevel%==0 (
    set "PYTHON=py"
) else (
    where python >nul 2>nul
    if %errorlevel%==0 (
        set "PYTHON=python"
    ) else (
        echo Python wurde nicht gefunden.
        echo Bitte Python installieren: https://www.python.org/downloads/
        echo Waehrend der Installation "Add Python to PATH" aktivieren.
        pause
        exit /b 1
    )
)

if not exist ".venv" (
    echo Erstelle virtuelle Python-Umgebung ...
    %PYTHON% -m venv .venv
)

call ".venv\Scripts\activate.bat"

echo Aktualisiere pip ...
python -m pip install --upgrade pip

echo Installiere bzw. pruefe benoetigte Pakete ...
python -m pip install --upgrade mss pillow pymupdf keyboard ocrmypdf

echo.
echo Starte PdfSnapOCR ...
python PdfSnapOCR.py

pause
