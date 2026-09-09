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
    from api_oled import OLED
    from api_expansion import Expansion
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

# Rotación según placa (FNK0107 requiere 180°, FNK0100 requiere 0°)
rot = 180 if board_type == "FNK0107" else 0
print(f"🖥️ Inicializando OLED en Bus 1, Dirección 0x3C, Rotación {rot}°...")

oled = None
for bus in [1, 0]:
    for addr in [0x3C, 0x3D]:
        for r in [rot, 0 if rot == 180 else 180]:
            try:
                candidate = OLED(bus_number=bus, i2c_address=addr, rotate_angle=r)
                if candidate.device is not None:
                    oled = candidate
                    print(f"🎉 ¡Éxito! Pantalla OLED detectada en Bus {bus}, Dirección {hex(addr)}, Rotación {r}°.")
                    break
            except Exception:
                continue
        if oled:
            break
    if oled:
        break

if not oled or not oled.device:
    print("\n❌ No se pudo inicializar la pantalla OLED.")
    print("Verifica:")
    print(" 1. Habilitar I2C: sudo raspi-config -> Interface Options -> I2C -> Yes")
    print(" 2. Ejecutar: i2cdetect -y 1 (debe verse '3c' y '21')")
    print(" 3. Conexiones: GND, 3V3, SDA (GPIO 2), SCL (GPIO 3)")
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


