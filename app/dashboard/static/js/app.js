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
        if (fpsEl) fpsEl.textContent = data.fps || '0.0';
        if (vehEl) vehEl.textContent = data.active_vehicles || '0';
        if (camEl) camEl.textContent = data.is_synthetic ? 'SIMULATION' : 'ONLINE';

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
let isLiveWebcamActive = false;
let webcamMediaStream = null;
let webcamWs = null;
let isAwaitingFrameResponse = false;
let streamIntervalId = null;

async function toggleLiveWebcam() {
    if (isLiveWebcamActive) {
        stopLiveWebcam();
    } else {
        await startLiveWebcam();
    }
}

async function startLiveWebcam() {
    const btn = document.getElementById('btn-webcam-toggle');
    const note = document.getElementById('webcam-status-note');
    const sourceTag = document.getElementById('cam-feed-source');
    const video = document.getElementById('client-webcam-video');
    const canvas = document.getElementById('client-webcam-canvas');

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        alert("Camera access is not supported by your browser. Please use Chrome, Edge, or Firefox over HTTPS.");
        return;
    }

    if (btn) btn.textContent = '⏳ Requesting Camera...';

    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            video: {
                width: { ideal: 640 },
                height: { ideal: 480 }
            },
            audio: false
        });

        webcamMediaStream = stream;
        video.srcObject = stream;
        await video.play();

        isLiveWebcamActive = true;
        if (btn) {
            btn.textContent = '🛑 Stop Live Camera';
            btn.style.background = 'linear-gradient(135deg, #ff416c 0%, #ff4b2b 100%)';
            btn.style.color = '#fff';
            btn.style.boxShadow = '0 0 15px rgba(255, 65, 108, 0.5)';
        }
        if (sourceTag) {
            sourceTag.textContent = 'FEED: LIVE WEBCAM (ACTIVE)';
            sourceTag.style.background = 'rgba(0, 255, 136, 0.2)';
            sourceTag.style.color = '#00ff88';
            sourceTag.style.borderColor = 'rgba(0, 255, 136, 0.6)';
        }
        if (note) {
            note.innerHTML = '<em>🟢 <strong>LIVE WEBCAM CONNECTED:</strong> YOLOv8 is actively tracking objects & vehicles in front of your camera!</em>';
        }

        initWebcamWebSocket();

    } catch (err) {
        console.error('Camera access error:', err);
        isLiveWebcamActive = false;
        if (btn) {
            btn.textContent = '📹 Start Live Device Camera';
            btn.style.background = 'linear-gradient(135deg, #00f2fe 0%, #4facfe 100%)';
            btn.style.color = '#000';
            btn.style.boxShadow = '0 0 15px rgba(0, 242, 254, 0.4)';
        }
        if (note) {
            note.innerHTML = `<em style="color:#ff6b6b">❌ Camera permission denied or camera not found: ${err.message}. Please allow camera access in browser settings.</em>`;
        }
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
        console.log('Live webcam WebSocket connected to server.');
        isAwaitingFrameResponse = false;
        startFrameCaptureLoop();
    };

    webcamWs.onmessage = (event) => {
        isAwaitingFrameResponse = false;
        const blob = new Blob([event.data], { type: 'image/jpeg' });
        const imgUrl = URL.createObjectURL(blob);
        const streamImg = document.getElementById('live-stream-img');
        if (streamImg && isLiveWebcamActive) {
            streamImg.src = imgUrl;
            setTimeout(() => URL.revokeObjectURL(imgUrl), 1000);
        }
    };

    webcamWs.onerror = (err) => {
        console.warn('Webcam WebSocket error:', err);
    };

    webcamWs.onclose = () => {
        console.log('Webcam WebSocket connection closed.');
        if (isLiveWebcamActive) {
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

    streamIntervalId = setInterval(() => {
        if (!isLiveWebcamActive || !webcamWs || webcamWs.readyState !== WebSocket.OPEN) return;
        if (isAwaitingFrameResponse) return;
        if (video.videoWidth === 0 || video.videoHeight === 0) return;

        canvas.width = 640;
        canvas.height = 480;
        ctx.drawImage(video, 0, 0, 640, 480);

        isAwaitingFrameResponse = true;
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
        }, 'image/jpeg', 0.65);
    }, 66); // ~15 FPS
}

function stopLiveWebcam() {
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

    const btn = document.getElementById('btn-webcam-toggle');
    const note = document.getElementById('webcam-status-note');
    const sourceTag = document.getElementById('cam-feed-source');
    const streamImg = document.getElementById('live-stream-img');

    if (btn) {
        btn.textContent = '📹 Start Live Device Camera';
        btn.style.background = 'linear-gradient(135deg, #00f2fe 0%, #4facfe 100%)';
        btn.style.color = '#000';
        btn.style.boxShadow = '0 0 15px rgba(0, 242, 254, 0.4)';
    }
    if (sourceTag) {
        sourceTag.textContent = 'FEED: SIMULATION';
        sourceTag.style.background = 'rgba(0,242,254,0.15)';
        sourceTag.style.color = '#00f2fe';
        sourceTag.style.borderColor = 'rgba(0,242,254,0.4)';
    }
    if (note) {
        note.innerHTML = '<em>💡 Click <strong>"Start Live Device Camera"</strong> to activate your laptop/mobile webcam for real-time live YOLO detection!</em>';
    }

    if (streamImg) {
        streamImg.src = `/api/stream?t=${Date.now()}`;
    }
}

async function useSimulationFeed() {
    if (isLiveWebcamActive) {
        stopLiveWebcam();
    }
    try {
        await fetch('/api/toggle-camera', { method: 'POST' });
        const streamImg = document.getElementById('live-stream-img');
        if (streamImg) {
            streamImg.src = `/api/stream?t=${Date.now()}`;
        }
        pollTelemetry();
    } catch (e) {
        console.error('Error switching to simulation feed:', e);
    }
}

// Initialize Polling
window.addEventListener('DOMContentLoaded', () => {
    fetchIncidents();
    setInterval(pollTelemetry, 800);
});
