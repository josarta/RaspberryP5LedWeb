"""
hardware_manager.py - Gestor de hardware para Raspberry Pi 5 y Breakout Board Freenove
Soporta control de 28 pines GPIO, display OLED SSD1306 (Freenove) y gestor multimedia.
"""
import os
import sys
import time
import socket
import psutil

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
from oled import OLED
from expansion import Expansion
from api_systemInfo import SystemInformation
from media_manager import MediaManager

HAS_GPIO = False
try:
    from gpiozero import LED as GpioLED
    HAS_GPIO = True
except Exception:
    HAS_GPIO = False

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
        self.media_manager = MediaManager()
        self.led_state = {str(pin): False for pin in self.ALL_BCM_PINS}
        self.last_log = "Breakout Board Ready"
        self.physical_leds = {}
        self.oled = None
        self.expansion = None
        self.board_type = "FNK0100"

        # Control de throttling para evitar sobrecarga de I2C y descriptores
        self.last_metrics_time = 0.0
        self.last_oled_render_time = 0.0
        self.last_oled_probe_time = 0.0
        self.cached_metrics = {
            "cpu_percent": 0.0,
            "cpu_temp": 42.0,
            "ram_percent": 0.0,
            "ip": "127.0.0.1",
            "timestamp": time.time()
        }

        # Inicializar subsistema de información de sistema
        try:
            self.sys_info = SystemInformation()
        except Exception:
            self.sys_info = None

        self._init_gpio()
        self._init_expansion()
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

    def _init_expansion(self):
        """Inicializa el chip de expansión Freenove (I2C 0x21) si está presente."""
        try:
            self.expansion = Expansion()
            self.board_type = self.expansion.get_board_type()
            if self.board_type in ["FNK0100", "FNK0107"]:
                try:
                    self.expansion.set_power_on_check(1)
                except Exception:
                    pass
                print(f"🟢 [HW] Placa de expansión detectada: {self.board_type}")
        except Exception:
            self.expansion = None
            self.board_type = "FNK0100"

    def _init_oled(self) -> bool:
        """Inicializa la pantalla OLED SSD1306 usando la clase OLED oficial."""
        if self.is_oled_available and self.oled is not None and self.oled.device is not None:
            return True

        now = time.time()
        if now - self.last_oled_probe_time < 2.0:
            return False
        self.last_oled_probe_time = now

        try:
            self.oled = OLED()
            if self.oled.device is not None:
                self.is_oled_available = True
                print("🟢 [HW] Pantalla OLED SSD1306 física conectada con éxito.")
                self._render_splash_screen()
                return True
        except Exception as e:
            print(f"❌ [HW OLED Error]: {e}")

        return False

    def _render_splash_screen(self):
        """Dibuja una pantalla de arranque limpia en el OLED."""
        if not self.oled or self.oled.device is None:
            return
        try:
            self.oled.clear()
            self.oled.draw_rectangle((0, 0, 127, 63), outline="white")
            self.oled.draw_text("RASPBERRY PI 5", position=(14, 8))
            self.oled.draw_line((0, 24, 127, 24), fill="white")
            self.oled.draw_text("IoT 3D Twin Ready", position=(10, 30))
            ip_str = self._get_ip_address()
            self.oled.draw_text(f"IP:{ip_str}", position=(6, 46))
            self.oled.show()
        except Exception as e:
            print(f"❌ [HW Splash Error]: {e}")

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
                pass

        status_str = "ON" if new_state else "OFF"
        self.last_log = f"IO{pin} -> {status_str} @ {time.strftime('%H:%M:%S')}"
        self.update_oled()
        return new_state

    def set_all_leds(self, state: bool):
        # Conmutar todos los pines en lote sin saturar I2C ni abrir descriptores repetidos
        new_state = bool(state)
        for pin in self.ALL_BCM_PINS:
            pin_str = str(pin)
            self.led_state[pin_str] = new_state
            if self.is_gpio_available and pin_str in self.physical_leds:
                try:
                    if new_state:
                        self.physical_leds[pin_str].on()
                    else:
                        self.physical_leds[pin_str].off()
                except Exception:
                    pass

        self.last_log = f"ALL GPIOs -> {'ON' if new_state else 'OFF'} @ {time.strftime('%H:%M:%S')}"
        self.update_oled(force=True)

    def set_repeat_mode(self, enabled: bool):
        self.media_manager.set_repeat_mode(enabled)
        self.last_log = f"Modo Bucle: {'ON' if enabled else 'OFF'}"
        self.update_oled()

    def _get_ip_address(self) -> str:
        """Obtiene la IP local de forma segura, refrescando periódicamente."""
        if self.sys_info:
            try:
                ip = self.sys_info.get_raspberry_pi_ip_address()
                if ip and ip != "0.0.0.0":
                    return ip
            except Exception:
                pass

        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.2)
            s.connect(("8.8.8.8", 80))
            ip_addr = s.getsockname()[0]
            s.close()
            return ip_addr
        except Exception:
            return "127.0.0.1"

    def get_system_metrics(self, force: bool = False) -> dict:
        """Devuelve las métricas del sistema utilizando caché para respuesta instantánea."""
        now = time.time()
        if not force and (now - self.last_metrics_time < 0.9):
            return self.cached_metrics

        self.last_metrics_time = now
        try:
            if self.sys_info:
                cpu_percent = self.sys_info.get_raspberry_pi_cpu_usage()
                cpu_temp = self.sys_info.get_raspberry_pi_cpu_temperature()
                mem_info = self.sys_info.get_raspberry_pi_memory_usage()
                ram_percent = mem_info[0] if isinstance(mem_info, list) else 0.0
                ip_addr = self.sys_info.get_raspberry_pi_ip_address()
                if not cpu_temp or cpu_temp == 0:
                    cpu_temp = 42.0
            else:
                cpu_percent = psutil.cpu_percent(interval=None)
                ram_percent = psutil.virtual_memory().percent
                cpu_temp = 42.0
                ip_addr = self._get_ip_address()

            self.cached_metrics = {
                "cpu_percent": float(cpu_percent or 0.0),
                "cpu_temp": round(float(cpu_temp or 42.0), 1),
                "ram_percent": float(ram_percent or 0.0),
                "ip": ip_addr or "127.0.0.1",
                "timestamp": now
            }
        except Exception:
            pass

        return self.cached_metrics

    def update_oled(self, force: bool = False):
        """Actualiza el display OLED SSD1306 físico de forma continua."""
        now = time.time()
        if not force and (now - self.last_oled_render_time < 0.2):
            return

        self.last_oled_render_time = now

        if not self.is_oled_available or self.oled is None or self.oled.device is None:
            if not self._init_oled():
                return

        try:
            metrics = self.get_system_metrics()
            ip_str = metrics.get("ip", "127.0.0.1")
            cpu = metrics.get("cpu_percent", 0.0)
            temp = metrics.get("cpu_temp", 42.0)
            ram = metrics.get("ram_percent", 0.0)

            active_pins = [pin for pin, val in self.led_state.items() if val]
            active_count = len(active_pins)
            active_preview = " ".join([f"IO{p}" for p in active_pins[:3]]) if active_pins else "All OFF"

            self.oled.clear()
            self.oled.draw_rectangle((0, 0, 127, 63), outline="white")
            
            # Fila 1: IP
            self.oled.draw_text(f"IP:{ip_str}", position=(4, 3))
            self.oled.draw_line((0, 17, 127, 17), fill="white")

            # Fila 2: GPIOs activos
            self.oled.draw_text(f"LED:{active_count:02d}/28 {active_preview[:12]}", position=(4, 19))
            self.oled.draw_line((0, 33, 127, 33), fill="white")

            # Fila 3: Métricas (CPU, Temp, RAM)
            self.oled.draw_text(f"C:{cpu:.0f}% T:{temp:.0f}C R:{ram:.0f}%", position=(4, 35))
            self.oled.draw_line((0, 49, 127, 49), fill="white")

            # Fila 4: Último Evento / Log
            log_str = self.last_log[:18]
            self.oled.draw_text(log_str, position=(4, 51))

            self.oled.show()
        except Exception as e:
            print(f"❌ [HW update_oled error]: {e}")
            self.is_oled_available = False

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
