@echo off
setlocal
cd /d "%~dp0"
title ResearchLens launcher

echo ==========================================
echo  ResearchLens - local research assistant
echo ==========================================
echo.

set "PYTHON_EXE="
if exist ".venv\Scripts\python.exe" set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"

if not defined PYTHON_EXE (
    where python >nul 2>nul
    if not errorlevel 1 (
        python -c "import streamlit, pymupdf, faiss, sentence_transformers, transformers, sklearn" >nul 2>nul
        if not errorlevel 1 set "PYTHON_EXE=python"
    )
)

if not defined PYTHON_EXE (
    echo Creating the project Python environment...
    where py >nul 2>nul
    if not errorlevel 1 (
        py -3.11 -m venv .venv
        if errorlevel 1 python -m venv .venv
    ) else (
        python -m venv .venv
    )
    if errorlevel 1 goto :error
    set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
)

"%PYTHON_EXE%" -c "import streamlit, pymupdf, faiss, sentence_transformers, transformers, sklearn" >nul 2>nul
if errorlevel 1 (
    echo Installing ResearchLens dependencies. This can take several minutes...
    "%PYTHON_EXE%" -m pip install --upgrade pip
    if errorlevel 1 goto :error
    "%PYTHON_EXE%" -m pip install -r requirements.txt
    if errorlevel 1 goto :error
)

echo.
echo Starting ResearchLens. Keep the server window open while using the app.
echo.
start "ResearchLens server" "%PYTHON_EXE%" -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true
echo Waiting for the local server...
for /L %%i in (1,1,60) do (
    curl.exe -fsS http://127.0.0.1:8501/_stcore/health >nul 2>nul
    if not errorlevel 1 goto :openchat
    timeout /t 1 /nobreak >nul
)
echo.
echo The server did not respond. Check the separate ResearchLens server window for errors.
pause
goto :done

:openchat
start "" "http://localhost:8501/?page=assistant"
echo ResearchLens opened in your browser. Keep the server window open.
timeout /t 3 >nul
goto :done

:error
echo.
echo ResearchLens could not start. Check the error above and see README.md for setup help.
pause

:done
endlocal
