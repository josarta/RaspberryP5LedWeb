import sys
import time

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

print("="*60)
print("🔍 Probando pantalla OLED SSD1306 (Controlador Oficial Freenove)")
print("="*60)

try:
    from oled import OLED
    from expansion import Expansion
    print("✅ Módulos oled.py y expansion.py importados con éxito.")
except Exception as e:
    print(f"❌ Error al cargar módulos: {e}")
    sys.exit(1)

try:
    exp = Expansion()
    exp.set_power_on_check(1)
    print("⚡ Placa de expansión configurada.")
except Exception as e:
    print(f"ℹ️ Expansión info: {e}")

try:
    oled = OLED()
    print("🎉 ¡OLED instanciado correctamente!")
    
    oled.clear()
    oled.draw_rectangle((0, 0, 127, 63), outline="white")
    oled.draw_text("FREENOVE OLED OK!", position=(12, 12))
    oled.draw_text("Raspberry Pi 5", position=(18, 30))
    oled.draw_text("WebLED 3D Twin", position=(18, 45))
    oled.show()
    print("📺 ¡Gráficos enviados a la pantalla OLED con éxito!")
    
    print("\n🚀 Manteniendo pantalla activa (Presiona Ctrl+C para salir)...")
    count = 0
    while True:
        count += 1
        time.sleep(1)
        oled.clear()
        oled.draw_rectangle((0, 0, 127, 63), outline="white")
        oled.draw_text("FREENOVE OLED OK!", position=(12, 10))
        oled.draw_text(f"Tick: {count}s", position=(12, 28))
        oled.draw_text(f"Hora: {time.strftime('%H:%M:%S')}", position=(12, 44))
        oled.show()
        print(f"Frame #{count:03d} en pantalla", end="\r")

except KeyboardInterrupt:
    print("\n🛑 Prueba finalizada.")
    if 'oled' in locals():
        oled.clear()
        oled.show()
except Exception as e:
    print(f"\n❌ Error al comunicarse con el OLED: {e}")
    sys.exit(1)


