@echo off
title Backend IoT Raspberry Pi
echo === Iniciando Servidor IoT (Modo Local/Emulacion) ===
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)
python app.py
pause

