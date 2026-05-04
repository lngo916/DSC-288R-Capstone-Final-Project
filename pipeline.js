
    const canvas = document.getElementById('c');
    const ctx = canvas.getContext('2d');
    const mm = document.getElementById('minimap');
    const mctx = mm.getContext('2d');
    const wrap = document.getElementById('canvas-wrap');

    const C = {
      source: '#4a9eca', branch: '#6fcf97', process: '#f2994a',
      eda: '#bb86fc', ml: '#e8880a', output: '#eb5757', infra: '#9cbfe2',
      bg: '#02050c', card: '#0d1a2e', border: 'rgba(156,191,226,0.18)',
      text: '#ffffff', subtext: '#c8d8e8', edge: 'rgba(156,191,226,0.25)',
    };

    /* ─── NODES ──────────────────────────────────────────────────────── */
    /* Layout mirrors the attached image: left=sources, flowing right to outputs.
       Rows are spaced 90px apart vertically; columns 180px apart horizontally. */
    const COL = (n) => 60 + n * 180;
    const ROW = (n) => 60 + n * 90;

    const NODES = [
      /* ── COL 0: Data Sources ── */
      {id:'kaggle1',   label:'Kaggle Dataset',  sub:'~43GB Game CSV',    x:COL(0), y:ROW(1), type:'source',  cat:'source',
       desc:'Raw Kaggle game dataset ~43GB CSV. Game metadata, tags, pricing, release info.',
       meta:{Size:'~43 GB',Format:'CSV',Output:'Parquet'}},
      {id:'kaggle2',   label:'Kaggle Dataset',  sub:'~43GB Multimodal',  x:COL(0), y:ROW(3), type:'source',  cat:'source',
       desc:'Second Kaggle dataset ~43GB CSV. Multimodal data: descriptions, screenshots, system requirements.',
       meta:{Size:'~43 GB',Format:'CSV',Output:'Parquet'}},
      {id:'kaggle3',   label:'Kaggle Dataset',  sub:'~43GB Reviews',     x:COL(0), y:ROW(5), type:'source',  cat:'source',
       desc:'Third Kaggle dataset ~43GB CSV. User review data including review text and helpfulness scores.',
       meta:{Size:'~43 GB',Format:'CSV',Output:'Parquet'}},
      {id:'steam_api', label:'Steam API',        sub:'JSONs',             x:COL(0), y:ROW(7), type:'source',  cat:'source',
       desc:'Live Steam API endpoints. Returns JSON on player counts, achievements, game details and profiles.',
       meta:{Format:'JSON',Protocol:'REST',Rate:'500/day'}},

      /* ── COL 1: Branches & API Scripts ── */
      {id:'game_br',   label:'Game Branch',      sub:'',                  x:COL(1), y:ROW(1), type:'branch',  cat:'source',
       desc:'Orchestrates all game-metadata pipeline stages. Routes game CSV through ingestion and health audit.',
       meta:{Framework:'Spark',Output:'Parquet'}},
      {id:'multi_br',  label:'Multimodal Branch',sub:'',                  x:COL(1), y:ROW(3), type:'branch',  cat:'source',
       desc:'Handles multimodal data (text + images). Reads author code as reference. Routes to multimodal EDA.',
       meta:{Framework:'Pandas',Output:'Parquet'}},
      {id:'review_br', label:'Review Branch',    sub:'',                  x:COL(1), y:ROW(5), type:'branch',  cat:'source',
       desc:'Manages review-data pipeline from ingestion through feature engineering and ML modeling.',
       meta:{Framework:'Spark',Output:'Parquet'}},
      {id:'api_rg',    label:'API Script',        sub:'Review & Game',    x:COL(1), y:ROW(7), type:'branch',  cat:'source',
       desc:'Python script calling Steam API for review and game data. Outputs structured JSON.',
       meta:{Output:'JSON',Runtime:'Python'}},
      {id:'api_mm',    label:'API Script',        sub:'Multimodal',       x:COL(1), y:ROW(8), type:'branch',  cat:'source',
       desc:'Dedicated API script for multimodal Steam data: screenshots, banners, descriptions.',
       meta:{Output:'JSON',Runtime:'Python'}},

      /* ── COL 2: Ingestion / KNN ── */
      {id:'knn',       label:'KNN Script',        sub:'~350MB → Parquet', x:COL(2), y:ROW(1), type:'process', cat:'process',
       desc:'K-Nearest Neighbors preprocessing. Reduces game dataset to ~350MB Parquet for Pandas pipeline.',
       meta:{Size:'~350 MB',Framework:'Pandas',Output:'Parquet'}},
      {id:'read_code', label:'Read Author Code',  sub:'As reference',     x:COL(2), y:ROW(3), type:'infra',   cat:'infra',
       desc:'Reference step: reads existing author code as context before processing multimodal data.',
       meta:{Type:'Reference',Stage:'Pre-processing'}},
      {id:'ingest',    label:'Data Ingestion',    sub:'~38GB → Parquet',  x:COL(2), y:ROW(5), type:'process', cat:'process',
       desc:'Spark ingestion job reading raw CSV review data ~38GB. Cleans and converts to columnar Parquet.',
       meta:{Size:'~38 GB',Framework:'Spark',Output:'Parquet'}},
      {id:'sample',    label:'Data Sampling',     sub:'2-5GB → Parquet',  x:COL(2), y:ROW(7), type:'process', cat:'process',
       desc:'Downsamples the full review dataset to 2-5GB Parquet for Pandas-based exploration.',
       meta:{Size:'2-5 GB',Framework:'Spark → Pandas',Output:'Parquet'}},

      /* ── COL 3: EDA / Health Audit ── */
      {id:'eda_knn',   label:'EDA',               sub:'~777 rows (Spark)',x:COL(3), y:ROW(1), type:'eda',     cat:'eda',
       desc:'Exploratory data analysis on KNN-preprocessed game data (~777 rows). Run in Spark for fast profiling.',
       meta:{Rows:'~777',Framework:'Spark',Output:'Parquet???'}},
      {id:'dha_global',label:'Data Health Audit', sub:'+ Global EDA',     x:COL(3), y:ROW(3), type:'eda',     cat:'eda',
       desc:'Combined health audit and global EDA on full game+review data. No practical size limit — Spark.',
       meta:{Framework:'Spark',Output:'Parquet'}},
      {id:'dha_review',label:'Data Health Audit', sub:'No output (Spark)',x:COL(3), y:ROW(5), type:'eda',     cat:'eda',
       desc:'Health audit on raw review ingestion. Checks nulls, schema drift, duplicate keys. Logs only.',
       meta:{Framework:'Spark',Output:'None (logs)'}},
      {id:'dha_sample',label:'Data Health Audit', sub:'No output (Pandas)',x:COL(3),y:ROW(7), type:'eda',     cat:'eda',
       desc:'Health audit on the sampled review dataset before Pandas EDA. Flags anomalies and schema violations.',
       meta:{Framework:'Pandas',Output:'None (logs)'}},

      /* ── COL 4: Data Comparison / Prep ── */
      {id:'data_comp', label:'Data Comparison',   sub:'Game vs Review',   x:COL(4), y:ROW(0), type:'process', cat:'process',
       desc:'Compares game-data vs review-data schemas and distributions. Identifies join keys and drift.',
       meta:{Framework:'Spark',Output:'None'}},
      {id:'prep_big',  label:'Data Preparation',  sub:'~33-34GB → Parquet',x:COL(4),y:ROW(3), type:'process', cat:'process',
       desc:'Full Spark data preparation on merged review data ~33-34GB. Produces clean Parquet for global EDA.',
       meta:{Size:'~33-34 GB',Framework:'Spark',Output:'Parquet'}},
      {id:'prep_small',label:'Data Preparation',  sub:'~1-4GB → Parquet', x:COL(4), y:ROW(5), type:'process', cat:'process',
       desc:'Lighter Pandas data prep on 1-4GB sampled data. Joins game metadata and cleans review text.',
       meta:{Size:'~1-4 GB',Framework:'Pandas',Output:'Parquet'}},
      {id:'dha_prep',  label:'Health Audit + Prep',sub:'~1-4GB → Parquet',x:COL(4), y:ROW(7), type:'process', cat:'process',
       desc:'Combined health audit and data prep on 1-4GB sample. Runs in Pandas with schema validation.',
       meta:{Size:'~1-4 GB',Framework:'Pandas',Output:'Parquet'}},

      /* ── COL 5: Global EDA / Mature EDA ── */
      {id:'rec_sys',   label:'Recommendation Sys',sub:'Pickle + App',     x:COL(5), y:ROW(0), type:'output',  cat:'output',
       desc:'Recommender system output: trained collaborative filter serialized as Pickle, served via App.',
       meta:{Output:'Pickle + App',Framework:'Pandas'}},
      {id:'global_eda',label:'Global EDA',         sub:'~33-34GB (Spark)',  x:COL(5), y:ROW(3), type:'eda',     cat:'eda',
       desc:'Full global EDA on ~33-34GB of merged Steam data in Spark. Distribution reports and feature insights.',
       meta:{Size:'~33-34 GB',Framework:'Spark',Output:'Parquet'}},
      {id:'mature_eda',label:'Mature Sample EDA',  sub:'Pandas',           x:COL(5), y:ROW(5), type:'eda',     cat:'eda',
       desc:'Deep-dive EDA on mature sample using Pandas. Segmentation, sentiment histograms, genre patterns.',
       meta:{Framework:'Pandas',Output:'Plots + Stats'}},
      {id:'pre_eda',   label:'Preliminary EDA',    sub:'Pandas',           x:COL(5), y:ROW(7), type:'eda',     cat:'eda',
       desc:'Initial quick-look EDA on sample before full preparation. Guides feature selection decisions.',
       meta:{Framework:'Pandas',Output:'Plots + Stats'}},

      /* ── COL 6: Review+Game Merging / Advanced EDA ── */
      {id:'rv_merge',  label:'Review & Game Merge',sub:'Spark',            x:COL(6), y:ROW(3), type:'process', cat:'process',
       desc:'Spark join merging cleaned review Parquet with game metadata Parquet on app_id.',
       meta:{Framework:'Spark',Output:'Merged Parquet'}},
      {id:'adv_eda',   label:'Advanced Sample EDA',sub:'No output',        x:COL(6), y:ROW(6), type:'eda',     cat:'eda',
       desc:'Advanced EDA: regression, spectral, variance analysis. Exploratory — no file output.',
       meta:{Framework:'Pandas',Output:'None',Analyses:'Regression, Spectral, Variance'}},

      /* ── COL 7: Train/Val/Test + Feature Eng ── */
      {id:'tvt_full',  label:'Train/Val/Test Split',sub:'60/20/20% Spark', x:COL(7), y:ROW(2), type:'process', cat:'process',
       desc:'Stratified 60/20/20% TVT split on 3 global files (~7GB total). Run in Spark.',
       meta:{Split:'60/20/20',Size:'~7 GB',Framework:'Spark'}},
      {id:'feat_eng',  label:'Feature Engineering', sub:'~2GB → Parquet',  x:COL(7), y:ROW(3), type:'process', cat:'process',
       desc:'Spark feature engineering: session aggregation, genre embeddings, social graph features. ~2GB Parquet.',
       meta:{Size:'~2 GB',Framework:'Spark',Output:'Parquet'}},
      {id:'tvt_sample',label:'Sample TVT Split',    sub:'Pandas',          x:COL(7), y:ROW(5), type:'process', cat:'process',
       desc:'Train/val/test split on sample-version dataset. Lighter Pandas split for fast experiments.',
       meta:{Framework:'Pandas',Output:'3 split files'}},
      {id:'feat_sample',label:'Sample Feature Eng.',sub:'Pandas',          x:COL(7), y:ROW(6), type:'process', cat:'process',
       desc:'Feature engineering on sample split. Produces smaller feature set for rapid ML experimentation.',
       meta:{Framework:'Pandas'}},

      /* ── COL 8: ML Modeling ── */
      {id:'ml_model',  label:'ML Modeling',         sub:'Spark',           x:COL(8), y:ROW(3), type:'ml',      cat:'ml',
       desc:'Core ML modeling in Spark: trains XGBoost, Random Forest, LSTM on full feature-engineered dataset.',
       meta:{Framework:'Spark',Output:'Pickle / ???',Models:'XGBoost, RF, LSTM'}},
      {id:'tvt_ml',    label:'Sample TVT Split',    sub:'(pre-ML)',         x:COL(8), y:ROW(5), type:'process', cat:'process',
       desc:'Final TVT split on sample data fed into ML models for validation and hyperparameter tuning.',
       meta:{Framework:'Pandas'}},

      /* ── COL 9: Config / Testing / ML Predict / MLaaS / Viz ── */
      {id:'testing',   label:'Testing Module',      sub:'All stages',       x:COL(9), y:ROW(1), type:'infra',   cat:'infra',
       desc:'Testing module applied across all pipeline stages. Unit tests, schema checks, integration tests.',
       meta:{Scope:'All stages',Type:'Unit + Integration'}},
      {id:'config',    label:'Config Module',       sub:'All stages',       x:COL(9), y:ROW(2), type:'infra',   cat:'infra',
       desc:'Central config managing env vars, file paths, and stage toggles across all pipeline steps.',
       meta:{Scope:'All stages',Type:'Config / Env'}},
      {id:'make_file', label:'Make File',           sub:'All stages',       x:COL(9), y:ROW(3), type:'infra',   cat:'infra',
       desc:'Makefile orchestrating all pipeline stages. Single-command pipeline run.',
       meta:{Scope:'All stages',Type:'Orchestration'}},
      {id:'ml_pred',   label:'ML Predict & Eval',  sub:'Spark',            x:COL(9), y:ROW(4), type:'ml',      cat:'ml',
       desc:'Spark ML prediction and evaluation: churn probabilities, AUC-ROC, precision, recall on test set.',
       meta:{Framework:'Spark',Output:'Metrics + Predictions'}},
      {id:'mlaas',     label:'ML as a Service',    sub:'MFaaS',            x:COL(9), y:ROW(5), type:'ml',      cat:'ml',
       desc:'Deploys trained model as a microservice (MFaaS). Serves real-time churn predictions via API.',
       meta:{Type:'MFaaS',Protocol:'REST API'}},
      {id:'viz_gal',   label:'Visualization Gallery',sub:'Deployment endpoint',x:COL(9),y:ROW(6),type:'output', cat:'output',
       desc:'Deployed visualization gallery: Plotly dashboards, Streamlit app, retention curves.',
       meta:{Output:'Streamlit / Plotly',Type:'Web app'}},

      /* ── COL 10: Milestones + Outputs ── */
      {id:'frontend',  label:'Frontend Website',   sub:'By Laura',         x:COL(10),y:ROW(0), type:'output',  cat:'output',
       desc:'Front-end narrative website built by Laura. Interactive presentation site for the project.',
       meta:{Author:'Laura',Stack:'HTML/CSS/JS + Three.js'}},
      {id:'ms1',       label:'Milestone 1',        sub:'',                 x:COL(10),y:ROW(1), type:'infra',   cat:'infra',
       desc:'Milestone 1: data ingestion complete, initial EDA signed off. Deliverable: EDA report + pipeline.',
       meta:{Deliverable:'EDA + Pipeline'}},
      {id:'ms2',       label:'Milestone 2',        sub:'',                 x:COL(10),y:ROW(2), type:'infra',   cat:'infra',
       desc:'Milestone 2: feature engineering complete, TVT splits validated. Deliverable: feature matrix.',
       meta:{Deliverable:'Feature matrix'}},
      {id:'ms3',       label:'Milestone 3',        sub:'',                 x:COL(10),y:ROW(3), type:'infra',   cat:'infra',
       desc:'Milestone 3: ML models trained and evaluated. Deliverable: model comparison report + checkpoint.',
       meta:{Deliverable:'Model checkpoint + report'}},
      {id:'ms4',       label:'Milestone 4',        sub:'',                 x:COL(10),y:ROW(4), type:'infra',   cat:'infra',
       desc:'Milestone 4: recommender system deployed. Deliverable: live recommendation endpoint + demo.',
       meta:{Deliverable:'Deployed recommender'}},
      {id:'web_app',   label:'Web App',            sub:'',                 x:COL(10),y:ROW(5), type:'output',  cat:'output',
       desc:'Front-end Streamlit or React web app surfacing churn scores and game recommendations.',
       meta:{Stack:'Streamlit / React',Type:'Consumer-facing'}},
      {id:'report',    label:'Report',             sub:'',                 x:COL(10),y:ROW(6), type:'output',  cat:'output',
       desc:'Final project report: methodology, EDA findings, model performance. Submitted to UCSD Capstone.',
       meta:{Audience:'UCSD Capstone',Format:'PDF + Slides'}},
      {id:'presentation',label:'Presentation',    sub:'',                 x:COL(10),y:ROW(7), type:'output',  cat:'output',
       desc:'Final presentation deck: narrative website + slides. Summarizes end-to-end pipeline and findings.',
       meta:{Author:'Laura (frontend)',Format:'Website + Slides'}},

      /* ── COL 11: DevOps ── */
      {id:'create_repo',label:'Create the Repo',  sub:'',                 x:COL(11),y:ROW(1), type:'infra',   cat:'infra',
       desc:'GitHub repository setup: branching strategy, folder structure, .gitignore, README scaffold.',
       meta:{Tool:'GitHub',Type:'Repo setup'}},
      {id:'org',        label:'Organization',     sub:'',                 x:COL(11),y:ROW(2), type:'infra',   cat:'infra',
       desc:'Project organization: task assignment, sprint planning, team communication, Notion docs.',
       meta:{Tool:'Notion / Slack',Type:'Project mgmt'}},
      {id:'expanse',    label:'Sync to Expanse',  sub:'',                 x:COL(11),y:ROW(3), type:'infra',   cat:'infra',
       desc:'Syncs codebase and datasets to UCSD Expanse HPC cluster for large-scale Spark and GPU training.',
       meta:{Platform:'UCSD Expanse HPC',Type:'HPC sync'}},
      {id:'dvc',        label:'DVC Tracking',     sub:'',                 x:COL(11),y:ROW(4), type:'infra',   cat:'infra',
       desc:'Data Version Control tracking: versions datasets, models, and pipeline stages for reproducibility.',
       meta:{Tool:'DVC',Type:'Data versioning'}},
      {id:'github',     label:'Github',           sub:'',                 x:COL(11),y:ROW(5), type:'infra',   cat:'infra',
       desc:'GitHub for code versioning, pull requests, CI/CD via GitHub Actions, and project board.',
       meta:{Tool:'GitHub',Type:'Version control'}},

      /* ── Final output ── */
      {id:'product',    label:'Project Product',  sub:'Final deliverable', x:COL(11),y:ROW(7), type:'output',  cat:'output',
       desc:'The shipped project product: deployed recommendation system + web app + full documentation.',
       meta:{Type:'Final deliverable',Status:'Shipped 🎉'}},
    ];

    const NW = 148, NH = 48, NR = 8;
    NODES.forEach(n => { n.w = NW; n.h = NH; });

    /* ─── EDGES ──────────────────────────────────────────────────────── */
    const EDGES = [
      {from:'kaggle1',  to:'game_br',    color:'#4a9eca'},
      {from:'kaggle2',  to:'multi_br',   color:'#4a9eca'},
      {from:'kaggle3',  to:'review_br',  color:'#4a9eca'},
      {from:'steam_api',to:'api_rg',     color:'#4a9eca'},
      {from:'steam_api',to:'api_mm',     color:'#4a9eca'},
      {from:'game_br',  to:'knn',        color:'#6fcf97'},
      {from:'game_br',  to:'dha_global', color:'#6fcf97'},
      {from:'multi_br', to:'read_code',  color:'#6fcf97'},
      {from:'multi_br', to:'dha_global', color:'#6fcf97'},
      {from:'review_br',to:'ingest',     color:'#6fcf97'},
      {from:'review_br',to:'sample',     color:'#6fcf97'},
      {from:'api_rg',   to:'ingest',     color:'#6fcf97'},
      {from:'api_mm',   to:'multi_br',   color:'#6fcf97'},
      {from:'knn',      to:'eda_knn',    color:'#f2994a'},
      {from:'ingest',   to:'dha_review', color:'#f2994a'},
      {from:'sample',   to:'dha_sample', color:'#f2994a'},
      {from:'eda_knn',  to:'data_comp',  color:'#bb86fc'},
      {from:'dha_global',to:'data_comp', color:'#bb86fc'},
      {from:'dha_global',to:'prep_big',  color:'#bb86fc'},
      {from:'dha_review',to:'prep_big',  color:'#bb86fc'},
      {from:'dha_sample',to:'prep_small',color:'#bb86fc'},
      {from:'dha_sample',to:'dha_prep',  color:'#bb86fc'},
      {from:'data_comp',to:'rec_sys',    color:'#f2994a'},
      {from:'prep_big', to:'global_eda', color:'#f2994a'},
      {from:'prep_small',to:'mature_eda',color:'#f2994a'},
      {from:'dha_prep', to:'pre_eda',    color:'#f2994a'},
      {from:'dha_prep', to:'mature_eda', color:'#f2994a'},
      {from:'global_eda',to:'rv_merge',  color:'#bb86fc'},
      {from:'mature_eda',to:'adv_eda',   color:'#bb86fc'},
      {from:'pre_eda',  to:'adv_eda',    color:'#bb86fc'},
      {from:'rec_sys',  to:'rv_merge',   color:'#eb5757'},
      {from:'rv_merge', to:'tvt_full',   color:'#f2994a'},
      {from:'rv_merge', to:'tvt_sample', color:'#f2994a'},
      {from:'adv_eda',  to:'tvt_sample', color:'#bb86fc'},
      {from:'tvt_full', to:'feat_eng',   color:'#f2994a'},
      {from:'tvt_sample',to:'feat_sample',color:'#f2994a'},
      {from:'feat_eng', to:'ml_model',   color:'#f2994a'},
      {from:'feat_sample',to:'tvt_ml',   color:'#f2994a'},
      {from:'tvt_ml',   to:'ml_model',   color:'#f2994a'},
      {from:'ml_model', to:'ml_pred',    color:'#e8880a'},
      {from:'ml_model', to:'mlaas',      color:'#e8880a'},
      {from:'ml_pred',  to:'viz_gal',    color:'#e8880a'},
      {from:'testing',  to:'ml_pred',    color:'#9cbfe2', dash:true},
      {from:'config',   to:'ml_pred',    color:'#9cbfe2', dash:true},
      {from:'make_file',to:'ml_pred',    color:'#9cbfe2', dash:true},
      {from:'ml_pred',  to:'ms1',        color:'#e8880a'},
      {from:'ml_pred',  to:'ms2',        color:'#e8880a'},
      {from:'ml_pred',  to:'ms3',        color:'#e8880a'},
      {from:'mlaas',    to:'ms4',        color:'#e8880a'},
      {from:'mlaas',    to:'web_app',    color:'#e8880a'},
      {from:'ml_pred',  to:'report',     color:'#e8880a'},
      {from:'ms1',      to:'create_repo',color:'#9cbfe2', dash:true},
      {from:'ms2',      to:'org',        color:'#9cbfe2', dash:true},
      {from:'ms3',      to:'expanse',    color:'#9cbfe2', dash:true},
      {from:'ms4',      to:'dvc',        color:'#9cbfe2', dash:true},
      {from:'create_repo',to:'org',      color:'#9cbfe2', dash:true},
      {from:'org',      to:'expanse',    color:'#9cbfe2', dash:true},
      {from:'expanse',  to:'dvc',        color:'#9cbfe2', dash:true},
      {from:'dvc',      to:'github',     color:'#9cbfe2', dash:true},
      {from:'frontend', to:'ms1',        color:'#eb5757'},
      {from:'presentation',to:'product', color:'#eb5757'},
      {from:'web_app',  to:'product',    color:'#eb5757'},
      {from:'report',   to:'product',    color:'#eb5757'},
      {from:'ms4',      to:'product',    color:'#9cbfe2', dash:true},
      {from:'github',   to:'product',    color:'#9cbfe2', dash:true},
    ];

    /* ─── STATE ──────────────────────────────────────────────────────── */
    let ox = 0, oy = 0, scale = 0.55;
    let drag = false, lastX = 0, lastY = 0, moved = false;
    let hovered = null, selected = null;
    let activeFilter = 'all';

    function bounds() {
      let minX=Infinity, minY=Infinity, maxX=-Infinity, maxY=-Infinity;
      NODES.forEach(n => {
        minX=Math.min(minX,n.x); minY=Math.min(minY,n.y);
        maxX=Math.max(maxX,n.x+n.w); maxY=Math.max(maxY,n.y+n.h);
      });
      return {minX,minY,maxX,maxY,w:maxX-minX,h:maxY-minY};
    }

    function resetView() {
      const b=bounds(), W=wrap.clientWidth, H=wrap.clientHeight;
      scale = Math.min(W/(b.w+120), H/(b.h+120), 1);
      ox = (W - b.w*scale)/2 - b.minX*scale;
      oy = (H - b.h*scale)/2 - b.minY*scale;
    }

    function resize() {
      canvas.width = wrap.clientWidth;
      canvas.height = wrap.clientHeight;
    }

    function nodeVisible(n) {
      return activeFilter === 'all' || n.cat === activeFilter;
    }
    function edgeVisible(e) {
      if (activeFilter === 'all') return true;
      const s = NODES.find(n=>n.id===e.from), t = NODES.find(n=>n.id===e.to);
      return s && t && (nodeVisible(s) || nodeVisible(t));
    }

    function hit(n, wx, wy) {
      const sx=n.x*scale+ox, sy=n.y*scale+oy;
      return wx>=sx && wx<=sx+n.w*scale && wy>=sy && wy<=sy+n.h*scale;
    }

    function typeColor(t) { return {source:'#4a9eca',branch:'#6fcf97',process:'#f2994a',eda:'#bb86fc',ml:'#e8880a',output:'#eb5757',infra:'#9cbfe2'}[t]||'#9cbfe2'; }

    /* ─── DRAW NODE ─────────────────────────────────────────────────── */
    function drawNode(n) {
      const x=n.x*scale+ox, y=n.y*scale+oy, w=n.w*scale, h=n.h*scale;
      const isHov=(hovered===n.id), isSel=(selected===n.id);
      const dim = !nodeVisible(n) && activeFilter !== 'all';
      ctx.save();
      ctx.globalAlpha = dim ? 0.12 : 1;

      /* card */
      ctx.fillStyle = '#0d1a2e';
      ctx.beginPath(); ctx.roundRect(x,y,w,h,NR*scale); ctx.fill();

      /* accent bar */
      ctx.fillStyle = typeColor(n.type);
      ctx.beginPath(); ctx.roundRect(x,y,4*scale,h,NR*scale); ctx.fill();

      /* border */
      ctx.strokeStyle = isSel ? typeColor(n.type) : isHov ? 'rgba(156,191,226,0.6)' : 'rgba(156,191,226,0.18)';
      ctx.lineWidth = isSel ? 1.5 : 0.5;
      ctx.beginPath(); ctx.roundRect(x,y,w,h,NR*scale); ctx.stroke();

      /* label */
      const fs = Math.max(8, 11*scale);
      ctx.font = `600 ${fs}px 'Poppins',sans-serif`;
      ctx.fillStyle = '#ffffff';
      ctx.textAlign = 'left'; ctx.textBaseline = 'middle';
      const tx = x+10*scale, maxW = w-16*scale;
      ctx.fillText(n.label, tx, y+h*(n.sub?0.35:0.5), maxW);

      if (n.sub) {
        ctx.font = `300 ${Math.max(7, 9.5*scale)}px 'Poppins',sans-serif`;
        ctx.fillStyle = 'rgba(200,216,232,0.6)';
        ctx.fillText(n.sub, tx, y+h*0.68, maxW);
      }
      ctx.restore();
    }

    /* ─── DRAW EDGE ─────────────────────────────────────────────────── */
    function drawEdge(e) {
      const s=NODES.find(n=>n.id===e.from), t=NODES.find(n=>n.id===e.to);
      if (!s||!t) return;
      const dim = !edgeVisible(e) && activeFilter !== 'all';
      ctx.save();
      ctx.globalAlpha = dim ? 0.04 : 0.45;
      ctx.strokeStyle = e.color||'rgba(156,191,226,0.25)';
      ctx.lineWidth = 1;
      if (e.dash) ctx.setLineDash([4,4]);

      const sx=(s.x+s.w)*scale+ox, sy=(s.y+s.h/2)*scale+oy;
      const tx2=t.x*scale+ox,       ty2=(t.y+t.h/2)*scale+oy;
      const cpx=(sx+tx2)/2;

      ctx.beginPath();
      ctx.moveTo(sx,sy);
      ctx.bezierCurveTo(cpx,sy, cpx,ty2, tx2,ty2);
      ctx.stroke();

      /* arrowhead */
      ctx.setLineDash([]);
      const ang = Math.atan2(ty2-((sy+ty2)/2), tx2-((sx+tx2)/2));
      ctx.beginPath();
      ctx.moveTo(tx2,ty2);
      ctx.lineTo(tx2-7*Math.cos(ang-0.4), ty2-7*Math.sin(ang-0.4));
      ctx.lineTo(tx2-7*Math.cos(ang+0.4), ty2-7*Math.sin(ang+0.4));
      ctx.closePath();
      ctx.fillStyle = e.color||'rgba(156,191,226,0.25)';
      ctx.fill();
      ctx.restore();
    }

    /* ─── MINIMAP ────────────────────────────────────────────────────── */
    function drawMinimap() {
      const b=bounds();
      mctx.clearRect(0,0,180,90);
      mctx.fillStyle='#0a1223';
      mctx.fillRect(0,0,180,90);
      const ms=Math.min(180/b.w, 90/b.h)*0.88;
      const mox=(180-b.w*ms)/2-b.minX*ms, moy=(90-b.h*ms)/2-b.minY*ms;
      NODES.forEach(n => {
        mctx.fillStyle=typeColor(n.type);
        mctx.globalAlpha=nodeVisible(n)||activeFilter==='all'?0.7:0.1;
        mctx.fillRect(n.x*ms+mox, n.y*ms+moy, Math.max(2,n.w*ms), Math.max(2,n.h*ms));
      });
      mctx.globalAlpha=1;
      mctx.strokeStyle='rgba(156,191,226,0.7)';
      mctx.lineWidth=1;
      const vx=(-ox/scale)*ms+mox, vy=(-oy/scale)*ms+moy;
      const vw=(canvas.width/scale)*ms, vh=(canvas.height/scale)*ms;
      mctx.strokeRect(vx,vy,vw,vh);
    }

    /* ─── MAIN LOOP ─────────────────────────────────────────────────── */
    function draw() {
      ctx.clearRect(0,0,canvas.width,canvas.height);
      /* grid */
      const gs=40*scale;
      ctx.fillStyle='rgba(156,191,226,0.04)';
      for(let gx=(ox%gs+gs)%gs;gx<canvas.width;gx+=gs)
        for(let gy=(oy%gs+gs)%gs;gy<canvas.height;gy+=gs)
          ctx.fillRect(gx,gy,1.5,1.5);
      EDGES.forEach(drawEdge);
      NODES.forEach(drawNode);
      drawMinimap();
      requestAnimationFrame(draw);
    }

    /* ─── INTERACTIONS ──────────────────────────────────────────────── */
    canvas.addEventListener('mousedown', e => {
      drag=true; moved=false; lastX=e.clientX; lastY=e.clientY;
    });
    canvas.addEventListener('mousemove', e => {
      const r=canvas.getBoundingClientRect(), mx=e.clientX-r.left, my=e.clientY-r.top;
      if (drag) {
        const dx=e.clientX-lastX, dy=e.clientY-lastY;
        if (Math.abs(dx)>2||Math.abs(dy)>2) moved=true;
        ox+=dx; oy+=dy; lastX=e.clientX; lastY=e.clientY; return;
      }
      let h=null;
      for (const n of NODES) { if(hit(n,mx,my)){h=n.id;break;} }
      hovered=h; canvas.style.cursor=h?'pointer':'grab';
    });
    canvas.addEventListener('mouseup', e => {
      drag=false;
      if (moved) return;
      const r=canvas.getBoundingClientRect(), mx=e.clientX-r.left, my=e.clientY-r.top;
      for (const n of NODES) {
        if (hit(n,mx,my)) { selected=n.id; showDetail(n); return; }
      }
      selected=null;
      document.getElementById('detail').classList.remove('open');
    });
    canvas.addEventListener('wheel', e => {
      e.preventDefault();
      const r=canvas.getBoundingClientRect(), mx=e.clientX-r.left, my=e.clientY-r.top;
      const f=e.deltaY<0?1.12:0.9;
      const ns=Math.max(0.15,Math.min(3,scale*f));
      ox=mx-(mx-ox)*(ns/scale); oy=my-(my-oy)*(ns/scale); scale=ns;
    },{passive:false});

    /* touch */
    let lastDist=0;
    canvas.addEventListener('touchstart',e=>{
      if(e.touches.length===1){drag=true;moved=false;lastX=e.touches[0].clientX;lastY=e.touches[0].clientY;}
      if(e.touches.length===2){lastDist=Math.hypot(e.touches[0].clientX-e.touches[1].clientX,e.touches[0].clientY-e.touches[1].clientY);}
    },{passive:true});
    canvas.addEventListener('touchmove',e=>{
      if(e.touches.length===1&&drag){ox+=e.touches[0].clientX-lastX;oy+=e.touches[0].clientY-lastY;lastX=e.touches[0].clientX;lastY=e.touches[0].clientY;moved=true;}
      if(e.touches.length===2){const d=Math.hypot(e.touches[0].clientX-e.touches[1].clientX,e.touches[0].clientY-e.touches[1].clientY);scale=Math.max(0.15,Math.min(3,scale*d/lastDist));lastDist=d;}
    },{passive:true});
    canvas.addEventListener('touchend',()=>{drag=false;});

    /* ─── DETAIL PANEL ──────────────────────────────────────────────── */
    function showDetail(n) {
      const col=typeColor(n.type);
      const tag=document.getElementById('detail-tag');
      tag.textContent=n.type.toUpperCase();
      tag.style.color=col; tag.style.borderColor=col; tag.style.background=col+'18';
      document.getElementById('detail-name').textContent=n.label+(n.sub?' — '+n.sub:'');
      document.getElementById('detail-desc').textContent=n.desc||'';
      document.getElementById('detail-meta').innerHTML=Object.entries(n.meta||{}).map(
        ([k,v])=>`<div class="meta-row"><span class="meta-key">${k}</span><span class="meta-val">${v}</span></div>`
      ).join('');
      document.getElementById('detail').classList.add('open');
    }
    document.getElementById('detail-close').onclick=()=>{
      document.getElementById('detail').classList.remove('open'); selected=null;
    };

    /* ─── CONTROLS ──────────────────────────────────────────────────── */
    document.getElementById('zin').onclick   = ()=>{ scale=Math.min(3,scale*1.2); };
    document.getElementById('zout').onclick  = ()=>{ scale=Math.max(0.15,scale/1.2); };
    document.getElementById('zreset').onclick= resetView;

    document.querySelectorAll('.filter-btn').forEach(b => {
      b.addEventListener('click', () => {
        activeFilter=b.dataset.filter;
        document.querySelectorAll('.filter-btn').forEach(x=>x.classList.remove('active'));
        b.classList.add('active');
      });
    });

    /* ─── INIT ──────────────────────────────────────────────────────── */
    resize();
    resetView();
    draw();
    window.addEventListener('resize', ()=>{ resize(); resetView(); });
