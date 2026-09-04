// RAKSHA AI — Frontend Telemetry & Incident Controller

let audioAlertEnabled = true;
let audioCtx = null;
let lastKnownIncidentId = null;

// Clock Display
function updateClock() {
    const now = new Date();
    const clockEl = document.getElementById('live-clock');
    if (clockEl) {
        clockEl.textContent = now.toLocaleTimeString('en-US', { hour12: false });
    }
}
setInterval(updateClock, 1000);
updateClock();

// Web Audio API Synthesizer for Emergency Siren
function playEmergencySiren() {
    if (!audioAlertEnabled) return;
    try {
        if (!audioCtx) {
            audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        }
        if (audioCtx.state === 'suspended') {
            audioCtx.resume();
        }

        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.type = 'sawtooth';
        
        // High-low emergency siren modulation
        const now = audioCtx.currentTime;
        osc.frequency.setValueAtTime(800, now);
        osc.frequency.exponentialRampToValueAtTime(1400, now + 0.25);
        osc.frequency.exponentialRampToValueAtTime(800, now + 0.5);
        osc.frequency.exponentialRampToValueAtTime(1400, now + 0.75);
        osc.frequency.exponentialRampToValueAtTime(800, now + 1.0);

        gain.gain.setValueAtTime(0.15, now);
        gain.gain.exponentialRampToValueAtTime(0.01, now + 1.1);

        osc.connect(gain);
        gain.connect(audioCtx.destination);
        osc.start(now);
        osc.stop(now + 1.1);
    } catch (e) {
        console.warn('Audio siren playback could not start:', e);
    }
}

function toggleAudioAlert() {
    audioAlertEnabled = !audioAlertEnabled;
    const btn = document.getElementById('btn-mute-sound');
    if (btn) {
        btn.textContent = audioAlertEnabled ? '🔊 Sound On' : '🔇 Muted';
        btn.style.borderColor = audioAlertEnabled ? 'var(--accent-cyan)' : 'var(--text-muted)';
    }
}

// Telemetry Polling Loop
async function pollTelemetry() {
    try {
        const res = await fetch('/api/telemetry');
        if (!res.ok) return;
        const data = await res.json();

        // Update FPS & Vehicle Count
        const fpsEl = document.getElementById('fps-counter');
        const vehEl = document.getElementById('active-vehicles-count');
        const camEl = document.getElementById('camera-indicator');
        const feedSourceEl = document.getElementById('cam-feed-source');

        if (fpsEl) fpsEl.textContent = data.fps || '0.0';
        if (vehEl) vehEl.textContent = data.active_vehicles || '0';
        if (camEl) {
            camEl.textContent = isLiveWebcamActive ? 'ONLINE (LIVE)' : (data.is_synthetic ? 'SIMULATION' : 'ONLINE');
        }
        if (feedSourceEl && !isLiveWebcamActive) {
            feedSourceEl.textContent = data.camera_source || (data.is_synthetic ? 'SIMULATION' : 'WEBCAM');
        }

        // Update Collision HUD & Banner
        const banner = document.getElementById('accident-alert-banner');
        const hudStatus = document.getElementById('collision-hud-status');
        const bannerTitle = document.getElementById('banner-title');
        const bannerSub = document.getElementById('banner-subtitle');

        if (data.active_collision && data.last_incident) {
            const inc = data.last_incident;
            
            if (banner) {
                banner.className = 'alert-banner accident-state';
                bannerTitle.innerHTML = `🚨 ACCIDENT DETECTED — [${inc.incident_id}]`;
                bannerSub.innerHTML = `Severity: <strong style="color:#ff6b6b">${inc.severity}</strong> | Vehicles: ${inc.vehicle_ids} | Automated Emergency Responders Notified.`;
            }
            if (hudStatus) {
                hudStatus.className = 'hud-status-badge alert pulse-anim';
                hudStatus.textContent = `🚨 ACCIDENT: ${inc.severity.toUpperCase()}`;
            }

            // If this is a newly detected incident, pop modal & siren
            if (inc.incident_id !== lastKnownIncidentId) {
                lastKnownIncidentId = inc.incident_id;
                playEmergencySiren();
                showEmergencyModal(inc);
                fetchIncidents();
            }
        } else {
            if (banner && !banner.classList.contains('normal-state')) {
                banner.className = 'alert-banner normal-state';
                bannerTitle.textContent = 'HIGHWAY MONITORING — ALL SECTORS NORMAL';
                bannerSub.textContent = 'Real-time computer vision actively scanning for vehicular collisions and anomalous trajectories.';
            }
            if (hudStatus && hudStatus.classList.contains('alert')) {
                hudStatus.className = 'hud-status-badge';
                hudStatus.textContent = 'STATUS: NORMAL';
            }
        }
    } catch (err) {
        console.error('Error fetching telemetry:', err);
    }
}

// Fetch Incidents History Table
async function fetchIncidents() {
    try {
        const res = await fetch('/api/incidents');
        if (!res.ok) return;
        const incidents = await res.json();
        const tbody = document.getElementById('incidents-table-body');
        if (!tbody) return;

        if (incidents.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="9" class="empty-state">
                        No collisions recorded in current surveillance session.
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = incidents.map(inc => {
            const sevClass = inc.severity === 'Critical' ? 'pill-critical' : inc.severity === 'Moderate' ? 'pill-moderate' : 'pill-minor';
            const timeStr = inc.timestamp ? new Date(inc.timestamp).toLocaleTimeString() : 'Just now';

            return `
                <tr>
                    <td style="font-family: var(--font-mono); font-weight: bold; color: var(--accent-cyan);">${inc.incident_id}</td>
                    <td>${timeStr}</td>
                    <td>${inc.location_name}</td>
                    <td><span class="severity-pill ${sevClass}">${inc.severity.toUpperCase()}</span></td>
                    <td><span style="font-family: var(--font-mono);">${inc.vehicle_ids || '01, 02'}</span></td>
                    <td style="color: var(--accent-emerald); font-weight: bold;">${inc.ai_confidence}%</td>
                    <td><span class="badge-emerald">${inc.hospital_alert_status}</span></td>
                    <td><span class="badge-emerald">${inc.nhai_alert_status}</span></td>
                    <td>
                        <div style="display: flex; gap: 6px;">
                            ${inc.screenshot_path ? `
                                <button class="btn btn-secondary btn-sm" onclick="previewScreenshot('${inc.incident_id}', '${inc.screenshot_path}')">
                                    📷 View Frame
                                </button>
                            ` : ''}
                            ${inc.pdf_path ? `
                                <a href="/api/reports/${inc.incident_id}/pdf" target="_blank" class="btn btn-primary btn-sm">
                                    📄 PDF
                                </a>
                            ` : ''}
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
    } catch (err) {
        console.error('Error fetching incidents list:', err);
    }
}

// Emergency Modal
function showEmergencyModal(inc) {
    const modal = document.getElementById('emergency-modal');
    if (!modal) return;

    document.getElementById('modal-incident-id').textContent = inc.incident_id;
    const sevBadge = document.getElementById('modal-severity-badge');
    sevBadge.textContent = inc.severity.toUpperCase();
    sevBadge.className = `severity-pill ${inc.severity === 'Critical' ? 'pill-critical' : inc.severity === 'Moderate' ? 'pill-moderate' : 'pill-minor'}`;

    document.getElementById('modal-location').textContent = inc.location_name || 'Kanpur NH-27 Corridor';
    document.getElementById('modal-vehicles').textContent = inc.vehicle_ids || '01, 02';
    document.getElementById('modal-confidence').textContent = `${inc.ai_confidence}%`;
    document.getElementById('modal-hospital').textContent = inc.hospital_name || 'LLR Level-1 Trauma Hospital';
    document.getElementById('modal-hospital-alert').textContent = `${inc.hospital_alert_status || 'SENT ✓'}`;
    document.getElementById('modal-nhai-alert').textContent = `${inc.nhai_alert_status || 'SENT ✓'}`;

    const shotImg = document.getElementById('modal-screenshot-img');
    if (shotImg) {
        shotImg.src = `/api/screenshots/${inc.incident_id}?t=${Date.now()}`;
    }

    const pdfBtn = document.getElementById('modal-pdf-link');
    if (pdfBtn) {
        pdfBtn.href = `/api/reports/${inc.incident_id}/pdf`;
    }

    const mapsBtn = document.getElementById('modal-maps-link');
    if (mapsBtn) {
        mapsBtn.href = `https://www.google.com/maps/search/?api=1&query=${inc.latitude || 26.4499},${inc.longitude || 80.3319}`;
    }

    modal.classList.remove('hidden');
}

function closeEmergencyModal() {
    const modal = document.getElementById('emergency-modal');
    if (modal) modal.classList.add('hidden');
}

// Screenshot Preview Modal
function previewScreenshot(incidentId, path) {
    const modal = document.getElementById('screenshot-modal');
    const title = document.getElementById('preview-modal-title');
    const img = document.getElementById('preview-modal-img');
    if (!modal) return;

    title.textContent = `Collision Evidence Frame — ${incidentId}`;
    img.src = `/api/screenshots/${incidentId}?t=${Date.now()}`;
    modal.classList.remove('hidden');
}

function closeScreenshotModal() {
    const modal = document.getElementById('screenshot-modal');
    if (modal) modal.classList.add('hidden');
}

// Simulation & Control Actions
async function triggerSimulatedCollision() {
    try {
        const res = await fetch('/api/simulate-collision', { method: 'POST' });
        const data = await res.json();
        console.log('Simulated collision triggered:', data);
        setTimeout(pollTelemetry, 300);
        setTimeout(fetchIncidents, 1000);
    } catch (e) {
        console.error('Error triggering simulation:', e);
    }
}

async function toggleSyntheticCamera() {
    try {
        const res = await fetch('/api/toggle-camera', { method: 'POST' });
        const data = await res.json();
        console.log('Camera mode toggled:', data);
        pollTelemetry();
    } catch (e) {
        console.error('Error toggling camera mode:', e);
    }
}

async function resetAlertState() {
    try {
        await fetch('/api/reset-alert', { method: 'POST' });
        closeEmergencyModal();
        pollTelemetry();
    } catch (e) {
        console.error('Error resetting alert state:', e);
    }
}

// ==========================================
// RAKSHA AI — Browser Live Camera Controller
// ==========================================

const CAMERA_CONFIG = {
    width: 640,
    height: 360,
    targetFps: 10,
    jpegQuality: 0.65
};

let isLiveWebcamActive = false;
let webcamMediaStream = null;
let webcamWs = null;
let isAwaitingFrameResponse = false;
let streamIntervalId = null;
let lastFrameSendTime = 0;

function updateCameraStatus(message, type = 'info') {
    const statusBox = document.getElementById('camera-status-msg');
    if (!statusBox) return;

    statusBox.textContent = message;
    if (type === 'error') {
        statusBox.style.color = '#ff6b6b';
    } else if (type === 'success') {
        statusBox.style.color = '#00ff88';
    } else {
        statusBox.style.color = '#cbd5e1';
    }
}

// Display annotated frame from AI pipeline onto the video panel
function displayAnnotatedFrame(blob) {
    const streamImg = document.getElementById('live-stream-img');
    const video = document.getElementById('client-webcam-video');
    if (!streamImg) return;

    const imgUrl = URL.createObjectURL(blob);
    streamImg.src = imgUrl;
    streamImg.style.display = 'block';

    // Auto-cleanup blob URL to avoid memory leak
    setTimeout(() => {
        try { URL.revokeObjectURL(imgUrl); } catch(e) {}
    }, 800);
}

// Start User Webcam on Button Click
async function startLiveCamera() {
    const btnStart = document.getElementById('btn-start-camera');
    const btnStop = document.getElementById('btn-stop-camera');
    const sourceTag = document.getElementById('cam-feed-source');
    const video = document.getElementById('client-webcam-video');
    const streamImg = document.getElementById('live-stream-img');

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        updateCameraStatus("Webcam API not supported in this browser. Please use Chrome or Edge.", "error");
        return;
    }

    if (btnStart) {
        btnStart.disabled = true;
        btnStart.textContent = '⏳ STARTING CAMERA...';
    }
    updateCameraStatus("Requesting camera permission from browser...", "info");

    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            video: {
                width: { ideal: CAMERA_CONFIG.width },
                height: { ideal: CAMERA_CONFIG.height },
                facingMode: "user"
            },
            audio: false
        });

        webcamMediaStream = stream;
        video.srcObject = stream;
        await video.play();

        isLiveWebcamActive = true;

        if (btnStart) {
            btnStart.textContent = '📹 CAMERA ACTIVE';
            btnStart.disabled = true;
            btnStart.style.opacity = '0.6';
        }
        if (btnStop) {
            btnStop.disabled = false;
            btnStop.style.opacity = '1.0';
            btnStop.style.background = 'linear-gradient(135deg, #ff416c 0%, #ff4b2b 100%)';
            btnStop.style.color = '#fff';
            btnStop.style.boxShadow = '0 0 15px rgba(255, 65, 108, 0.4)';
        }
        if (sourceTag) {
            sourceTag.textContent = 'BROWSER WEBCAM';
        }

        // Show local video immediately
        video.style.display = 'block';

        updateCameraStatus("🟢 Camera active! Streaming to YOLOv8 & ByteTrack for object tracking & collision detection.", "success");

        // Initialize WebSocket and frame capture loop
        initWebcamWebSocket();
        startFrameCaptureLoop();

    } catch (err) {
        console.warn('Camera startup failed:', err);
        isLiveWebcamActive = false;

        if (btnStart) {
            btnStart.textContent = '📹 START CAMERA';
            btnStart.disabled = false;
            btnStart.style.opacity = '1.0';
        }

        updateCameraStatus(`Camera error: ${err.message}. Please check browser camera permissions.`, "error");
    }
}

// Stop User Webcam
function stopLiveCamera() {
    isLiveWebcamActive = false;
    isAwaitingFrameResponse = false;

    if (streamIntervalId) {
        clearInterval(streamIntervalId);
        streamIntervalId = null;
    }

    if (webcamMediaStream) {
        webcamMediaStream.getTracks().forEach(track => track.stop());
        webcamMediaStream = null;
    }

    if (webcamWs) {
        try { webcamWs.close(); } catch(e) {}
        webcamWs = null;
    }

    const btnStart = document.getElementById('btn-start-camera');
    const btnStop = document.getElementById('btn-stop-camera');
    const sourceTag = document.getElementById('cam-feed-source');
    const video = document.getElementById('client-webcam-video');
    const streamImg = document.getElementById('live-stream-img');

    if (btnStart) {
        btnStart.textContent = '📹 START CAMERA';
        btnStart.disabled = false;
        btnStart.style.opacity = '1.0';
    }
    if (btnStop) {
        btnStop.disabled = true;
        btnStop.style.opacity = '0.5';
        btnStop.style.background = '';
        btnStop.style.color = '';
        btnStop.style.boxShadow = '';
    }
    if (sourceTag) {
        sourceTag.textContent = 'SIMULATION';
    }
    if (video) {
        video.style.display = 'none';
    }
    if (streamImg) {
        streamImg.style.display = 'block';
        streamImg.src = `/api/stream?t=${Date.now()}`;
    }

    updateCameraStatus("Camera stopped. Switched back to simulation stream.", "info");
}

// Switch to Simulation Highway Traffic Feed
async function useSimulationFeed() {
    if (isLiveWebcamActive) {
        stopLiveCamera();
    }
    try {
        await fetch('/api/toggle-camera', { method: 'POST' });
        const streamImg = document.getElementById('live-stream-img');
        const sourceTag = document.getElementById('cam-feed-source');
        if (streamImg) {
            streamImg.src = `/api/stream?t=${Date.now()}`;
            streamImg.style.display = 'block';
        }
        if (sourceTag) {
            sourceTag.textContent = 'SIMULATION';
        }
        updateCameraStatus("Switched to simulated highway traffic feed.", "info");
        pollTelemetry();
    } catch (e) {
        console.error('Error switching to simulation feed:', e);
    }
}

// Initialize WebSocket with automatic reconnection
function initWebcamWebSocket() {
    if (webcamWs) {
        try { webcamWs.close(); } catch(e) {}
    }

    const loc = window.location;
    const wsProto = loc.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProto}//${loc.host}/ws/live-stream`;

    try {
        webcamWs = new WebSocket(wsUrl);
        webcamWs.binaryType = 'arraybuffer';

        webcamWs.onopen = () => {
            console.log('Live camera WebSocket connected.');
            isAwaitingFrameResponse = false;
        };

        webcamWs.onmessage = (event) => {
            isAwaitingFrameResponse = false;
            const blob = new Blob([event.data], { type: 'image/jpeg' });
            displayAnnotatedFrame(blob);
        };

        webcamWs.onerror = (err) => {
            console.warn('Webcam WebSocket error; will use HTTP fallback:', err);
        };

        webcamWs.onclose = () => {
            console.log('Webcam WebSocket closed.');
            if (isLiveWebcamActive) {
                setTimeout(() => {
                    if (isLiveWebcamActive && (!webcamWs || webcamWs.readyState === WebSocket.CLOSED)) {
                        initWebcamWebSocket();
                    }
                }, 3000);
            }
        };
    } catch (wsErr) {
        console.warn('Could not initialize WebSocket:', wsErr);
    }
}

// Capture and Send Frames (Dual Transport: WebSocket + HTTP POST fallback)
function startFrameCaptureLoop() {
    if (streamIntervalId) clearInterval(streamIntervalId);

    const video = document.getElementById('client-webcam-video');
    const canvas = document.getElementById('client-webcam-canvas');
    if (!video || !canvas) return;
    const ctx = canvas.getContext('2d');

    const intervalMs = Math.round(1000 / CAMERA_CONFIG.targetFps);

    streamIntervalId = setInterval(() => {
        if (!isLiveWebcamActive) return;

        // Safety timeout: unlock if waiting longer than 1500ms
        if (isAwaitingFrameResponse && Date.now() - lastFrameSendTime > 1500) {
            isAwaitingFrameResponse = false;
        }
        if (isAwaitingFrameResponse) return;
        if (!video.videoWidth || !video.videoHeight) return;

        canvas.width = CAMERA_CONFIG.width;
        canvas.height = CAMERA_CONFIG.height;
        ctx.drawImage(video, 0, 0, CAMERA_CONFIG.width, CAMERA_CONFIG.height);

        isAwaitingFrameResponse = true;
        lastFrameSendTime = Date.now();

        canvas.toBlob((blob) => {
            if (!blob || !isLiveWebcamActive) {
                isAwaitingFrameResponse = false;
                return;
            }

            // PRIMARY: Send via WebSocket if open
            if (webcamWs && webcamWs.readyState === WebSocket.OPEN) {
                blob.arrayBuffer().then(buffer => {
                    if (webcamWs && webcamWs.readyState === WebSocket.OPEN) {
                        webcamWs.send(buffer);
                    } else {
                        // WS closed mid-send, fallback to HTTP
                        sendFrameViaHttp(blob);
                    }
                }).catch(() => {
                    sendFrameViaHttp(blob);
                });
            } else {
                // FALLBACK: Send via HTTP POST
                sendFrameViaHttp(blob);
            }
        }, 'image/jpeg', CAMERA_CONFIG.jpegQuality);
    }, intervalMs);
}

// HTTP Fallback frame sender
async function sendFrameViaHttp(blob) {
    try {
        const response = await fetch('/api/detect-frame', {
            method: 'POST',
            body: blob,
            headers: { 'Content-Type': 'image/jpeg' }
        });
        if (response.ok) {
            const resultBlob = await response.blob();
            displayAnnotatedFrame(resultBlob);
        }
    } catch (e) {
        console.debug('HTTP frame send error:', e);
    } finally {
        isAwaitingFrameResponse = false;
    }
}

// Initialize Polling on Page Load
window.addEventListener('DOMContentLoaded', () => {
    fetchIncidents();
    setInterval(pollTelemetry, 800);
});
