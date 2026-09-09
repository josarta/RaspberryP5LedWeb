"""
video_player.py - Reproductor de video a pantalla completa para Raspberry Pi / PC
Maneja el bucle de reposo (Idle) y conmuta a videos de evento (LED ON / LED OFF) con retorno automático.
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
        self.player_cmd = self._detect_player()

        self._ensure_sample_videos()
        
        # Iniciar video en bucle en un hilo separado
        threading.Thread(target=self.start_idle_loop, daemon=True).start()

    def _detect_player(self):
        """Detecta el reproductor disponible en el sistema (mpv, vlc, ffplay)."""
        if shutil.which("mpv"):
            return "mpv"
        elif shutil.which("vlc") or shutil.which("cvlc"):
            return "vlc"
        elif shutil.which("ffplay"):
            return "ffplay"
        return "none"

    def _ensure_sample_videos(self):
        """Crea archivos informativos o placeholders si los videos no existen."""
        readme_path = os.path.join(self.video_dir, "README_VIDEOS.txt")
        if not os.path.exists(readme_path):
            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(
                    "Coloca aquí tus 3 videos MP4 con audio:\n"
                    "1. idle.mp4     -> Video en bucle constante cuando no hay actividad.\n"
                    "2. led_on.mp4   -> Video con audio que se reproduce al encender un LED.\n"
                    "3. led_off.mp4  -> Video con audio que se reproduce al apagar un LED.\n"
                )

    def _kill_current(self):
        """Detiene el proceso de video actual de forma segura."""
        if self.current_process:
            try:
                self.current_process.terminate()
                self.current_process.wait(timeout=0.5)
            except Exception:
                try:
                    self.current_process.kill()
                except Exception:
                    pass
            self.current_process = None

    def _play_command(self, video_path, loop=False):
        """Genera el comando adecuado según el reproductor detectado."""
        if not os.path.exists(video_path):
            # print(f"[VideoPlayer] Archivo no encontrado: {video_path}")
            return None

        if self.player_cmd == "mpv":
            args = ["mpv", "--fs", "--no-osc", "--no-osd-bar", "--ontop"]
            if loop:
                args.append("--loop-file=inf")
            args.append(video_path)
            return args

        elif self.player_cmd == "vlc":
            cmd_bin = "cvlc" if shutil.which("cvlc") else "vlc"
            args = [cmd_bin, "--fullscreen", "--no-video-title-show"]
            if loop:
                args.append("--loop")
            else:
                args.append("--play-and-exit")
            args.append(video_path)
            return args

        elif self.player_cmd == "ffplay":
            args = ["ffplay", "-fs", "-autoexit", "-nodisp" if not sys.platform.startswith('win') else ""]
            if loop:
                args.extend(["-loop", "0"])
            args = [a for a in args if a]
            args.append(video_path)
            return args

        return None

    def start_idle_loop(self):
        """Inicia el video de reposo en bucle continuo."""
        with self.lock:
            self._kill_current()
            self.current_state = "IDLE"

            args = self._play_command(self.idle_video, loop=True)
            if args:
                try:
                    # print(f"[VideoPlayer] Iniciando video IDLE en bucle: {self.idle_video}")
                    self.current_process = subprocess.Popen(
                        args,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                except Exception as e:
                    print(f"[VideoPlayer Error] No se pudo reproducir idle: {e}")

    def trigger_on(self):
        """Reproduce el video de LED ON y al terminar regresa a IDLE."""
        threading.Thread(target=self._play_event_video, args=(self.on_video, "PLAYING_ON"), daemon=True).start()

    def trigger_off(self):
        """Reproduce el video de LED OFF y al terminar regresa a IDLE."""
        threading.Thread(target=self._play_event_video, args=(self.off_video, "PLAYING_OFF"), daemon=True).start()

    def _play_event_video(self, video_path, state_name):
        with self.lock:
            if not os.path.exists(video_path):
                # Si el video específico no existe, permanece en idle
                return

            self._kill_current()
            self.current_state = state_name

            args = self._play_command(video_path, loop=False)
            if not args:
                return

            try:
                # print(f"[VideoPlayer] Reproduciendo evento: {video_path}")
                proc = subprocess.Popen(
                    args,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                self.current_process = proc
            except Exception as e:
                print(f"[VideoPlayer Error] {e}")
                self.start_idle_loop()
                return

        # Esperar a que termine la reproducción del video de evento
        try:
            proc.wait()
        except Exception:
            pass

        # Volver al bucle IDLE solo si no ha comenzado otro evento
        with self.lock:
            if self.current_state == state_name:
                self.start_idle_loop()

