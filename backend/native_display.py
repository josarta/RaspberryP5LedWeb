"""
native_display.py - Aplicación de Pantalla Nativa Fullscreen para Raspberry Pi 5 & Windows
Renderizado acelerado con Pygame y OpenCV (Decodificación de video, imágenes, audio y HUD).
Video y medios 100% encuadrados y centrados sin solaparse con barras superiores ni inferiores.
"""
import os
import sys
import time
import math
import queue
import subprocess
import cv2
import pygame

# 1. Desactivar teclados virtuales y fijar posición de ventana a pantalla completa
os.environ["SDL_ENABLE_SCREEN_KEYBOARD"] = "0"
os.environ["SDL_IME_SHOW_UI"] = "0"
os.environ["SDL_VIDEO_WINDOW_POS"] = "0,0"

class NativeVideoPlayer:
    def __init__(self, videos_dir, audio_cache_dir=None):
        self.videos_dir = videos_dir
        self.audio_cache_dir = audio_cache_dir or os.path.join(os.path.dirname(videos_dir), "audio_cache")
        os.makedirs(self.audio_cache_dir, exist_ok=True)

        self.cap = None
        self.current_file = None
        self.is_looping = False
        self.is_playing = False
        self.fps = 30.0
        self.last_frame_time = 0
        self.last_surface = None
        self.audio_enabled = True
        self.volume = 0.6

    def _ensure_audio_extracted(self, video_path):
        """Extrae la pista de audio del video en segundo plano o sincrónicamente a audio_cache."""
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        audio_path = os.path.join(self.audio_cache_dir, f"{base_name}.wav")
        if not os.path.exists(audio_path):
            try:
                cmd = ["ffmpeg", "-y", "-i", video_path, "-vn", "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "2", audio_path]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            except Exception:
                pass
        return audio_path if os.path.exists(audio_path) else None

    def load_video(self, filename, loop=False):
        path = os.path.join(self.videos_dir, filename)
        if not os.path.exists(path):
            if os.path.exists(filename):
                path = filename
            else:
                self.stop()
                return False

        if self.cap:
            self.cap.release()

        self.cap = cv2.VideoCapture(path)
        if not self.cap.isOpened():
            self.cap = None
            self.is_playing = False
            return False

        self.current_file = filename
        self.is_looping = loop
        self.is_playing = True
        fps_val = self.cap.get(cv2.CAP_PROP_FPS)
        self.fps = fps_val if fps_val > 0 else 30.0
        self.last_frame_time = time.time()

        # Reproducir audio sincronizado desde el video
        audio_file = self._ensure_audio_extracted(path)
        if audio_file and pygame.mixer.get_init():
            try:
                pygame.mixer.music.load(audio_file)
                pygame.mixer.music.set_volume(self.volume if self.audio_enabled else 0.0)
                pygame.mixer.music.play(loops=-1 if loop else 0)
            except Exception:
                pass
        return True

    def set_loop(self, loop: bool):
        self.is_looping = bool(loop)
        if self.is_looping and not self.is_playing and self.cap:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self.is_playing = True
            if pygame.mixer.get_init():
                try:
                    pygame.mixer.music.play(loops=-1)
                except Exception:
                    pass

    def set_volume(self, level: float):
        self.volume = max(0.0, min(1.0, float(level)))
        if pygame.mixer.get_init():
            try:
                pygame.mixer.music.set_volume(self.volume if self.audio_enabled else 0.0)
            except Exception:
                pass

    def set_audio_enabled(self, enabled: bool):
        self.audio_enabled = bool(enabled)
        if pygame.mixer.get_init():
            try:
                pygame.mixer.music.set_volume(self.volume if self.audio_enabled else 0.0)
            except Exception:
                pass

    def get_next_frame_surface(self, target_size):
        if not self.cap:
            return self.last_surface

        if not self.is_playing:
            return self.last_surface

        ret, frame = self.cap.read()
        if not ret:
            if self.is_looping:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.cap.read()
                if not ret:
                    return self.last_surface
            else:
                self.is_playing = False
                return self.last_surface

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, _ = rgb_frame.shape

        tw, th = target_size
        scale = min(tw / w, th / h)
        nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
        resized = cv2.resize(rgb_frame, (nw, nh), interpolation=cv2.INTER_LINEAR)

        self.last_surface = pygame.image.frombuffer(resized.tobytes(), (nw, nh), "RGB")
        return self.last_surface

    def stop(self):
        self.is_playing = False
        if self.cap:
            self.cap.release()
            self.cap = None
        if pygame.mixer.get_init():
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass


class NativeDisplayApp:
    def __init__(self, base_dir=None, fullscreen=True):
        if base_dir is None:
            self.base_dir = os.path.dirname(os.path.abspath(__file__))
        else:
            self.base_dir = base_dir

        self.media_dir = os.path.join(self.base_dir, "media")
        self.videos_dir = os.path.join(self.media_dir, "videos")
        self.images_dir = os.path.join(self.media_dir, "images")
        self.audio_dir = os.path.join(self.media_dir, "audio")
        self.audio_cache_dir = os.path.join(self.media_dir, "audio_cache")

        os.makedirs(self.videos_dir, exist_ok=True)
        os.makedirs(self.images_dir, exist_ok=True)
        os.makedirs(self.audio_dir, exist_ok=True)
        os.makedirs(self.audio_cache_dir, exist_ok=True)

        self.is_fullscreen = fullscreen
        self.is_running = True
        self.event_queue = queue.Queue()
        self.show_hud = True
        self.state = "LOADER"
        self.repeat_event_mode = False
        self.audio_enabled = True
        self.volume = 0.6

        # Telemetría en vivo
        self.metrics = {"cpu_percent": 0, "cpu_temp": 0.0, "ram_percent": 0, "ip": "127.0.0.1"}
        self.leds = {}
        self.last_log = "Sistema Iniciando..."
        self.current_image = None
        self.current_image_caption = ""
        self.image_end_time = 0
        self._font_cache = {}

        # Control de interacción táctil reactiva (bebe.mp4)
        self.is_touch_held = False
        self.touch_start_time = 0.0
        self.min_touch_duration = 2.0  # Mínimo 2 segundos de reproducción
        self.pre_touch_state = "IDLE"
        self.pre_touch_video = "idle.mp4"
        self.pre_touch_loop = False

        # Control de estado de inactividad (InactividadDurmiendo.mp4)
        self.inactivity_timeout = 25.0  # 25 segundos sin actividad para entrar en modo reposo
        self.last_activity_time = time.time()
        self.sleep_video = "InactividadDurmiendo.mp4"

        # Sub-motor de video con audio integrado
        self.video = NativeVideoPlayer(self.videos_dir, self.audio_cache_dir)

        self._suppress_virtual_keyboards()

    def _suppress_virtual_keyboards(self):
        if not sys.platform.startswith("win"):
            for proc in ["squeekboard", "matchbox-keyboard", "onboard", "wvkbd"]:
                try:
                    subprocess.run(["pkill", "-f", proc], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception:
                    pass

    def reset_activity(self):
        """Reinicia el reloj de inactividad y despierta el dispositivo si estaba durmiendo."""
        self.last_activity_time = time.time()
        if self.state == "SLEEPING":
            self.state = "IDLE"
            self.video.load_video("idle.mp4", loop=self.repeat_event_mode)
            self.last_log = "Sistema Activo (Despierto)"

    def trigger_wake_up(self):
        """Fuerza despertar desde la API o WebSockets."""
        self.event_queue.put(("WAKE_UP", None))

    def _get_font(self, font_name: str, size: int, bold: bool = True):
        """Devuelve una fuente cacheada de forma segura sin fugas de descriptores de archivo."""
        key = (font_name, size, bold)
        if key not in self._font_cache:
            font_obj = None
            try:
                font_obj = pygame.font.SysFont(font_name, size, bold=bold)
            except Exception:
                font_obj = None
            if font_obj is None:
                try:
                    font_obj = pygame.font.Font(None, size)
                except Exception:
                    font_obj = pygame.font.SysFont(None, size)
            self._font_cache[key] = font_obj
        return self._font_cache[key]

    def handle_touch_press(self):
        """Maneja el inicio de un toque/clic en la pantalla: reproduce bebe.mp4 de inmediato."""
        self.reset_activity()
        self.is_touch_held = True
        if self.state != "TOUCH_INTERACTION":
            self.pre_touch_state = "IDLE"
            self.pre_touch_video = "idle.mp4"
            self.pre_touch_loop = self.repeat_event_mode
            self.state = "TOUCH_INTERACTION"
            self.touch_start_time = time.time()
            self.last_log = "TACTIL: Video Bebe Activo"
            self.video.load_video("bebe.mp4", loop=True)

    def handle_touch_release(self):
        """Maneja la liberación del toque/clic en la pantalla."""
        self.reset_activity()
        self.is_touch_held = False

    def trigger_touch_down(self):
        self.event_queue.put(("TOUCH_DOWN", None))

    def trigger_touch_up(self):
        self.event_queue.put(("TOUCH_UP", None))

    def trigger_led_on(self, pin=None):
        self.event_queue.put(("PLAY_LED_ON", pin))

    def trigger_led_off(self, pin=None):
        self.event_queue.put(("PLAY_LED_OFF", pin))

    def show_custom_image(self, filename, caption="", duration_sec=0):
        self.event_queue.put(("SHOW_IMAGE", (filename, caption, duration_sec)))

    def show_custom_video(self, filename, loop=False):
        self.event_queue.put(("SHOW_VIDEO", (filename, loop)))

    def set_volume(self, level: float):
        self.volume = max(0.0, min(1.0, float(level)))
        self.video.set_volume(self.volume)
        self.event_queue.put(("SET_VOLUME", self.volume))
        return self.volume

    def set_audio_enabled(self, enabled: bool):
        self.audio_enabled = bool(enabled)
        self.video.set_audio_enabled(self.audio_enabled)
        self.event_queue.put(("SET_AUDIO_ENABLED", self.audio_enabled))

    def update_telemetry(self, state_dict):
        self.event_queue.put(("TELEMETRY", state_dict))

    def set_repeat_mode(self, enabled):
        self.repeat_event_mode = bool(enabled)
        self.video.set_loop(self.repeat_event_mode)

    # =========================================================================
    # BUCLE PRINCIPAL GRÁFICO (PYGAME NATIVO)
    # =========================================================================
    def run(self):
        pygame.init()
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
        except Exception:
            pass
        pygame.font.init()

        if hasattr(pygame.key, "stop_text_input"):
            pygame.key.stop_text_input()

        pygame.display.set_caption("Raspberry Pi 5 - Breakout Board Native Kiosk Display")

        flags = pygame.DOUBLEBUF | pygame.HWSURFACE
        if self.is_fullscreen:
            flags |= pygame.FULLSCREEN | pygame.NOFRAME

        screen = pygame.display.set_mode((0, 0) if self.is_fullscreen else (1280, 720), flags)
        clock = pygame.time.Clock()

        if self.is_fullscreen:
            pygame.mouse.set_visible(False)

        info = pygame.display.Info()
        screen_w = info.current_w
        screen_h = info.current_h

        # Variables para el Loader
        loader_pct = 0.0
        loader_step = 0
        loader_steps = [
            ("Verificando Broadcom BCM2712 & 8GB RAM...", 20),
            ("Inicializando controlador de 28 Pines GPIO...", 45),
            ("Escaneando Bus I2C & Pantalla OLED SSD1306...", 70),
            ("Configurando Motor Multimedia & Video Engine...", 88),
            ("¡Sistema IoT Listo y Operativo!", 100)
        ]
        loader_step_timer = time.time()
        ring_angle = 0

        # Colores Cyberpunk
        C_BG = (7, 9, 14)
        C_CYAN = (0, 255, 204)
        C_GREEN = (0, 255, 136)
        C_YELLOW = (255, 204, 0)
        C_WHITE = (240, 246, 252)
        C_MUTED = (139, 148, 158)
        C_PANEL = (13, 20, 36)
        C_BORDER = (0, 255, 204)

        while self.is_running:
            dt = clock.tick(30) / 1000.0
            now = time.time()
            current_w, current_h = screen.get_size()

            # Obtención de fuentes tipográficas cacheadas (sin re-instanciación por frame)
            font_size_title = max(18, min(32, int(current_h * 0.045)))
            font_size_main = max(12, min(20, int(current_h * 0.030)))
            font_size_hud = max(11, min(16, int(current_h * 0.026)))

            font_title = self._get_font("consolas", font_size_title, bold=True)
            font_main = self._get_font("consolas", font_size_main, bold=True)
            font_hud = self._get_font("consolas", font_size_hud, bold=True)

            # Cálculo de la zona segura central maximizada (barras superiores/inferiores compactas)
            margin_x = max(10, int(current_w * 0.015))
            hdr_h = max(34, min(44, int(current_h * 0.070)))
            hdr_y = 8
            ftr_h = max(34, min(44, int(current_h * 0.070)))
            ftr_y = current_h - ftr_h - 8

            safe_top = hdr_y + hdr_h + 6
            safe_bottom = ftr_y - 6
            safe_w = current_w - margin_x * 2
            safe_h = max(80, safe_bottom - safe_top)

            # 1. Manejar Eventos de Teclado, Ratón y Pantalla Táctil
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.is_running = False
                elif event.type == pygame.MOUSEMOTION:
                    self.reset_activity()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        self.handle_touch_press()
                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:
                        self.handle_touch_release()
                elif event.type == pygame.FINGERDOWN:
                    self.handle_touch_press()
                elif event.type == pygame.FINGERUP:
                    self.handle_touch_release()
                elif event.type == pygame.KEYDOWN:
                    self.reset_activity()
                    if event.key in [pygame.K_ESCAPE, pygame.K_q]:
                        self.is_running = False
                    elif event.key in [pygame.K_f, pygame.K_F11]:
                        self.is_fullscreen = not self.is_fullscreen
                        pygame.display.quit()
                        pygame.display.init()
                        try:
                            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
                        except Exception:
                            pass
                        if hasattr(pygame.key, "stop_text_input"):
                            pygame.key.stop_text_input()
                        flags = pygame.DOUBLEBUF | pygame.HWSURFACE
                        if self.is_fullscreen:
                            flags |= pygame.FULLSCREEN | pygame.NOFRAME
                            screen = pygame.display.set_mode((0, 0), flags)
                            pygame.mouse.set_visible(False)
                        else:
                            screen = pygame.display.set_mode((1280, 720), flags)
                            pygame.mouse.set_visible(True)
                    elif event.key == pygame.K_h:
                        self.show_hud = not self.show_hud
                    elif event.key == pygame.K_m:
                        self.set_audio_enabled(not self.audio_enabled)
                    elif event.key in [pygame.K_PLUS, pygame.K_KP_PLUS, pygame.K_EQUALS, pygame.K_UP, pygame.K_PAGEUP]:
                        self.set_volume(self.volume + 0.05)
                        self.last_log = f"Volumen: {int(self.volume * 100)}%"
                    elif event.key in [pygame.K_MINUS, pygame.K_KP_MINUS, pygame.K_DOWN, pygame.K_PAGEDOWN]:
                        self.set_volume(self.volume - 0.05)
                        self.last_log = f"Volumen: {int(self.volume * 100)}%"
                    elif event.key == pygame.K_r:
                        self.state = "LOADER"
                        loader_pct = 0.0
                        loader_step = 0
                        loader_step_timer = now

            # 2. Procesar Cola de Mensajes desde Backend / Hardware
            while not self.event_queue.empty():
                try:
                    ev_type, ev_data = self.event_queue.get_nowait()
                    if ev_type == "TELEMETRY":
                        if "metrics" in ev_data:
                            self.metrics.update(ev_data["metrics"])
                        if "leds" in ev_data:
                            self.leds = ev_data["leds"]
                        if "last_log" in ev_data:
                            self.last_log = ev_data["last_log"]

                    elif ev_type == "WAKE_UP":
                        self.reset_activity()

                    elif ev_type == "TOUCH_DOWN":
                        self.handle_touch_press()

                    elif ev_type == "TOUCH_UP":
                        self.handle_touch_release()

                    elif ev_type == "PLAY_LED_ON":
                        self.reset_activity()
                        pin = ev_data
                        self.state = "PLAYING_EVENT"
                        self.last_log = f"LED ON (Pin {pin})" if pin else "ALL LEDS ON"
                        self.video.load_video("led_on.mp4", loop=self.repeat_event_mode)

                    elif ev_type == "PLAY_LED_OFF":
                        self.reset_activity()
                        pin = ev_data
                        self.state = "PLAYING_EVENT"
                        self.last_log = f"LED OFF (Pin {pin})" if pin else "ALL LEDS OFF"
                        self.video.load_video("led_off.mp4", loop=self.repeat_event_mode)

                    elif ev_type == "SHOW_IMAGE":
                        self.reset_activity()
                        fname, cap, dur = ev_data
                        img_path = os.path.join(self.images_dir, fname) if not os.path.exists(fname) else fname
                        if os.path.exists(img_path):
                            try:
                                self.current_image = pygame.image.load(img_path).convert_alpha()
                                self.current_image_caption = cap or fname
                                self.state = "IMAGE"
                                self.image_end_time = now + dur if dur > 0 else 0
                                self.video.stop()
                            except Exception:
                                pass

                    elif ev_type == "SHOW_VIDEO":
                        self.reset_activity()
                        fname, loop = ev_data
                        self.state = "PLAYING_EVENT"
                        self.video.load_video(fname, loop=loop)

                    elif ev_type == "SET_VOLUME":
                        self.reset_activity()
                        self.volume = max(0.0, min(1.0, float(ev_data)))
                        self.video.set_volume(self.volume)
                        self.last_log = f"Volumen: {int(self.volume * 100)}%"

                    elif ev_type == "SET_AUDIO_ENABLED":
                        self.reset_activity()
                        self.audio_enabled = bool(ev_data)
                        self.video.set_audio_enabled(self.audio_enabled)

                except queue.Empty:
                    break

            # 3. Limpiar Fondo
            screen.fill(C_BG)

            # =================================================================
            # ESTADO 1: SPLASH LOADER (ANIMACIÓN DE ARRANQUE)
            # =================================================================
            if self.state == "LOADER":
                ring_angle = (ring_angle + 120 * dt) % 360
                cx, cy = current_w // 2, current_h // 2 - 35

                pygame.draw.circle(screen, (0, 100, 80), (cx, cy), 65, 2)
                pygame.draw.circle(screen, C_CYAN, (cx, cy), 50, 3)

                pts = []
                for i in range(6):
                    ang = math.radians(ring_angle + i * 60)
                    pts.append((cx + int(32 * math.cos(ang)), cy + int(32 * math.sin(ang))))
                pygame.draw.polygon(screen, C_GREEN, pts, 3)
                pygame.draw.circle(screen, C_CYAN, (cx, cy), 8)

                t_surf = font_title.render("RASPBERRY PI 5 IoT KIOSK", True, C_WHITE)
                screen.blit(t_surf, (cx - t_surf.get_width() // 2, cy + 75))

                sub_surf = font_hud.render("INICIALIZANDO SISTEMA MULTIMEDIA Y BREAKOUT BOARD", True, C_CYAN)
                screen.blit(sub_surf, (cx - sub_surf.get_width() // 2, cy + 115))

                if loader_step < len(loader_steps):
                    text, target_pct = loader_steps[loader_step]
                    loader_pct += (target_pct - loader_pct) * 0.12

                    if now - loader_step_timer > 0.65 and loader_pct >= target_pct - 2:
                        loader_step += 1
                        loader_step_timer = now
                else:
                    loader_pct = 100.0
                    if now - loader_step_timer > 0.7:
                        self.state = "IDLE"
                        self.last_activity_time = now
                        self.video.load_video("idle.mp4", loop=self.repeat_event_mode)

                bar_w, bar_h = min(600, int(current_w * 0.75)), 14
                bar_x, bar_y = cx - bar_w // 2, cy + 145
                pygame.draw.rect(screen, (30, 40, 60), (bar_x, bar_y, bar_w, bar_h), border_radius=7)
                fill_w = int(bar_w * (loader_pct / 100.0))
                if fill_w > 0:
                    pygame.draw.rect(screen, C_CYAN, (bar_x, bar_y, fill_w, bar_h), border_radius=7)

                pct_txt = font_main.render(f"{int(loader_pct)}%", True, C_CYAN)
                screen.blit(pct_txt, (bar_x + bar_w + 14, bar_y - 4))

                cur_step_text = loader_steps[min(loader_step, len(loader_steps)-1)][0]
                status_txt = font_hud.render(cur_step_text, True, C_MUTED)
                screen.blit(status_txt, (cx - status_txt.get_width() // 2, bar_y + 24))

            # =================================================================
            # ESTADO 2: VIDEO O CANVAS INTERACTIVO (IDLE / EVENTO / TACTIL / REPOSO)
            # =================================================================
            elif self.state in ["IDLE", "PLAYING_EVENT", "TOUCH_INTERACTION", "SLEEPING"]:
                # Transición automática a reposo por inactividad
                if self.state == "IDLE":
                    if (now - self.last_activity_time) >= self.inactivity_timeout:
                        self.state = "SLEEPING"
                        self.last_log = "Inactividad: Durmiendo..."
                        self.video.load_video(self.sleep_video, loop=True)

                # Transición de retorno cuando finaliza un video de evento
                elif self.state == "PLAYING_EVENT":
                    if not self.video.is_playing and not self.repeat_event_mode:
                        self.state = "IDLE"
                        self.last_activity_time = now
                        self.video.load_video("idle.mp4", loop=self.repeat_event_mode)

                # Renderizar frame de video centrado en el área segura
                frame_surf = self.video.get_next_frame_surface((safe_w, safe_h))
                if frame_surf:
                    fw, fh = frame_surf.get_size()
                    pos_x = (current_w - fw) // 2
                    pos_y = safe_top + (safe_h - fh) // 2
                    screen.blit(frame_surf, (pos_x, pos_y))
                else:
                    cols, rows = 7, 4
                    spacing_x = safe_w // (cols + 1)
                    spacing_y = safe_h // (rows + 1)
                    for r in range(rows):
                        for c in range(cols):
                            pin_idx = r * cols + c
                            nx = margin_x + (c + 1) * spacing_x
                            ny = safe_top + (r + 1) * spacing_y
                            is_active = self.leds.get(str(pin_idx), False)
                            color = C_GREEN if is_active else (40, 55, 80)
                            pygame.draw.circle(screen, color, (nx, ny), 12 if is_active else 7)
                            if is_active:
                                pygame.draw.circle(screen, C_CYAN, (nx, ny), 22, 3)

                # Control temporal de la interacción táctil (bebe.mp4)
                if self.state == "TOUCH_INTERACTION":
                    if not self.is_touch_held:
                        elapsed = now - self.touch_start_time
                        if elapsed >= self.min_touch_duration:
                            self.state = "IDLE"
                            self.last_activity_time = now
                            self.video.load_video("idle.mp4", loop=self.repeat_event_mode)
                            self.last_log = "TACTIL: Fin interacción (2s+)"

            # =================================================================
            # ESTADO 3: VISOR DE IMAGEN EN ZONA SEGURA
            # =================================================================
            elif self.state == "IMAGE":
                if self.current_image:
                    iw, ih = self.current_image.get_size()
                    scale = min(safe_w / iw, safe_h / ih)
                    scaled = pygame.transform.smoothscale(self.current_image, (max(1, int(iw * scale)), max(1, int(ih * scale))))
                    sw, sh = scaled.get_size()
                    pos_x = (current_w - sw) // 2
                    pos_y = safe_top + (safe_h - sh) // 2
                    screen.blit(scaled, (pos_x, pos_y))

                    if self.current_image_caption:
                        cap_surf = font_title.render(self.current_image_caption, True, C_CYAN)
                        screen.blit(cap_surf, ((current_w - cap_surf.get_width()) // 2, pos_y + sh - 35))

                if self.image_end_time > 0 and now > self.image_end_time:
                    self.state = "IDLE"
                    self.last_activity_time = now
                    self.video.load_video("idle.mp4", loop=self.repeat_event_mode)

            # =================================================================
            # CAPA HUD Y TELEMETRÍA (DISEÑO ADAPTATIVO SIN SOLAPAMIENTO)
            # =================================================================
            if self.show_hud and self.state != "LOADER":
                # --- 1. HEADER SUPERIOR ---
                pygame.draw.rect(screen, C_PANEL, (margin_x, hdr_y, current_w - margin_x * 2, hdr_h), border_radius=8)
                pygame.draw.rect(screen, C_BORDER, (margin_x, hdr_y, current_w - margin_x * 2, hdr_h), 1, border_radius=8)

                # Lado izquierdo: Indicador de estado y Título
                dot_x = margin_x + 14
                dot_y = hdr_y + hdr_h // 2
                dot_color = C_YELLOW if self.state == "SLEEPING" else C_GREEN
                pygame.draw.circle(screen, dot_color, (dot_x, dot_y), 6)

                title_text = "RPI 5 KIOSK" if current_w < 900 else "RPI 5 BREAKOUT KIOSK"
                title_surf = font_hud.render(title_text, True, C_WHITE)
                screen.blit(title_surf, (dot_x + 12, hdr_y + (hdr_h - title_surf.get_height()) // 2))
                left_boundary_x = dot_x + 12 + title_surf.get_width() + 16

                # Lado derecho: Audio, IP, Modo (renderizados de derecha a izquierda con límite de seguridad)
                vol_pct = int(self.volume * 100)
                vol_str = f"🔊 {vol_pct}%" if self.audio_enabled else "🔇 MUTE"
                audio_surf = font_hud.render(vol_str, True, C_GREEN if self.audio_enabled else C_YELLOW)

                ip_val = self.metrics.get('ip', '127.0.0.1')
                ip_str = f"IP:{ip_val}"
                ip_surf = font_hud.render(ip_str, True, C_MUTED)

                if self.state == "TOUCH_INTERACTION":
                    mode_label = "BEBE"
                    loop_badge = "[HOLD]"
                elif self.state == "SLEEPING":
                    mode_label = "DURMIENDO"
                    loop_badge = "[REPOSO zZz]"
                elif self.state == "PLAYING_EVENT":
                    mode_label = "EVENT"
                    loop_badge = "[LOOP]" if self.repeat_event_mode else "[1-SHOT]"
                else:
                    mode_label = "IDLE"
                    loop_badge = "[LOOP]" if self.repeat_event_mode else "[1-SHOT]"

                mode_str = f"{mode_label} {loop_badge}"
                mode_surf = font_hud.render(mode_str, True, C_YELLOW if self.state == "SLEEPING" else C_CYAN)

                right_cursor_x = current_w - margin_x - 14

                # Audio
                right_cursor_x -= audio_surf.get_width()
                screen.blit(audio_surf, (right_cursor_x, hdr_y + (hdr_h - audio_surf.get_height()) // 2))
                right_cursor_x -= 16

                # IP
                if right_cursor_x - ip_surf.get_width() > left_boundary_x:
                    right_cursor_x -= ip_surf.get_width()
                    screen.blit(ip_surf, (right_cursor_x, hdr_y + (hdr_h - ip_surf.get_height()) // 2))
                    right_cursor_x -= 16

                # Modo
                if right_cursor_x - mode_surf.get_width() > left_boundary_x:
                    right_cursor_x -= mode_surf.get_width()
                    screen.blit(mode_surf, (right_cursor_x, hdr_y + (hdr_h - mode_surf.get_height()) // 2))

                # --- 2. FOOTER INFERIOR ---
                pygame.draw.rect(screen, C_PANEL, (margin_x, ftr_y, current_w - margin_x * 2, ftr_h), border_radius=8)
                pygame.draw.rect(screen, C_BORDER, (margin_x, ftr_y, current_w - margin_x * 2, ftr_h), 1, border_radius=8)

                cpu_v = self.metrics.get("cpu_percent", 0.0)
                temp_v = self.metrics.get("cpu_temp", 0.0)
                ram_v = self.metrics.get("ram_percent", 0.0)
                active_gpios = len([k for k, v in self.leds.items() if v])

                # Telemetría adaptable
                if current_w < 850:
                    tel_str = f"CPU:{cpu_v:.0f}% {temp_v:.0f}°C RAM:{ram_v:.0f}% GP:{active_gpios:02d}/28"
                else:
                    tel_str = f"CPU: {cpu_v:02.0f}% | TEMP: {temp_v:.1f}°C | RAM: {ram_v:02.0f}% | GPIOS: {active_gpios:02d}/28"

                tel_surf = font_hud.render(tel_str, True, C_WHITE)
                screen.blit(tel_surf, (margin_x + 14, ftr_y + (ftr_h - tel_surf.get_height()) // 2))
                tel_boundary_x = margin_x + 14 + tel_surf.get_width() + 16

                # Log con corte de seguridad automático para no colisionar nunca
                available_log_w = (current_w - margin_x - 14) - tel_boundary_x
                if available_log_w > 80:
                    log_text = self.last_log
                    log_surf = font_hud.render(f"LOG: {log_text}", True, C_CYAN)
                    if log_surf.get_width() > available_log_w:
                        # Truncar con elipsis si excede el ancho disponible
                        while len(log_text) > 4 and log_surf.get_width() > available_log_w:
                            log_text = log_text[:-2]
                            log_surf = font_hud.render(f"LOG: {log_text}...", True, C_CYAN)

                    screen.blit(log_surf, (current_w - margin_x - log_surf.get_width() - 14, ftr_y + (ftr_h - log_surf.get_height()) // 2))

            pygame.display.flip()

        pygame.quit()

if __name__ == "__main__":
    app = NativeDisplayApp(fullscreen=False)
    app.run()
