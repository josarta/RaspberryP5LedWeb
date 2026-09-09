import * as THREE from 'three';

export class VirtualOLED {
  constructor(width = 512, height = 256) {
    this.width = width;
    this.height = height;

    this.canvas = document.createElement('canvas');
    this.canvas.width = this.width;
    this.canvas.height = this.height;
    this.ctx = this.canvas.getContext('2d');
    this.ctx.imageSmoothingEnabled = false;

    this.texture = new THREE.CanvasTexture(this.canvas);
    this.texture.minFilter = THREE.LinearFilter;
    this.texture.magFilter = THREE.LinearFilter;
    this.texture.generateMipmaps = false;

    this.mirrorCanvas = document.getElementById('oled-mirror-canvas');
    if (this.mirrorCanvas) {
      this.mirrorCanvas.width = this.width;
      this.mirrorCanvas.height = this.height;
      this.mirrorCtx = this.mirrorCanvas.getContext('2d');
      if (this.mirrorCtx) {
        this.mirrorCtx.imageSmoothingEnabled = true;
      }
    }

    this.drawInitialScreen();
  }

  drawInitialScreen() {
    this.update({
      leds: {},
      metrics: { cpu_percent: 5, cpu_temp: 42.0, ram_percent: 18, ip: '192.168.1.37' },
      last_log: 'Freenove Breakout Ready'
    });
  }

  update(stateData) {
    const ctx = this.ctx;
    const w = this.width;
    const h = this.height;

    // Fondo negro OLED
    ctx.fillStyle = '#05070a';
    ctx.fillRect(0, 0, w, h);

    const cyanGlow = '#00f0ff';
    const textWhite = '#f0f6fc';

    // 1. Header Bar Nítido
    ctx.fillStyle = cyanGlow;
    ctx.fillRect(0, 0, w, 40);
    ctx.fillStyle = '#05070a';
    ctx.font = 'bold 22px "Consolas", monospace';
    const ip = stateData.metrics?.ip || '127.0.0.1';
    ctx.fillText(`BREAKOUT RPi5  IP:${ip}`, 12, 28);

    // 2. Resumen GPIOs
    const leds = stateData.leds || {};
    const activePins = Object.keys(leds).filter(k => leds[k]);
    
    ctx.fillStyle = cyanGlow;
    ctx.font = 'bold 24px "Consolas", monospace';
    const countStr = String(activePins.length).padStart(2, '0');
    ctx.fillText(`ACTIVOS: ${countStr}/28`, 12, 78);

    const sampleTxt = activePins.length > 0 
      ? activePins.slice(0, 6).map(p => `IO${p}`).join(' ') 
      : 'ALL GPIOS OFF';
    ctx.fillStyle = '#a0ecff';
    ctx.font = 'bold 20px "Consolas", monospace';
    ctx.fillText(sampleTxt, 12, 110);

    // 3. Línea divisoria y Telemetría
    ctx.strokeStyle = 'rgba(0, 240, 255, 0.4)';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(0, 128);
    ctx.lineTo(w, 128);
    ctx.stroke();

    ctx.fillStyle = cyanGlow;
    ctx.font = 'bold 22px "Consolas", monospace';
    const cpu = stateData.metrics?.cpu_percent ?? 0;
    const temp = stateData.metrics?.cpu_temp ?? 0;
    const ram = stateData.metrics?.ram_percent ?? 0;
    ctx.fillText(`CPU:${cpu.toFixed(0)}%  T:${temp.toFixed(1)}°C  RAM:${ram.toFixed(0)}%`, 12, 165);

    // 4. Footer: Log
    ctx.beginPath();
    ctx.moveTo(0, 192);
    ctx.lineTo(w, 192);
    ctx.stroke();

    ctx.fillStyle = textWhite;
    ctx.font = '18px "Consolas", monospace';
    const log = stateData.last_log || 'Breakout Ready';
    ctx.fillText(`> ${log.slice(0, 34)}`, 12, 228);

    this.texture.needsUpdate = true;

    if (this.mirrorCtx && this.mirrorCanvas) {
      this.mirrorCtx.drawImage(this.canvas, 0, 0, this.mirrorCanvas.width, this.mirrorCanvas.height);
    }
  }

  getTexture() {
    return this.texture;
  }
}
