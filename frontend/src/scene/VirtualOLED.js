import * as THREE from 'three';

export class VirtualOLED {
  constructor(width = 256, height = 128) {
    this.width = width;
    this.height = height;

    this.canvas = document.createElement('canvas');
    this.canvas.width = this.width;
    this.canvas.height = this.height;
    this.ctx = this.canvas.getContext('2d');

    this.texture = new THREE.CanvasTexture(this.canvas);
    this.texture.minFilter = THREE.NearestFilter;
    this.texture.magFilter = THREE.NearestFilter;
    this.texture.generateMipmaps = false;

    this.mirrorCanvas = document.getElementById('oled-mirror-canvas');
    if (this.mirrorCanvas) {
      this.mirrorCtx = this.mirrorCanvas.getContext('2d');
    }

    this.drawInitialScreen();
  }

  drawInitialScreen() {
    this.update({
      leds: {},
      metrics: { cpu_percent: 5, cpu_temp: 42.0, ram_percent: 18, ip: '192.168.1.105' },
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

    // 1. Header Bar
    ctx.fillStyle = cyanGlow;
    ctx.fillRect(0, 0, w, 20);
    ctx.fillStyle = '#05070a';
    ctx.font = 'bold 13px monospace';
    const ip = stateData.metrics?.ip || '127.0.0.1';
    ctx.fillText(`BREAKOUT RPi5  IP:${ip.slice(-10)}`, 6, 15);

    // 2. Resumen GPIOs
    const leds = stateData.leds || {};
    const activePins = Object.keys(leds).filter(k => leds[k]);
    
    ctx.fillStyle = cyanGlow;
    const countStr = String(activePins.length).padStart(2, '0');
    ctx.fillText(`ACTIVOS: ${countStr}/26`, 6, 40);

    const sampleTxt = activePins.length > 0 
      ? activePins.slice(0, 5).map(p => `IO${p}`).join(' ') 
      : 'ALL GPIOS OFF';
    ctx.fillStyle = '#a0ecff';
    ctx.fillText(sampleTxt, 6, 56);

    // 3. Telemetría de Sistema
    ctx.strokeStyle = 'rgba(0, 240, 255, 0.35)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, 64);
    ctx.lineTo(w, 64);
    ctx.stroke();

    ctx.fillStyle = cyanGlow;
    ctx.font = '12px monospace';
    const cpu = stateData.metrics?.cpu_percent ?? 0;
    const temp = stateData.metrics?.cpu_temp ?? 0;
    const ram = stateData.metrics?.ram_percent ?? 0;
    ctx.fillText(`CPU:${cpu.toFixed(0)}%  T:${temp.toFixed(1)}C  RAM:${ram.toFixed(0)}%`, 6, 82);

    // 4. Footer: Log
    ctx.beginPath();
    ctx.moveTo(0, 96);
    ctx.lineTo(w, 96);
    ctx.stroke();

    ctx.fillStyle = '#ffffff';
    ctx.font = '11px monospace';
    const log = stateData.last_log || 'OK';
    ctx.fillText(`> ${log.slice(0, 28)}`, 6, 114);

    this.texture.needsUpdate = true;

    if (this.mirrorCtx && this.mirrorCanvas) {
      this.mirrorCtx.drawImage(this.canvas, 0, 0, this.mirrorCanvas.width, this.mirrorCanvas.height);
    }
  }

  getTexture() {
    return this.texture;
  }
}

