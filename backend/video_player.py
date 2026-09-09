"""
video_player.py - Reproductor de video optimizado para DSI (DSI-1 / DSI-2) y HDMI en Raspberry Pi 5
Maneja salida gráfica hacia Wayland / X11 / DRM con selección de pantalla y bucle configurable.
"""
import os
import sys
import time
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

        self.current_process = None
        self.current_state = "IDLE"  # IDLE, PLAYING_ON, PLAYING_OFF
        self.lock = threading.Lock()
        self.repeat_event_video = False  # Configurable desde el frontend
        
        self.player_cmd = self._detect_player()
        self.env = self._build_display_env()

        self._ensure_sample_videos()
        
        # Iniciar video en bucle en un hilo separado
        threading.Thread(target=self.start_idle_loop, daemon=True).start()

    def _build_display_env(self):
        """Prepara las variables de entorno para que el reproductor tome la pantalla DSI/Wayland."""
        env = os.environ.copy()
        
        if not sys.platform.startswith('win'):
            # Forzar acceso a la sesión gráfica del usuario en Raspberry Pi OS
            if "DISPLAY" not in env:
                env["DISPLAY"] = ":0"
            if "WAYLAND_DISPLAY" not in env:
                env["WAYLAND_DISPLAY"] = "wayland-0"
            if "XDG_RUNTIME_DIR" not in env:
                uid = os.getuid() if hasattr(os, "getuid") else 1000
                env["XDG_RUNTIME_DIR"] = f"/run/user/{uid}"
                
        return env

    def _detect_player(self):
        """Detecta el mejor reproductor disponible."""
        if shutil.which("mpv"):
            return "mpv"
        elif shutil.which("vlc") or shutil.which("cvlc"):
            return "vlc"
        elif shutil.which("ffplay"):
            return "ffplay"
        return "none"

    def _ensure_sample_videos(self):
        """Verifica la existencia del directorio de videos."""
        readme_path = os.path.join(self.video_dir, "README_VIDEOS.txt")
        if not os.path.exists(readme_path):
            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(
                    "Videos requeridos:\n"
                    "1. idle.mp4     -> Bucle de reposo en pantalla DSI.\n"
                    "2. led_on.mp4   -> Video con audio al encender LED.\n"
                    "3. led_off.mp4  -> Video con audio al apagar LED.\n"
                )

    def set_repeat_mode(self, enabled: bool):
        """Configura si los videos de evento se repiten o vuelven al reposo."""
        self.repeat_event_video = bool(enabled)
        print(f"[VideoPlayer] Modo repetición de evento: {'ON' if self.repeat_event_video else 'OFF'}")

    def _kill_current(self):
        """Detiene el proceso de video actual de forma segura."""
        if self.current_process:
            try:
                self.current_process.terminate()
                self.current_process.wait(timeout=0.4)
            except Exception:
                try:
                    self.current_process.kill()
                except Exception:
                    pass
            self.current_process = None

    def _play_command(self, video_path, loop=False):
        """Genera el comando con argumentos de pantalla completa forzada para pantalla DSI."""
        if not os.path.exists(video_path):
            return None

        if self.player_cmd == "mpv":
            # Parámetros optimizados para Raspberry Pi 5 (DSI / Wayland / X11)
            args = [
                "mpv",
                "--fs",                     # Pantalla completa
                "--no-osc",                 # Sin controles en pantalla
                "--no-osd-bar",             # Sin barra OSD
                "--ontop",                  # Siempre al frente
                "--screen=0",               # Pantalla principal DSI
                "--fs-screen=0",
                "--vo=gpu,drm,x11",         # Prioridad de salida de video
                "--hwdec=auto-safe"          # Aceleración por hardware
            ]
            if loop:
                args.append("--loop-file=inf")
            args.append(video_path)
            return args

        elif self.player_cmd == "vlc":
            cmd_bin = "cvlc" if shutil.which("cvlc") else "vlc"
            args = [
                cmd_bin,
                "--fullscreen",
                "--no-video-title-show",
                "--video-on-top"
            ]
            if loop:
                args.append("--loop")
            else:
                args.append("--play-and-exit")
            args.append(video_path)
            return args

        elif self.player_cmd == "ffplay":
            args = ["ffplay", "-fs", "-autoexit", "-alwaysontop"]
            if loop:
                args.extend(["-loop", "0"])
            args.append(video_path)
            return args

        return None

    def start_idle_loop(self):
        """Inicia el video de reposo en bucle continuo en la pantalla DSI."""
        with self.lock:
            self._kill_current()
            self.current_state = "IDLE"

            args = self._play_command(self.idle_video, loop=True)
            if args:
                try:
                    self.current_process = subprocess.Popen(
                        args,
                        env=self.env,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                except Exception as e:
                    print(f"[VideoPlayer Error] Fallo al iniciar loop idle: {e}")

    def trigger_on(self):
        threading.Thread(target=self._play_event_video, args=(self.on_video, "PLAYING_ON"), daemon=True).start()

    def trigger_off(self):
        threading.Thread(target=self._play_event_video, args=(self.off_video, "PLAYING_OFF"), daemon=True).start()

    def _play_event_video(self, video_path, state_name):
        with self.lock:
            if not os.path.exists(video_path):
                return

            self._kill_current()
            self.current_state = state_name

            # Si está activado repeat_event_video, reproduce en bucle hasta nueva acción
            is_loop = self.repeat_event_video
            args = self._play_command(video_path, loop=is_loop)
            if not args:
                return

            try:
                proc = subprocess.Popen(
                    args,
                    env=self.env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                self.current_process = proc
            except Exception as e:
                print(f"[VideoPlayer Error] {e}")
                self.start_idle_loop()
                return

        # Si no está en bucle continuo, espera a que termine y regresa al idle
        if not self.repeat_event_video:
            try:
                proc.wait()
            except Exception:
                pass

            with self.lock:
                if self.current_state == state_name:
                    self.start_idle_loop()
