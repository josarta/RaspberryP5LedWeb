import * as THREE from 'three';
import { SceneManager } from './scene/SceneManager.js';
import { BreakoutBoardMesh } from './scene/BreakoutBoardMesh.js';
import { SocketClient } from './network/SocketClient.js';
import { HudOverlay } from './ui/HudOverlay.js';

class App {
  constructor() {
    this.container = document.getElementById('canvas-container');
    this.sceneManager = new SceneManager(this.container);
    this.breakoutBoard = new BreakoutBoardMesh();
    this.sceneManager.scene.add(this.breakoutBoard.group);

    this.socketClient = new SocketClient();
    this.hud = new HudOverlay(this.socketClient);

    this.raycaster = new THREE.Raycaster();
    this.mouse = new THREE.Vector2();
    this.hoveredObject = null;
    this.isOledPressed = false;

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
      // Evitar clics sobre los paneles HUD 2D
      if (e.target.closest('.hud-panel') || e.target.closest('.top-hint')) return;

      this.raycaster.setFromCamera(this.mouse, this.sceneManager.camera);
      const intersects = this.raycaster.intersectObjects(this.breakoutBoard.clickableObjects, true);

      if (intersects.length > 0) {
        const hit = intersects[0].object;
        if (hit.userData && hit.userData.isGPIO) {
          const pin = hit.userData.pin;
          this.socketClient.toggleLed(pin);
        } else if (hit.userData && hit.userData.isOLED) {
          this.isOledPressed = true;
          if (this.socketClient.socket) {
            this.socketClient.socket.emit('touch_event', { action: 'down' });
          }
        }
      }
    });

    window.addEventListener('pointerup', () => {
      if (this.isOledPressed) {
        this.isOledPressed = false;
        if (this.socketClient.socket) {
          this.socketClient.socket.emit('touch_event', { action: 'up' });
        }
      }
    });
  }

  initNetworking() {
    this.socketClient.onStatusChange((statusText, isOnline) => {
      this.hud.setStatus(statusText, isOnline);
    });

    this.socketClient.onStateUpdate((state) => {
      this.breakoutBoard.updateState(state);
      this.hud.update(state);
    });
  }

  animate() {
    requestAnimationFrame(this.animate.bind(this));
    this.sceneManager.render();
  }
}

new App();
