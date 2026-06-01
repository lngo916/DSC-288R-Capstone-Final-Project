// =====================
// Start Loading
// =====================
// =====================
// Start Loading (RUN ONCE)
// =====================

const HAS_STARTED = sessionStorage.getItem("hasStarted");

const startBtn = document.getElementById("press-start");
const startScreen = document.getElementById("start-screen");
const bootScreen = document.getElementById("boot-screen");

// If already started in this tab session → skip intro entirely
if (HAS_STARTED) {
  startScreen.style.display = "none";
  bootScreen.style.display = "none";
  document.body.classList.remove("locked");
} else {

  startBtn.addEventListener("click", () => {

    startBtn.style.pointerEvents = "none";

    // mark as started (persists until tab is closed or Cmd+R refresh)
    sessionStorage.setItem("hasStarted", "true");

    // 1. fade out start screen
    startScreen.classList.add("gone");

    // 2. boot screen
    setTimeout(() => {
      bootScreen.classList.add("active");

      const fill = document.querySelector(".boot-fill");
      fill.style.width = "0%";

      setTimeout(() => fill.style.width = "30%", 200);
      setTimeout(() => fill.style.width = "65%", 700);
      setTimeout(() => fill.style.width = "100%", 1400);

    }, 600);

    // 3. finish boot
    setTimeout(() => {
      bootScreen.classList.remove("active");

      document.body.classList.remove("locked");

      document.querySelector(".top-nav").style.opacity = "1";
      document.querySelector("#hero").style.opacity = "1";

      document.querySelector("#hero").scrollIntoView({
        behavior: "smooth"
      });

    }, 2200);

  });
}

// =====================
// Hero
// =====================
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

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

// Loading GLB
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

document.addEventListener("DOMContentLoaded", () => {

  const container = document.getElementById("container3D");
  if (!container) {
    console.error("container3D not found");
    return;
  }

  // Scene/Camera/Rendering
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(
    50,
    container.clientWidth / container.clientHeight,
    0.1,
    1000
  );
  camera.position.set(0, 0.2, 8);

  const renderer = new THREE.WebGLRenderer({
    alpha: true,
    antialias: true,
    powerPreference: "high-performance"
  });


  renderer.setSize(container.clientWidth, container.clientHeight);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;

  container.appendChild(renderer.domElement);

  const controls = new OrbitControls(camera, renderer.domElement);

  // optional polish settings
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;

  // IMPORTANT: restrict movement if this is a hero object
  controls.enablePan = false;
  controls.minDistance = 5;
  controls.maxDistance = 10;

  // optional: limit vertical rotation
  controls.minPolarAngle = Math.PI / 2.5;
  controls.maxPolarAngle = Math.PI / 1.8;

  // Lighting
  scene.add(new THREE.AmbientLight(0xffffff, 2.0));

  const key = new THREE.DirectionalLight(0xffffff, 2.2);
  key.position.set(3, 5, 2);
  scene.add(key);

  const rim = new THREE.DirectionalLight(0x9cbfe2, 1.8);
  rim.position.set(-5, 3, -5);
  scene.add(rim);

  const fill = new THREE.DirectionalLight(0xffffff, 0.8);
  fill.position.set(0, 2, 5);
  scene.add(fill);

  // Model
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

  let scrollY = 0;

  window.addEventListener("scroll", () => {
    scrollY = window.scrollY;
  });

  // Animation Loop
  function animate() {
    requestAnimationFrame(animate);

    const delta = clock.getDelta();

    if (mixer) mixer.update(delta);

    if (object) {
      object.rotation.x = Math.sin(Date.now() * 0.001) * 0.02;
      object.position.y = -0.8 + scrollY * -0.0002;
    }

    renderer.render(scene, camera);

    controls.update();
  }

  animate();

  // Resizing
  window.addEventListener("resize", () => {
    const w = container.clientWidth;
    const h = container.clientHeight;

    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
  });

  // =====================
  // Overview
  // =====================
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

  // =====================
  // Process
  // =====================

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

  // =====================
  // EDA
  // =====================

  (function () {
    const EDA_CARDS = [
      {
        title: 'Playtime Distributions', tag: 'Univariate',
        desc: 'Playtime-related features show strong right skew. Most players exhibited low activity levels, while a small subset accumulated high playtime values.'
      },
      {
        title: 'Sparse Engagement Signals', tag: 'Engagement',
        desc: 'Engagement metrics such as votes, comments, and funny reactions were heavily sparse. Most observations contained low values with few dominating highly engaged users, suggesting uneven participation across the player base.'
      },
      {
        title: 'Class Imbalances', tag: 'Categorical',
        desc: 'Categorical variables such as voted_up and written_during_early_access exhibited class imbalances, indicating that certain player behaviors and review patterns occurred more frequently than others. We will consider this aspect for downstream modeling and retention prediction.'
      },
      {
        title: 'Behavioral Correlations', tag: 'Correlation',
        desc: 'Engagement metrics such as votes, comments, and funny reactions were heavily sparse. Most observations contained low values with few dominating highly engaged users, suggesting uneven participation across the player base.'
      },
      {
        title: 'Recency & Churn', tag: 'Recency',
        desc: 'Inactivity(recency) exhibited a negative relationship with engagement such that players inactive for longer periods were more likely to churn. As so, recency emerged as a critical predictor of player retention.'
      },
      {
        title: 'Outlier Detection', tag: 'Outliers',
        desc: 'Box Plot analysis revealed significant outliers in playtime and engagement features. A small amount of users exhibited disproportionately high activity levels, highlighting the existence of extreme behavioral cases within the dataset.'
      },
      {
        title: 'Automated Profiling Reports', tag: 'Profiling',
        desc: 'We utilized YData Profiling and SweetViz to automate feature exploration such that reports summarized distributions, missing values, correlations, and data quality metrics.'
      },
      {
        title: 'Behavior Insights', tag: 'Retention',
        desc: 'Behavior engagement metrics collectively contributed to retention outcomes. Highly active or engaged players consistently demonstrated lower churn likelihood, suggesting that retention is strongly connected to sustained platform interaction.'
      },
    ];

    const TOTAL = EDA_CARDS.length;
    const track = document.getElementById('eda-track');
    const dotsEl = document.getElementById('eda-dots');
    const btnPrev = document.getElementById('eda-prev');
    const btnNext = document.getElementById('eda-next');

    if (!track || !btnPrev || !btnNext) return;

    function getVisible() {
      if (window.innerWidth < 600) return 1;
      if (window.innerWidth < 1000) return 2;
      return 4;
    }

    let VISIBLE = getVisible();
    let current = VISIBLE;

    // ── Build one card DOM element ──
    function makeCard(cardData, realIdx) {
      const el = document.createElement('div');
      el.className = 'eda-card';
      el.dataset.i = realIdx;
      el.innerHTML = `
      <div class="eda-card-bg"></div>
      <div class="eda-card-overlay"></div>
      <div class="eda-card-inner">
        <div>
          <div class="eda-card-title">${cardData.title}</div>
          <div class="eda-card-desc">${cardData.desc}</div>
        </div>
        <div><span class="eda-card-tag">${cardData.tag}</span></div>
      </div>`;
      return el;
    }

    // ── Populate track with clones on each side for infinite loop ──
    function buildTrack() {
      track.innerHTML = '';
      // clones of last VISIBLE cards prepended
      EDA_CARDS.slice(TOTAL - VISIBLE).forEach((c, i) => {
        track.appendChild(makeCard(c, TOTAL - VISIBLE + i));
      });
      // real cards
      EDA_CARDS.forEach((c, i) => track.appendChild(makeCard(c, i)));
      // clones of first VISIBLE cards appended
      EDA_CARDS.slice(0, VISIBLE).forEach((c, i) => {
        track.appendChild(makeCard(c, i));
      });
    }

    // ── Dots ──
    function buildDots() {
      dotsEl.innerHTML = '';
      EDA_CARDS.forEach((_, i) => {
        const d = document.createElement('div');
        d.className = 'eda-dot';
        d.addEventListener('click', () => goTo(i + VISIBLE));
        dotsEl.appendChild(d);
      });
    }

    function updateDots() {
      const real = ((current - VISIBLE) % TOTAL + TOTAL) % TOTAL;
      dotsEl.querySelectorAll('.eda-dot').forEach((d, i) =>
        d.classList.toggle('active', i === real)
      );
    }

    // ── Step: one card width + gap ──
    function getStep() {
      const first = track.children[0];
      if (!first) return 0;
      const gap = parseFloat(getComputedStyle(track).gap) || 20;
      return first.offsetWidth + gap;
    }

    // ── Navigate ──
    function goTo(idx, animate = true) {
      current = idx;
      track.style.transition = animate
        ? 'transform 0.55s cubic-bezier(0.65, 0, 0.35, 1)'
        : 'none';
      track.style.transform = `translateX(-${current * getStep()}px)`;
      updateDots();
    }

    // ── Silent snap after transition ──
    track.addEventListener('transitionend', () => {
      if (current >= TOTAL + VISIBLE) goTo(current - TOTAL, false);
      else if (current < VISIBLE) goTo(current + TOTAL, false);
    });

    btnNext.addEventListener('click', () => goTo(current + 1));
    btnPrev.addEventListener('click', () => goTo(current - 1));

    // ── Rebuild on resize if visible count changes ──
    let resizeTimer;
    window.addEventListener('resize', () => {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(() => {
        const v = getVisible();
        if (v !== VISIBLE) {
          VISIBLE = v;
          current = VISIBLE;
          buildTrack();
          buildDots();
        }
        goTo(current, false);
      }, 100);
    });

    // ── Init ──
    buildTrack();
    buildDots();
    goTo(VISIBLE, false);
  })();

});

const edaSection = document.querySelector("#eda");
const edaCards = document.querySelectorAll(".eda-card");

// section observer (show/hide)
const edaObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      edaSection.classList.add("show");
    } else {
      edaSection.classList.remove("show"); // re-trigger on re-scroll
    }
  });
}, { threshold: 0.3 });

edaObserver.observe(edaSection);

// optional: individual card observer (extra polish)
const cardObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add("show");
    } else {
      entry.target.classList.remove("show");
    }
  });
}, { threshold: 0.2 });

edaCards.forEach(card => cardObserver.observe(card));

// =====================
// Machine Learning
// =====================


// =====================
// TECHNIQUES SECTION
// =====================

  

// =====================
// INSIGHT SECTION
// =====================


// =====================
// THANK YOU 
// =====================

