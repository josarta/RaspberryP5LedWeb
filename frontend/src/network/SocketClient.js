import { io } from 'socket.io-client';

export class SocketClient {
  constructor(serverUrl = null) {
    const savedHost = localStorage.getItem('rpi_host_url');
    const host = window.location.hostname || 'localhost';
    this.serverUrl = serverUrl || savedHost || `http://${host}:8000`;

    console.log(`[WS] Intentando conectar a: ${this.serverUrl}`);

    this.socket = io(this.serverUrl, {
      transports: ['polling', 'websocket'], // Inicia con polling y actualiza a websocket para máxima compatibilidad
      reconnectionAttempts: Infinity,
      reconnectionDelay: 1000,
      timeout: 10000
    });

    this.onStateUpdateCallback = null;
    this.onStatusChangeCallback = null;
    this.setupListeners();
    this.fetchInitialState();
  }

  async fetchInitialState() {
    try {
      const res = await fetch(`${this.serverUrl}/api/status`);
      if (res.ok) {
        const data = await res.json();
        console.log('[HTTP] Estado inicial recibido por REST:', data);
        if (this.onStateUpdateCallback) {
          this.onStateUpdateCallback(data);
        }
      }
    } catch (err) {
      console.warn('[HTTP] No se pudo obtener estado inicial por REST:', err.message);
    }
  }

  setupListeners() {
    this.socket.on('connect', () => {
      console.log(`🟢 [WS] Conectado exitosamente con ID: ${this.socket.id}`);
      if (this.onStatusChangeCallback) this.onStatusChangeCallback('ONLINE', true);
    });

    this.socket.on('disconnect', (reason) => {
      console.warn(`🔴 [WS] Desconectado: ${reason}`);
      if (this.onStatusChangeCallback) this.onStatusChangeCallback('OFFLINE', false);
    });

    this.socket.on('connect_error', (error) => {
      console.error(`⚠️ [WS Error] Error de conexión: ${error.message}`);
      if (this.onStatusChangeCallback) this.onStatusChangeCallback('ERROR CONEXIÓN', false);
    });

    this.socket.on('state_snapshot', (state) => {
      if (this.onStateUpdateCallback) this.onStateUpdateCallback(state);
    });

    this.socket.on('state_update', (state) => {
      if (this.onStateUpdateCallback) this.onStateUpdateCallback(state);
    });

    this.socket.on('telemetry_update', (state) => {
      if (this.onStateUpdateCallback) this.onStateUpdateCallback(state);
    });
  }

  onStateUpdate(callback) {
    this.onStateUpdateCallback = callback;
  }

  onStatusChange(callback) {
    this.onStatusChangeCallback = callback;
  }

  toggleLed(pin, state = null) {
    if (this.socket.connected) {
      this.socket.emit('toggle_led', { pin, state });
    } else {
      console.warn(`[WS] No conectado. Intentando enviar por API REST...`);
      // Fallback por REST si WS está reconectando
      fetch(`${this.serverUrl}/api/status`)
        .catch(e => console.error(e));
    }
  }

  setAllLeds(state) {
    if (this.socket.connected) {
      this.socket.emit('set_all_leds', { state });
    }
  }

  setRepeatMode(enabled) {
    if (this.socket.connected) {
      this.socket.emit('set_repeat_mode', { enabled });
    }
  }

  wakeUp() {
    if (this.socket.connected) {
      this.socket.emit('wake_up', {});
    } else {
      fetch(`${this.serverUrl}/api/wake`, { method: 'POST' }).catch(() => {});
    }
  }
}
