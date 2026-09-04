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

// Live Webcam Streaming State
// ==========================================
// RAKSHA AI — Browser Live Camera Controller
// ==========================================

// Configurable Camera Parameters
const CAMERA_CONFIG = {
    width: 640,
    height: 360,
    targetFps: 12,
    jpegQuality: 0.65
};

let isLiveWebcamActive = false;
let webcamMediaStream = null;
let webcamWs = null;
let isAwaitingFrameResponse = false;
let streamIntervalId = null;

function updateCameraStatus(message, type = 'info') {
    const statusBox = document.getElementById('camera-status-msg');
    if (!statusBox) return;

    statusBox.textContent = message;
    if (type === 'error') {
        statusBox.style.background = 'rgba(255, 65, 108, 0.12)';
        statusBox.style.border = '1px solid rgba(255, 65, 108, 0.4)';
        statusBox.style.color = '#ff6b6b';
    } else if (type === 'success') {
        statusBox.style.background = 'rgba(0, 255, 136, 0.12)';
        statusBox.style.border = '1px solid rgba(0, 255, 136, 0.4)';
        statusBox.style.color = '#00ff88';
    } else {
        statusBox.style.background = 'rgba(0, 242, 254, 0.08)';
        statusBox.style.border = '1px solid rgba(0, 242, 254, 0.25)';
        statusBox.style.color = '#cbd5e1';
    }
}

// ==========================================
// RAKSHA AI — Autonomous Live Camera Controller
// ==========================================

const CAMERA_CONFIG = {
    width: 640,
    height: 360,
    targetFps: 12,
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

// Automatic Camera Startup — Starts immediately on page load without any manual button click
async function autoStartCamera() {
    const video = document.getElementById('client-webcam-video');
    const streamImg = document.getElementById('live-stream-img');
    const sourceTag = document.getElementById('cam-feed-source');

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        updateCameraStatus("Webcam API not supported by browser. Showing highway simulation feed.", "info");
        if (streamImg) streamImg.style.display = 'block';
        return;
    }

    updateCameraStatus("Connecting to camera...", "info");

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

        // Show live camera immediately on screen (NO black screen)
        video.style.display = 'block';
        if (streamImg) streamImg.style.display = 'none';

        if (sourceTag) {
            sourceTag.textContent = 'AUTOMATIC LIVE WEBCAM';
        }

        updateCameraStatus("🟢 AUTONOMOUS SURVEILLANCE ACTIVE: Camera online, scanning for vehicles & collisions.", "success");
        initWebcamWebSocket();

    } catch (err) {
        console.warn('Camera startup:', err);
        isLiveWebcamActive = false;

        // If browser requires user interaction first to allow camera
        if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
            updateCameraStatus("🔒 Camera permission needed: Click anywhere on video to activate camera.", "info");
            const wrapper = document.querySelector('.video-wrapper');
            if (wrapper) {
                wrapper.style.cursor = 'pointer';
                wrapper.onclick = () => {
                    wrapper.onclick = null;
                    wrapper.style.cursor = 'default';
                    autoStartCamera();
                };
            }
        } else {
            updateCameraStatus(`Camera: ${err.message}. Monitoring active.`, "info");
        }

        if (streamImg) streamImg.style.display = 'block';
    }
}

function initWebcamWebSocket() {
    if (webcamWs) {
        try { webcamWs.close(); } catch(e) {}
    }

    const loc = window.location;
    const wsProto = loc.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProto}//${loc.host}/ws/live-stream`;

    webcamWs = new WebSocket(wsUrl);
    webcamWs.binaryType = 'arraybuffer';

    webcamWs.onopen = () => {
        console.log('Autonomous WebSocket connected to RAKSHA AI.');
        isAwaitingFrameResponse = false;
        startFrameCaptureLoop();
    };

    webcamWs.onmessage = (event) => {
        isAwaitingFrameResponse = false;
        const blob = new Blob([event.data], { type: 'image/jpeg' });
        const imgUrl = URL.createObjectURL(blob);
        const streamImg = document.getElementById('live-stream-img');
        const video = document.getElementById('client-webcam-video');

        if (streamImg && isLiveWebcamActive) {
            streamImg.src = imgUrl;
            streamImg.style.display = 'block';
            if (video) video.style.display = 'none';
            setTimeout(() => URL.revokeObjectURL(imgUrl), 800);
        }
    };

    webcamWs.onerror = (err) => {
        console.warn('Webcam WebSocket error:', err);
    };

    webcamWs.onclose = () => {
        console.log('Webcam WebSocket disconnected.');
        if (isLiveWebcamActive) {
            // Keep local video visible even if WebSocket reconnects
            const video = document.getElementById('client-webcam-video');
            const streamImg = document.getElementById('live-stream-img');
            if (video) video.style.display = 'block';
            if (streamImg) streamImg.style.display = 'none';

            setTimeout(() => {
                if (isLiveWebcamActive) initWebcamWebSocket();
            }, 2000);
        }
    };
}

function startFrameCaptureLoop() {
    if (streamIntervalId) clearInterval(streamIntervalId);

    const video = document.getElementById('client-webcam-video');
    const canvas = document.getElementById('client-webcam-canvas');
    if (!video || !canvas) return;
    const ctx = canvas.getContext('2d');

    const intervalMs = Math.round(1000 / CAMERA_CONFIG.targetFps);

    streamIntervalId = setInterval(() => {
        if (!isLiveWebcamActive || !webcamWs || webcamWs.readyState !== WebSocket.OPEN) return;

        // Safety timeout: if server response is delayed more than 1200ms, unlock
        if (isAwaitingFrameResponse && Date.now() - lastFrameSendTime > 1200) {
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
            if (blob && webcamWs && webcamWs.readyState === WebSocket.OPEN) {
                blob.arrayBuffer().then(buffer => {
                    if (webcamWs && webcamWs.readyState === WebSocket.OPEN) {
                        webcamWs.send(buffer);
                    } else {
                        isAwaitingFrameResponse = false;
                    }
                }).catch(() => { isAwaitingFrameResponse = false; });
            } else {
                isAwaitingFrameResponse = false;
            }
        }, 'image/jpeg', CAMERA_CONFIG.jpegQuality);
    }, intervalMs);
}

// Initialize Polling & Autonomous Camera on Page Load
window.addEventListener('DOMContentLoaded', () => {
    fetchIncidents();
    setInterval(pollTelemetry, 800);

    // Automatically trigger live camera and AI monitoring without requiring any button clicks!
    autoStartCamera();
});
