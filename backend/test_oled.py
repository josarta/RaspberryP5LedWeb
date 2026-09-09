import sys
import time

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

print("="*60)
print("🔍 Probando pantalla OLED SSD1306 con controlador oficial...")
print("="*60)

try:
    from oled import OLED
    from expansion import Expansion
    from api_systemInfo import SystemInformation
    print("✅ Módulos de Hardware Freenove cargados.")
except Exception as e:
    print(f"❌ Error al cargar módulos: {e}")
    sys.exit(1)

board_type = "FNK0100"
try:
    exp = Expansion()
    board_type = exp.get_board_type()
    print(f"📋 Tipo de placa de expansión: {board_type}")
    exp.set_power_on_check(1)
except Exception as e:
    print(f"ℹ️ Placa de expansión opcional no detectada: {e}")

# Escaneo I2C detallado para diagnóstico rápido
print("\n🔍 Escaneando bus I2C...")
detected_devices = {}
try:
    import smbus
except ImportError:
    try:
        import smbus2 as smbus
    except ImportError:
        smbus = None

if smbus is not None:
    for b in [1, 0]:
        try:
            bus_obj = smbus.SMBus(b)
            detected_devices[b] = []
            for a in range(0x03, 0x78):
                try:
                    bus_obj.read_byte(a)
                    detected_devices[b].append(hex(a))
                except Exception:
                    pass
            bus_obj.close()
        except Exception as e_bus:
            pass

    for b, addrs in detected_devices.items():
        if addrs:
            print(f"   📡 Dispositivos I2C detectados en Bus {b}: {', '.join(addrs)}")
        else:
            print(f"   ⚠️ Bus {b} disponible pero sin dispositivos I2C detectados.")
else:
    print("   ⚠️ Módulo smbus / smbus2 no disponible para escaneo preliminar.")

# Rotación según placa (FNK0107 requiere 180°, FNK0100 requiere 0°)
rot = 180 if board_type == "FNK0107" else 0
print(f"\n🖥️ Inicializando OLED (Rotación por defecto {rot}°)...")

oled = None
last_errors = []
for bus in [1, 0]:
    for addr in [0x3C, 0x3D]:
        for r in [rot, 0 if rot == 180 else 180]:
            try:
                candidate = OLED(bus_number=bus, i2c_address=addr, rotate_angle=r)
                if candidate.device is not None:
                    oled = candidate
                    print(f"🎉 ¡Éxito! Pantalla OLED inicializada en Bus {bus}, Dirección {hex(addr)}, Rotación {r}° (Driver: {candidate.device.__class__.__name__}).")
                    break
                else:
                    if candidate.init_error:
                        last_errors.append(f"Bus {bus}, Addr {hex(addr)}: {candidate.init_error}")
            except Exception as e:
                last_errors.append(f"Bus {bus}, Addr {hex(addr)}: {e}")
        if oled:
            break
    if oled:
        break

if not oled or not oled.device:
    print("\n❌ No se pudo inicializar la pantalla OLED.")
    if last_errors:
        print("Detalle de intentos:")
        for err in set(last_errors):
            print(f" - {err}")
    print("\nVerifica en la Raspberry Pi:")
    print(" 1. Habilitar I2C: sudo raspi-config -> Interface Options -> I2C -> Yes")
    print(" 2. Ejecutar: i2cdetect -y 1 (debe verse '3c' y '21')")
    print(" 3. Conexiones físicas: VCC/3V3, GND, SDA (GPIO 2 - Pin 3), SCL (GPIO 3 - Pin 5)")
    sys.exit(1)

sys_info = SystemInformation()

print("\n🚀 Iniciando animación de prueba continua en el OLED (Presiona Ctrl+C para salir)...")
try:
    count = 0
    while True:
        count += 1
        oled.clear()
        
        # Marco exterior
        oled.draw_rectangle((0, 0, 127, 63), outline="white")
        
        # Cabecera
        oled.draw_rectangle((0, 0, 127, 14), fill="white")
        oled.draw_text("FREENOVE OLED OK!", position=((0, 1), (128, 13)), directory="center", font_size=10)
        
        # Datos del sistema en vivo
        ip = sys_info.get_raspberry_pi_ip_address()
        cpu = sys_info.get_raspberry_pi_cpu_usage()
        temp = sys_info.get_raspberry_pi_cpu_temperature()
        
        oled.draw_text(f"IP: {ip}", position=((4, 18), (124, 30)), directory="left", font_size=10)
        oled.draw_text(f"CPU: {cpu:.0f}%  Temp: {temp:.1f}C", position=((4, 32), (124, 44)), directory="left", font_size=10)
        
        # Barra de progreso animada
        progress = (count * 5) % 100
        oled.draw_progress_bar((4, 48), (123, 58), progress, outline="white", fill="white")
        
        oled.show()
        print(f"📺 Frame #{count:03d} enviado al OLED - IP: {ip} | CPU: {cpu}% | Temp: {temp}°C", end="\r")
        time.sleep(0.3)

except KeyboardInterrupt:
    print("\n\n🛑 Prueba finalizada por el usuario.")
    oled.clear()
    oled.show()


