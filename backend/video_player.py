"""
video_player.py - Controlador de Video Profesional con Servidor IPC mpv
Garantiza transiciones con fondo negro sin parpadeos, audio al 100% desmuteado y control de pantalla DSI.
"""
import os
import sys
import json
import time
import socket
import shutil
import threading
import subprocess

class FullscreenVideoPlayer:
    def __init__(self, video_dir=None):
        if video_dir is None:
            self.video_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "videos")
        else:
            self.video_dir = video_dir

        os.makedirs(self.video_dir, exist_ok=True)

        self.idle_video = os.path.join(self.video_dir, "idle.mp4")
        self.on_video = os.path.join(self.video_dir, "led_on.mp4")
        self.off_video = os.path.join(self.video_dir, "led_off.mp4")

        self.ipc_socket_path = "/tmp/mpv_dsi_socket" if not sys.platform.startswith('win') else r"\\.\pipe\mpv_dsi_socket"
        self.mpv_process = None
        self.current_state = "IDLE"  # IDLE, PLAYING_ON, PLAYING_OFF
        self.repeat_mode = False
        self.lock = threading.Lock()
        
        self.env = self._build_display_env()
        self._ensure_sample_videos()

        # Iniciar el proceso persistente de mpv
        threading.Thread(target=self._start_mpv_daemon, daemon=True).start()

    def _build_display_env(self):
        env = os.environ.copy()
        if not sys.platform.startswith('win'):
            if "DISPLAY" not in env:
                env["DISPLAY"] = ":0"
            if "WAYLAND_DISPLAY" not in env:
                env["WAYLAND_DISPLAY"] = "wayland-0"
            if "XDG_RUNTIME_DIR" not in env:
                uid = os.getuid() if hasattr(os, "getuid") else 1000
                env["XDG_RUNTIME_DIR"] = f"/run/user/{uid}"
        return env

    def _ensure_sample_videos(self):
        readme_path = os.path.join(self.video_dir, "README_VIDEOS.txt")
        if not os.path.exists(readme_path):
            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(
                    "Videos requeridos:\n"
                    "1. idle.mp4     -> Bucle de reposo continuo.\n"
                    "2. led_on.mp4   -> Video de encendido con audio.\n"
                    "3. led_off.mp4  -> Video de apagado con audio.\n"
                )

    def _start_mpv_daemon(self):
        """Lanza mpv en modo daemon persistente con fondo negro y servidor IPC."""
        if not shutil.which("mpv"):
            print("⚠️ [VideoPlayer] mpv no encontrado. Ejecuta: sudo apt install -y mpv")
            return

        # Eliminar socket anterior si existe
        if not sys.platform.startswith('win') and os.path.exists(self.ipc_socket_path):
            try:
                os.remove(self.ipc_socket_path)
            except Exception:
                pass

        cmd = [
            "mpv",
            "--idle=yes",                         # Mantiene el proceso vivo con fondo negro
            "--force-window=yes",
            "--background-color=#000000",         # Fondo negro puro para transiciones sin destellos
            "--fs",                               # Pantalla completa
            "--screen=0",                         # Pantalla DSI principal
            "--fs-screen=0",
            "--ontop",                            # Siempre al frente
            "--no-osc",                           # Sin controles en pantalla
            "--no-osd-bar",                       # Sin barra de progreso OSD
            "--cursor-autohide=always",           # Ocultar cursor
            "--volume=100",                       # Volumen al 100%
            "--mute=no",                          # Desmuteado forzado
            f"--input-ipc-server={self.ipc_socket_path}",
            "--vo=gpu,drm,x11",
            "--hwdec=auto-safe"
        ]

        try:
            self.mpv_process = subprocess.Popen(
                cmd,
                env=self.env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            # Esperar a que el socket IPC esté listo
            time.sleep(0.8)
            print("🟢 [VideoPlayer] Servidor mpv IPC iniciado en pantalla DSI.")
            self.start_idle_loop()

            # Hilo de monitoreo para detectar fin de video en modo 1-shot
            threading.Thread(target=self._ipc_event_listener, daemon=True).start()

        except Exception as e:
            print(f"🔴 [VideoPlayer Error] Fallo al iniciar mpv daemon: {e}")

    def _send_ipc_command(self, command_dict):
        """Envía comandos JSON a través del socket IPC de mpv."""
        if sys.platform.startswith('win'):
            return None

        if not os.path.exists(self.ipc_socket_path):
            return None

        try:
            client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            client.connect(self.ipc_socket_path)
            msg = json.dumps(command_dict) + "\n"
            client.sendall(msg.encode('utf-8'))
            
            # Recibir respuesta
            response = client.recv(1024).decode('utf-8')
            client.close()
            return response
        except Exception:
            return None

    def _ipc_event_listener(self):
        """Monitorea cuando un video de 1 sola reproducción termina para regresar al idle."""
        while True:
            time.sleep(0.5)
            with self.lock:
                if self.current_state in ["PLAYING_ON", "PLAYING_OFF"] and not self.repeat_mode:
                    try:
                        # Consultar si el video actual llegó a su fin (eof-reached o idle-active)
                        resp = self._send_ipc_command({"command": ["get_property", "eof-reached"]})
                        if resp:
                            data = json.loads(resp.strip().split("\n")[0])
                            if data.get("data") is True:
                                self._play_file(self.idle_video, loop=True)
                                self.current_state = "IDLE"
                    except Exception:
                        pass

    def _play_file(self, file_path, loop=False):
        """Carga y reproduce un archivo sin cerrar la ventana de mpv."""
        if not os.path.exists(file_path):
            return False

        # Desmutear y fijar volumen
        self._send_ipc_command({"command": ["set_property", "mute", "no"]})
        self._send_ipc_command({"command": ["set_property", "volume", 100]})
        
        # Configurar bucle
        loop_val = "inf" if loop else "no"
        self._send_ipc_command({"command": ["set_property", "loop-file", loop_val]})
        
        # Cargar archivo reemplazando el actual sin destello
        self._send_ipc_command({"command": ["loadfile", file_path, "replace"]})
        return True

    def start_idle_loop(self):
        with self.lock:
            self.current_state = "IDLE"
            self._play_file(self.idle_video, loop=True)

    def trigger_on(self):
        with self.lock:
            if os.path.exists(self.on_video):
                self.current_state = "PLAYING_ON"
                self._play_file(self.on_video, loop=self.repeat_mode)
            else:
                self.start_idle_loop()

    def trigger_off(self):
        with self.lock:
            if os.path.exists(self.off_video):
                self.current_state = "PLAYING_OFF"
                self._play_file(self.off_video, loop=self.repeat_mode)
            else:
                self.start_idle_loop()

    def set_repeat_mode(self, enabled: bool):
        with self.lock:
            self.repeat_mode = bool(enabled)
            print(f"[VideoPlayer] Modo bucle configurado: {'ON' if self.repeat_mode else 'OFF'}")
            
            # Si actualmente está reproduciendo un evento, actualizar el estado de bucle
            if self.current_state == "PLAYING_ON":
                self._play_file(self.on_video, loop=self.repeat_mode)
            elif self.current_state == "PLAYING_OFF":
                self._play_file(self.off_video, loop=self.repeat_mode)
            elif self.current_state == "IDLE":
                self._play_file(self.idle_video, loop=True)
