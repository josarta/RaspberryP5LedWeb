"""
app.py - Servidor WebSocket y API FastAPI para control de la Breakout Board Freenove & OLED
"""
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import socketio
from hardware_manager import HardwareManager

# Configurar Socket.IO con CORS total para WebSockets y HTTP Polling
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    logger=False,
    engineio_logger=False
)

app = FastAPI(title="Raspberry Pi Breakout Board 3D Controller")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

hw = HardwareManager()
telemetry_started = False

async def telemetry_loop():
    print("[Telemetry] Bucle de telemetría y OLED iniciado.")
    while True:
        try:
            await asyncio.sleep(1.2)
            hw.update_oled()
            await sio.emit("telemetry_update", hw.get_full_state())
        except Exception as e:
            print(f"[Telemetry Error] {e}")
            await asyncio.sleep(2)

@app.get("/api/status")
async def get_status():
    global telemetry_started
    if not telemetry_started:
        telemetry_started = True
        sio.start_background_task(telemetry_loop)
    return hw.get_full_state()

@sio.event
async def connect(sid, environ):
    global telemetry_started
    print(f"🟢 [WS] Cliente conectado con ID: {sid}")
    
    if not telemetry_started:
        telemetry_started = True
        sio.start_background_task(telemetry_loop)
        
    await sio.emit("state_snapshot", hw.get_full_state(), to=sid)

@sio.event
async def disconnect(sid):
    print(f"🔴 [WS] Cliente desconectado: {sid}")

@sio.event
async def toggle_led(sid, data):
    pin = data.get("pin")
    state = data.get("state", None)
    if pin is not None:
        new_state = hw.toggle_led(pin, forced_state=state)
        print(f"⚡ [GPIO] Pin BCM {pin} -> {'ON' if new_state else 'OFF'}")
        await sio.emit("state_update", hw.get_full_state())

@sio.event
async def set_all_leds(sid, data):
    state = bool(data.get("state", False))
    hw.set_all_leds(state)
    print(f"⚡ [GPIO] TODOS los pines -> {'ON' if state else 'OFF'}")
    await sio.emit("state_update", hw.get_full_state())

@sio.event
async def set_repeat_mode(sid, data):
    enabled = bool(data.get("enabled", False))
    hw.set_repeat_mode(enabled)
    print(f"🎬 [Video] Modo repetición evento -> {'ON' if enabled else 'OFF'}")
    await sio.emit("state_update", hw.get_full_state())

# Montar Socket.IO sobre la app ASGI
socket_app = socketio.ASGIApp(sio, app)

if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*55)
    print("🚀 Servidor IoT Raspberry Pi corriendo")
    print("👉 API REST:     http://localhost:8000/api/status")
    print("👉 WebSockets:   http://localhost:8000/socket.io/")
    print("="*55 + "\n")
    uvicorn.run(socket_app, host="0.0.0.0", port=8000, log_level="info")
