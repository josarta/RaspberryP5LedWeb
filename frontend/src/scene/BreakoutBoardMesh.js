import * as THREE from 'three';
import { VirtualOLED } from './VirtualOLED.js';

export const PIN_CONFIG_LEFT = [
  { label: '+3V3', type: 'power3v', bcm: null, color: 0xffaa00 },
  { label: 'SDA1', type: 'gpio', bcm: 2, color: 0x00ff88 },
  { label: 'SCL1', type: 'gpio', bcm: 3, color: 0x00ff88 },
  { label: 'IO4', type: 'gpio', bcm: 4, color: 0x00ff88 },
  { label: 'GND', type: 'gnd', bcm: null, color: 0x222222 },
  { label: 'IO17', type: 'gpio', bcm: 17, color: 0x00ff88 },
  { label: 'IO27', type: 'gpio', bcm: 27, color: 0x00ff88 },
  { label: 'IO22', type: 'gpio', bcm: 22, color: 0x00ff88 },
  { label: '+3V3', type: 'power3v', bcm: null, color: 0xffaa00 },
  { label: 'IO10', type: 'gpio', bcm: 10, color: 0x00ff88 },
  { label: 'IO9', type: 'gpio', bcm: 9, color: 0x00ff88 },
  { label: 'IO11', type: 'gpio', bcm: 11, color: 0x00ff88 },
  { label: 'GND', type: 'gnd', bcm: null, color: 0x222222 },
  { label: 'IO0', type: 'gpio', bcm: 0, color: 0x00ff88 },
  { label: 'IO5', type: 'gpio', bcm: 5, color: 0x00ff88 },
  { label: 'IO6', type: 'gpio', bcm: 6, color: 0x00ff88 },
  { label: 'IO13', type: 'gpio', bcm: 13, color: 0x00ff88 },
  { label: 'IO19', type: 'gpio', bcm: 19, color: 0x00ff88 },
  { label: 'IO26', type: 'gpio', bcm: 26, color: 0x00ff88 },
  { label: 'GND', type: 'gnd', bcm: null, color: 0x222222 }
];

export const PIN_CONFIG_RIGHT = [
  { label: '+5V', type: 'power5v', bcm: null, color: 0xff3344 },
  { label: '+5V', type: 'power5v', bcm: null, color: 0xff3344 },
  { label: 'GND', type: 'gnd', bcm: null, color: 0x222222 },
  { label: 'IO14', type: 'gpio', bcm: 14, color: 0x00ff88 },
  { label: 'IO15', type: 'gpio', bcm: 15, color: 0x00ff88 },
  { label: 'IO18', type: 'gpio', bcm: 18, color: 0x00ff88 },
  { label: 'GND', type: 'gnd', bcm: null, color: 0x222222 },
  { label: 'IO23', type: 'gpio', bcm: 23, color: 0x00ff88 },
  { label: 'IO24', type: 'gpio', bcm: 24, color: 0x00ff88 },
  { label: 'GND', type: 'gnd', bcm: null, color: 0x222222 },
  { label: 'IO25', type: 'gpio', bcm: 25, color: 0x00ff88 },
  { label: 'IO8', type: 'gpio', bcm: 8, color: 0x00ff88 },
  { label: 'IO7', type: 'gpio', bcm: 7, color: 0x00ff88 },
  { label: 'IO1', type: 'gpio', bcm: 1, color: 0x00ff88 },
  { label: 'GND', type: 'gnd', bcm: null, color: 0x222222 },
  { label: 'IO12', type: 'gpio', bcm: 12, color: 0x00ff88 },
  { label: 'GND', type: 'gnd', bcm: null, color: 0x222222 },
  { label: 'IO16', type: 'gpio', bcm: 16, color: 0x00ff88 },
  { label: 'IO20', type: 'gpio', bcm: 20, color: 0x00ff88 },
  { label: 'IO21', type: 'gpio', bcm: 21, color: 0x00ff88 }
];

export class BreakoutBoardMesh {
  constructor() {
    this.group = new THREE.Group();
    this.virtualOled = new VirtualOLED();
    this.ledMap = new Map();
    this.clickableObjects = [];

    this.buildPCB();
    this.buildTerminalBlocks();
    this.buildCenterHeaders();
    this.buildSMDLeds();
    this.buildOledModule();
  }

  buildPCB() {
    const pcbGeo = new THREE.BoxGeometry(9.2, 0.16, 9.2);
    const pcbMat = new THREE.MeshStandardMaterial({
      color: 0x0b6623,
      roughness: 0.45,
      metalness: 0.15
    });
    const pcb = new THREE.Mesh(pcbGeo, pcbMat);
    pcb.receiveShadow = true;
    this.group.add(pcb);

    const holePositions = [
      [-4.1, 0.09, -4.1],
      [4.1, 0.09, -4.1],
      [-4.1, 0.09, 4.1],
      [4.1, 0.09, 4.1]
    ];
    const ringGeo = new THREE.RingGeometry(0.18, 0.35, 16);
    ringGeo.rotateX(-Math.PI / 2);
    const goldMat = new THREE.MeshStandardMaterial({ color: 0xd4af37, metalness: 0.9, roughness: 0.2 });

    holePositions.forEach(pos => {
      const ring = new THREE.Mesh(ringGeo, goldMat);
      ring.position.set(pos[0], pos[1], pos[2]);
      this.group.add(ring);
    });
  }

  buildTerminalBlocks() {
    const blockMat = new THREE.MeshStandardMaterial({
      color: 0x1e824c,
      roughness: 0.6
    });
    const screwMat = new THREE.MeshStandardMaterial({
      color: 0xcccccc,
      metalness: 0.9,
      roughness: 0.25
    });

    const screwGeo = new THREE.CylinderGeometry(0.12, 0.12, 0.06, 12);

    [-3.8, 3.8].forEach((xPos, colIdx) => {
      const blockGeo = new THREE.BoxGeometry(1.4, 0.85, 7.8);
      const block = new THREE.Mesh(blockGeo, blockMat);
      block.position.set(xPos, 0.5, 0);
      block.castShadow = true;
      this.group.add(block);

      for (let i = 0; i < 20; i++) {
        const zPos = -3.42 + i * 0.36;
        const screw = new THREE.Mesh(screwGeo, screwMat);
        screw.position.set(xPos, 0.94, zPos);
        this.group.add(screw);

        const wireHoleGeo = new THREE.BoxGeometry(0.5, 0.3, 0.25);
        const holeMat = new THREE.MeshBasicMaterial({ color: 0x050505 });
        const hole = new THREE.Mesh(wireHoleGeo, holeMat);
        hole.position.set(xPos + (colIdx === 0 ? -0.45 : 0.45), 0.5, zPos);
        this.group.add(hole);
      }
    });
  }

  buildCenterHeaders() {
    const baseGeo = new THREE.BoxGeometry(1.1, 0.5, 7.6);
    const baseMat = new THREE.MeshStandardMaterial({ color: 0x111111, roughness: 0.9 });
    const headerBase = new THREE.Mesh(baseGeo, baseMat);
    headerBase.position.set(0, 0.33, 0);
    this.group.add(headerBase);

    const pinGeo = new THREE.CylinderGeometry(0.035, 0.035, 0.55, 8);
    const pinMat = new THREE.MeshStandardMaterial({ color: 0xffd700, metalness: 0.95, roughness: 0.1 });

    for (let i = 0; i < 20; i++) {
      const zPos = -3.42 + i * 0.36;
      [-0.2, 0.2].forEach(xPos => {
        const pin = new THREE.Mesh(pinGeo, pinMat);
        pin.position.set(xPos, 0.72, zPos);
        this.group.add(pin);
      });
    }
  }

  buildSMDLeds() {
    const ledGeo = new THREE.BoxGeometry(0.18, 0.1, 0.22);

    const setupSide = (configList, xOffset, colKey) => {
      configList.forEach((cfg, idx) => {
        const zPos = -3.42 + idx * 0.36;

        const isPower = cfg.type === 'power3v' || cfg.type === 'power5v';
        const isGnd = cfg.type === 'gnd';

        const mat = new THREE.MeshPhysicalMaterial({
          color: cfg.color,
          emissive: isPower ? cfg.color : 0x000000,
          emissiveIntensity: isPower ? 1.8 : 0.0,
          roughness: 0.2,
          metalness: 0.1,
          transmission: 0.3,
          transparent: true,
          opacity: 0.9
        });

        const ledMesh = new THREE.Mesh(ledGeo, mat);
        ledMesh.position.set(xOffset, 0.14, zPos);
        this.group.add(ledMesh);

        const pLight = new THREE.PointLight(cfg.color, isPower ? 0.6 : 0, 1.2, 2);
        pLight.position.set(xOffset, 0.3, zPos);
        this.group.add(pLight);

        if (cfg.bcm !== null) {
          const clickBoxGeo = new THREE.BoxGeometry(0.8, 0.6, 0.32);
          const clickMat = new THREE.MeshBasicMaterial({ visible: false });
          const clickMesh = new THREE.Mesh(clickBoxGeo, clickMat);
          clickMesh.position.set(xOffset * 1.4, 0.5, zPos);
          clickMesh.userData = { isGPIO: true, pin: cfg.bcm, label: cfg.label, ledMesh, mat, pLight };
          this.group.add(clickMesh);
          this.clickableObjects.push(clickMesh);

          this.ledMap.set(String(cfg.bcm), {
            mesh: ledMesh,
            material: mat,
            light: pLight,
            config: cfg,
            isOn: false
          });
        }
      });
    };

    setupSide(PIN_CONFIG_LEFT, -1.9, 'left');
    setupSide(PIN_CONFIG_RIGHT, 1.9, 'right');
  }

  buildOledModule() {
    // Pantalla OLED SSD1306 posicionada ARRIBA (Norte) de la placa
    const oledGroup = new THREE.Group();
    oledGroup.position.set(0, 0.45, -6.0); // Posicionada arriba para dejar la board 100% visible

    // PCB del módulo OLED
    const oledPcbGeo = new THREE.BoxGeometry(3.6, 0.1, 2.6);
    const oledPcbMat = new THREE.MeshStandardMaterial({ color: 0x0a1e3f, roughness: 0.4 });
    const oledPcb = new THREE.Mesh(oledPcbGeo, oledPcbMat);
    oledGroup.add(oledPcb);

    // Marco negro del cristal
    const frameGeo = new THREE.BoxGeometry(3.3, 0.08, 1.8);
    const frameMat = new THREE.MeshStandardMaterial({ color: 0x050505, roughness: 0.1 });
    const frame = new THREE.Mesh(frameGeo, frameMat);
    frame.position.set(0, 0.08, 0.1);
    oledGroup.add(frame);

    // Pantalla emisiva con CanvasTexture de alta resolución
    const screenGeo = new THREE.PlaneGeometry(3.1, 1.6);
    screenGeo.rotateX(-Math.PI / 2);

    const screenMat = new THREE.MeshStandardMaterial({
      map: this.virtualOled.getTexture(),
      emissiveMap: this.virtualOled.getTexture(),
      emissive: 0xffffff,
      emissiveIntensity: 1.4,
      roughness: 0.2,
      metalness: 0.1
    });

    const screenMesh = new THREE.Mesh(screenGeo, screenMat);
    screenMesh.position.set(0, 0.14, 0.1);
    screenMesh.userData = { isOLED: true };
    oledGroup.add(screenMesh);
    this.clickableObjects.push(screenMesh);

    // Cables de conexión flexibles simulados (I2C: VCC, GND, SCL, SDA hacia la parte superior)
    const curvePoints = [
      [new THREE.Vector3(-1.2, 0.1, -4.8), new THREE.Vector3(-3.8, 0.6, -3.42), 0xffaa00], // 3V3
      [new THREE.Vector3(-0.4, 0.1, -4.8), new THREE.Vector3(-3.8, 0.6, -3.06), 0x00f0ff], // SDA
      [new THREE.Vector3(0.4, 0.1, -4.8),  new THREE.Vector3(-3.8, 0.6, -2.70), 0xff00ff], // SCL
      [new THREE.Vector3(1.2, 0.1, -4.8),  new THREE.Vector3(-3.8, 0.6, -1.98), 0x222222]  // GND
    ];

    curvePoints.forEach(([pStart, pEnd, colorHex]) => {
      const curve = new THREE.QuadraticBezierCurve3(
        pStart,
        new THREE.Vector3((pStart.x + pEnd.x) / 2, 1.8, (pStart.z + pEnd.z) / 2),
        pEnd
      );
      const tubeGeo = new THREE.TubeGeometry(curve, 20, 0.04, 8, false);
      const tubeMat = new THREE.MeshStandardMaterial({ color: colorHex, roughness: 0.5 });
      this.group.add(new THREE.Mesh(tubeGeo, tubeMat));
    });

    this.group.add(oledGroup);
  }

  updateState(stateData) {
    if (stateData.leds) {
      for (const [pinStr, isOn] of Object.entries(stateData.leds)) {
        const item = this.ledMap.get(pinStr);
        if (item) {
          item.isOn = Boolean(isOn);
          if (item.isOn) {
            item.material.emissive.setHex(item.config.color);
            item.material.emissiveIntensity = 2.5;
            item.light.intensity = 1.6;
          } else {
            item.material.emissive.setHex(0x000000);
            item.material.emissiveIntensity = 0.0;
            item.light.intensity = 0.0;
          }
        }
      }
    }

    this.virtualOLED = this.virtualOled;
    this.virtualOled.update(stateData);
  }
}
