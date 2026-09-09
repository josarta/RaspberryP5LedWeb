#!/bin/bash
echo "=== Iniciando Servidor IoT Raspberry Pi 5 ==="
if [ -d "venv" ]; then
    source venv/bin/activate
fi
python3 app.py

