import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";

document.addEventListener("DOMContentLoaded", () => {

  // =====================
  // CONTAINER
  // =====================
  const container = document.getElementById("container3D");

  if (!container) {
    console.error("container3D not found");
    return;
  }

  // =====================
  // SCENE
  // =====================
  const scene = new THREE.Scene();

  // =====================
  // CAMERA
  // =====================
  const camera = new THREE.PerspectiveCamera(
    50,
    container.clientWidth / container.clientHeight,
    0.1,
    1000
  );

  camera.position.set(0, 0.2, 8);

  // =====================
  // RENDERER
  // =====================
  const renderer = new THREE.WebGLRenderer({
    alpha: true,
    antialias: true
  });

  renderer.setSize(container.clientWidth, container.clientHeight);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  container.appendChild(renderer.domElement);

  // =====================
  // LIGHTING
  // =====================
  scene.add(new THREE.AmbientLight(0xffffff, 1.1));

  const key = new THREE.DirectionalLight(0xffffff, 1.2);
  key.position.set(3, 5, 2);
  scene.add(key);

  const rim = new THREE.DirectionalLight(0x9cbfe2, 1.0);
  rim.position.set(-5, 3, -5);
  scene.add(rim);

  // =====================
  // MODEL
  // =====================
  let object;
  let mixer;
  const clock = new THREE.Clock();
  const loader = new GLTFLoader();

  loader.load(
    "images/steam2.glb",

    (gltf) => {
      console.log("GLB loaded successfully");

      object = gltf.scene;
      scene.add(object);

      const box = new THREE.Box3().setFromObject(object);
      const center = box.getCenter(new THREE.Vector3());
      object.position.sub(center);

      object.scale.set(1.3, 1.3, 1.3);
      object.position.x -= 0.3;
      object.position.y -= 0.8;

      if (gltf.animations.length > 0) {
        mixer = new THREE.AnimationMixer(object);
        gltf.animations.forEach((clip) =>
          mixer.clipAction(clip).play()
        );
      }
    },

    undefined,

    (error) => {
      console.error("GLB failed to load:", error);
    }
  );

  // =====================
  // SCROLL
  // =====================
  let scrollY = 0;

  window.addEventListener("scroll", () => {
    scrollY = window.scrollY;
  });

  // =====================
  // ANIMATE
  // =====================
  function animate() {
    requestAnimationFrame(animate);

    const delta = clock.getDelta();

    if (mixer) mixer.update(delta);

    if (object) {
      object.rotation.y = 0.1;
      object.rotation.x = Math.sin(Date.now() * 0.001) * 0.02;
      object.position.y = -0.8 + scrollY * -0.0002;
    }

    renderer.render(scene, camera);
  }

  animate();

  // =====================
  // RESIZE
  // =====================
  window.addEventListener("resize", () => {
    const w = container.clientWidth;
    const h = container.clientHeight;

    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
  });

  // =====================
  // MACHINE LEARNING (unchanged)
  // =====================
  const mlTrack = document.getElementById('ml-track');
  const mlCounter = document.getElementById('ml-counter');
  const mlSlides = document.querySelectorAll('.carousel-slide');
  const mlTotal = mlSlides.length;
  let mlCurrent = 0;

  function mlGoTo(index) {
    mlCurrent = (index + mlTotal) % mlTotal;
    mlTrack.style.transform = `translateX(-${mlCurrent * 100}%)`;
    mlCounter.textContent = `${mlCurrent + 1} / ${mlTotal}`;
  }

  document.getElementById('ml-prev').addEventListener('click', () => mlGoTo(mlCurrent - 1));
  document.getElementById('ml-next').addEventListener('click', () => mlGoTo(mlCurrent + 1));

});
