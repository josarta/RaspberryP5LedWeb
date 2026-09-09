"""
media_manager.py - Gestor Centralizado Multimedia para Pantalla Nativa y WebSockets
"""
import os
import time

class MediaManager:
    def __init__(self, base_media_dir=None):
        if base_media_dir is None:
            self.base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "media")
        else:
            self.base_dir = base_media_dir

        self.videos_dir = os.path.join(self.base_dir, "videos")
        self.images_dir = os.path.join(self.base_dir, "images")
        self.audio_cache_dir = os.path.join(self.base_dir, "audio_cache")

        os.makedirs(self.videos_dir, exist_ok=True)
        os.makedirs(self.images_dir, exist_ok=True)
        os.makedirs(self.audio_cache_dir, exist_ok=True)

        self.sio = None
        self.native_app = None
        self.current_mode = "loader"
        self.repeat_event_mode = False
        self.last_event = "System Initialized"
        self.audio_enabled = True
        self.volume = 0.6  # 60% por defecto

    def set_sio(self, sio_instance):
        self.sio = sio_instance

    def set_native_app(self, native_app_instance):
        self.native_app = native_app_instance

    def get_catalog(self) -> dict:
        def list_files(directory, extensions):
            if not os.path.exists(directory):
                return []
            return [
                f for f in sorted(os.listdir(directory))
                if os.path.isfile(os.path.join(directory, f)) and f.lower().endswith(extensions)
            ]

        return {
            "videos": list_files(self.videos_dir, (".mp4", ".webm", ".mkv", ".mov", ".avi")),
            "images": list_files(self.images_dir, (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".bmp"))
        }

    async def emit_display_event(self, event_type: str, data: dict = None):
        if self.sio:
            payload = {
                "type": event_type,
                "data": data or {},
                "timestamp": time.time(),
                "repeat_mode": self.repeat_event_mode,
                "audio_enabled": self.audio_enabled,
                "volume": self.volume
            }
            try:
                await self.sio.emit("display_event", payload)
            except Exception:
                pass

    def trigger_led_on_sync(self, pin: int = None):
        self.current_mode = "video"
        self.last_event = f"LED ON (Pin {pin})" if pin is not None else "ALL LEDS ON"
        if self.native_app:
            self.native_app.trigger_led_on(pin)

    def trigger_led_off_sync(self, pin: int = None):
        self.current_mode = "video"
        self.last_event = f"LED OFF (Pin {pin})" if pin is not None else "ALL LEDS OFF"
        if self.native_app:
            self.native_app.trigger_led_off(pin)

    async def trigger_led_on(self, pin: int = None):
        self.trigger_led_on_sync(pin)
        await self.emit_display_event("PLAY_LED_ON", {
            "pin": pin,
            "video_url": "/media/videos/led_on.mp4",
            "loop": self.repeat_event_mode
        })

    async def trigger_led_off(self, pin: int = None):
        self.trigger_led_off_sync(pin)
        await self.emit_display_event("PLAY_LED_OFF", {
            "pin": pin,
            "video_url": "/media/videos/led_off.mp4",
            "loop": self.repeat_event_mode
        })

    async def trigger_idle(self):
        self.current_mode = "idle"
        self.last_event = "Idle Standby"
        if self.native_app:
            self.native_app.event_queue.put(("SHOW_VIDEO", ("idle.mp4", self.repeat_event_mode)))
        await self.emit_display_event("PLAY_IDLE", {
            "video_url": "/media/videos/idle.mp4",
            "loop": self.repeat_event_mode
        })

    async def show_custom_image(self, filename: str, caption: str = "", duration_sec: float = 0):
        self.current_mode = "image"
        self.last_event = f"Display Image: {filename}"
        if self.native_app:
            self.native_app.show_custom_image(filename, caption, duration_sec)
        await self.emit_display_event("SHOW_IMAGE", {
            "image_url": f"/media/images/{filename}",
            "caption": caption,
            "duration": duration_sec
        })

    async def show_custom_video(self, filename: str, loop: bool = False):
        self.current_mode = "video"
        self.last_event = f"Display Video: {filename}"
        if self.native_app:
            self.native_app.show_custom_video(filename, loop)
        await self.emit_display_event("SHOW_VIDEO", {
            "video_url": f"/media/videos/{filename}",
            "loop": loop
        })

    def trigger_wake_up(self):
        """Despierta la pantalla nativa de inactividad."""
        if self.native_app:
            self.native_app.trigger_wake_up()

    def set_repeat_mode(self, enabled: bool):
        self.repeat_event_mode = bool(enabled)
        if self.native_app:
            self.native_app.set_repeat_mode(enabled)

    def set_audio_enabled(self, enabled: bool):
        self.audio_enabled = bool(enabled)
        if self.native_app:
            self.native_app.set_audio_enabled(enabled)

    def set_volume(self, level: float) -> float:
        val = max(0.0, min(1.0, float(level)))
        self.volume = val
        if self.native_app:
            self.native_app.set_volume(val)
        return self.volume
