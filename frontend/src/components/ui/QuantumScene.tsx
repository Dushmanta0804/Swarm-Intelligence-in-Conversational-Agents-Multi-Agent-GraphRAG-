"use client";

import { useEffect, useRef } from "react";
import * as THREE from "three";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

export function QuantumScene() {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    gsap.registerPlugin(ScrollTrigger);

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({
        antialias: true,
        alpha: true,
        powerPreference: "high-performance",
      });
    } catch (error) {
      console.error("Unable to initialize the animated WebGL background.", error);
      return;
    }

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(
      40,
      window.innerWidth / window.innerHeight,
      0.1,
      100,
    );
    camera.position.set(0, 0, 9.5);
    renderer.setClearColor(0x000000, 0);
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.75));
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.25;
    renderer.domElement.setAttribute("aria-hidden", "true");
    container.appendChild(renderer.domElement);

    scene.add(new THREE.AmbientLight(0xffffff, 0.4));

    const keyLight = new THREE.PointLight(0x00f5d4, 3.5, 30);
    keyLight.position.set(6, 6, 8);
    scene.add(keyLight);

    const plasmaLight = new THREE.PointLight(0x7928ca, 3, 30);
    plasmaLight.position.set(-6, -5, 5);
    scene.add(plasmaLight);

    const goldLight = new THREE.PointLight(0xf6e05e, 2, 25);
    goldLight.position.set(0, 8, -6);
    scene.add(goldLight);

    const quantumGroup = new THREE.Group();
    quantumGroup.position.set(1.5, 0, 0);
    scene.add(quantumGroup);

    const sphere = new THREE.Mesh(
      new THREE.SphereGeometry(2.2, 24, 24),
      new THREE.MeshBasicMaterial({
        color: 0x00f5d4,
        transparent: true,
        opacity: 0.18,
        wireframe: true,
      }),
    );
    quantumGroup.add(sphere);

    const ringMaterial = new THREE.MeshStandardMaterial({
      color: 0x1e293b,
      metalness: 0.95,
      roughness: 0.15,
    });
    const equatorRing = new THREE.Mesh(
      new THREE.TorusGeometry(2.2, 0.016, 16, 120),
      ringMaterial,
    );
    equatorRing.rotation.x = Math.PI / 2;
    quantumGroup.add(equatorRing);

    const meridianRing = new THREE.Mesh(
      new THREE.TorusGeometry(2.2, 0.016, 16, 120),
      ringMaterial,
    );
    quantumGroup.add(meridianRing);

    const crystalGeometry = new THREE.OctahedronGeometry(1.15, 0);
    const crystalMaterial = new THREE.MeshPhysicalMaterial({
      color: 0x030508,
      emissive: 0x0a1628,
      roughness: 0.05,
      metalness: 0.2,
      transmission: 0.94,
      ior: 1.6,
      transparent: true,
      opacity: 0.9,
      reflectivity: 0.95,
    });
    const crystal = new THREE.Mesh(crystalGeometry, crystalMaterial);
    quantumGroup.add(crystal);

    const crystalEdges = new THREE.LineSegments(
      new THREE.EdgesGeometry(crystalGeometry),
      new THREE.LineBasicMaterial({
        color: 0x00f5d4,
        transparent: true,
        opacity: 0.45,
      }),
    );
    quantumGroup.add(crystalEdges);

    const particleCount = window.innerWidth < 700 ? 600 : 1200;
    const positions = new Float32Array(particleCount * 3);
    const originals = new Float32Array(particleCount * 3);
    const velocitiesX = new Float32Array(particleCount);
    const velocitiesY = new Float32Array(particleCount);
    const colors = new Float32Array(particleCount * 3);
    const cyan = new THREE.Color("#00F5D4");
    const plasma = new THREE.Color("#7928CA");
    const gold = new THREE.Color("#F6E05E");

    for (let i = 0; i < particleCount; i += 1) {
      const radius = 1.3 + Math.random() ** 2 * 1.8;
      const theta = Math.acos(2 * Math.random() - 1);
      const phi = 2 * Math.PI * Math.random();
      const x = radius * Math.sin(theta) * Math.cos(phi);
      const y = radius * Math.sin(theta) * Math.sin(phi);
      const z = radius * Math.cos(theta);
      const offset = i * 3;

      positions[offset] = originals[offset] = x;
      positions[offset + 1] = originals[offset + 1] = y;
      positions[offset + 2] = originals[offset + 2] = z;

      const colorMix = Math.random();
      const color =
        colorMix < 0.6
          ? cyan.clone().lerp(plasma, colorMix)
          : plasma.clone().lerp(gold, colorMix);
      colors[offset] = color.r;
      colors[offset + 1] = color.g;
      colors[offset + 2] = color.b;
    }

    const particleGeometry = new THREE.BufferGeometry();
    const positionAttribute = new THREE.BufferAttribute(positions, 3);
    particleGeometry.setAttribute("position", positionAttribute);
    particleGeometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));
    const particleMaterial = new THREE.PointsMaterial({
      size: 0.03,
      vertexColors: true,
      transparent: true,
      opacity: 0.75,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });
    const probabilityCloud = new THREE.Points(particleGeometry, particleMaterial);
    quantumGroup.add(probabilityCloud);

    const qubitCoordinates = [
      new THREE.Vector3(0, 0, 0),
      new THREE.Vector3(-1.4, 1.1, 0.4),
      new THREE.Vector3(1.5, -0.8, -0.5),
      new THREE.Vector3(-0.8, -1.5, 0.7),
      new THREE.Vector3(1.2, 1.3, 0.6),
      new THREE.Vector3(0.2, -1.8, -1),
    ];
    const qubitColors = [0x00f5d4, 0x7928ca, 0x7928ca, 0x10b981, 0x10b981, 0xf6e05e];
    const qubitMeshes: THREE.Mesh[] = [];

    qubitCoordinates.forEach((coordinate, index) => {
      const qubit = new THREE.Mesh(
        new THREE.SphereGeometry(index === 0 ? 0.18 : 0.09, 24, 24),
        new THREE.MeshStandardMaterial({
          color: qubitColors[index],
          emissive: qubitColors[index],
          emissiveIntensity: 2.5,
          roughness: 0.15,
        }),
      );
      qubit.position.copy(coordinate);
      quantumGroup.add(qubit);
      qubitMeshes.push(qubit);
    });

    const strandCurves = [
      [qubitCoordinates[0], new THREE.Vector3(-0.6, 0.5, 0.3), qubitCoordinates[1]],
      [qubitCoordinates[0], new THREE.Vector3(0.7, -0.3, -0.2), qubitCoordinates[2]],
      [qubitCoordinates[1], new THREE.Vector3(-1.1, -0.4, 0.7), qubitCoordinates[3]],
      [qubitCoordinates[2], new THREE.Vector3(1.3, 0.4, 0.2), qubitCoordinates[4]],
      [qubitCoordinates[3], new THREE.Vector3(-0.2, -1.6, -0.2), qubitCoordinates[5]],
    ];
    strandCurves.forEach((points, index) => {
      const geometry = new THREE.BufferGeometry().setFromPoints(
        new THREE.CatmullRomCurve3(points).getPoints(50),
      );
      quantumGroup.add(
        new THREE.Line(
          geometry,
          new THREE.LineBasicMaterial({
            color: index === 4 ? 0xf6e05e : 0x00f5d4,
            transparent: true,
            opacity: 0.55,
          }),
        ),
      );
    });

    const shockRingMaterial = new THREE.MeshBasicMaterial({
      color: 0x00f5d4,
      transparent: true,
      opacity: 0,
      side: THREE.DoubleSide,
      depthWrite: false,
    });
    const shockRing = new THREE.Mesh(
      new THREE.RingGeometry(0.1, 0.18, 64),
      shockRingMaterial,
    );
    quantumGroup.add(shockRing);

    const mouse = { x: 0, y: 0, targetX: 0, targetY: 0 };
    const mouseNdc = new THREE.Vector2();
    const raycaster = new THREE.Raycaster();
    const onMouseMove = (event: MouseEvent) => {
      mouse.targetX = (event.clientX / window.innerWidth - 0.5) * 2;
      mouse.targetY = -(event.clientY / window.innerHeight - 0.5) * 2;
      mouseNdc.set(mouse.targetX, mouse.targetY);
      const display = document.getElementById("coordDisplay");
      if (display) {
        display.textContent = `BLOCH_VECTOR: [${mouse.targetX.toFixed(2)}, 1.00, ${(-mouse.targetY).toFixed(2)}]`;
      }
    };

    const igniteCollapse = (origin = new THREE.Vector3()) => {
      shockRing.position.copy(origin);
      shockRing.scale.setScalar(0.4);
      shockRingMaterial.opacity = 1;
      gsap.killTweensOf(shockRing.scale);
      gsap.killTweensOf(shockRingMaterial);
      gsap.to(shockRing.scale, {
        x: 28,
        y: 28,
        z: 28,
        duration: 1.2,
        ease: "power2.out",
      });
      gsap.to(shockRingMaterial, { opacity: 0, duration: 1.2, ease: "power2.out" });
      gsap.fromTo(
        crystalMaterial.emissive,
        { r: 0, g: 0.08, b: 0.16 },
        { r: 0, g: 0.96, b: 0.83, duration: 0.12, yoyo: true, repeat: 1 },
      );
      gsap.fromTo(
        camera.position,
        { z: 9.2 },
        { z: 9.5, duration: 0.7, ease: "elastic.out(1, 0.35)" },
      );
    };

    const onWindowClick = (event: MouseEvent) => {
      mouseNdc.set(
        (event.clientX / window.innerWidth) * 2 - 1,
        -(event.clientY / window.innerHeight) * 2 + 1,
      );
      raycaster.setFromCamera(mouseNdc, camera);
      const [hit] = raycaster.intersectObjects(qubitMeshes);
      if (!hit) return;
      gsap.fromTo(
        hit.object.scale,
        { x: 2.2, y: 2.2, z: 2.2 },
        { x: 1, y: 1, z: 1, duration: 0.8, ease: "elastic.out(1, 0.3)" },
      );
      igniteCollapse(hit.object.position);
    };

    const timeline = gsap.timeline({
      scrollTrigger: {
        trigger: ".scroll-orchestration",
        start: "top top",
        end: "bottom bottom",
        scrub: 1.4,
      },
    });
    timeline
      .to(quantumGroup.position, { x: -1.7, y: 0.15, z: 0.4, ease: "power2.inOut" }, 0)
      .to(quantumGroup.rotation, { x: 0.6, y: 1.8, z: 0.2, ease: "power2.inOut" }, 0)
      .to(crystal.scale, { x: 1.35, y: 0.65, z: 1.35, ease: "power2.inOut" }, 0)
      .to(quantumGroup.position, { x: 1.6, y: -0.2, z: 1.1, ease: "power2.inOut" }, 1)
      .to(quantumGroup.rotation, { x: -0.35, y: 3.5, z: -0.25, ease: "power2.inOut" }, 1)
      .to(particleMaterial, { size: 0.045, ease: "power2.inOut" }, 1)
      .to(quantumGroup.position, { x: -0.1, y: 0, z: -0.4, ease: "power2.inOut" }, 2)
      .to(quantumGroup.rotation, { x: 0, y: 5.2, z: 0, ease: "power2.inOut" }, 2)
      .to(crystal.scale, { x: 1, y: 1, z: 1, ease: "power2.inOut" }, 2);

    const onCollapseEvent = () => igniteCollapse();
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("click", onWindowClick);
    window.addEventListener("quantum-collapse", onCollapseEvent);

    const animationStart = performance.now();
    let frameId = 0;
    const render = () => {
      frameId = window.requestAnimationFrame(render);
      const elapsed = (performance.now() - animationStart) / 1000;
      equatorRing.rotation.z = elapsed * 0.14;
      meridianRing.rotation.y = elapsed * 0.18;
      crystal.rotation.y = elapsed * 0.08;
      crystal.rotation.x = Math.sin(elapsed * 0.2) * 0.1;
      crystalEdges.rotation.copy(crystal.rotation);

      const mouseWorldX = mouse.x * 3.5;
      const mouseWorldY = mouse.y * 3.5;
      for (let i = 0; i < particleCount; i += 1) {
        const offset = i * 3;
        const x = positions[offset];
        const y = positions[offset + 1];
        const dx = mouseWorldX - x;
        const dy = mouseWorldY - y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        if (distance < 2.4) {
          const force = (2.4 - distance) * 0.035;
          velocitiesX[i] += dx * force;
          velocitiesY[i] += dy * force;
        }
        velocitiesX[i] += (originals[offset] - x) * 0.018;
        velocitiesY[i] += (originals[offset + 1] - y) * 0.018;
        velocitiesX[i] *= 0.88;
        velocitiesY[i] *= 0.88;
        positions[offset] += velocitiesX[i];
        positions[offset + 1] += velocitiesY[i];
      }
      positionAttribute.needsUpdate = true;
      probabilityCloud.rotation.y = -elapsed * 0.04;

      mouse.x += (mouse.targetX - mouse.x) * 0.045;
      mouse.y += (mouse.targetY - mouse.y) * 0.045;
      camera.position.x = mouse.x * 0.4;
      camera.position.y = mouse.y * 0.4;
      camera.lookAt(0, 0, 0);
      renderer.render(scene, camera);
    };

    const onResize = () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.75));
    };

    window.addEventListener("resize", onResize);
    render();

    return () => {
      window.cancelAnimationFrame(frameId);
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("click", onWindowClick);
      window.removeEventListener("quantum-collapse", onCollapseEvent);
      window.removeEventListener("resize", onResize);
      timeline.scrollTrigger?.kill();
      timeline.kill();
      scene.traverse((object) => {
        if (object instanceof THREE.Mesh || object instanceof THREE.Line || object instanceof THREE.Points) {
          object.geometry.dispose();
          const materials = Array.isArray(object.material) ? object.material : [object.material];
          materials.forEach((material) => material.dispose());
        }
      });
      renderer.dispose();
      container.removeChild(renderer.domElement);
    };
  }, []);

  return <div ref={containerRef} className="canvas-container" aria-hidden="true" />;
}
