@echo off
setlocal EnableExtensions
chcp 65001 >nul
title Ogrenci Not Takip - Baslat

rem Proje klasorune gec (bosluk ve Turkce karakterli yollar icin tirnakli).
cd /d "%~dp0"

set "VENV_DIR=%~dp0.venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"
set "STAMP=%VENV_DIR%\requirements.installed"
set "CHECK=import sys, tkinter, sqlite3; sys.exit(0 if sys.version_info >= (3, 11) else 1)"

rem 1) Var olan sanal ortam calisiyor mu? (baska bilgisayardan kopyalanmissa bozuk olabilir)
if exist "%VENV_PY%" (
    "%VENV_PY%" -c "%CHECK%" >nul 2>&1
    if errorlevel 1 (
        echo Mevcut .venv bu bilgisayarda calismiyor, yeniden olusturuluyor...
        rmdir /s /q "%VENV_DIR%"
    )
)

if exist "%VENV_PY%" goto install

rem 2) Python bul: once py baslaticisi, sonra PATH uzerindeki python.
set "PY_CMD="
py -3 -c "%CHECK%" >nul 2>&1
if not errorlevel 1 set "PY_CMD=py -3"
if not defined PY_CMD (
    python -c "%CHECK%" >nul 2>&1
    if not errorlevel 1 set "PY_CMD=python"
)
if not defined PY_CMD (
    echo.
    echo [HATA] Python 3.11 veya uzeri bulunamadi ^(tkinter ile birlikte^).
    echo https://www.python.org/downloads/ adresinden Python kurun ve
    echo kurulumda "Add python.exe to PATH" secenegini isaretleyin.
    echo.
    pause
    exit /b 1
)

echo Sanal ortam olusturuluyor: %PY_CMD%
%PY_CMD% -m venv "%VENV_DIR%"
if errorlevel 1 (
    echo [HATA] Sanal ortam olusturulamadi.
    pause
    exit /b 1
)

:install
rem 3) Gereksinimler: yalnizca requirements.txt degistiyse veya ilk kurulumda yuklenir.
if exist "%STAMP%" (
    fc /b "requirements.txt" "%STAMP%" >nul 2>&1
    if not errorlevel 1 goto run
)
echo Gereksinimler yukleniyor...
"%VENV_PY%" -m pip install --disable-pip-version-check -r "requirements.txt"
if errorlevel 1 (
    echo [HATA] Gereksinimler yuklenemedi. Internet baglantisini kontrol edin.
    pause
    exit /b 1
)
copy /y "requirements.txt" "%STAMP%" >nul

:run
rem 4) Uygulamayi demo veritabaniyla ac (data\demo.db). Ek parametreler aktarilir.
"%VENV_PY%" "%~dp0main.py" --demo %*
if errorlevel 1 pause
endlocal
