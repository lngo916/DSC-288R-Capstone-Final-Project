/* ========================== */
/* RESET */
/* ========================== */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html {
  scroll-behavior: smooth;
}

.section {
  min-height: 100vh;
  padding: 100px 80px;
}

html, body {
  margin: 0;
  padding: 0;
}

/* ========================== */
/* ROOT VARIABLES */
/* ========================== */
:root {
  --bg: #111111;
  --accent: #9cbfe2;
  --text: #ffffff;
  --subtext: #e4e4e4;
}

/* ========================== */
/* BODY */
/* ========================== */
body {
  background-color: var(--bg);
  color: var(--text);
  font-family: 'Poppins', sans-serif;
  overflow-x: hidden;
}

/* ========================== */
/* NAVBAR */
/* ========================== */
.top-nav {
  position: fixed;   /* 🔥 important fix */
  top: 0;
  left: 0;
  width: 100%;
  height: 80px;
  z-index: 1000;

  display: flex;
  justify-content: center;
  align-items: center;

  padding: 0 clamp(20px, 6vw, 80px);

  /* glass effect */
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);

  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

/* REMOVE LIST DEFAULTS */
.top-nav ul {
  list-style: none;
  display: flex;
  gap: clamp(20px, 3vw, 50px);
  margin: 0;
  padding: 0;
}

/* LINKS */
.top-nav a {
  text-decoration: none;
  color: var(--text);
  font-size: 14px;
  transition: 0.3s;
  white-space: nowrap;
}

/* HOVER EFFECT */
.top-nav a:hover {
  color: var(--accent);
}

/* OPTIONAL: active link feel */
.top-nav a:active {
  color: var(--accent);
}

/* ========================== */
/* NAV CONTAINER */
/* ========================== */
.navbar nav {
  display: flex;
  justify-content: center; /* 🔥 centers links */
  align-items: center;

  gap: clamp(20px, 3vw, 50px);
}

/* ========================== */
/* HERO SECTION */
/* ========================== */
#hero {
  scroll-margin-top: 80px;
  background: linear-gradient(to bottom, #aaabba, #1e3261);

  /* 🔥 important: prevents top gap under fixed navbar */
  padding-top: 80px;
}

.hero {
  display: flex;
  align-items: center;
  justify-content: space-between; /* key change */

  gap: clamp(30px, 6vw, 80px);
  padding: 0 clamp(10px, 6vw, 80px);

  min-height: 100vh;
}

.hero-text {
  max-width: 600px;

}

.hero-text h1 {
  font-size: clamp(32px, 4vw, 56px);
  font-weight: 700;
  color: var(--accent);
  line-height: 1.15;
  margin-bottom: 20px;
}


.hero-text p {
  font-size: 14px;
  color: var(--subtext);
  line-height: 1.7;
  margin-bottom: 25px;
}

.btn {
  padding: 12px 26px;
  border: 1px solid var(--accent);
  background: transparent;
  color: var(--text);
  cursor: pointer;
  transition: 0.3s;
  font-family: 'Poppins', sans-serif;
}

.btn:hover {
  background: var(--accent);
  color: black;
}

.hero-image {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
}

#container3D {
  width: 100%;
  height: 650px;
  padding: 0px;
}

/* ========================== */
/* FOOTER LINE */
/* ========================== */
.footer-link {
  display: flex;
  align-items: center;
  margin-top: 40px;
}

.footer-link span {
  font-size: 13px;
  margin-right: 15px;
}

.footer-link .line {
  width: 100px;
  height: 2px;
  background: var(--accent);
}

.ripple-block {
  opacity: 0;
  transform: translateY(25px);
  filter: blur(8px);
}

@keyframes rippleIn {
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}


/* ========================== */
/* RESPONSIVE (TABLET / SMALL LAPTOP) */
/* ========================== */
@media (max-width: 900px) {

  .hero {
    flex-direction: column-reverse; /* 🔥 key fix */
    text-align: center;

    height: auto;
    padding: 60px 20px;
  }

  .hero-text {
    max-width: 90%;
  }

  .hero-image {
    margin-bottom: 30px; /* spacing above text now */
  }

}

/* ========================== */
/* Introduction */
/* ========================== */

.intro-section {
  min-height: 100vh;
  display: flex;
  flex-direction: column;

  background: linear-gradient(to bottom, #1e3261, #132652);
  position: relative;
  overflow: hidden;
  color: white;
}

/* subtle grid overlay */
.intro-section::before {
  content: '';
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.04) 1px, transparent 1px);
  background-size: 60px 60px;
  pointer-events: none;
}

/* ── TOP TEXT ── */
.intro-top {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  text-align: center;

  padding: 80px 20px 30px;
  max-width: 900px;
  margin: 0 auto;
}

.intro-heading {
  font-size: clamp(32px, 4vw, 56px);
  color: #9cbfe2;
  margin-bottom: 20px;
}

.intro-body {
  font-size: 14px;
  color: #c8d8e8;
  line-height: 1.7;
  max-width: 700px;
}

/* ── STEAM SLIDER ── */
.steam-slider {
  height: 35vh;
  width: 100%;
  overflow: hidden;
  display: flex;
  align-items: center;
  position: relative;
}

/* fade edges like Steam */
.steam-slider::before,
.steam-slider::after {
  content: "";
  position: absolute;
  top: 0;
  width: 120px;
  height: 100%;
  z-index: 2;
  pointer-events: none;
}

.steam-slider::before {
  left: 0;
  background: linear-gradient(to right, #5f617d, transparent);
}

.steam-slider::after {
  right: 0;
  background: linear-gradient(to left, #5f617d, transparent);
}

/* moving track */
.steam-track {
  display: flex;
  width: max-content;
  animation: scroll 22s linear infinite;
}

/* card */
.steam-card {
  width: 280px;
  flex: 0 0 auto;
  margin-right: 16px;
  border-radius: 12px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.03);
  transition: transform 0.25s ease;
}

.steam-card img {
  width: 100%;
  border-radius: 10px;
  display: block;
  transition: transform 0.3s ease;
}

.steam-card p {
  margin-top: 8px;
  font-size: 14px;
  opacity: 0.85;
}

/* hover effect */
.steam-card:hover {
  transform: translateY(-6px);
}

.steam-card:hover img {
  transform: scale(1.05);

}

/* infinite animation */
@keyframes scroll {
  0% {
    transform: translateX(0);
  }
  100% {
    transform: translateX(-50%);
  }
}

/* EDA */
.eda-section {
  min-height: 100vh;
  padding: 80px;
  background: linear-gradient(to bottom, #132652, #081535);
  color: white;
  display: flex;
  flex-direction: column;
  gap: 40px;
  padding-top: 100px;
}

/* ── TOP ROW ── */
.eda-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 40px;
}

/* big text block (right-leaning feel) */
.eda-text {
  max-width: 700px;
}

.eda-text h2 {
  font-size: 42px;
  color: #9cbfe2;
  margin-bottom: 10px;
  margin-top: 60px;
}

.eda-text p {
  font-size: 15px;
  color: #c8d8e8;
  line-height: 1.6;
}

/* github box */
.eda-github {
  width: 140px;
  height: 40px;

  background: #155bc4;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 4px;

  margin-top: 180px;
  text-decoration: none;
  color: rgb(60, 70, 203);

  display: flex;
  align-items: center;
  justify-content: center;

  white-space: nowrap;

  transition: transform 0.25s ease, border 0.25s ease;
}

.eda-github h3 {
  margin: 0;
  color: #f6f7f9;
  font-size: 15px;
}

.eda-github:hover {
  transform: translateY(-5px);
  border: 1px solid rgba(156, 191, 226, 0.6);
}

/* ── BOTTOM GRID ── */
.eda-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-top: 80px;
}

/* cards */
.eda-card {
  background: #f0efef;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 6px;

  padding: 25px;
  min-height: 180px;
  height: 40vh;

  transition: transform 0.25s ease, border 0.25s ease;
}

.eda-card h3 {
  color: #0b447e;
  margin-bottom: 10px;
}

.eda-card p {
  font-size: 13px;
  opacity: 0.8;
  line-height: 1.5;
  color: #134f8a;
}

.eda-card:hover {
  transform: translateY(-6px);
  border: 1px solid rgba(156, 191, 226, 0.4);
}

/* ── RESPONSIVE ── */
@media (max-width: 1000px) {
  .eda-top {
    flex-direction: column;
  }

  .eda-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 600px) {
  .eda-grid {
    grid-template-columns: 1fr;
  }
}

/* Machine Learning */
.carousel {
  position: relative;
  width: 100%;
  max-width: 1100px;
  margin: auto;
  overflow: hidden;
}

/* IMPORTANT: row of slides */
.carousel-track {
  display: flex;
  transition: transform 0.6s ease;
}

/* EACH slide takes full width */
.carousel-slide {
  min-width: 100%;
  display: flex;
  gap: 40px;
  align-items: center;
  padding: 40px;
  box-sizing: border-box;
}

.ml-image {
  flex: 1;
}

.ml-image img {
  width: 100%;
  border-radius: 12px;
}

.ml-content {
  flex: 1;
  color: white;
}

/* arrows */
.arrow {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  background: rgba(255,255,255,0.1);
  border: none;
  color: white;
  font-size: 30px;
  padding: 10px 15px;
  cursor: pointer;
  z-index: 10;
}

.arrow.left { left: 10px; }
.arrow.right { right: 10px; }

.arrow:hover {
  background: rgba(255,255,255,0.25);
}

/* MACHINE LEARNING */
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:wght@300;400;500&display=swap');
 
#ml {
  min-height: 100vh;
  width: 100%;
  background: linear-gradient(to bottom, #081535, #030916);
  display: flex;
  flex-direction: column;
}

.ml-section {
  width: 100%;
  max-width: 100%
  padding: 60px 40px;
  font-family: 'Poppins', sans-serif;
}
 
.carousel-outer {
  position: relative;
  overflow: hidden;
}
 
.carousel-track {
  display: flex;
  transition: transform 0.55s cubic-bezier(0.65, 0, 0.35, 1);
}
 
.carousel-slide {
  min-width: 100%;
  display: grid;
  grid-template-columns: 0.9fr 1fr;
  gap: 60px;
  align-items: center;
  margin-top: 50px;
}
 
.slide-image {
  aspect-ratio: 4/3;
  border-radius: 3px;
  overflow: hidden;
}
 
.slide-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
 
.slide-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
 
.slide-title {
  font-family: 'Poppins', serif;
  font-size: clamp(44px, 6vw, 72px);
  color: #9cbfe2;
  line-height: 1.0;
  font-weight: 600;
}
 
.slide-desc {
  font-size: 17px;
  color: #f2f4f6;
  line-height: 1.65;
  font-weight: 300;
}
 
.slide-meta {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-top: 8px;
}
 
.meta-icon {
  width: 52px;
  height: 52px;
  border-radius: 8px;
  background: #fbfbfb;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
}
 
.meta-name {
  font-size: 13px;
  font-weight: 500;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #eaeef3;
}
 
.meta-tag {
  font-size: 13px;
  color: #eaeef3;
  margin-top: 2px;
}
 
.ml-controls {
  display: flex;
  gap: 10px;
  margin-top: 36px;
  align-items: center;
}
 
.ml-arrow {
  width: 44px;
  height: 44px;
  border-radius: 8px;
  border: none;
  background: #f2f2f4;
  color: #3a6bc0;
  font-size: 20px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s, transform 0.15s;
  line-height: 1;
  margin-left: 30px;
}
 
.ml-arrow:hover {
  background: #9cbfe2;
  transform: scale(1.06);
}
 
.ml-arrow:active {
  transform: scale(0.97);
}
 
.ml-counter {
  font-size: 13px;
  color: #f9f5f0;
  margin-left: 4px;
  letter-spacing: 0.05em;
}

/* INSIGHTS SECTION */
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;500&family=DM+Sans:wght@300;400;500&display=swap');

.insights-section {
  min-height: 100vh;
  width: 100%;
  display: grid;
  grid-template-columns: 1fr 1fr;
  align-items: center;
  background: linear-gradient(to bottom, #030916, #c7d1de);
  font-family: 'Poppins', sans-serif;
  overflow: hidden;
}

/* ── LEFT ── */
.insights-left {
  padding: 80px 60px 80px 80px;
  display: flex;
  flex-direction: column;
  gap: 28px;
}

.insights-heading {
  font-family: 'Poppins', serif;
  font-size: clamp(36px, 4vw, 56px);
  font-weight: 400;
  color: #faf8f8;
  line-height: 1.1;
  margin: 0;
}

.insights-subheading {
  font-size: 15px;
  color: #f1eded;
  line-height: 1.7;
  font-weight: 300;
  max-width: 480px;
  margin: 0;
}

.insights-list {
  display: flex;
  flex-direction: column;
  margin-top: 8px;
}

.insights-item {
  display: flex;
  align-items: flex-start;
  gap: 24px;
  padding: 18px 0;
  border-top: 1px solid #e8e8e8;
}

.insights-item:last-child {
  border-bottom: 1px solid #e8e8e8;
}

.insights-num {
  font-size: 13px;
  color: #f1f1f1;
  font-weight: 400;
  letter-spacing: 0.05em;
  min-width: 24px;
  padding-top: 2px;
}

.insights-item p {
  font-size: 15px;
  color: #f5f1f1;
  line-height: 1.6;
  font-weight: 400;
  margin: 0;
}


/* ── RIGHT ── */
.insights-right {
  position: relative;
  background: transparent;
  border-radius: 0;
  padding-right: 20px;
  box-sizing: border-box;
}

.insights-carousel-outer {
  width: 100%;
  height: 100%;
  overflow: hidden;
  position: relative;
}

.insights-carousel-track {
  display: flex;
  height: 100%;
  width: 100%;
}

.insights-slide {
  min-width: 100%;
  width: 100%;
  flex-shrink: 0;

  display: flex;
  align-items: center;
  justify-content: center;

  padding: 20px 20px;
  box-sizing: border-box; 
}

.insights-slide img {
  max-width: 100%;
  max-height: 100%;

  width: auto;
  height: auto;

  object-fit: contain;
  display: block;
  border-radius: 20px;
}

.insights-image-wrapper {
  position: relative;  /* arrows now position relative to this */
  width: 100%;
  height: 100%;
  overflow: hidden;
}

.insights-arrows {
  position: absolute;
  top: 10px;       /* sits just above the image */
  right: 0px;
  display: flex;
  gap: 8px;
  z-index: 10;
}

.insights-arrow {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  border: none;
  background: rgba(255, 255, 255, 0.9);
  color: #333;
  font-size: 18px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s, transform 0.15s;
  backdrop-filter: blur(4px);
}

.insights-arrow:hover {
  background: #3d5fe8;
  transform: scale(1.08);
}

.insights-arrow:active {
  transform: scale(0.96);
}
