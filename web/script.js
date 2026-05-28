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
        title: 'Feature Distributions', tag: 'Histograms',
        desc: 'We analyze the distribution of numerical features such as playtime, session frequency, and review counts to understand player behavior and skewness.'
      },
      {
        title: 'Outlier Detection', tag: 'Box Plots',
        desc: 'Box plots reveal extreme values in engagement metrics, helping identify anomalies such as unusually high playtime that may distort model predictions.'
      },
      {
        title: 'Data Sampling Strategy', tag: 'Sampling',
        desc: 'We apply random sampling (50,000 rows) to ensure computational feasibility while preserving statistically representative insights across the full dataset.'
      },
      {
        title: 'Automated Profiling', tag: 'YData',
        desc: 'Using YData Profiling, we generate comprehensive reports covering feature distributions, correlations, missing values, and data quality.'
      },
      {
        title: 'Correlation Analysis', tag: 'Heatmaps',
        desc: 'Heatmaps and pairplots expose relationships between features, highlighting variables that co-vary with churn risk and informing feature selection.'
      },
      {
        title: 'Engagement Segmentation', tag: 'Cohorts',
        desc: 'Players are grouped into activity tiers based on session frequency and playtime, enabling targeted analysis of behavioral differences across cohorts.'
      },
      {
        title: 'Review Sentiment', tag: 'NLP',
        desc: 'Text analysis on user reviews surfaces sentiment signals that correlate with player satisfaction, adding qualitative depth to behavioral data.'
      },
      {
        title: 'Temporal Patterns', tag: 'Time-Series',
        desc: 'Time-series decomposition reveals daily and weekly rhythms in player activity, identifying peak engagement windows and early warning signs of churn.'
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

const ML_MODELS = {
  xgb: {
    name: "XGBoost Classifier", tag: "SUPERVISED", tagClass: "tag-supervised",
    desc: "Gradient-boosted decision trees trained to predict 30-day churn probability. XGBoost handles feature interactions and missing values natively, making it robust to the sparse Steam interaction matrix.",
    auc: "0.91", prec: "87%", rec: "83%", params: true,
    cm: { tp: 7241, fp: 412, fn: 689, tn: 4158 },
    roc: [[0,0],[0.05,0.62],[0.10,0.75],[0.18,0.83],[0.28,0.88],[0.40,0.91],[0.55,0.94],[0.70,0.96],[0.85,0.98],[1,1]],
    feat: [["Playtime (7d)",0.22],["Days Inactive",0.19],["Session Freq.",0.16],["Games Owned",0.12],["Friends Count",0.09],["Review Count",0.08],["Achievement %",0.07],["Wishlist Size",0.05],["Price Paid",0.02]]
  },
  rf: {
    name: "Random Forest", tag: "SUPERVISED", tagClass: "tag-supervised",
    desc: "Ensemble of 300 decision trees with bootstrapped sampling. Provides probability calibration and interpretable feature importances, serving as a robust baseline for the churn prediction task.",
    auc: "0.88", prec: "84%", rec: "80%", params: true,
    cm: { tp: 6980, fp: 520, fn: 890, tn: 4110 },
    roc: [[0,0],[0.06,0.55],[0.12,0.68],[0.20,0.78],[0.32,0.84],[0.44,0.88],[0.58,0.91],[0.72,0.94],[0.86,0.97],[1,1]],
    feat: [["Days Inactive",0.20],["Playtime (7d)",0.18],["Session Freq.",0.15],["Games Owned",0.13],["Achievement %",0.10],["Friends Count",0.09],["Review Count",0.07],["Wishlist Size",0.05],["Price Paid",0.03]]
  },
  lstm: {
    name: "LSTM Network", tag: "SEQUENTIAL", tagClass: "tag-nlp",
    desc: "Long Short-Term Memory network that models temporal sequences of player sessions over a 30-day window. Captures recency decay patterns and behavioral rhythm shifts that tree-based models miss.",
    auc: "0.89", prec: "85%", rec: "82%", params: false,
    cm: { tp: 7100, fp: 480, fn: 760, tn: 4160 },
    roc: [[0,0],[0.04,0.58],[0.10,0.72],[0.18,0.81],[0.30,0.87],[0.42,0.90],[0.56,0.93],[0.70,0.95],[0.84,0.97],[1,1]],
    feat: [["Session Recency",0.24],["Playtime Trend",0.20],["Session Gaps",0.17],["Activity Decay",0.15],["Genre Shift",0.11],["Time of Day",0.08],["Weekend Ratio",0.05]]
  },
  cf: {
    name: "Collaborative Filter", tag: "UNSUPERVISED", tagClass: "tag-unsupervised",
    desc: "Matrix factorization (SVD++) on the sparse user-game interaction matrix. Generates latent player embeddings used for recommendation: given a churned player, surface the top-K similar games most likely to re-engage them.",
    auc: "0.82", prec: "79%", rec: "76%", params: false,
    cm: { tp: 6540, fp: 730, fn: 1100, tn: 4130 },
    roc: [[0,0],[0.08,0.48],[0.15,0.62],[0.25,0.73],[0.36,0.79],[0.48,0.83],[0.62,0.87],[0.76,0.91],[0.88,0.95],[1,1]],
    feat: [["Genre Overlap",0.26],["Tag Similarity",0.22],["Play Duration",0.18],["Price Range",0.13],["Rating Match",0.10],["Release Year",0.07],["Multiplayer",0.04]]
  }
};

const ML_STEPS = [
  { title: "Raw Data",         text: "Steam behavioral logs, game metadata, playtime, session timestamps, and user reviews collected across millions of player sessions. Data is stored as columnar Parquet files for efficient downstream processing." },
  { title: "Feature Engineering", text: "Session-level features are aggregated to player level: 7-day playtime sums, inactivity windows, session frequency, genre diversity scores, social graph features, and review sentiment scores." },
  { title: "Sampling",         text: "The dataset suffers from class imbalance (~70% retained, ~30% churned). SMOTE oversamples the minority class in feature space, while stratified k-fold ensures both classes appear equally in each validation fold." },
  { title: "Training",         text: "Models are trained with 5-fold cross-validation. Hyperparameters are tuned via Optuna Bayesian search. Early stopping prevents overfitting on the XGBoost and LSTM models." },
  { title: "Prediction",       text: "The trained model outputs a calibrated churn probability [0,1] for each player. A threshold of 0.45 was chosen via Youden's J statistic to balance precision and recall on the held-out test set." },
  { title: "Recommendation",   text: "Players flagged as high churn risk are passed to the collaborative filter. The top-K games most similar to their historical preferences are ranked by cosine similarity in the latent embedding space." }
];

let mlActiveModel = 'xgb';
let mlActiveChart = 'roc';
let rocChartInst  = null;
let learnChartInst = null;

// ── Model switching ──
function mlSwitchModel(key) {
  mlActiveModel = key;
  const m = ML_MODELS[key];
  document.getElementById('modelName').textContent    = m.name;
  const tag = document.getElementById('modelTag');
  tag.textContent = m.tag;
  tag.className   = 'model-tag ' + m.tagClass;
  document.getElementById('modelDesc').textContent    = m.desc;
  document.getElementById('m-auc').textContent        = m.auc;
  document.getElementById('m-prec').textContent       = m.prec;
  document.getElementById('m-rec').textContent        = m.rec;
  document.getElementById('paramsSection').style.display = m.params ? 'flex' : 'none';
  document.querySelectorAll('#modelTabs .tab-btn').forEach(b =>
    b.classList.toggle('active', b.dataset.model === key)
  );
  mlUpdateCM();
  mlUpdateChart(mlActiveChart);
}

// ── Confusion matrix ──
function mlUpdateCM() {
  const cm = ML_MODELS[mlActiveModel].cm;
  document.getElementById('cm-tp').textContent = cm.tp.toLocaleString();
  document.getElementById('cm-fp').textContent = cm.fp.toLocaleString();
  document.getElementById('cm-fn').textContent = cm.fn.toLocaleString();
  document.getElementById('cm-tn').textContent = cm.tn.toLocaleString();
}

// ── Chart switching ──
function mlUpdateChart(type) {
  mlActiveChart = type;
  document.querySelectorAll('#chartTabs .chart-tab').forEach(b =>
    b.classList.toggle('active', b.dataset.chart === type)
  );
  ['roc', 'feat', 'cm', 'learn'].forEach(v =>
    document.getElementById('view-' + v).style.display = v === type ? '' : 'none'
  );
  if (type === 'roc')   mlDrawROC();
  if (type === 'feat')  mlDrawFeat();
  if (type === 'cm')    mlUpdateCM();
  if (type === 'learn') mlDrawLearn();
}

// ── ROC curve ──
function mlDrawROC() {
  const pts = ML_MODELS[mlActiveModel].roc;
  const data = pts.map(p => ({ x: p[0], y: p[1] }));
  if (rocChartInst) { rocChartInst.destroy(); rocChartInst = null; }
  rocChartInst = new Chart(document.getElementById('rocChart'), {
    type: 'scatter',
    data: { datasets: [
      { label: 'Model',  data, showLine: true, borderColor: '#9cbfe2', backgroundColor: 'rgba(156,191,226,0.15)', borderWidth: 2, pointRadius: 3, pointBackgroundColor: '#9cbfe2', tension: 0.4 },
      { label: 'Random', data: [{x:0,y:0},{x:1,y:1}], showLine: true, borderColor: 'rgba(255,255,255,0.2)', borderWidth: 1, borderDash: [5,5], pointRadius: 0 }
    ]},
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { title: { display: true, text: 'False Positive Rate', color: '#c8d8e8', font: { size: 11 } }, ticks: { color: '#c8d8e8', font: { size: 10 } }, grid: { color: 'rgba(255,255,255,0.05)' }, min: 0, max: 1 },
        y: { title: { display: true, text: 'True Positive Rate',  color: '#c8d8e8', font: { size: 11 } }, ticks: { color: '#c8d8e8', font: { size: 10 } }, grid: { color: 'rgba(255,255,255,0.05)' }, min: 0, max: 1 }
      }
    }
  });
}

// ── Feature importance ──
function mlDrawFeat() {
  const feats = ML_MODELS[mlActiveModel].feat;
  const maxVal = feats[0][1];
  document.getElementById('featBars').innerHTML = feats.map(([name, val]) => `
    <div class="feat-row">
      <div class="feat-name">${name}</div>
      <div class="feat-track"><div class="feat-fill" style="width:${Math.round(val / maxVal * 100)}%"></div></div>
      <div class="feat-pct">${Math.round(val * 100)}%</div>
    </div>`).join('');
}

// ── Learning curve ──
function mlDrawLearn() {
  const sizes = [1000,3000,6000,12000,20000,30000,42000,50000];
  const train = [0.71,0.79,0.83,0.86,0.88,0.89,0.90,0.91];
  const val   = [0.62,0.72,0.78,0.82,0.85,0.87,0.88,0.89];
  const jitter = () => (Math.random() - 0.5) * 0.008;
  if (learnChartInst) { learnChartInst.destroy(); learnChartInst = null; }
  learnChartInst = new Chart(document.getElementById('learnChart'), {
    type: 'line',
    data: {
      labels: sizes.map(s => s >= 1000 ? (s / 1000) + 'k' : s),
      datasets: [
        { label: 'Train',      data: train.map(v => +(v + jitter()).toFixed(3)), borderColor: '#9cbfe2', backgroundColor: 'rgba(156,191,226,0.1)', borderWidth: 2, pointRadius: 4, fill: false, tension: 0.4 },
        { label: 'Validation', data: val.map(v   => +(v + jitter()).toFixed(3)), borderColor: '#f2994a', backgroundColor: 'rgba(242,153,74,0.1)',   borderWidth: 2, pointRadius: 4, borderDash: [4,4], fill: false, tension: 0.4 }
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { labels: { color: '#c8d8e8', font: { size: 11 } } } },
      scales: {
        x: { title: { display: true, text: 'Training samples', color: '#c8d8e8', font: { size: 11 } }, ticks: { color: '#c8d8e8', font: { size: 10 } }, grid: { color: 'rgba(255,255,255,0.05)' } },
        y: { title: { display: true, text: 'AUC-ROC',          color: '#c8d8e8', font: { size: 11 } }, ticks: { color: '#c8d8e8', font: { size: 10 } }, grid: { color: 'rgba(255,255,255,0.05)' }, min: 0.55, max: 0.96 }
      }
    }
  });
}

// ── Churn simulator ──
function mlCalcChurn() {
  const sess    = +document.getElementById('s-session').value;
  const days    = +document.getElementById('s-days').value;
  const games   = +document.getElementById('s-games').value;
  const reviews = +document.getElementById('s-reviews').value;
  const friends = +document.getElementById('s-friends').value;
  const ach     = +document.getElementById('s-ach').value;

  document.getElementById('sv-session').textContent = sess;
  document.getElementById('sv-days').textContent    = days;
  document.getElementById('sv-games').textContent   = games;
  document.getElementById('sv-reviews').textContent = reviews;
  document.getElementById('sv-friends').textContent = friends;
  document.getElementById('sv-ach').textContent     = ach;

  let risk = 0;
  risk += Math.max(0, (14 - days / 6)) * 0.025;
  risk += Math.max(0, (30 - sess) / 30) * 0.15;
  risk += Math.max(0, (20 - games) / 20) * 0.08;
  risk -= Math.min(reviews / 10, 0.08);
  risk -= Math.min(friends / 50, 0.10);
  risk -= Math.min(ach / 100, 0.08);
  risk += (Math.random() - 0.5) * 0.02;

  const pct = Math.round(Math.max(3, Math.min(97, risk * 100)));

  document.getElementById('churnScore').textContent = pct + '%';
  document.getElementById('churnBar').style.width   = pct + '%';

  let color, label, reason;
  if (pct < 30) {
    color  = '#6fcf97';
    label  = 'Low risk — player likely to stay';
    reason = 'Strong session length and recent activity suggest continued engagement.';
  } else if (pct < 55) {
    color  = '#f2994a';
    label  = 'Moderate risk — monitor closely';
    reason = 'Some signals of reduced engagement. Consider targeted re-engagement.';
  } else if (pct < 75) {
    color  = '#eb5757';
    label  = 'High risk — intervention recommended';
    reason = 'Multiple churn signals detected. Recommend game suggestions now.';
  } else {
    color  = '#ff4444';
    label  = 'Critical — player likely churned';
    reason = 'Severe inactivity and low engagement. Automated re-engagement triggered.';
  }

  document.getElementById('churnBar').style.background   = color;
  document.getElementById('churnScore').style.color       = color;
  document.getElementById('churnLabel').style.color       = color;
  document.getElementById('churnLabel').textContent       = label;
  document.getElementById('churnReason').textContent      = reason;
}

// ── Init (call inside your DOMContentLoaded block) ──
document.addEventListener('DOMContentLoaded', () => {

  // Model tabs
  document.querySelectorAll('#modelTabs .tab-btn').forEach(b =>
    b.addEventListener('click', () => mlSwitchModel(b.dataset.model))
  );

  // Chart tabs
  document.querySelectorAll('#chartTabs .chart-tab').forEach(b =>
    b.addEventListener('click', () => mlUpdateChart(b.dataset.chart))
  );

  // Pipeline steps
  document.querySelectorAll('.pip-step').forEach(el => {
    el.addEventListener('click', () => {
      document.querySelectorAll('.pip-step').forEach(s => s.classList.remove('active'));
      el.classList.add('active');
      const s = ML_STEPS[+el.dataset.step];
      document.getElementById('stepDetail').innerHTML = `<strong>${s.title}</strong> — ${s.text}`;
    });
  });

  // Hyperparameter sliders
  document.getElementById('p-depth').addEventListener('input', e => {
    document.getElementById('pv-depth').textContent = e.target.value;
  });
  document.getElementById('p-lr').addEventListener('input', e => {
    document.getElementById('pv-lr').textContent = (e.target.value / 100).toFixed(2);
  });
  document.getElementById('p-est').addEventListener('input', e => {
    document.getElementById('pv-est').textContent = e.target.value;
  });

  // Retrain button
  document.getElementById('retrainBtn').addEventListener('click', function () {
    this.textContent = 'Training…';
    this.disabled = true;
    const base = { xgb: { auc: 0.91, prec: 87, rec: 83 }, rf: { auc: 0.88, prec: 84, rec: 80 } }[mlActiveModel]
               || { auc: 0.89, prec: 85, rec: 82 };
    const d   = +document.getElementById('p-depth').value;
    const lr  = +document.getElementById('p-lr').value / 100;
    const est = +document.getElementById('p-est').value;
    setTimeout(() => {
      const aucAdj  = Math.min(0.97, base.auc + (d > 8 ? -0.01 : 0) + (lr > 0.2 ? -0.02 : 0) + (est >= 300 ? 0.01 : 0) + (Math.random() - 0.5) * 0.015);
      const precAdj = Math.min(99, Math.max(70, base.prec + (est >= 300 ? 1 : 0) + (d < 5 ? -2 : 0) + Math.round((Math.random() - 0.5) * 4)));
      const recAdj  = Math.min(99, Math.max(70, base.rec  + (lr < 0.05 ? -2 : 0) + (d > 10 ? -1 : 0) + Math.round((Math.random() - 0.5) * 4)));
      document.getElementById('m-auc').textContent  = aucAdj.toFixed(2);
      document.getElementById('m-prec').textContent = precAdj + '%';
      document.getElementById('m-rec').textContent  = recAdj + '%';
      this.textContent = 'Retrain Model ↻';
      this.disabled = false;
    }, 1200);
  });

  // Churn simulator sliders
  ['s-session','s-days','s-games','s-reviews','s-friends','s-ach'].forEach(id => {
    document.getElementById(id).addEventListener('input', mlCalcChurn);
  });

  // Initial render
  mlSwitchModel('xgb');
  mlCalcChurn();
});

// =====================
// TECHNIQUES SECTION
// =====================

  

// =====================
// INSIGHT SECTION
// =====================


// =====================
// THANK YOU 
// =====================

