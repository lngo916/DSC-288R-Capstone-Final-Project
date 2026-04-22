import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";

// =====================
// SCENE
// =====================
const scene = new THREE.Scene();

// =====================
// CONTAINER
// =====================
const container = document.getElementById("container3D");

if (!container) throw new Error("container3D not found");

// =====================
// CAMERA (Apple framing)
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
// LIGHTING (SOFT APPLE STYLE)
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

loader.load("/images/steam2.glb", (gltf) => {
  object = gltf.scene;
  scene.add(object);

  // center model
  const box = new THREE.Box3().setFromObject(object);
  const center = box.getCenter(new THREE.Vector3());
  object.position.sub(center);

  // Apple-style framing (NOT too big, not too small)
  object.scale.set(1.3, 1.3, 1.3);

  object.position.x -= 0.3;
  object.position.y -= 0.8;

  // animations if exist
  if (gltf.animations.length > 0) {
    mixer = new THREE.AnimationMixer(object);
    gltf.animations.forEach((clip) =>
      mixer.clipAction(clip).play()
    );
  }
});

// =====================
// SCROLL-DRIVEN CINEMATIC MOTION
// =====================
let scrollY = 0;

window.addEventListener("scroll", () => {
  scrollY = window.scrollY;
});

// =====================
// ANIMATE LOOP
// =====================
function animate() {
  requestAnimationFrame(animate);

  const delta = clock.getDelta();

  if (mixer) mixer.update(delta);

  if (object) {
    object.rotation.y = 0.1; // fixed angle
    object.rotation.x = Math.sin(Date.now() * 0.001) * 0.02; // subtle breathing motion

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


// MACHINE LEARNING 

document.addEventListener('DOMContentLoaded', () => {
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
