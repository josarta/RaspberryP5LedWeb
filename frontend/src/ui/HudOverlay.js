import { PIN_CONFIG_LEFT, PIN_CONFIG_RIGHT } from '../scene/BreakoutBoardMesh.js';

export class HudOverlay {
  constructor(socketClient) {
    this.socketClient = socketClient;
    this.listContainer = document.getElementById('gpio-list');
    this.hwBadge = document.getElementById('hw-mode-badge');
    this.activeCountLabel = document.getElementById('active-count-label');
    this.metricCpu = document.getElementById('metric-cpu');
    this.metricTemp = document.getElementById('metric-temp');
    this.metricRam = document.getElementById('metric-ram');
    this.metricIp = document.getElementById('metric-ip');
    this.logConsole = document.getElementById('log-console');

    this.btnAllOn = document.getElementById('btn-all-on');
    this.btnAllOff = document.getElementById('btn-all-off');
    this.inputHostIp = document.getElementById('input-host-ip');
    this.btnConnectIp = document.getElementById('btn-connect-ip');

    this.renderList();
    this.initActions();
  }

  renderList() {
    this.listContainer.innerHTML = '';

    const allPins = [];
    for (let i = 0; i < 20; i++) {
      allPins.push({ ...PIN_CONFIG_LEFT[i], side: 'L', pinNum: i * 2 + 1 });
      allPins.push({ ...PIN_CONFIG_RIGHT[i], side: 'R', pinNum: (i + 1) * 2 });
    }

    allPins.forEach(item => {
      const row = document.createElement('div');
      row.className = 'terminal-row';
      row.id = item.bcm !== null ? `row-pin-${item.bcm}` : `row-static-${item.side}-${item.pinNum}`;

      if (item.type === 'power3v') {
        row.classList.add('power-pin', 'active-power-3v');
      } else if (item.type === 'power5v') {
        row.classList.add('power-pin', 'active-power-5v');
      } else if (item.type === 'gnd') {
        row.classList.add('power-pin');
      }

      const leftInfo = document.createElement('div');
      leftInfo.style.display = 'flex';
      leftInfo.style.alignItems = 'center';
      leftInfo.style.gap = '8px';

      const dot = document.createElement('div');
      dot.className = 'pin-led-dot';

      const labelText = document.createElement('span');
      labelText.className = 'pin-tag';
      labelText.textContent = item.label;

      const subText = document.createElement('span');
      subText.style.fontSize = '0.7rem';
      subText.style.color = '#64748b';
      subText.textContent = `P${item.pinNum}`;

      leftInfo.appendChild(dot);
      leftInfo.appendChild(labelText);
      leftInfo.appendChild(subText);

      const actionDiv = document.createElement('div');
      if (item.bcm !== null) {
        const toggleBtn = document.createElement('button');
        toggleBtn.className = 'state-toggle';
        toggleBtn.textContent = 'OFF';
        actionDiv.appendChild(toggleBtn);

        row.addEventListener('click', () => {
          this.socketClient.toggleLed(item.bcm);
        });
      } else {
        const typeTag = document.createElement('span');
        typeTag.style.fontSize = '0.7rem';
        typeTag.style.color = item.type === 'gnd' ? '#64748b' : (item.type === 'power3v' ? '#ffaa00' : '#ff3344');
        typeTag.textContent = item.type.toUpperCase();
        actionDiv.appendChild(typeTag);
      }

      row.appendChild(leftInfo);
      row.appendChild(actionDiv);
      this.listContainer.appendChild(row);
    });
  }

  initActions() {
    if (this.btnAllOn) {
      this.btnAllOn.addEventListener('click', () => {
        this.socketClient.setAllLeds(true);
      });
    }
    if (this.btnAllOff) {
      this.btnAllOff.addEventListener('click', () => {
        this.socketClient.setAllLeds(false);
      });
    }

    this.btnToggleRepeat = document.getElementById('btn-toggle-repeat');
    this.repeatMode = false;
    if (this.btnToggleRepeat) {
      this.btnToggleRepeat.addEventListener('click', () => {
        this.repeatMode = !this.repeatMode;
        this.socketClient.setRepeatMode(this.repeatMode);
        this.btnToggleRepeat.textContent = this.repeatMode ? '🔁 EN BUCLE' : '1 VEZ';
        this.btnToggleRepeat.style.color = this.repeatMode ? '#00f0ff' : '#8fa0b3';
        this.btnToggleRepeat.style.borderColor = this.repeatMode ? '#00f0ff' : 'rgba(255,255,255,0.2)';
        this.btnToggleRepeat.style.background = this.repeatMode ? 'rgba(0,240,255,0.15)' : 'rgba(255,255,255,0.1)';
      });
    }

    // Configuración de IP personalizada
    const savedHost = localStorage.getItem('rpi_host_url') || (window.location.hostname ? `http://${window.location.hostname}:8000` : 'http://localhost:8000');
    if (this.inputHostIp) {
      this.inputHostIp.value = savedHost.replace('http://', '').replace(':8000', '');
    }

    if (this.btnConnectIp && this.inputHostIp) {
      this.btnConnectIp.addEventListener('click', () => {
        const val = this.inputHostIp.value.trim();
        if (val) {
          const targetUrl = val.startsWith('http') ? val : `http://${val}:8000`;
          localStorage.setItem('rpi_host_url', targetUrl);
          window.location.reload();
        }
      });
    }
  }

  setStatus(statusText, isOnline) {
    if (this.hwBadge) {
      this.hwBadge.textContent = statusText;
      this.hwBadge.style.color = isOnline ? '#00ff88' : '#ff3366';
      this.hwBadge.style.borderColor = isOnline ? '#00ff88' : '#ff3366';
    }
    const logEntry = document.createElement('div');
    logEntry.textContent = `[${new Date().toLocaleTimeString()}] Red: ${statusText}`;
    if (this.logConsole) {
      this.logConsole.appendChild(logEntry);
      this.logConsole.scrollTop = this.logConsole.scrollHeight;
    }
  }

  update(state) {
    // 1. Estado de GPIOs
    if (state.leds) {
      let activeCount = 0;
      for (const [bcmStr, isOn] of Object.entries(state.leds)) {
        const row = document.getElementById(`row-pin-${bcmStr}`);
        if (row) {
          const btn = row.querySelector('.state-toggle');
          if (isOn) {
            row.classList.add('active');
            if (btn) btn.textContent = 'ON';
            activeCount++;
          } else {
            row.classList.remove('active');
            if (btn) btn.textContent = 'OFF';
          }
        }
      }
      if (this.activeCountLabel) {
        this.activeCountLabel.textContent = `${activeCount} ON`;
      }
    }

    // 2. Hardware Mode
    if (this.hwBadge && state.hardware_mode) {
      this.hwBadge.textContent = state.hardware_mode.toUpperCase();
      this.hwBadge.style.color = state.hardware_mode.includes('Physical') ? '#00ff88' : '#00f0ff';
      this.hwBadge.style.borderColor = state.hardware_mode.includes('Physical') ? '#00ff88' : '#00f0ff';
    }

    // 3. Telemetría
    if (state.metrics) {
      this.metricCpu.textContent = `${state.metrics.cpu_percent.toFixed(1)}%`;
      this.metricTemp.textContent = `${state.metrics.cpu_temp.toFixed(1)}°C`;
      this.metricRam.textContent = `${state.metrics.ram_percent.toFixed(1)}%`;
      this.metricIp.textContent = state.metrics.ip || '127.0.0.1';
    }

    // 4. Logs
    if (state.last_log) {
      const logEntry = document.createElement('div');
      logEntry.textContent = `[${new Date().toLocaleTimeString()}] ${state.last_log}`;
      this.logConsole.appendChild(logEntry);
      this.logConsole.scrollTop = this.logConsole.scrollHeight;

      while (this.logConsole.children.length > 25) {
        this.logConsole.removeChild(this.logConsole.firstChild);
      }
    }
  }
}
