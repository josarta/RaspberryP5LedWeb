# 🍓 Freenove Breakout Board & Raspberry Pi 5 - 3D IoT Digital Twin

Sistema integral de monitoreo y control en tiempo real para la **Freenove Breakout Board for Raspberry Pi (BCM Numbering v1.0)** con soporte para **todos los 28 GPIOs**, LEDs indicadores SMD y pantalla **OLED SSD1306 / SH1106 (I2C)**.

---

##  Arquitectura del Proyecto

```text
webled/
├── backend/
│   ├── app.py                  # Servidor WebSocket & API REST (FastAPI + Socket.IO)
│   ├── hardware_manager.py     # Controlador de 28 GPIOs físicos y OLED I2C (con auto-emulación)
│   ├── oled_renderer.py        # Generador de gráficos/texto monocromático 128x64 (Pillow)
│   ├── requirements.txt        # Dependencias de Python
│   ├── run.sh                  # Lanzador para Raspberry Pi (Linux)
│   └── run.bat                 # Lanzador para Windows (Dev)
└── frontend/
    ├── index.html              # HUD Glassmorphism 2D + Canvas 3D Three.js
    ├── package.json            # Dependencias Web (Three.js + Socket.IO Client)
    ├── vite.config.js          # Configuración del servidor Vite
    └── src/
        ├── main.js             # Entrada principal, animación 60 FPS y Raycasting 3D
        ├── network/
        │   └── SocketClient.js # Cliente WebSocket con reconexión automática y soporte de IP remota
        ├── scene/
        │   ├── BreakoutBoardMesh.js # Modelo 3D de la placa Freenove (40 terminales + LEDs SMD)
        │   ├── SceneManager.js      # Escena Three.js, Luces y OrbitControls amortiguados
        │   └── VirtualOLED.js       # Textura Canvas dinámica 128x64 para la OLED 3D
        └── ui/
            └── HudOverlay.js        # Panel HUD de control de pines, selector de IP y telemetría
```

---

##  Tabla de Conexiones de Hardware

### 1. Pantalla OLED I2C (0.96" / 1.3")
| Pin Pantalla OLED | Terminal Freenove Board | Pin Físico RPi 5 | Función |
| :--- | :--- | :--- | :--- |
| **GND** | **`GND`** | Pin 6 / 9 / 14 | Tierra común |
| **VCC / VDD** | **`+3V3`** | Pin 1 | Alimentación 3.3V |
| **SCL / SCK** | **`SCL1`** | Pin 5 (GPIO 3) | Reloj I2C-1 |
| **SDA** | **`SDA1`** | Pin 3 (GPIO 2) | Datos I2C-1 |

### 2. Mapeo de Terminales y LEDs
- **Columna Izquierda (Impares):** `+3V3`, `SDA1 (GPIO2)`, `SCL1 (GPIO3)`, `IO4`, `GND`, `IO17`, `IO27`, `IO22`, `+3V3`, `IO10`, `IO9`, `IO11`, `GND`, `IO0`, `IO5`, `IO6`, `IO13`, `IO19`, `IO26`, `GND`.
- **Columna Derecha (Pares):** `+5V`, `+5V`, `GND`, `IO14`, `IO15`, `IO18`, `GND`, `IO23`, `IO24`, `GND`, `IO25`, `IO8`, `IO7`, `IO1`, `GND`, `IO12`, `GND`, `IO16`, `IO20`, `IO21`.

---

## 🚀 Puesta en Marcha

### 1. En la Raspberry Pi (Backend)
```bash
cd backend
pip3 install -r requirements.txt --break-system-packages
python3 app.py
```
*(O ejecuta directamente `./run.sh`)*

### 2. En el Cliente Web (Frontend en PC o Pi)
```bash
cd frontend
npm install
npm run dev
```
1. Abre **`http://localhost:5173`** en el navegador.
2. Si el backend corre en otra máquina, ingresa la IP de la Raspberry Pi en la barra superior del HUD y presiona **`CONECTAR`**.
