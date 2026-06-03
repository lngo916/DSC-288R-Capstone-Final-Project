
const SLIDES = [
  { id:'s1', label:'Intro' },
  { id:'toc', label:'Table of Contents' },
  { id:'po-pic', label:'Overview' },
  { id:'po1', label:'Overview' },
  { id:'ls-pic', label:'Literature Survey' },
  { id:'ls1', label:'Literature Survey' },
  { id:'ls2', label:'Literature Survey' },
  { id:'dataset-pic', label:'Dataset' },
  { id:'d1', label:'Dataset' },
  { id:'d2', label:'Dataset' },
  { id:'fe-pic', label:'Feature Extraction' },
  { id:'fe1', label:'Feature Extraction' },
  { id:'fe2', label:'EDA' },
  { id:'fe3', label:'Feature Engineering' },
  { id:'ml-pic', label:'Machine Learning' },
  { id:'ml1', label:'Machine Learning' },
  { id:'ro-pic', label:'Results' },
  { id:'ro1', label:'Key Findings' },
  { id:'ro2', label:'More Results' },
  { id:'planning-pic', label:'Planning' },
  { id:'p1', label:'Implementation' },
  { id:'p2', label:'Pipeline' },
  { id:'team1', label:'Team' },
  { id:'references-pic', label:'References' },
  { id:'r1', label:'Reference List' },
  { id:'thankyou', label:'Thank You' },
];

const els=SLIDES.map(s=>document.getElementById(s.id));
const dotsEl=document.getElementById('nav-dots');
const labelEl=document.getElementById('nav-label');
let cur=0;

// build dots
SLIDES.forEach((_,i)=>{
  const d=document.createElement('div');
  d.className='nav-dot'+(i===0?' active':'');
  d.addEventListener('click',()=>goTo(i));
  dotsEl.appendChild(d);
});

function goTo(idx){
  const prev=cur;
  cur=Math.max(0,Math.min(SLIDES.length-1,idx));
  els[prev].classList.remove('active');
  els[prev].classList.add('prev');
  setTimeout(()=>els[prev].classList.remove('prev'),500);
  els[cur].classList.add('active');
  dotsEl.querySelectorAll('.nav-dot').forEach((d,i)=>d.classList.toggle('active',i===cur));
  labelEl.textContent=SLIDES[cur].label;

  // trigger metric bars on slide 5
  if(cur===4){
    setTimeout(()=>{
      const targets=[91,87,83,85];
      ['b1','b2','b3','b4'].forEach((id,i)=>{
        const el=document.getElementById(id);
        if(el) el.style.width=targets[i]+'%';
      });
    },400);
  }
}

document.getElementById('nav-prev').addEventListener('click',()=>goTo(cur-1));
document.getElementById('nav-next').addEventListener('click',()=>goTo(cur+1));

// keyboard
window.addEventListener('keydown',e=>{
  if(e.key==='ArrowRight'||e.key===' ') goTo(cur+1);
  if(e.key==='ArrowLeft') goTo(cur-1);
});

// init first slide
els[0].classList.add('active');
