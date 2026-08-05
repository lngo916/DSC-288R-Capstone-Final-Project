
const MODELS = {
  xgb: {
    name:'XGBoost', tag:'ENSEMBLE', tagClass:'tag-ensemble',
    desc:'Gradient-boosted decision trees via XGBoost4J-Spark. Achieves the highest AUC-ROC (0.877) with a near-zero generalization gap — the top performer in this pipeline.',
    auc:'0.877', aucpr:'0.990', acc:'93.4%', f1:'0.910',
    trainAUC:0.8802, valAUC:0.8772,
    cm:{ tp:18259, fp:3004, fn:5142, tn:289042 },
    roc:[
      {x:0.0, y:0.114},
      {x:0.1, y:0.682},
      {x:0.2, y:0.789},
      {x:0.3, y:0.852},
      {x:0.4, y:0.896},
      {x:0.5, y:0.928},
      {x:0.6, y:0.952},
      {x:0.7, y:0.970},
      {x:0.8, y:0.984},
      {x:0.9, y:0.994},
      {x:1.0, y:1.000}
    ],
    feat:[
      ['author_playtime_forever',     0.781],
      ['author_playtime_at_review',   0.081],
      ['author_num_games_owned',      0.029],
      ['written_during_early_access', 0.024],
      ['weighted_vote_score',         0.019],
      ['votes_up',                    0.017],
      ['author_num_reviews',          0.014],
      ['voted_up',                    0.013],
      ['comment_count',               0.011],
      ['votes_funny',                 0.01]
    ]
  },
  rf: {
    name:'Random Forest', tag:'ENSEMBLE', tagClass:'tag-ensemble',
    desc:'Ensemble of bootstrapped decision trees. Strong AUC-PR (0.986) and excellent generalization — only a +0.002 train-val gap. Trades slight AUC-ROC for faster iteration.',
    auc:'0.852', aucpr:'0.986', acc:'93.3%', f1:'0.900',
    trainAUC:0.8543, valAUC:0.8520,
    cm:{ tp:0, fp:0, fn:21222, tn:294283 },
    roc:[
      {x:0.0, y:0.000},
      {x:0.1, y:0.621},
      {x:0.2, y:0.767},
      {x:0.3, y:0.832},
      {x:0.4, y:0.885},
      {x:0.5, y:0.920},
      {x:0.6, y:0.946},
      {x:0.7, y:0.966},
      {x:0.8, y:0.982},
      {x:0.9, y:0.992},
      {x:1.0, y:1.000}
    ],
    feat:[
      ['author_playtime_forever',     0.711],
      ['author_playtime_at_review',   0.25],
      ['author_num_reviews',          0.016],
      ['author_num_games_owned',      0.014],
      ['voted_up',                    0.003],
      ['weighted_vote_score',         0.002],
      ['wirtten_during_early_access', 0.002],
      ['comment_count',               0.001],
      ['votes_funny',                 0.001],
      ['voted_up',                    0.00]
    ]
  },
  lr: {
    name:'Logistic Regression', tag:'LINEAR', tagClass:'tag-linear',
    desc:'Linear classifier optimized via L-BFGS. Near-zero generalization gap (−0.0003) confirms no overfitting. Fastest to interpret and a strong baseline for nonlinear comparisons.',
    auc:'0.826', aucpr:'0.981', acc:'93.3%', f1:'0.911',
    trainAUC:0.8255, valAUC:0.8257,
    cm:{ tp:2071, fp:1885, fn:19151, tn:29238 },
    roc:[
      {x:0.0, y:0.000},
      {x:0.1, y:0.460},
      {x:0.2, y:0.699},
      {x:0.3, y:0.835},
      {x:0.4, y:0.887},
      {x:0.5, y:0.922},
      {x:0.6, y:0.948},
      {x:0.7, y:0.968},
      {x:0.8, y:0.983},
      {x:0.9, y:0.993},
      {x:1.0, y:1.000}
    ],
    feat:[
      ['weighted_vote_score',         0.616],
      ['voted_up',                    0.227],
      ['written_during_early_access', 0.107],
      ['comment_count',               0.023],
      ['author_num_reviews',          0.022],
      ['votes_funny',                 0.002],
      ['author_num_games_owned',      0.001],
      ['votes_up',                    0.001],
      ['author_playtime_forever',     0.00],
      ['author_playtime_at_review',   0.00]
    ]
  },
  dt: {
    name:'Decision Tree', tag:'TREE', tagClass:'tag-tree',
    desc:'Single interpretable decision tree — fastest non-linear option (101s). Matched Logistic Regression exactly on AUC and accuracy, suggesting natural decision boundaries in this dataset.',
    auc:'0.755', aucpr:'0.9676', acc:'93.3%', f1:'0.9042',
    trainAUC:0.7548, valAUC:0.7550,
    cm:{ tp:669, fp:20553, fn:658, tn:293625 },
    roc:[
      {x:0.0, y:0.000},
      {x:0.1, y:0.318},
      {x:0.2, y:0.566},
      {x:0.3, y:0.753},
      {x:0.4, y:0.881},
      {x:0.5, y:0.920},
      {x:0.6, y:0.944},
      {x:0.7, y:0.967},
      {x:0.8, y:0.982},
      {x:0.9, y:0.992},
      {x:1.0, y:1.000}
    ],
    feat:[
      ['author_playtime_forever',     0.985],
      ['author_playtime_at_review',   0.007],
      ['author_num_games_owned',      0.004],
      ['votes_up',                    0.001],
      ['written_during_early_access', 0.001],
      ['author_num_reviews',          0.001],
      ['comment_count',               0.001],
      ['weighted_vote_score',         0.00],
      ['voted_up',                    0.00],
      ['votes_funny',                 0.00]
    ]
  },
  svm: {
    name:'SVM', tag:'LINEAR', tagClass:'tag-svm',
    desc:'Linear Support Vector Machine. Lowest AUC-ROC (0.753) and no probability output — a notable limitation for workflows requiring calibrated churn scores. Excluded from final pipeline.',
    auc:'0.753', aucpr:'0.972', acc:'93.3%', f1:'0.900',
    trainAUC:0.7548, valAUC:0.7533,
    cm:{ tp:0, fp:0, fn:21222, tn:294283 },
    roc:[
      {x:0.0, y:0.000},
      {x:0.1, y:0.297},
      {x:0.2, y:0.500},
      {x:0.3, y:0.657},
      {x:0.4, y:0.886},
      {x:0.5, y:0.880},
      {x:0.6, y:0.923},
      {x:0.7, y:0.963},
      {x:0.8, y:0.981},
      {x:0.9, y:0.993},
      {x:1.0, y:1.000}
    ],
    feat:[
      ['written_during_early_access', 0.40],
      ['voted_up',                    0.342],
      ['comment_count',               0.109],
      ['author_num_reviews',          0.081],
      ['votes_funny',                 0.068],
      ['votes_up',                    0.001],
      ['author_num_games_owned',      0.00],
      ['author_playtime_forever',     0.00],
      ['author_playtime_at_review',   0.00],
      ['weighted_vote_score',         0.00]
    ]
  }
};

let activeModel = 'xgb';
let activeChart = 'feat';
let rocInst = null;

function switchModel(key) {
  activeModel = key;
  const m = MODELS[key];

  document.getElementById('mName').textContent = m.name;
  const tag = document.getElementById('mTag');
  tag.textContent = m.tag;
  tag.className = 'model-tag ' + m.tagClass;
  document.getElementById('mDesc').textContent = m.desc;
  document.getElementById('mAUC').textContent = m.auc;
  document.getElementById('mAUCPR').textContent = m.aucpr;
  document.getElementById('mAcc').textContent = m.acc;
  document.getElementById('mF1').textContent = m.f1;

  document.querySelectorAll('.mtab').forEach(b => {
    b.classList.toggle('active', b.getAttribute('onclick').includes("'" + key + "'"));
  });

  const gap = (m.trainAUC - m.valAUC);
  const gapStr = (gap >= 0 ? '+' : '') + gap.toFixed(4);
  document.getElementById('mGapRows').innerHTML = `
    <div class="gap-row">
      <span class="gap-name">AUC-ROC</span>
      <div class="gap-bar-track"><div class="gap-bar-fill" style="width:${Math.round(m.valAUC*100)}%"></div></div>
      <span class="gap-val">${m.valAUC.toFixed(4)}</span>
      <span class="gap-diff">(${gapStr})</span>
    </div>`;

  document.getElementById('cmTP').textContent = m.cm.tp.toLocaleString();
  document.getElementById('cmFP').textContent = m.cm.fp.toLocaleString();
  document.getElementById('cmFN').textContent = m.cm.fn.toLocaleString();
  document.getElementById('cmTN').textContent = m.cm.tn.toLocaleString();

  renderActiveChart();
}

function switchChart(type) {
  activeChart = type;
  document.querySelectorAll('.chart-tab').forEach(b =>
    b.classList.toggle('active', b.getAttribute('onclick').includes("'" + type + "'"))
  );
  ['feat','roc','cm'].forEach(v => {
    document.getElementById('view-' + v).classList.toggle('active', v === type);
  });
  renderActiveChart();
}

function renderActiveChart() {
  if (activeChart === 'feat') renderFeat();
  if (activeChart === 'roc') renderROC();
}

function renderFeat() {
  const feats = MODELS[activeModel].feat;
  const max = feats[0][1];
  document.getElementById('featBarsEl').innerHTML = feats.map(([name, val]) => `
    <div class="fbar-row">
      <div class="fbar-name">${name}</div>
      <div class="fbar-track"><div class="fbar-fill" style="width:${Math.round(val/max*100)}%"></div></div>
      <div class="fbar-pct">${(val * 100).toFixed(1)}%</div>
    </div>`).join('');
}

function renderROC() {
  if (rocInst) { rocInst.destroy(); rocInst = null; }
  const m = MODELS[activeModel];

  // Use real ROC points if available, otherwise fall back to approximation
  const pts = m.roc
    ? m.roc
    : (() => {
        const auc = parseFloat(m.auc);
        const generated = [];
        for (let i = 0; i <= 20; i++) {
          const x = i / 20;
          const y = Math.min(1, Math.pow(x, 1 / (auc * 3 + 0.5)));
          generated.push({ x: +x.toFixed(3), y: +y.toFixed(3) });
        }
        return generated;
      })();

  rocInst = new Chart(document.getElementById('rocCanvas'), {
    type: 'scatter',
    data: { datasets: [
      { label: m.name, data: pts, showLine: true, borderColor: '#9cbfe2', backgroundColor: 'rgba(156,191,226,0.08)', borderWidth: 2, pointRadius: 3, tension: 0.3 },
      { label: 'Random', data: [{x:0,y:0},{x:1,y:1}], showLine: true, borderColor: 'rgba(255,255,255,0.15)', borderWidth: 1, borderDash: [5,5], pointRadius: 0 }
    ]},
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { title: { display: true, text: 'False positive rate', color: '#c8d8e8', font: { size: 10, family: 'Poppins' } }, ticks: { color: '#c8d8e8', font: { size: 10 }, stepSize: 0.1 }, grid: { color: 'rgba(255,255,255,0.04)' }, min: 0, max: 1 },
        y: { title: { display: true, text: 'True positive rate',  color: '#c8d8e8', font: { size: 10, family: 'Poppins' } }, ticks: { color: '#c8d8e8', font: { size: 10 }, stepSize: 0.1 }, grid: { color: 'rgba(255,255,255,0.04)' }, min: 0, max: 1 }
      }
    }
  });
}

// AUC bar chart
new Chart(document.getElementById('aucChart'), {
  type: 'bar',
  data: {
    labels: ['XGBoost','Rand Forest','Log Reg','Dec Tree','SVM'],
    datasets: [{
      data: [0.877, 0.852, 0.826, 0.826, 0.753],
      backgroundColor: ['#b9dcf9','#6fa8d4','#4d8ab8','#4d8ab8','#3a6f9e'],
      borderWidth: 0, borderRadius: 4
    }]
  },
  options: {
    responsive: true, maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      x: { ticks: { color: '#c8d8e8', font: { size: 10, family: 'Poppins' } }, grid: { display: false } },
      y: { min: 0.7, max: 0.92, ticks: { color: '#c8d8e8', font: { size: 10 } }, grid: { color: 'rgba(255,255,255,0.04)' } }
    }
  }
});

// Train vs val chart
new Chart(document.getElementById('gapChart'), {
  type: 'bar',
  data: {
    labels: ['XGBoost','Rand Forest','Log Reg','Dec Tree','SVM'],
    datasets: [
      { label:'Train', data:[0.8802,0.8543,0.8255,0.8255,0.7548], backgroundColor:'#6baced', borderWidth:0, borderRadius:4 },
      { label:'Val',   data:[0.8772,0.8520,0.8257,0.8257,0.7533], backgroundColor:'#0d4379', borderWidth:1, borderColor:'#9cbfe2', borderRadius:4 }
    ]
  },
  options: {
    responsive: true, maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      x: { ticks: { color: '#c8d8e8', font: { size: 10, family: 'Poppins' } }, grid: { display: false } },
      y: { min: 0.7, max: 0.92, ticks: { color: '#c8d8e8', font: { size: 10 } }, grid: { color: 'rgba(255,255,255,0.04)' } }
    }
  }
});

switchModel('xgb');
