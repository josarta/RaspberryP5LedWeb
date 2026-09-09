"""
oled_renderer.py - Generador de frames gráficos 128x64 para OLED SSD1306 (Freenove / Raspberry Pi 5)
"""
from PIL import Image, ImageDraw, ImageFont
import datetime

class OLEDRenderer:
    def __init__(self, width=128, height=64):
        self.width = width
        self.height = height
        try:
            self.font_small = ImageFont.load_default()
        except Exception:
            self.font_small = None

    def draw_frame(self, state: dict, metrics: dict, last_log: str) -> Image.Image:
        """Crea una imagen monocromática 1-bit para el display SSD1306."""
        image = Image.new("1", (self.width, self.height), 0)
        draw = ImageDraw.Draw(image)

        # 1. Header con IP y status
        ip_addr = metrics.get("ip", "127.0.0.1")
        draw.rectangle((0, 0, self.width - 1, 9), outline=1, fill=1)
        draw.text((2, 0), f"RPi5 BREAKOUT  IP:{ip_addr[-9:]}", fill=0, font=self.font_small)

        # 2. Resumen de GPIOs activos
        leds = state.get("leds", {})
        active_pins = [pin for pin, val in leds.items() if val]
        active_count = len(active_pins)

        draw.text((2, 12), f"GPIOS ON: {active_count:02d}/26", fill=1, font=self.font_small)
        # Mostrar los primeros pines activos o lista abreviada
        active_str = " ".join([f"IO{p}" for p in active_pins[:4]]) if active_pins else "All GPIOs OFF"
        draw.text((2, 22), active_str[:22], fill=1, font=self.font_small)

        # 3. Métricas de Sistema
        cpu = metrics.get("cpu_percent", 0.0)
        temp = metrics.get("cpu_temp", 0.0)
        ram = metrics.get("ram_percent", 0.0)
        draw.line((0, 33, self.width, 33), fill=1)
        draw.text((2, 35), f"CPU:{cpu:.0f}%  T:{temp:.1f}C  RAM:{ram:.0f}%", fill=1, font=self.font_small)

        # 4. Footer: Registro de última acción
        draw.line((0, 48, self.width, 48), fill=1)
        short_log = (last_log[:22] + "..") if len(last_log) > 24 else last_log
        draw.text((2, 51), short_log, fill=1, font=self.font_small)

        return image

