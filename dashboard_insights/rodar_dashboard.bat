@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo   Dashboard de Insights - Praias de SC
echo ============================================
where python >nul 2>nul
if errorlevel 1 (
  echo.
  echo [ERRO] Python nao encontrado.
  echo Instale em https://www.python.org/downloads/ e marque
  echo "Add Python to PATH" no instalador. Depois rode este arquivo de novo.
  echo.
  pause
  exit /b
)
echo Instalando dependencias (so demora na primeira vez)...
python -m pip install -r requirements.txt
echo.
echo Abrindo o app no navegador (http://localhost:8501)...
echo Para PARAR: feche esta janela preta.
echo.
python -m streamlit run app.py
pause
