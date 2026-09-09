"""
hardware_manager.py - Gestor de hardware para Raspberry Pi 5 y Breakout Board Freenove
Soporta control de 28 pines GPIO, display OLED SSD1306 (Freenove) y gestor multimedia.
"""
import os
import time
import socket
import psutil
from oled_renderer import OLEDRenderer
from media_manager import MediaManager

HAS_GPIO = False
try:
    from gpiozero import LED as GpioLED
    HAS_GPIO = True
except Exception:
    HAS_GPIO = False

HAS_LUMA = False
try:
    from luma.core.interface.serial import i2c
    from luma.oled.device import ssd1306, sh1106
    HAS_LUMA = True
except Exception:
    HAS_LUMA = False

class HardwareManager:
    ALL_BCM_PINS = [
        # Columna Izquierda
        2, 3, 4, 17, 27, 22, 10, 9, 11, 0, 5, 6, 13, 19, 26,
        # Columna Derecha
        14, 15, 18, 23, 24, 25, 8, 7, 1, 12, 16, 20, 21
    ]

    def __init__(self):
        self.is_gpio_available = False
        self.is_oled_available = False
        self.renderer = OLEDRenderer()
        self.media_manager = MediaManager()
        self.led_state = {str(pin): False for pin in self.ALL_BCM_PINS}
        self.last_log = "Breakout Board Ready"
        self.physical_leds = {}
        self.oled_device = None

        self._init_gpio()
        self._init_oled()

    def _init_gpio(self):
        if not HAS_GPIO:
            print("🟡 [HW] Control GPIO físico no disponible (Modo Emulado).")
            return

        try:
            for pin in self.ALL_BCM_PINS:
                try:
                    self.physical_leds[str(pin)] = GpioLED(pin)
                    self.physical_leds[str(pin)].off()
                except Exception:
                    pass
            
            if len(self.physical_leds) > 0:
                self.is_gpio_available = True
                print(f"🟢 [HW] {len(self.physical_leds)} Pines GPIO físicos inicializados correctamente.")
        except Exception as e:
            print(f"🔴 [HW Error] Fallo al inicializar GPIOs: {e}")
            self.is_gpio_available = False

    def _init_oled(self) -> bool:
        """Inicializa la pantalla OLED SSD1306/SH1106 probando buses, direcciones y rotaciones."""
        if self.is_oled_available and self.oled_device is not None:
            return True

        if not HAS_LUMA:
            return False

        # Intentar bus 1 (estándar RPi 5/4/3) y bus 0, direcciones 0x3C y 0x3D, y rotaciones 0 y 2
        for port in [1, 0]:
            for addr in [0x3C, 0x3D]:
                for device_class, dev_name in [(ssd1306, "SSD1306"), (sh1106, "SH1106")]:
                    for rot in [0, 2]:
                        try:
                            serial = i2c(port=port, address=addr)
                            dev = device_class(serial, width=128, height=64, rotate=rot)
                            
                            # Enviar frame de prueba para confirmar comunicación I2C
                            img = self.renderer.draw_frame(
                                {"leds": self.led_state},
                                self.get_system_metrics(),
                                "OLED Inicializado"
                            )
                            dev.display(img)
                            self.oled_device = dev
                            self.is_oled_available = True
                            print(f"🟢 [HW] Pantalla OLED {dev_name} física conectada y activa en Bus {port}, Dirección {hex(addr)}, Rotación {rot * 90}°.")
                            return True
                        except Exception:
                            continue

        return False

    def toggle_led(self, pin: int, forced_state: bool = None) -> bool:
        pin_str = str(pin)
        if pin_str not in self.led_state:
            return False

        new_state = (not self.led_state[pin_str]) if forced_state is None else bool(forced_state)
        self.led_state[pin_str] = new_state

        if self.is_gpio_available and pin_str in self.physical_leds:
            try:
                if new_state:
                    self.physical_leds[pin_str].on()
                else:
                    self.physical_leds[pin_str].off()
            except Exception as e:
                print(f"[HW Error] Fallo al conmutar GPIO {pin}: {e}")

        status_str = "ON" if new_state else "OFF"
        self.last_log = f"IO{pin} -> {status_str} @ {time.strftime('%H:%M:%S')}"
        self.update_oled()
        return new_state

    def set_all_leds(self, state: bool):
        for pin in self.ALL_BCM_PINS:
            self.toggle_led(pin, forced_state=state)
            
        self.last_log = f"ALL GPIOs -> {'ON' if state else 'OFF'} @ {time.strftime('%H:%M:%S')}"
        self.update_oled()

    def set_repeat_mode(self, enabled: bool):
        self.media_manager.set_repeat_mode(enabled)
        self.last_log = f"Modo Bucle: {'ON' if enabled else 'OFF'}"
        self.update_oled()

    def get_system_metrics(self) -> dict:
        cpu_percent = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory()

        cpu_temp = 42.0
        try:
            if os.path.exists("/sys/class/thermal/thermal_zone0/temp"):
                with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                    cpu_temp = float(f.read().strip()) / 1000.0
            else:
                cpu_temp = 40.0 + (cpu_percent * 0.15)
        except Exception:
            cpu_temp = 42.0

        ip_addr = "127.0.0.1"
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip_addr = s.getsockname()[0]
            s.close()
        except Exception:
            ip_addr = "192.168.1.37"

        return {
            "cpu_percent": cpu_percent,
            "cpu_temp": round(cpu_temp, 1),
            "ram_percent": ram.percent,
            "ip": ip_addr,
            "timestamp": time.time()
        }

    def update_oled(self):
        if not self.is_oled_available or self.oled_device is None:
            if not self._init_oled():
                return

        try:
            metrics = self.get_system_metrics()
            state = {"leds": self.led_state}
            img = self.renderer.draw_frame(state, metrics, self.last_log)
            self.oled_device.display(img)
        except Exception:
            self.is_oled_available = False
            self.oled_device = None

    def get_full_state(self) -> dict:
        mode_str = "Physical (GPIO+OLED)" if (self.is_gpio_available and self.is_oled_available) else (
            "Physical (GPIO)" if self.is_gpio_available else ("Physical (OLED)" if self.is_oled_available else "Emulated")
        )
        return {
            "leds": self.led_state,
            "last_log": self.last_log,
            "metrics": self.get_system_metrics(),
            "hardware_mode": mode_str
        }
