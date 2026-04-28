import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";

function wrapLetters(el) {
  const text = el.innerText; // IMPORTANT: use innerText, not innerHTML
  el.innerHTML = "";

  [...text].forEach((char, i) => {
    const span = document.createElement("span");
    span.className = "ripple-char";
    span.textContent = char === " " ? "\u00A0" : char;
    span.style.animationDelay = `${i * 0.03}s`;
    el.appendChild(span);
  });
}

function triggerRipple() {
  const items = document.querySelectorAll(".ripple-block");

  items.forEach((el, i) => {
    el.style.transition = "none";
    el.style.opacity = "0";
    el.style.transform = "translateY(20px)";
    el.style.filter = "blur(8px)";
  });

  items.forEach((el, i) => {
    setTimeout(() => {
      el.style.transition = "all 0.9s cubic-bezier(0.16, 1, 0.3, 1)";
      el.style.opacity = "1";
      el.style.transform = "translateY(0)";
      el.style.filter = "blur(0)";
    }, i * 180);
  });
}

window.addEventListener("DOMContentLoaded", triggerRipple);

window.addEventListener("pageshow", (event) => {
  triggerRipple(); // always replay (including back/forward cache)
});

const hero = document.querySelector("#hero");

const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      triggerRipple();
      hasPlayed = true;
    }
  });
}, {
  threshold: 0.5
});

observer.observe(hero);


// =====================
// LOAD MODEL ASAP (before DOM)
// =====================
let gltfData = null;
const loader = new GLTFLoader();

loader.load(
  "images/steam2.glb",
  (gltf) => {
    console.log("GLB preloaded");
    gltfData = gltf;
  },
  undefined,
  (error) => {
    console.error("GLB failed to preload:", error);
  }
);

// =====================
// MAIN APP
// =====================
document.addEventListener("DOMContentLoaded", () => {

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
    antialias: true,
    powerPreference: "high-performance"
  });

  renderer.setSize(container.clientWidth, container.clientHeight);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;

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
  let object, mixer;
  const clock = new THREE.Clock();

  function tryAddModel() {
    if (!gltfData) {
      requestAnimationFrame(tryAddModel);
      return;
    }

    object = gltfData.scene;
    scene.add(object);

    // center model
    const box = new THREE.Box3().setFromObject(object);
    const center = box.getCenter(new THREE.Vector3());
    object.position.sub(center);

    object.scale.set(1.3, 1.3, 1.3);
    object.position.x -= 0.3;
    object.position.y -= 0.8;

    // animations
    if (gltfData.animations.length > 0) {
      mixer = new THREE.AnimationMixer(object);
      gltfData.animations.forEach((clip) =>
        mixer.clipAction(clip).play()
      );
    }
  }

  tryAddModel();

  // =====================
  // SCROLL
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

  // Overview 
  const aboutSection = document.querySelector("#about");

const aboutObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      aboutSection.classList.add("show");
    } else {
      aboutSection.classList.remove("show"); // allows replay
    }
  });
}, { threshold: 0.3 });

aboutObserver.observe(aboutSection);

  // The process 

const section = document.querySelector("#process");

const observer2 = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      section.classList.add("show");
    } else {
      section.classList.remove("show"); // 
    }
  });
}, { threshold: 0.3 });

observer2.observe(section);

const items = document.querySelectorAll(".process-item");

const observer = new IntersectionObserver((entries) => {
  entries.forEach((entry, index) => {
    if (entry.isIntersecting) {
      setTimeout(() => {
        entry.target.classList.add("show");
      }, index * 150);
    } else {
      entry.target.classList.remove("show"); // 
    }
  });
}, { threshold: 0.2 });

items.forEach(item => observer.observe(item));

// EDA 
const edaCards = document.querySelectorAll(".eda-card");

const edaObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add("show");
    } else {
      entry.target.classList.remove("show"); // replay
    }
  });
}, { threshold: 0.2 });

edaCards.forEach((card, index) => {
  edaObserver.observe(card);
  card.style.transitionDelay = `${index * 0.15}s`;
});


  // =====================
  // MACHINE LEARNING SLIDER
  // =====================
  const mlTrack = document.getElementById('ml-track');
  const mlCounter = document.getElementById('ml-counter');
  const mlSlides = document.querySelectorAll('.carousel-slide');

  if (mlTrack && mlCounter && mlSlides.length) {
    const mlTotal = mlSlides.length;
    let mlCurrent = 0;

    function mlGoTo(index) {
  mlCurrent = (index + mlTotal) % mlTotal;
  mlTrack.style.transform = `translateX(-${mlCurrent * 100}%)`;
  mlCounter.textContent = `${mlCurrent + 1} / ${mlTotal}`;

  // RESET animations
  mlSlides.forEach(slide => {
    slide.classList.remove("active");
  });

  // ACTIVATE current slide
  mlSlides[mlCurrent].classList.add("active");
}

    document.getElementById('ml-prev')?.addEventListener('click', () => mlGoTo(mlCurrent - 1));
    document.getElementById('ml-next')?.addEventListener('click', () => mlGoTo(mlCurrent + 1));
  }

});

// Insights // 
document.addEventListener('DOMContentLoaded', () => {
  const track = document.getElementById('insights-track');
  const slides = track.querySelectorAll('.insights-slide'); // scope to track, not document
  const total = slides.length;
  let current = 0;

  console.log('insights slides found:', total); // check this in browser console

  function goTo(index) {
    current = (index + total) % total;
    track.style.transform = `translateX(-${current * 100}%)`;
  }

  document.getElementById('insights-prev').addEventListener('click', () => goTo(current - 1));
  document.getElementById('insights-next').addEventListener('click', () => goTo(current + 1));
});
