
/* ================================================================
   CONFIGURATION
================================================================ */
const API_BASE = 'http://localhost:8000';
const WS_URL   = 'ws://localhost:8000/ws/live';
const HEALTH_INTERVAL = 3000;
const WS_FRAME_INTERVAL = 500;

/* ================================================================
   STATE
================================================================ */
const state = {
  camStream: null,
  ws: null,
  wsActive: false,
  sending: false,
  fpsFrames: 0,
  fpsLast: performance.now(),
  fpsVal: 0,
  detectionHistory: [],
  stats: { detections: 0, confSum: 0, chars: 0 },
  currentText: '',
  currentConf: 0,
  currentMethod: '',
  manualWord: [],
  typewriterTimer: null,
  uploadFile: null,
  audioPlaying: false,
  wsReconnectTimer: null,
  wsReconnectDelay: 2000,
};

/* ================================================================
   BRAILLE DATA
================================================================ */
// Standard Grade 1 Braille (dots 1-6 → positions in 2-col, 3-row)
// dot positions: [d1, d2, d3, d4, d5, d6] = [top-L, mid-L, bot-L, top-R, mid-R, bot-R]
const BRAILLE_MAP = {
  A:[1,0,0,0,0,0], B:[1,1,0,0,0,0], C:[1,0,0,1,0,0],
  D:[1,0,0,1,1,0], E:[1,0,0,0,1,0], F:[1,1,0,1,0,0],
  G:[1,1,0,1,1,0], H:[1,1,0,0,1,0], I:[0,1,0,1,0,0],
  J:[0,1,0,1,1,0], K:[1,0,1,0,0,0], L:[1,1,1,0,0,0],
  M:[1,0,1,1,0,0], N:[1,0,1,1,1,0], O:[1,0,1,0,1,0],
  P:[1,1,1,1,0,0], Q:[1,1,1,1,1,0], R:[1,1,1,0,1,0],
  S:[0,1,1,1,0,0], T:[0,1,1,1,1,0], U:[1,0,1,0,0,1],
  V:[1,1,1,0,0,1], W:[0,1,0,1,1,1], X:[1,0,1,1,0,1],
  Y:[1,0,1,1,1,1], Z:[1,0,1,0,1,1],
};

/* ================================================================
   DOM REFS
================================================================ */
const $ = id => document.getElementById(id);
const dom = {
  statusDot:      $('status-dot'),
  statusText:     $('status-text'),
  statusPill:     $('status-pill'),
  video:          $('live-video'),
  overlayCanvas:  $('overlay-canvas'),
  camPlaceholder: $('cam-placeholder'),
  btnStartCam:    $('btn-start-cam'),
  btnStopCam:     $('btn-stop-cam'),
  btnCapture:     $('btn-capture'),
  liveBadge:      $('live-badge'),
  fpsCounter:     $('fps-counter'),
  wsStatusText:   $('ws-status-text'),
  uploadZone:     $('upload-zone'),
  uploadInput:    $('upload-input'),
  uploadPreview:  $('upload-preview'),
  uploadImg:      $('upload-img'),
  btnClearUpload: $('btn-clear-upload'),
  btnDetectUpload:$('btn-detect-upload'),
  btnBrowse:      $('btn-browse'),
  uploadStatusTxt:$('upload-status-text'),
  manualLetterGrid:$('manual-letter-grid'),
  manualWord:     $('manual-word'),
  btnManualClear: $('btn-manual-clear'),
  btnManualDecode:$('btn-manual-decode'),
  detectedTextBox:$('detected-text-box'),
  confRing:       $('conf-ring'),
  confPct:        $('conf-pct'),
  confMethod:     $('conf-method'),
  btnSpeak:       $('btn-speak'),
  btnCopy:        $('btn-copy'),
  btnDownload:    $('btn-download'),
  audioWave:      $('audio-wave'),
  historyList:    $('history-list'),
  refGrid:        $('ref-grid'),
  statDetections: $('stat-detections'),
  statAvgConf:    $('stat-avg-conf'),
  statChars:      $('stat-chars'),
  statSessions:   $('stat-sessions'),
  ttsAudio:       $('tts-audio'),
  toastContainer: $('toast-container'),
};

/* ================================================================
   PARTICLES
================================================================ */
(function initParticles() {
  const canvas = $('particle-canvas');
  const ctx = canvas.getContext('2d');
  let W, H, particles = [], mouse = { x: -9999, y: -9999 };

  function resize() {
    W = canvas.width  = window.innerWidth;
    H = canvas.height = window.innerHeight;
  }
  resize();
  window.addEventListener('resize', resize);
  window.addEventListener('mousemove', e => { mouse.x = e.clientX; mouse.y = e.clientY; });

  const COLORS = ['rgba(124,58,237,', 'rgba(6,182,212,', 'rgba(157,90,245,', 'rgba(34,211,238,'];
  class Particle {
    constructor() { this.reset(true); }
    reset(init) {
      this.x  = Math.random() * (W || 1200);
      this.y  = init ? Math.random() * (H || 800) : (H || 800) + 10;
      this.r  = Math.random() * 2 + 0.5;
      this.vx = (Math.random() - 0.5) * 0.3;
      this.vy = -(Math.random() * 0.4 + 0.1);
      this.alpha = Math.random() * 0.5 + 0.1;
      this.color = COLORS[Math.floor(Math.random() * COLORS.length)];
      this.life = 0;
      this.maxLife = Math.random() * 400 + 200;
    }
    update() {
      // Mouse repel
      const dx = this.x - mouse.x, dy = this.y - mouse.y;
      const dist = Math.sqrt(dx*dx + dy*dy);
      if (dist < 120) {
        const force = (120 - dist) / 120 * 0.5;
        this.vx += (dx / dist) * force;
        this.vy += (dy / dist) * force;
      }
      this.vx *= 0.98; this.vy *= 0.98;
      this.x += this.vx; this.y += this.vy;
      this.life++;
      const ratio = this.life / this.maxLife;
      this.currentAlpha = this.alpha * Math.sin(Math.PI * ratio);
      if (this.life >= this.maxLife || this.y < -10) this.reset(false);
    }
    draw() {
      ctx.beginPath();
      ctx.arc(this.x, this.y, this.r, 0, Math.PI * 2);
      ctx.fillStyle = this.color + this.currentAlpha + ')';
      ctx.fill();
    }
  }

  for (let i = 0; i < 120; i++) particles.push(new Particle());

  function loop() {
    ctx.clearRect(0, 0, W, H);
    for (const p of particles) { p.update(); p.draw(); }
    // Draw connections
    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const dx = particles[i].x - particles[j].x;
        const dy = particles[i].y - particles[j].y;
        const dist = Math.sqrt(dx*dx + dy*dy);
        if (dist < 80) {
          ctx.beginPath();
          ctx.moveTo(particles[i].x, particles[i].y);
          ctx.lineTo(particles[j].x, particles[j].y);
          ctx.strokeStyle = `rgba(124,58,237,${0.06 * (1 - dist/80)})`;
          ctx.lineWidth = 0.5;
          ctx.stroke();
        }
      }
    }
    requestAnimationFrame(loop);
  }
  loop();
})();

/* ================================================================
   TOAST NOTIFICATIONS
================================================================ */
function showToast(msg, type = 'info', duration = 3000) {
  const icons = { success: '✅', error: '❌', info: 'ℹ️' };
  const t = document.createElement('div');
  t.className = `toast ${type}`;
  t.innerHTML = `<span>${icons[type]}</span><span>${msg}</span>`;
  dom.toastContainer.appendChild(t);
  setTimeout(() => {
    t.style.animation = 'toastOut 0.3s ease forwards';
    setTimeout(() => t.remove(), 300);
  }, duration);
}

/* ================================================================
   HEALTH CHECK
================================================================ */
async function pingHealth() {
  try {
    const r = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(2500) });
    const ok = r.ok;
    dom.statusDot.className = 'status-dot ' + (ok ? 'online' : 'offline');
    dom.statusText.textContent = ok ? 'Backend Online' : 'Backend Error';
  } catch {
    dom.statusDot.className = 'status-dot offline';
    dom.statusText.textContent = 'Backend Offline';
  }
}
pingHealth();
setInterval(pingHealth, HEALTH_INTERVAL);

/* ================================================================
   TABS
================================================================ */
document.querySelectorAll('.cam-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.cam-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    tab.classList.add('active');
    $('tab-' + tab.dataset.tab).classList.add('active');
  });
});

/* ================================================================
   CAMERA & WEBSOCKET
================================================================ */
dom.btnStartCam.addEventListener('click', startCamera);
dom.btnStopCam.addEventListener('click', stopCamera);
dom.btnCapture.addEventListener('click', captureAndSend);

async function startCamera() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: 'environment' }
    });
    state.camStream = stream;
    dom.video.srcObject = stream;
    dom.video.style.display = 'block';
    dom.camPlaceholder.style.display = 'none';
    dom.btnStartCam.classList.add('hidden');
    dom.btnStopCam.classList.remove('hidden');
    dom.btnCapture.classList.remove('hidden');
    dom.liveBadge.classList.remove('hidden');
    dom.fpsCounter.classList.remove('hidden');
    connectWebSocket();
    startFpsCounter();
    startAutoSend();
    showToast('Camera started successfully', 'success');
  } catch (err) {
    showToast(`Camera error: ${err.message}`, 'error');
  }
}

function stopCamera() {
  if (state.camStream) {
    state.camStream.getTracks().forEach(t => t.stop());
    state.camStream = null;
  }
  dom.video.srcObject = null;
  dom.video.style.display = 'none';
  dom.camPlaceholder.style.display = '';
  dom.btnStartCam.classList.remove('hidden');
  dom.btnStopCam.classList.add('hidden');
  dom.btnCapture.classList.add('hidden');
  dom.liveBadge.classList.add('hidden');
  dom.fpsCounter.classList.add('hidden');
  clearInterval(state.autoSendInterval);
  disconnectWebSocket();
  clearCanvas();
  showToast('Camera stopped', 'info');
}

function connectWebSocket() {
  if (state.ws && state.ws.readyState <= 1) return;
  clearTimeout(state.wsReconnectTimer);
  try {
    state.ws = new WebSocket(WS_URL);
    state.ws.binaryType = 'arraybuffer';

    state.ws.onopen = () => {
      state.wsActive = true;
      state.wsReconnectDelay = 2000;
      dom.wsStatusText.textContent = 'WS Connected';
      dom.wsStatusText.style.color = '#10B981';
      showToast('WebSocket connected', 'success');
    };

    state.ws.onclose = () => {
      state.wsActive = false;
      dom.wsStatusText.textContent = 'WS Reconnecting…';
      dom.wsStatusText.style.color = '';
      if (state.camStream) scheduleWsReconnect();
    };

    state.ws.onerror = () => {
      state.wsActive = false;
      dom.wsStatusText.textContent = 'WS Error';
    };

    state.ws.onmessage = event => {
      try {
        const data = JSON.parse(event.data);
        handleDetectionResult(data);
        // Draw annotated frame if returned
        if (data.annotated_frame) {
          drawAnnotatedFrame(data.annotated_frame);
        } else if (data.boxes) {
          drawBoxes(data.boxes);
        }
      } catch (e) {
        console.warn('WS parse error', e);
      }
    };
  } catch (e) {
    scheduleWsReconnect();
  }
}

function scheduleWsReconnect() {
  clearTimeout(state.wsReconnectTimer);
  state.wsReconnectTimer = setTimeout(() => {
    if (state.camStream) connectWebSocket();
  }, state.wsReconnectDelay);
  state.wsReconnectDelay = Math.min(state.wsReconnectDelay * 1.5, 15000);
}

function disconnectWebSocket() {
  clearTimeout(state.wsReconnectTimer);
  if (state.ws) { try { state.ws.close(); } catch {} state.ws = null; }
  state.wsActive = false;
}

function startAutoSend() {
  clearInterval(state.autoSendInterval);
  state.autoSendInterval = setInterval(sendFrame, WS_FRAME_INTERVAL);
}

function sendFrame() {
  if (!state.wsActive || state.sending || !state.camStream) return;
  const tmpCanvas = document.createElement('canvas');
  tmpCanvas.width  = dom.video.videoWidth  || 640;
  tmpCanvas.height = dom.video.videoHeight || 360;
  const ctx = tmpCanvas.getContext('2d');
  ctx.drawImage(dom.video, 0, 0);
  const b64 = tmpCanvas.toDataURL('image/jpeg', 0.75).split(',')[1];
  if (state.ws && state.ws.readyState === WebSocket.OPEN) {
    state.ws.send(JSON.stringify({ frame: b64, timestamp: Date.now() }));
    state.fpsFrames++;
  }
}

function captureAndSend() {
  if (!state.camStream) return;
  sendFrame();
  // Flash effect
  const flash = document.createElement('div');
  flash.style.cssText = 'position:absolute;inset:0;background:#fff;opacity:0.6;pointer-events:none;z-index:10;transition:opacity 0.4s';
  dom.video.parentElement.appendChild(flash);
  setTimeout(() => { flash.style.opacity = '0'; setTimeout(() => flash.remove(), 400); }, 50);
  showToast('Frame captured and sent', 'info');
}

/* FPS counter */
function startFpsCounter() {
  clearInterval(state.fpsInterval);
  state.fpsInterval = setInterval(() => {
    const now = performance.now();
    const elapsed = (now - state.fpsLast) / 1000;
    state.fpsVal = Math.round(state.fpsFrames / elapsed);
    state.fpsFrames = 0;
    state.fpsLast = now;
    dom.fpsCounter.childNodes[0].textContent = state.fpsVal + ' FPS  |  ';
  }, 1000);
}

function clearCanvas() {
  const ctx = dom.overlayCanvas.getContext('2d');
  ctx.clearRect(0, 0, dom.overlayCanvas.width, dom.overlayCanvas.height);
}

function drawAnnotatedFrame(b64) {
  const img = new Image();
  img.onload = () => {
    const c = dom.overlayCanvas;
    c.width  = dom.video.offsetWidth;
    c.height = dom.video.offsetHeight;
    const ctx = c.getContext('2d');
    ctx.clearRect(0, 0, c.width, c.height);
    ctx.drawImage(img, 0, 0, c.width, c.height);
  };
  img.src = 'data:image/jpeg;base64,' + b64;
}

function drawBoxes(boxes) {
  const c = dom.overlayCanvas;
  c.width  = dom.video.offsetWidth;
  c.height = dom.video.offsetHeight;
  const ctx = c.getContext('2d');
  ctx.clearRect(0, 0, c.width, c.height);
  if (!boxes || !boxes.length) return;
  const scaleX = c.width  / (dom.video.videoWidth  || 640);
  const scaleY = c.height / (dom.video.videoHeight || 360);
  boxes.forEach(box => {
    const [x1, y1, x2, y2] = [box.x1*scaleX, box.y1*scaleY, box.x2*scaleX, box.y2*scaleY];
    ctx.strokeStyle = 'rgba(59, 130, 246, 0.7)';
    ctx.lineWidth = 2;
    ctx.strokeRect(x1, y1, x2-x1, y2-y1);
    if (box.label) {
      ctx.fillStyle = 'rgba(59, 130, 246, 0.85)';
      ctx.fillRect(x1, y1-22, ctx.measureText(box.label).width + 12, 22);
      ctx.fillStyle = '#fff';
      ctx.font = 'bold 12px "Plus Jakarta Sans", sans-serif';
      ctx.fillText(box.label, x1+6, y1-6);
    }
  });
}

/* ================================================================
   DETECTION RESULT HANDLER
================================================================ */
function handleDetectionResult(data) {
  const text   = data.text   || data.detected_text || data.result || '';
  const conf   = parseFloat(data.confidence || data.conf || 0);
  const method = data.method || data.model || '';

  if (!text) return;

  state.currentText   = text;
  state.currentConf   = conf;
  state.currentMethod = method;

  // Update UI
  updateDetectedText(text);
  updateConfidence(conf, method);
  addToHistory(text, conf, method);
  updateStats(data);
}

function updateDetectedText(text) {
  clearTimeout(state.typewriterTimer);
  dom.detectedTextBox.textContent = text;
}

function updateConfidence(conf, method) {
  const pct = Math.round(conf * 100);
  const circumference = 163;
  const offset = circumference - (pct / 100) * circumference;
  dom.confRing.style.strokeDashoffset = offset;
  dom.confPct.textContent = pct + '%';

  dom.confMethod.className = 'conf-method ' + (method.toLowerCase().includes('yolo') ? 'yolo' : method ? 'classical' : 'none');
  dom.confMethod.textContent = method || 'Unknown';
  const icon = method.toLowerCase().includes('yolo') ? ' ' : method ? ' ' : '';
  dom.confMethod.textContent = icon + (method || 'No Detection');
}

function addToHistory(text, conf, method) {
  const entry = {
    text, conf, method,
    time: new Date().toLocaleTimeString(),
    id: Date.now(),
  };
  state.detectionHistory.unshift(entry);
  if (state.detectionHistory.length > 10) state.detectionHistory.pop();
  renderHistory();
}

function renderHistory() {
  if (!state.detectionHistory.length) {
    dom.historyList.innerHTML = '<div class="empty-history"><div class="icon"></div>No detections yet.<br/>Start the camera or upload an image.</div>';
    return;
  }
  dom.historyList.innerHTML = state.detectionHistory.map(e => `
    <div class="history-item" data-text="${encodeURIComponent(e.text)}" data-conf="${e.conf}" data-method="${e.method}">
      <div class="history-text">${e.text}</div>
      <div class="history-meta">
        <span>${e.time}</span>
        <span class="history-conf">${Math.round(e.conf*100)}%</span>
        <span>${e.method || 'Unknown'}</span>
      </div>
    </div>
  `).join('');
  dom.historyList.querySelectorAll('.history-item').forEach(item => {
    item.addEventListener('click', () => {
      const text = decodeURIComponent(item.dataset.text);
      const conf = parseFloat(item.dataset.conf);
      const method = item.dataset.method;
      updateDetectedText(text);
      updateConfidence(conf, method);
      state.currentText = text;
      speakText(text);
    });
  });
}

function updateStats(data) {
  const text = data.text || '';
  const conf = data.confidence || 0;
  const lines = data.lines_detected || 1;
  
  state.stats.detections++;
  state.stats.confSum += conf;
  state.stats.chars += text.replace(/\s/g, '').length;
  state.stats.lines += lines;
  
  animateCounter(dom.statDetections, state.stats.detections);
  const avg = Math.round((state.stats.confSum / state.stats.detections) * 100);
  dom.statAvgConf.textContent = avg + '%';
  animateCounter(dom.statChars, state.stats.chars);
  animateCounter(dom.statLines, lines);
}

function animateCounter(el, target) {
  const start = parseInt(el.textContent.replace(/\D/g, '')) || 0;
  const dur = 600;
  const t0 = performance.now();
  function step(now) {
    const p = Math.min((now - t0) / dur, 1);
    const val = Math.round(start + (target - start) * easeOut(p));
    el.textContent = val;
    if (p < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}
function easeOut(t) { return 1 - Math.pow(1 - t, 3); }

/* ================================================================
   UPLOAD
================================================================ */
dom.uploadZone.addEventListener('click', () => dom.uploadInput.click());
dom.btnBrowse.addEventListener('click', () => dom.uploadInput.click());

dom.uploadInput.addEventListener('change', e => {
  const file = e.target.files[0];
  if (file) previewFile(file);
});

dom.uploadZone.addEventListener('dragover', e => {
  e.preventDefault();
  dom.uploadZone.classList.add('drag-over');
});
dom.uploadZone.addEventListener('dragleave', () => dom.uploadZone.classList.remove('drag-over'));
dom.uploadZone.addEventListener('drop', e => {
  e.preventDefault();
  dom.uploadZone.classList.remove('drag-over');
  const file = e.dataTransfer.files[0];
  if (file && file.type.startsWith('image/')) previewFile(file);
  else showToast('Please drop a valid image file', 'error');
});

function previewFile(file) {
  state.uploadFile = file;
  const reader = new FileReader();
  reader.onload = ev => {
    dom.uploadImg.src = ev.target.result;
    dom.uploadZone.style.display = 'none';
    dom.uploadPreview.style.display = 'block';
  };
  reader.readAsDataURL(file);
}

dom.btnClearUpload.addEventListener('click', () => {
  state.uploadFile = null;
  dom.uploadImg.src = '';
  dom.uploadZone.style.display = '';
  dom.uploadPreview.style.display = 'none';
  dom.uploadInput.value = '';
  dom.uploadStatusTxt.textContent = '';
});

dom.btnDetectUpload.addEventListener('click', async () => {
  if (!state.uploadFile) { showToast('Please select an image first', 'error'); return; }
  dom.uploadStatusTxt.textContent = 'Detecting…';
  dom.btnDetectUpload.disabled = true;
  try {
    const formData = new FormData();
    formData.append('file', state.uploadFile);
    const r = await fetch(`${API_BASE}/detect`, { method: 'POST', body: formData });
    if (!r.ok) throw new Error('Detection failed: ' + r.status);
    const data = await r.json();
    handleDetectionResult(data);
    if (data.annotated_image) {
      dom.uploadImg.src = 'data:image/jpeg;base64,' + data.annotated_image;
    }
    dom.uploadStatusTxt.textContent = '✅ Detection complete';
    showToast('Braille detected successfully!', 'success');
    if (data.text) setTimeout(() => speakText(data.text), 500);
  } catch (e) {
    dom.uploadStatusTxt.textContent = '❌ ' + e.message;
    showToast(e.message, 'error');
  }
  dom.btnDetectUpload.disabled = false;
});

/* ================================================================
   MANUAL BRAILLE
================================================================ */
function buildManualGrid() {
  const letters = Object.keys(BRAILLE_MAP).sort();
  dom.manualLetterGrid.innerHTML = '';
  letters.forEach(letter => {
    const dots = BRAILLE_MAP[letter];
    const cell = document.createElement('div');
    cell.className = 'braille-letter-cell';
    cell.dataset.letter = letter;
    const dotGrid = document.createElement('div');
    dotGrid.className = 'braille-dot-mini';
    // Braille cell: col1 = dots 1,2,3 (top to bottom), col2 = dots 4,5,6
    // Render order for 2-col grid: d1, d4, d2, d5, d3, d6
    const order = [0, 3, 1, 4, 2, 5];
    order.forEach(i => {
      const d = document.createElement('div');
      d.className = 'dot' + (dots[i] ? ' active' : '');
      dotGrid.appendChild(d);
    });
    const span = document.createElement('span');
    span.textContent = letter;
    cell.appendChild(dotGrid);
    cell.appendChild(span);
    cell.addEventListener('click', () => {
      cell.classList.toggle('selected');
      const i = state.manualWord.indexOf(letter);
      if (i === -1) state.manualWord.push(letter);
      else state.manualWord.splice(i, 1);
      dom.manualWord.textContent = state.manualWord.join('') || '—';
    });
    dom.manualLetterGrid.appendChild(cell);
  });
}
buildManualGrid();

dom.btnManualClear.addEventListener('click', () => {
  state.manualWord = [];
  dom.manualWord.textContent = '—';
  dom.manualLetterGrid.querySelectorAll('.braille-letter-cell').forEach(c => c.classList.remove('selected'));
});

dom.btnManualDecode.addEventListener('click', async () => {
  if (!state.manualWord.length) { showToast('Select some letters first', 'error'); return; }
  const word = state.manualWord.join('');
  try {
    const r = await fetch(`${API_BASE}/decode`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ braille: word, dots: state.manualWord.map(l => BRAILLE_MAP[l]) }),
    });
    if (!r.ok) throw new Error('Decode error');
    const data = await r.json();
    handleDetectionResult({ text: data.text || word, confidence: data.confidence || 0.95, method: 'Manual/Classical' });
  } catch {
    // Fallback: use typed word directly
    handleDetectionResult({ text: word, confidence: 0.95, method: 'Manual Input' });
  }
  showToast(`Decoded: ${word}`, 'success');
});

/* ================================================================
   SPEAK / TTS
================================================================ */
dom.btnSpeak.addEventListener('click', () => speakText(state.currentText));

async function speakText(text) {
  if (!text || state.audioPlaying) return;
  try {
    const r = await fetch(`${API_BASE}/tts`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });
    if (r.ok) {
      const data = await r.json();
      if (data.audio) {
        const audio = dom.ttsAudio;
        audio.src = 'data:audio/mp3;base64,' + data.audio;
        audio.play();
        state.audioPlaying = true;
        dom.audioWave.classList.remove('hidden');
        audio.onended = () => {
          state.audioPlaying = false;
          dom.audioWave.classList.add('hidden');
        };
        return;
      }
    }
  } catch {}
  // Fallback to Web Speech API
  if ('speechSynthesis' in window) {
    const utt = new SpeechSynthesisUtterance(text);
    utt.rate = 0.9; utt.pitch = 1;
    utt.onstart = () => { state.audioPlaying = true; dom.audioWave.classList.remove('hidden'); };
    utt.onend   = () => { state.audioPlaying = false; dom.audioWave.classList.add('hidden'); };
    speechSynthesis.speak(utt);
    showToast('Speaking via browser TTS', 'info');
  } else {
    showToast('No TTS available', 'error');
  }
}

/* ================================================================
   COPY & DOWNLOAD
================================================================ */
dom.btnCopy.addEventListener('click', () => {
  if (!state.currentText) { showToast('Nothing to copy', 'error'); return; }
  navigator.clipboard.writeText(state.currentText)
    .then(() => showToast('Copied to clipboard!', 'success'))
    .catch(() => showToast('Copy failed', 'error'));
});

dom.btnDownload.addEventListener('click', () => {
  if (!state.currentText) { showToast('Nothing to download', 'error'); return; }
  const blob = new Blob([state.currentText], { type: 'text/plain' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `braille_decoded_${Date.now()}.txt`;
  a.click();
  URL.revokeObjectURL(a.href);
  showToast('Downloaded!', 'success');
});

/* ================================================================
   BRAILLE REFERENCE CHART
================================================================ */
async function buildRefChart() {
  let map = BRAILLE_MAP;
  try {
    const r = await fetch(`${API_BASE}/braille/reference`, { signal: AbortSignal.timeout(3000) });
    if (r.ok) { const d = await r.json(); if (d.patterns) map = d.patterns; }
  } catch {}

  const letters = Object.keys(map).sort();
  dom.refGrid.innerHTML = '';
  letters.forEach((letter, idx) => {
    const dots = map[letter];
    const cell = document.createElement('div');
    cell.className = 'ref-cell glass';
    // Braille dot grid (2-col, 3-row)
    const order = [0, 3, 1, 4, 2, 5];
    const dotsHtml = order.map(i => `<div class="ref-dot${dots[i] ? ' on' : ''}"></div>`).join('');
    cell.innerHTML = `
      <span class="ref-letter">${letter}</span>
      <div class="ref-dots">${dotsHtml}</div>
      <div class="ref-name">${letter}</div>
    `;
    cell.title = `Letter ${letter} — click to hear`;
    cell.addEventListener('click', () => speakText(letter));
    dom.refGrid.appendChild(cell);

    // Staggered reveal via intersection observer
    setTimeout(() => {
      if (cell.classList.contains('visible')) return;
      const io = new IntersectionObserver(entries => {
        if (entries[0].isIntersecting) {
          cell.style.transitionDelay = (idx % 13) * 40 + 'ms';
          cell.classList.add('visible');
          io.disconnect();
        }
      }, { threshold: 0.1 });
      io.observe(cell);
    }, 0);
  });
}
buildRefChart();

/* ================================================================
   SCROLL ANIMATIONS (Intersection Observer)
================================================================ */
const scrollObserver = new IntersectionObserver(entries => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      const el = entry.target;
      const delay = el.dataset.delay || 0;
      setTimeout(() => el.classList.add('visible'), parseInt(delay));
      scrollObserver.unobserve(el);
    }
  });
}, { threshold: 0.15 });

document.querySelectorAll('.step-card').forEach(el => scrollObserver.observe(el));

/* ================================================================
   SMOOTH SCROLL FOR NAV LINKS
================================================================ */
document.querySelectorAll('a[href^="#"]').forEach(a => {
  a.addEventListener('click', e => {
    e.preventDefault();
    const target = document.querySelector(a.getAttribute('href'));
    if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });
});

/* ================================================================
   RESIZE OVERLAY CANVAS
================================================================ */
function syncCanvasSize() {
  const rect = dom.video.getBoundingClientRect();
  dom.overlayCanvas.width  = rect.width;
  dom.overlayCanvas.height = rect.height;
}
window.addEventListener('resize', syncCanvasSize);
dom.video.addEventListener('loadedmetadata', syncCanvasSize);

/* ================================================================
   KEYBOARD SHORTCUTS
================================================================ */
document.addEventListener('keydown', e => {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
  if (e.key === 'c' && !e.ctrlKey) { if (state.camStream) captureAndSend(); }
  if (e.key === 's') speakText(state.currentText);
  if (e.key === 'Escape') { if (state.camStream) stopCamera(); }
});

/* ================================================================
   DEMO / FALLBACK DATA (for when backend is offline)
================================================================ */
// After 5s, if no detection happened, show demo data
setTimeout(() => {
  if (state.stats.detections === 0) {
    handleDetectionResult({
      text: 'HELLO',
      confidence: 0.94,
      method: 'Demo Mode',
    });
  }
}, 5000);

console.log(
  '%c BrailleVision ️ ',
  'background: linear-gradient(135deg, #7C3AED, #06B6D4); color: white; padding: 8px 16px; border-radius: 6px; font-size: 14px; font-weight: bold;',
  '\nAPI:', API_BASE, '\nWS:', WS_URL
);

/* ================================================================
   ACCESSIBILITY: SEMANTIC VOICE COMMANDS
================================================================ */
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
if (SpeechRecognition) {
  const recognition = new SpeechRecognition();
  recognition.continuous = true;
  recognition.interimResults = false;
  recognition.lang = 'en-US';

  // UI indicator
  const voiceIndicator = document.createElement('div');
  voiceIndicator.style.cssText = 'position:fixed; bottom:20px; right:20px; background:rgba(59,130,246,0.15); backdrop-filter:blur(12px); color:#fff; padding:12px 24px; border-radius:30px; font-weight:bold; font-size:16px; z-index:9999; box-shadow: 0 0 20px rgba(59,130,246,0.2); border: 1px solid rgba(59,130,246,0.4); display:flex; align-items:center; gap:8px; cursor:pointer;';
  voiceIndicator.innerHTML = '<span style="font-size:20px">🎤</span> Voice Commands: Listening';
  document.body.appendChild(voiceIndicator);

  // Add Tutorial Audio Button to Top Nav
  const topNav = document.querySelector('.top-nav');
  if(topNav) {
      const tutBtn = document.createElement('button');
      tutBtn.className = 'btn btn-primary';
      tutBtn.innerHTML = '🔊 Play Tutorial';
      tutBtn.style.marginRight = 'auto';
      tutBtn.onclick = () => speakText("Welcome to Braille Vision. Say 'Start Scan' to open your camera and read braille documents. Say 'Stop Scan' to close the camera. The system will automatically read detected text out loud.");
      topNav.insertBefore(tutBtn, topNav.firstChild);
  }

  recognition.onresult = (event) => {
    const lastResult = event.results[event.results.length - 1];
    const command = lastResult[0].transcript.trim().toLowerCase();
    console.log("Voice command received:", command);
    
    // Flash indicator
    voiceIndicator.style.background = 'rgba(59,130,246,0.4)';
    setTimeout(() => voiceIndicator.style.background = 'rgba(59,130,246,0.15)', 300);

    if (command.includes('start scan') || command.includes('open camera')) {
      showToast('Voice Command: Starting camera...', 'success');
      const liveTab = document.querySelector('.cam-tab[data-tab="live"]');
      if (liveTab) liveTab.click();
      startCamera();
    } 
    else if (command.includes('stop scan') || command.includes('close camera')) {
      showToast('Voice Command: Stopping camera...', 'success');
      stopCamera();
    }
    else if (command.includes('tutorial') || command.includes('help')) {
      showToast('Voice Command: Playing tutorial...', 'success');
      speakText("Welcome to Braille Vision. Say 'Start Scan' to open your camera and read braille documents. Say 'Stop Scan' to close the camera. The system will automatically read detected text out loud.");
    }
    else if (command.includes('upload') || command.includes('browse')) {
      showToast('Voice Command: Opening file browser...', 'success');
      const uploadTab = document.querySelector('.cam-tab[data-tab="upload"]');
      if (uploadTab) uploadTab.click();
      if (dom.uploadInput) dom.uploadInput.click();
    }
    else if (command.includes('detect') || command.includes('analyze')) {
      showToast('Voice Command: Detecting Braille...', 'success');
      if (dom.btnDetectUpload) dom.btnDetectUpload.click();
    }
    else if (command.includes('read') || command.includes('speak')) {
      showToast('Voice Command: Reading text aloud...', 'success');
      if (state.currentText) speakText(state.currentText);
      else showToast('Nothing to read yet!', 'error');
    }
  };

  recognition.onend = () => {
    recognition.start(); // Auto-restart
  };
  
  try {
    recognition.start();
  } catch(e) {}
}
