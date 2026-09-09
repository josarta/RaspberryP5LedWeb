"""
app.py - Servidor IoT & Aplicación Nativa de Pantalla para Raspberry Pi 5 / Windows
Ejecuta la API REST, WebSockets, Pantalla Nativa Fullscreen y actualización continua del OLED físico.
"""
import os
import sys
import time
import asyncio
import threading
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import socketio
import uvicorn

from hardware_manager import HardwareManager
from native_display import NativeDisplayApp

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MEDIA_DIR = os.path.join(BASE_DIR, "media")

# Configurar Socket.IO con CORS total
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    logger=False,
    engineio_logger=False
)

app = FastAPI(title="Raspberry Pi Breakout Board 3D & Native Screen Controller")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicializar Hardware y Pantalla Nativa Fullscreen
hw = HardwareManager()
is_linux = not sys.platform.startswith("win")
native_display = NativeDisplayApp(base_dir=BASE_DIR, fullscreen=is_linux)

# Vincular Gestor Multimedia con Socket.IO y Pantalla Nativa
hw.media_manager.set_sio(sio)
hw.media_manager.set_native_app(native_display)

# Servir carpeta de medios para clientes remotos
os.makedirs(MEDIA_DIR, exist_ok=True)
app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")

telemetry_started = False

async def ws_telemetry_loop():
    """Emite actualizaciones de telemetría a los clientes web conectados."""
    while True:
        try:
            await asyncio.sleep(1.0)
            await sio.emit("telemetry_update", hw.get_full_state())
        except Exception:
            await asyncio.sleep(2)

def hardware_telemetry_worker():
    """Bucle autónomo que actualiza el OLED físico y la pantalla nativa continuamente."""
    print("🟢 [HW] Bucle de telemetría y OLED físico iniciado.")
    while True:
        try:
            time.sleep(1.0)
            hw.update_oled()
            native_display.update_telemetry(hw.get_full_state())
        except Exception as e:
            time.sleep(2.0)

# Iniciar bucle de hardware permanente de inmediato
threading.Thread(target=hardware_telemetry_worker, daemon=True).start()

@app.get("/api/status")
async def get_status():
    global telemetry_started
    if not telemetry_started:
        telemetry_started = True
        sio.start_background_task(ws_telemetry_loop)
    return hw.get_full_state()

@app.get("/api/media/catalog")
async def get_media_catalog():
    """Devuelve el listado de videos, imágenes y pistas de audio disponibles."""
    return hw.media_manager.get_catalog()

@app.post("/api/media/show_image")
async def api_show_image(filename: str, caption: str = "", duration: float = 0):
    await hw.media_manager.show_custom_image(filename, caption, duration)
    return {"status": "ok", "image": filename}

@app.post("/api/media/show_video")
async def api_show_video(filename: str, loop: bool = False):
    await hw.media_manager.show_custom_video(filename, loop)
    return {"status": "ok", "video": filename}

@app.post("/api/media/volume")
async def api_set_volume(level: float):
    """Fija el nivel de volumen (0.0 a 1.0, o 0 a 100)."""
    vol = level / 100.0 if level > 1.0 else level
    actual = hw.media_manager.set_volume(vol)
    return {"status": "ok", "volume": actual, "percentage": int(actual * 100)}

@app.post("/api/wake")
async def api_wake():
    """Despierta la pantalla nativa del estado de reposo."""
    native_display.trigger_wake_up()
    return {"status": "ok", "action": "wake"}

@app.post("/api/touch/down")
async def api_touch_down():
    """Simula inicio de toque/presión en la pantalla (dispara bebe.mp4)."""
    native_display.trigger_touch_down()
    return {"status": "ok", "touch": "down"}

@app.post("/api/touch/up")
async def api_touch_up():
    """Simula fin de toque en la pantalla (retorna tras min 2s)."""
    native_display.trigger_touch_up()
    return {"status": "ok", "touch": "up"}

# ==============================================================================
# EVENTOS WEBSOCKET SOCKET.IO
# ==============================================================================

@sio.event
async def connect(sid, environ):
    global telemetry_started
    print(f"🟢 [WS] Cliente conectado: {sid}")
    
    if not telemetry_started:
        telemetry_started = True
        sio.start_background_task(ws_telemetry_loop)
        
    await sio.emit("state_snapshot", hw.get_full_state(), to=sid)

@sio.event
async def disconnect(sid):
    print(f"🔴 [WS] Cliente desconectado: {sid}")

@sio.event
async def wake_up(sid, data=None):
    native_display.trigger_wake_up()

@sio.event
async def touch_event(sid, data):
    action = data.get("action", "down")
    if action == "down":
        native_display.trigger_touch_down()
    elif action == "up":
        native_display.trigger_touch_up()

@sio.event
async def toggle_led(sid, data):
    pin = data.get("pin")
    state = data.get("state", None)
    if pin is not None:
        new_state = hw.toggle_led(pin, forced_state=state)
        print(f"⚡ [GPIO] Pin BCM {pin} -> {'ON' if new_state else 'OFF'}")
        
        # Disparar video del evento en la pantalla nativa
        if new_state:
            await hw.media_manager.trigger_led_on(pin)
        else:
            await hw.media_manager.trigger_led_off(pin)

        await sio.emit("state_update", hw.get_full_state())

@sio.event
async def set_all_leds(sid, data):
    state = bool(data.get("state", False))
    hw.set_all_leds(state)
    print(f"⚡ [GPIO] TODOS los pines -> {'ON' if state else 'OFF'}")
    
    if state:
        await hw.media_manager.trigger_led_on(None)
    else:
        await hw.media_manager.trigger_led_off(None)

    await sio.emit("state_update", hw.get_full_state())

@sio.event
async def set_repeat_mode(sid, data):
    enabled = bool(data.get("enabled", False))
    hw.set_repeat_mode(enabled)
    print(f"🎬 [Media] Modo repetición evento -> {'ON' if enabled else 'OFF'}")
    await sio.emit("state_update", hw.get_full_state())

@sio.event
async def set_volume(sid, data):
    level = float(data.get("level", 0.6))
    vol = level / 100.0 if level > 1.0 else level
    hw.media_manager.set_volume(vol)
    print(f"🔊 [Audio] Volumen ajustado a: {int(vol * 100)}%")

@sio.event
async def trigger_display_event(sid, data):
    event_type = data.get("type", "PLAY_IDLE")
    event_data = data.get("data", {})
    await hw.media_manager.emit_display_event(event_type, event_data)

# Montar Socket.IO sobre la app ASGI
socket_app = socketio.ASGIApp(sio, app)

def run_uvicorn_server():
    """Ejecuta el servidor FastAPI y Socket.IO en un hilo en segundo plano."""
    config = uvicorn.Config(
        app=socket_app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        access_log=False
    )
    server = uvicorn.Server(config)
    server.run()

if __name__ == "__main__":
    print("\n" + "="*65)
    print("🚀 Servidor IoT & Pantalla Nativa Raspberry Pi 5")
    print("👉 Servidor API & WebSockets: http://localhost:8000/api/status")
    print("👉 Catálogo Multimedia:       http://localhost:8000/api/media/catalog")
    print("👉 Atajos en Pantalla:        [F] Pantalla Completa | [H] HUD | [M] Audio | [R] Loader | [ESC] Salir")
    print("="*65 + "\n")

    # Iniciar servidor FastAPI en hilo secundario
    server_thread = threading.Thread(target=run_uvicorn_server, daemon=True)
    server_thread.start()

    # Iniciar la aplicación gráfica nativa en el hilo principal
    try:
        native_display.run()
    except KeyboardInterrupt:
        print("\n🛑 Deteniendo servidor y pantalla...")
        sys.exit(0)
