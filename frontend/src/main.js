import * as THREE from 'three';
import { SceneManager } from './scene/SceneManager.js';
import { BreakoutBoardMesh } from './scene/BreakoutBoardMesh.js';
import { SocketClient } from './network/SocketClient.js';
import { HudOverlay } from './ui/HudOverlay.js';
import { AudioFeedback } from './audio/AudioFeedback.js';

class App {
  constructor() {
    this.container = document.getElementById('canvas-container');
    this.sceneManager = new SceneManager(this.container);
    this.breakoutBoard = new BreakoutBoardMesh();
    this.sceneManager.scene.add(this.breakoutBoard.group);

    this.audio = new AudioFeedback();
    this.socketClient = new SocketClient();
    this.hud = new HudOverlay(this.socketClient, this.audio);

    this.raycaster = new THREE.Raycaster();
    this.mouse = new THREE.Vector2();
    this.hoveredObject = null;

    this.previousLedStates = {};

    this.initInteraction();
    this.initNetworking();
    this.animate();

    setTimeout(() => {
      const loader = document.getElementById('loading-screen');
      if (loader) loader.style.display = 'none';
    }, 500);
  }

  initInteraction() {
    window.addEventListener('mousemove', (e) => {
      this.mouse.x = (e.clientX / window.innerWidth) * 2 - 1;
      this.mouse.y = -(e.clientY / window.innerHeight) * 2 + 1;

      this.raycaster.setFromCamera(this.mouse, this.sceneManager.camera);
      const intersects = this.raycaster.intersectObjects(this.breakoutBoard.clickableObjects, true);

      if (intersects.length > 0) {
        document.body.style.cursor = 'pointer';
        this.hoveredObject = intersects[0].object;
      } else {
        document.body.style.cursor = 'default';
        this.hoveredObject = null;
      }
    });

    window.addEventListener('pointerdown', (e) => {
      // Activar contexto de audio con la primera interacción del usuario
      this.audio.initContext();

      // Evitar clics sobre los paneles HUD 2D
      if (e.target.closest('.hud-panel') || e.target.closest('.top-hint')) return;

      this.raycaster.setFromCamera(this.mouse, this.sceneManager.camera);
      const intersects = this.raycaster.intersectObjects(this.breakoutBoard.clickableObjects, true);

      if (intersects.length > 0) {
        const hit = intersects[0].object;
        if (hit.userData && hit.userData.isGPIO) {
          const pin = hit.userData.pin;
          this.socketClient.toggleLed(pin);
        }
      }
    });
  }

  initNetworking() {
    this.socketClient.onStatusChange((statusText, isOnline) => {
      this.hud.setStatus(statusText, isOnline);
    });

    this.socketClient.onStateUpdate((state) => {
      this.checkAudioTriggers(state);
      this.breakoutBoard.updateState(state);
      this.hud.update(state);
    });
  }

  checkAudioTriggers(state) {
    if (!state.leds) return;

    let turnedOnCount = 0;
    let turnedOffCount = 0;

    for (const [pin, isOn] of Object.entries(state.leds)) {
      const prev = this.previousLedStates[pin];
      if (prev !== undefined) {
        if (!prev && isOn) {
          turnedOnCount++;
        } else if (prev && !isOn) {
          turnedOffCount++;
        }
      }
      this.previousLedStates[pin] = isOn;
    }

    // Reproducir sonido adecuado
    if (turnedOnCount > 0) {
      this.audio.playLedOn();
    } else if (turnedOffCount > 0) {
      this.audio.playLedOff();
    }
  }

  animate() {
    requestAnimationFrame(this.animate.bind(this));
    this.sceneManager.render();
  }
}

new App();
