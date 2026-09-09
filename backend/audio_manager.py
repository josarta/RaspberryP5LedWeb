"""
audio_manager.py - Gestor de audio para el backend en Raspberry Pi (Linux ALSA) y Windows
Genera y reproduce tonos sintéticos instantáneos sin bloquear el bucle de eventos.
"""
import os
import sys
import math
import struct
import wave
import tempfile
import threading
import subprocess

class BackendAudio:
    def __init__(self):
        self.is_windows = sys.platform.startswith('win')
        self.temp_dir = tempfile.gettempdir()
        self.sound_on_path = os.path.join(self.temp_dir, 'rpi_led_on.wav')
        self.sound_off_path = os.path.join(self.temp_dir, 'rpi_led_off.wav')
        
        self._generate_wav_files()

    def _generate_wav_files(self):
        """Genera dos archivos WAV sintetizados en el directorio temporal."""
        sample_rate = 44100
        
        # 1. Tono de encendido: barrido ascendente (800Hz a 1400Hz) en 100ms
        duration_on = 0.10
        total_samples_on = int(sample_rate * duration_on)
        samples_on = []
        for i in range(total_samples_on):
            t = i / sample_rate
            # Frecuencia interpolada
            freq = 800 + (1400 - 800) * (t / duration_on)
            # Envolvente exponencial suave
            envelope = math.exp(-3.5 * (t / duration_on))
            val = math.sin(2 * math.pi * freq * t) * envelope
            # Convertir a 16-bit PCM
            samples_on.append(int(val * 24000))

        self._write_wav(self.sound_on_path, sample_rate, samples_on)

        # 2. Tono de apagado: barrido descendente (550Hz a 220Hz) en 90ms
        duration_off = 0.09
        total_samples_off = int(sample_rate * duration_off)
        samples_off = []
        for i in range(total_samples_off):
            t = i / sample_rate
            freq = 550 - (550 - 220) * (t / duration_off)
            envelope = math.exp(-4.0 * (t / duration_off))
            val = math.sin(2 * math.pi * freq * t) * envelope
            samples_off.append(int(val * 20000))

        self._write_wav(self.sound_off_path, sample_rate, samples_off)

    def _write_wav(self, file_path, sample_rate, samples):
        try:
            with wave.open(file_path, 'w') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(sample_rate)
                data = struct.pack('<' + 'h' * len(samples), *samples)
                wav_file.writeframes(data)
        except Exception as e:
            print(f"[Audio Warn] No se pudo guardar {file_path}: {e}")

    def play_on(self):
        """Reproduce el sonido de encendido en un hilo separado."""
        threading.Thread(target=self._play_sound, args=(self.sound_on_path, True), daemon=True).start()

    def play_off(self):
        """Reproduce el sonido de apagado en un hilo separado."""
        threading.Thread(target=self._play_sound, args=(self.sound_off_path, False), daemon=True).start()

    def _play_sound(self, wav_path, is_on):
        try:
            if self.is_windows:
                import winsound
                # Frecuencia en Hz y duración en ms
                if is_on:
                    winsound.Beep(1200, 80)
                else:
                    winsound.Beep(450, 80)
            else:
                # En Raspberry Pi / Linux: usar aplay (ALSA nativo) o paplay / pw-play
                if os.path.exists(wav_path):
                    subprocess.run(["aplay", "-q", wav_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

