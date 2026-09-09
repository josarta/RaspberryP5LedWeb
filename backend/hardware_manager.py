"""
hardware_manager.py - Gestor de hardware para Raspberry Pi 5 y Breakout Board Freenove
Soporta control independiente de los 28 pines GPIO y del display OLED SSD1306 / SH1106
"""
import os
import time
import socket
import psutil
from oled_renderer import OLEDRenderer

IS_RPI = False
try:
    from gpiozero import LED as GpioLED
    from luma.core.interface.serial import i2c
    from luma.oled.device import ssd1306, sh1106
    IS_RPI = True
except Exception:
    IS_RPI = False

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
        self.led_state = {str(pin): False for pin in self.ALL_BCM_PINS}
        self.last_log = "Breakout Board Ready"
        self.physical_leds = {}
        self.oled_device = None

        self._init_hardware()

    def _init_hardware(self):
        if not IS_RPI:
            print("[HW] Ejecutando en modo Emulación / Digital Twin (Sin librerías RPi nativas).")
            return

        # 1. Inicializar GPIOs físicos independientemente
        try:
            for pin in self.ALL_BCM_PINS:
                try:
                    self.physical_leds[str(pin)] = GpioLED(pin)
                    self.physical_leds[str(pin)].off()
                except Exception as ex:
                    pass
            
            if len(self.physical_leds) > 0:
                self.is_gpio_available = True
                print(f"🟢 [HW] {len(self.physical_leds)} Pines GPIO físicos inicializados correctamente.")
        except Exception as e:
            print(f"🔴 [HW Error] Fallo al inicializar GPIOs: {e}")
            self.is_gpio_available = False

        # 2. Inicializar Pantalla OLED I2C (Prueba SSD1306 y SH1106 en puertos 1 y 0, addrs 0x3C y 0x3D)
        for port in [1, 0]:
            for addr in [0x3C, 0x3D]:
                for device_class, dev_name in [(ssd1306, "SSD1306"), (sh1106, "SH1106")]:
                    try:
                        serial = i2c(port=port, address=addr)
                        self.oled_device = device_class(serial, width=128, height=64)
                        self.is_oled_available = True
                        print(f"🟢 [HW] Pantalla OLED {dev_name} física detectada en Bus {port}, Dirección {hex(addr)}.")
                        break
                    except Exception:
                        continue
                if self.is_oled_available:
                    break
            if self.is_oled_available:
                break

        if not self.is_oled_available:
            print("🟡 [HW Info] Pantalla OLED no detectada en bus I2C. Revisa la conexión I2C (SDA, SCL, VCC, GND).")

        self.update_oled()

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
            ip_addr = "192.168.1.100"

        return {
            "cpu_percent": cpu_percent,
            "cpu_temp": round(cpu_temp, 1),
            "ram_percent": ram.percent,
            "ip": ip_addr,
            "timestamp": time.time()
        }

    def update_oled(self):
        if self.is_oled_available and self.oled_device:
            try:
                metrics = self.get_system_metrics()
                state = {"leds": self.led_state}
                img = self.renderer.draw_frame(state, metrics, self.last_log)
                self.oled_device.display(img)
            except Exception as e:
                pass

    def get_full_state(self) -> dict:
        mode_str = "Physical (GPIO+OLED)" if (self.is_gpio_available and self.is_oled_available) else (
            "Physical (GPIO)" if self.is_gpio_available else "Emulated"
        )
        return {
            "leds": self.led_state,
            "last_log": self.last_log,
            "metrics": self.get_system_metrics(),
            "hardware_mode": mode_str
        }
