"""
oled_renderer.py - Generador de frames gráficos 128x64 para OLED SSD1306 (Freenove / Raspberry Pi 5)
"""
from PIL import Image, ImageDraw, ImageFont

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

        # 1. Header con IP completa
        ip_addr = metrics.get("ip", "127.0.0.1")
        draw.rectangle((0, 0, self.width - 1, 10), outline=1, fill=1)
        draw.text((2, 0), f"RPi5 IP:{ip_addr}", fill=0, font=self.font_small)

        # 2. Resumen de GPIOs activos
        leds = state.get("leds", {})
        active_pins = [pin for pin, val in leds.items() if val]
        active_count = len(active_pins)

        draw.text((2, 13), f"GPIOS ON: {active_count:02d}/28", fill=1, font=self.font_small)
        active_str = " ".join([f"IO{p}" for p in active_pins[:5]]) if active_pins else "All GPIOs OFF"
        draw.text((2, 23), active_str[:22], fill=1, font=self.font_small)

        # 3. Métricas de Sistema
        cpu = metrics.get("cpu_percent", 0.0)
        temp = metrics.get("cpu_temp", 0.0)
        ram = metrics.get("ram_percent", 0.0)
        draw.line((0, 34, self.width, 34), fill=1)
        draw.text((2, 36), f"CPU:{cpu:.0f}% T:{temp:.1f}C RAM:{ram:.0f}%", fill=1, font=self.font_small)

        # 4. Footer: Registro de última acción
        draw.line((0, 48, self.width, 48), fill=1)
        short_log = (last_log[:22] + "..") if len(last_log) > 24 else last_log
        draw.text((2, 51), short_log, fill=1, font=self.font_small)

        return image
