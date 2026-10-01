@echo off
title Legal Bot - Panel de Control
echo ======================================================
echo  Iniciando Legal Bot - Panel de Control Web...
echo ======================================================

:: Buscar Python en el orden correcto
set PYTHON_EXE=

:: 1. Ruta directa verificada en este equipo
if exist "C:\Users\frand\AppData\Local\Python\bin\python.exe" (
    set PYTHON_EXE=C:\Users\frand\AppData\Local\Python\bin\python.exe
    goto :found
)

:: 2. Intentar alias "py" (Python Launcher para Windows)
where py >nul 2>&1
if %errorlevel% == 0 (
    set PYTHON_EXE=py
    goto :found
)

:: 3. Intentar "python" en PATH
where python >nul 2>&1
if %errorlevel% == 0 (
    for /f "delims=" %%i in ('where python 2^>nul') do (
        "%%i" --version >nul 2>&1
        if %errorlevel% == 0 (
            set PYTHON_EXE=%%i
            goto :found
        )
    )
)

:: 4. Otras rutas comunes
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe
    goto :found
)
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe
    goto :found
)
if exist "C:\Python312\python.exe" (
    set PYTHON_EXE=C:\Python312\python.exe
    goto :found
)

echo [ERROR] No se encontro Python. Instala Python desde https://python.org
pause
exit /b 1

:found
echo Python encontrado: %PYTHON_EXE%
echo Abriendo navegador en http://localhost:5000
echo ======================================================
cd /d "%~dp0"
"%PYTHON_EXE%" server.py
pause
