"""
test_oled.py - Script de prueba directa para pantalla OLED SSD1306 / SH1106 en Raspberry Pi 5
Basado en el controlador oficial de Freenove (luma.oled)
"""
import time
import sys

print("="*50)
print("🔍 Probando pantalla OLED con luma.oled...")
print("="*50)

try:
    from luma.core.interface.serial import i2c
    from luma.oled.device import ssd1306, sh1106
    from PIL import Image, ImageDraw, ImageFont
    print("✅ Librerías luma.oled y Pillow importadas con éxito.")
except ImportError as e:
    print(f"❌ Error al importar librerías: {e}")
    print("👉 Instala con: sudo apt install python3-luma.oled python3-pil")
    print("👉 O con pip: pip install luma.oled Pillow")
    sys.exit(1)

device = None
for port in [1, 0]:
    for addr in [0x3C, 0x3D]:
        for dev_class, dev_name in [(ssd1306, "SSD1306"), (sh1106, "SH1106")]:
            for rot in [0, 2]:
                try:
                    print(f"Probando {dev_name} en Bus {port}, Dir {hex(addr)}, Rotación {rot*90}°...")
                    serial = i2c(port=port, address=addr)
                    device = dev_class(serial, width=128, height=64, rotate=rot)
                    print(f"🎉 ¡Éxito! Pantalla {dev_name} detectada y lista.")
                    break
                except Exception:
                    continue
            if device:
                break
        if device:
            break
    if device:
        break

if not device:
    print("\n❌ No se pudo comunicar con la pantalla OLED.")
    print("Por favor verifica:")
    print(" 1. Que I2C esté habilitado: sudo raspi-config -> Interface Options -> I2C -> Yes")
    print(" 2. Ejecuta: i2cdetect -y 1 (debe aparecer 3c)")
    print(" 3. Revisa la polaridad de los 4 cables (GND -> GND, VCC -> 3V3, SCL -> SCL, SDA -> SDA)")
    sys.exit(1)

print("\n📺 Dibujando patrón de prueba en la pantalla...")
try:
    image = Image.new("1", (128, 64), 0)
    draw = ImageDraw.Draw(image)

    # Marco
    draw.rectangle((0, 0, 127, 63), outline=1, fill=0)
    
    # Texto
    font = ImageFont.load_default()
    draw.rectangle((0, 0, 127, 14), fill=1)
    draw.text((10, 2), "FREENOVE OLED OK!", fill=0, font=font)
    
    draw.text((10, 22), "Raspberry Pi 5", fill=1, font=font)
    draw.text((10, 36), "I2C: 0x3C (Bus 1)", fill=1, font=font)
    draw.text((10, 50), "Web 3D IoT Twin", fill=1, font=font)

    device.display(image)
    print("✅ ¡Mensaje enviado a la pantalla física! Verifica si está encendida.")
    print("Manteniendo 5 segundos...")
    time.sleep(5)

except Exception as e:
    print(f"❌ Error al dibujar en el display: {e}")

