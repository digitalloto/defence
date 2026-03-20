/* ================================================================
   AIMCRS SIMULATION ENGINE
   Interactive Traffic & Green Corridor Simulator
   Patent Pending: IN202541120892
   ================================================================ */

// ── Vehicle Class Definitions ─────────────────────────────
const VEHICLE_CLASSES = [
    { id: 0, name: 'Car',           color: '#3498db', w: 30, h: 18, speed: 2.5 },
    { id: 1, name: 'Motorcycle',    color: '#e67e22', w: 14, h: 24, speed: 3.5 },
    { id: 2, name: 'Auto Rickshaw', color: '#f1c40f', w: 20, h: 16, speed: 2.0 },
    { id: 3, name: 'Bus',           color: '#27ae60', w: 50, h: 20, speed: 1.8 },
    { id: 4, name: 'Truck',         color: '#8e44ad', w: 45, h: 22, speed: 1.5 },
    { id: 5, name: 'Ambulance',     color: '#e74c3c', w: 35, h: 18, speed: 4.0 },
    { id: 6, name: 'Pedestrian',    color: '#1abc9c', w: 8,  h: 8,  speed: 0.8 },
    { id: 7, name: 'Cycle',         color: '#95a5a6', w: 10, h: 18, speed: 1.5 },
    { id: 8, name: 'Animal',        color: '#d35400', w: 16, h: 12, speed: 0.6 },
];

// ── Simulation State ──────────────────────────────────────
const SIM = {
    canvas: null,
    ctx: null,
    width: 0,
    height: 0,
    vehicles: [],
    signals: [],
    frame: 0,
    paused: false,
    speed: 1,
    density: 25,
    nightMode: false,
    showDetection: true,
    showCorridor: true,
    showLabels: true,
    corridorActive: false,
    corridorPhase: 'inactive', // inactive, detected, clearing, active, restoring
    corridorDirection: null,
    ambulanceInScene: false,
    selectedVehicleType: null,
    scenario: 'normal',
    spawnTimer: 0,
    // Intersection geometry
    roadWidth: 80,
    centerX: 0,
    centerY: 0,
    // Multi-intersection
    intersections: [],
    multiMode: false,
};

// ── Road & Intersection ───────────────────────────────────
const DIRECTIONS = ['north', 'south', 'east', 'west'];

class TrafficSignal {
    constructor(x, y, direction) {
        this.x = x;
        this.y = y;
        this.direction = direction;
        this.state = direction === 'north' || direction === 'south' ? 'green' : 'red';
        this.timer = 0;
        this.greenDuration = 180; // frames (~6s at 30fps)
        this.yellowDuration = 30;
        this.overridden = false;
    }

    update() {
        if (this.overridden) return;
        this.timer++;
        if (this.state === 'green' && this.timer >= this.greenDuration) {
            this.state = 'yellow';
            this.timer = 0;
        } else if (this.state === 'yellow' && this.timer >= this.yellowDuration) {
            this.state = 'red';
            this.timer = 0;
        } else if (this.state === 'red' && this.timer >= this.greenDuration + this.yellowDuration) {
            this.state = 'green';
            this.timer = 0;
        }
    }

    override(state) {
        this.overridden = true;
        this.state = state;
    }

    release() {
        this.overridden = false;
        this.timer = 0;
    }
}

// ── Vehicle ───────────────────────────────────────────────
class Vehicle {
    constructor(classId, x, y, direction, lane) {
        const cls = VEHICLE_CLASSES[classId];
        this.classId = classId;
        this.className = cls.name;
        this.color = cls.color;
        this.baseWidth = cls.w;
        this.baseHeight = cls.h;
        this.maxSpeed = cls.speed;
        this.x = x;
        this.y = y;
        this.direction = direction;
        this.lane = lane || 0;
        this.speed = cls.speed * (0.7 + Math.random() * 0.6);
        this.stopped = false;
        this.yielding = false;
        this.confidence = 0.85 + Math.random() * 0.14;
        this.trackId = Math.floor(Math.random() * 9999);
        this.flashTimer = 0;

        // Adjust dimensions based on direction
        if (direction === 'east' || direction === 'west') {
            this.w = this.baseWidth;
            this.h = this.baseHeight;
        } else {
            this.w = this.baseHeight;
            this.h = this.baseWidth;
        }
    }

    update(signals) {
        this.flashTimer++;

        // Check if should stop at signal
        const signal = this.getRelevantSignal(signals);
        const shouldStop = signal && signal.state === 'red' && this.isApproachingIntersection();

        // Ambulance yielding
        if (this.yielding && this.classId !== 5) {
            this.speed = Math.max(0, this.speed - 0.1);
        } else if (shouldStop && this.classId !== 5) {
            this.speed = Math.max(0, this.speed - 0.15);
        } else {
            this.speed = Math.min(this.maxSpeed, this.speed + 0.05);
        }

        // Check for vehicle ahead
        const ahead = this.getVehicleAhead();
        if (ahead && ahead.dist < 30) {
            this.speed = Math.max(0, this.speed - 0.2);
        }

        // Move
        const dx = { north: 0, south: 0, east: 1, west: -1 }[this.direction];
        const dy = { north: -1, south: 1, east: 0, west: 0 }[this.direction];
        this.x += dx * this.speed * SIM.speed;
        this.y += dy * this.speed * SIM.speed;
    }

    getRelevantSignal(signals) {
        return signals.find(s => s.direction === this.direction);
    }

    isApproachingIntersection() {
        const cx = SIM.centerX;
        const cy = SIM.centerY;
        const rw = SIM.roadWidth;
        const margin = rw + 30;

        switch (this.direction) {
            case 'north': return this.y > cy + rw / 2 && this.y < cy + margin + 40;
            case 'south': return this.y < cy - rw / 2 && this.y > cy - margin - 40;
            case 'east':  return this.x < cx - rw / 2 && this.x > cx - margin - 40;
            case 'west':  return this.x > cx + rw / 2 && this.x < cx + margin + 40;
        }
        return false;
    }

    getVehicleAhead() {
        let closest = null;
        let minDist = Infinity;
        for (const v of SIM.vehicles) {
            if (v === this || v.direction !== this.direction) continue;
            let dist;
            switch (this.direction) {
                case 'north': dist = this.y - v.y; break;
                case 'south': dist = v.y - this.y; break;
                case 'east':  dist = v.x - this.x; break;
                case 'west':  dist = this.x - v.x; break;
            }
            if (dist > 0 && dist < minDist && Math.abs(
                (this.direction === 'north' || this.direction === 'south' ? this.x - v.x : this.y - v.y)
            ) < 25) {
                minDist = dist;
                closest = { vehicle: v, dist };
            }
        }
        return closest;
    }

    isOffScreen() {
        return this.x < -60 || this.x > SIM.width + 60 ||
               this.y < -60 || this.y > SIM.height + 60;
    }

    render(ctx) {
        ctx.save();
        ctx.translate(this.x, this.y);

        // Vehicle body
        ctx.fillStyle = this.color;
        if (this.classId === 5) {
            // Ambulance — special rendering
            ctx.fillStyle = (this.flashTimer % 20 < 10) ? '#e74c3c' : '#ffffff';
            ctx.fillRect(-this.w / 2, -this.h / 2, this.w, this.h);
            // Red cross
            ctx.fillStyle = '#e74c3c';
            ctx.fillRect(-2, -this.h / 2 + 2, 4, this.h - 4);
            ctx.fillRect(-this.w / 4, -2, this.w / 2, 4);
        } else if (this.classId === 6) {
            // Pedestrian — circle
            ctx.beginPath();
            ctx.arc(0, 0, this.w / 2, 0, Math.PI * 2);
            ctx.fill();
        } else if (this.classId === 8) {
            // Animal — rounded
            ctx.beginPath();
            ctx.ellipse(0, 0, this.w / 2, this.h / 2, 0, 0, Math.PI * 2);
            ctx.fill();
        } else {
            ctx.fillRect(-this.w / 2, -this.h / 2, this.w, this.h);
            // Windshield
            ctx.fillStyle = 'rgba(0,0,0,0.3)';
            if (this.direction === 'north') ctx.fillRect(-this.w / 2 + 2, -this.h / 2, this.w - 4, 4);
            else if (this.direction === 'south') ctx.fillRect(-this.w / 2 + 2, this.h / 2 - 4, this.w - 4, 4);
            else if (this.direction === 'east') ctx.fillRect(this.w / 2 - 4, -this.h / 2 + 2, 4, this.h - 4);
            else if (this.direction === 'west') ctx.fillRect(-this.w / 2, -this.h / 2 + 2, 4, this.h - 4);
        }

        ctx.restore();

        // Detection box overlay
        if (SIM.showDetection) {
            ctx.strokeStyle = this.classId === 5 ? '#ff0000' : 'rgba(78, 205, 196, 0.6)';
            ctx.lineWidth = this.classId === 5 ? 2 : 1;
            ctx.setLineDash(this.classId === 5 ? [] : [3, 3]);
            ctx.strokeRect(this.x - this.w / 2 - 4, this.y - this.h / 2 - 4, this.w + 8, this.h + 8);
            ctx.setLineDash([]);

            if (SIM.showLabels) {
                const label = `${this.className} ${(this.confidence * 100).toFixed(0)}%`;
                ctx.font = '9px Courier New';
                ctx.fillStyle = this.classId === 5 ? '#ff0000' : 'rgba(78, 205, 196, 0.8)';
                ctx.fillText(label, this.x - this.w / 2 - 4, this.y - this.h / 2 - 8);
            }
        }
    }
}

// ── Rendering ─────────────────────────────────────────────
function drawRoads(ctx) {
    const cx = SIM.centerX;
    const cy = SIM.centerY;
    const rw = SIM.roadWidth;
    const w = SIM.width;
    const h = SIM.height;

    // Background
    if (SIM.nightMode) {
        ctx.fillStyle = '#050510';
    } else {
        ctx.fillStyle = '#1a3a1a';
    }
    ctx.fillRect(0, 0, w, h);

    // Roads
    ctx.fillStyle = SIM.nightMode ? '#1a1a2a' : '#333';
    // Vertical road
    ctx.fillRect(cx - rw / 2, 0, rw, h);
    // Horizontal road
    ctx.fillRect(0, cy - rw / 2, w, rw);

    // Lane markings
    ctx.strokeStyle = SIM.nightMode ? '#444' : '#666';
    ctx.lineWidth = 1;
    ctx.setLineDash([10, 10]);

    // Vertical center line
    ctx.beginPath();
    ctx.moveTo(cx, 0);
    ctx.lineTo(cx, cy - rw / 2);
    ctx.moveTo(cx, cy + rw / 2);
    ctx.lineTo(cx, h);
    ctx.stroke();

    // Horizontal center line
    ctx.beginPath();
    ctx.moveTo(0, cy);
    ctx.lineTo(cx - rw / 2, cy);
    ctx.moveTo(cx + rw / 2, cy);
    ctx.lineTo(w, cy);
    ctx.stroke();
    ctx.setLineDash([]);

    // Stop lines
    ctx.strokeStyle = '#fff';
    ctx.lineWidth = 2;
    // North approach
    ctx.beginPath(); ctx.moveTo(cx - rw / 2, cy + rw / 2 + 5); ctx.lineTo(cx, cy + rw / 2 + 5); ctx.stroke();
    // South approach
    ctx.beginPath(); ctx.moveTo(cx, cy - rw / 2 - 5); ctx.lineTo(cx + rw / 2, cy - rw / 2 - 5); ctx.stroke();
    // East approach
    ctx.beginPath(); ctx.moveTo(cx - rw / 2 - 5, cy); ctx.lineTo(cx - rw / 2 - 5, cy + rw / 2); ctx.stroke();
    // West approach
    ctx.beginPath(); ctx.moveTo(cx + rw / 2 + 5, cy - rw / 2); ctx.lineTo(cx + rw / 2 + 5, cy); ctx.stroke();

    // Green corridor highlight
    if (SIM.corridorActive && SIM.showCorridor && SIM.corridorDirection) {
        ctx.fillStyle = `rgba(46, 204, 113, ${0.15 + 0.1 * Math.sin(SIM.frame * 0.05)})`;
        const dir = SIM.corridorDirection;
        if (dir === 'north' || dir === 'south') {
            ctx.fillRect(cx - rw / 2, 0, rw, h);
        } else {
            ctx.fillRect(0, cy - rw / 2, w, rw);
        }
    }

    // Intersection box
    ctx.fillStyle = SIM.nightMode ? '#222' : '#444';
    ctx.fillRect(cx - rw / 2, cy - rw / 2, rw, rw);

    // Zebra crossing marks
    ctx.fillStyle = 'rgba(255,255,255,0.3)';
    for (let i = 0; i < 6; i++) {
        ctx.fillRect(cx - rw / 2 + i * (rw / 6), cy + rw / 2 + 8, rw / 12, 6);
        ctx.fillRect(cx - rw / 2 + i * (rw / 6), cy - rw / 2 - 14, rw / 12, 6);
        ctx.fillRect(cx + rw / 2 + 8, cy - rw / 2 + i * (rw / 6), 6, rw / 12);
        ctx.fillRect(cx - rw / 2 - 14, cy - rw / 2 + i * (rw / 6), 6, rw / 12);
    }
}

function drawSignals(ctx) {
    const cx = SIM.centerX;
    const cy = SIM.centerY;
    const rw = SIM.roadWidth;

    const positions = {
        north: { x: cx - rw / 2 - 18, y: cy + rw / 2 + 18 },
        south: { x: cx + rw / 2 + 18, y: cy - rw / 2 - 18 },
        east:  { x: cx - rw / 2 - 18, y: cy - rw / 2 - 18 },
        west:  { x: cx + rw / 2 + 18, y: cy + rw / 2 + 18 },
    };

    for (const signal of SIM.signals) {
        const pos = positions[signal.direction];
        if (!pos) continue;

        // Signal housing
        ctx.fillStyle = '#111';
        ctx.fillRect(pos.x - 8, pos.y - 14, 16, 28);
        ctx.strokeStyle = '#555';
        ctx.lineWidth = 1;
        ctx.strokeRect(pos.x - 8, pos.y - 14, 16, 28);

        // Lights
        const colors = { red: '#e74c3c', yellow: '#f39c12', green: '#2ecc71' };
        ['red', 'yellow', 'green'].forEach((light, i) => {
            ctx.beginPath();
            ctx.arc(pos.x, pos.y - 8 + i * 8, 3, 0, Math.PI * 2);
            ctx.fillStyle = signal.state === light ? colors[light] : '#333';
            ctx.fill();
            if (signal.state === light) {
                ctx.shadowColor = colors[light];
                ctx.shadowBlur = 8;
                ctx.fill();
                ctx.shadowBlur = 0;
            }
        });
    }
}

function drawNightOverlay(ctx) {
    if (!SIM.nightMode) return;
    // Darken non-road areas more
    ctx.fillStyle = 'rgba(0, 0, 0, 0.3)';
    ctx.fillRect(0, 0, SIM.width, SIM.height);

    // Vehicle headlights
    for (const v of SIM.vehicles) {
        const grad = ctx.createRadialGradient(v.x, v.y, 2, v.x, v.y, 40);
        grad.addColorStop(0, 'rgba(255, 255, 200, 0.15)');
        grad.addColorStop(1, 'rgba(255, 255, 200, 0)');
        ctx.fillStyle = grad;
        ctx.fillRect(v.x - 40, v.y - 40, 80, 80);
    }
}

function drawHUD(ctx) {
    // Top-left info
    ctx.font = '11px Courier New';
    ctx.fillStyle = 'rgba(78, 205, 196, 0.7)';
    ctx.fillText(`AIMCRS Sim | Frame: ${SIM.frame} | Vehicles: ${SIM.vehicles.length}`, 10, 20);
    if (SIM.paused) {
        ctx.font = '20px Courier New';
        ctx.fillStyle = 'rgba(255, 215, 0, 0.8)';
        ctx.fillText('PAUSED', SIM.width / 2 - 40, SIM.height / 2);
    }
}

// ── Spawning ──────────────────────────────────────────────
function spawnVehicle() {
    const cx = SIM.centerX;
    const cy = SIM.centerY;
    const rw = SIM.roadWidth;
    const dir = DIRECTIONS[Math.floor(Math.random() * 4)];

    // Pick random vehicle type (weighted — more cars and motorcycles)
    const weights = [25, 25, 10, 5, 5, 0, 5, 8, 2]; // No random ambulances
    const totalWeight = weights.reduce((a, b) => a + b);
    let r = Math.random() * totalWeight;
    let classId = 0;
    for (let i = 0; i < weights.length; i++) {
        r -= weights[i];
        if (r <= 0) { classId = i; break; }
    }

    // Lane offset
    const laneOffset = (Math.random() > 0.5 ? 1 : -1) * (rw / 4 * (0.3 + Math.random() * 0.4));
    let x, y;
    switch (dir) {
        case 'north':
            x = cx + rw / 4;
            y = SIM.height + 30;
            break;
        case 'south':
            x = cx - rw / 4;
            y = -30;
            break;
        case 'east':
            x = -30;
            y = cy + rw / 4;
            break;
        case 'west':
            x = SIM.width + 30;
            y = cy - rw / 4;
            break;
    }

    SIM.vehicles.push(new Vehicle(classId, x, y, dir, 0));
}

function injectAmbulance() {
    const cx = SIM.centerX;
    const cy = SIM.centerY;
    const rw = SIM.roadWidth;
    const dirs = ['north', 'south', 'east', 'west'];
    const dir = dirs[Math.floor(Math.random() * 4)];
    let x, y;
    switch (dir) {
        case 'north': x = cx + rw / 4; y = SIM.height + 30; break;
        case 'south': x = cx - rw / 4; y = -30; break;
        case 'east':  x = -30; y = cy + rw / 4; break;
        case 'west':  x = SIM.width + 30; y = cy - rw / 4; break;
    }
    const amb = new Vehicle(5, x, y, dir, 0);
    amb.speed = amb.maxSpeed;
    SIM.vehicles.push(amb);
    SIM.corridorDirection = dir;
    activateGreenCorridor(dir);
}

// ── Green Corridor Engine ─────────────────────────────────
function activateGreenCorridor(direction) {
    SIM.corridorActive = true;
    SIM.corridorPhase = 'detected';
    SIM.corridorDirection = direction;

    // Override signals
    for (const signal of SIM.signals) {
        if (signal.direction === direction) {
            signal.override('green');
        } else if (
            (direction === 'north' && signal.direction === 'south') ||
            (direction === 'south' && signal.direction === 'north') ||
            (direction === 'east' && signal.direction === 'west') ||
            (direction === 'west' && signal.direction === 'east')
        ) {
            signal.override('green');
        } else {
            signal.override('red');
        }
    }

    // Make other vehicles yield
    for (const v of SIM.vehicles) {
        if (v.classId !== 5 && v.direction !== direction) {
            v.yielding = true;
        }
    }

    // Show banner
    const banner = document.getElementById('corridorBanner');
    banner.classList.add('active');

    setTimeout(() => {
        SIM.corridorPhase = 'active';
        banner.classList.add('green');
        document.getElementById('corridorText').textContent =
            'GREEN CORRIDOR ACTIVE — VEHICLES CLEARING PATH';
    }, 2000);

    updateCorridorPanel();
}

function deactivateGreenCorridor() {
    SIM.corridorActive = false;
    SIM.corridorPhase = 'inactive';
    SIM.corridorDirection = null;

    for (const signal of SIM.signals) {
        signal.release();
    }
    for (const v of SIM.vehicles) {
        v.yielding = false;
    }

    const banner = document.getElementById('corridorBanner');
    banner.classList.remove('active', 'green');
    document.getElementById('corridorText').textContent =
        'AMBULANCE DETECTED \u2014 GREEN CORRIDOR ACTIVE';

    updateCorridorPanel();
}

function checkAmbulance() {
    const ambulances = SIM.vehicles.filter(v => v.classId === 5);
    SIM.ambulanceInScene = ambulances.length > 0;

    if (!SIM.ambulanceInScene && SIM.corridorActive) {
        deactivateGreenCorridor();
    }

    if (SIM.ambulanceInScene && !SIM.corridorActive) {
        const amb = ambulances[0];
        activateGreenCorridor(amb.direction);
    }
}

// ── Data Panel Updates ────────────────────────────────────
function updateDataPanel() {
    document.getElementById('dataFrame').textContent = SIM.frame;
    document.getElementById('dataTotalVehicles').textContent = SIM.vehicles.length;

    // Vehicle counts
    const counts = {};
    VEHICLE_CLASSES.forEach(c => counts[c.id] = 0);
    SIM.vehicles.forEach(v => counts[v.classId]++);

    const countsEl = document.getElementById('vehicleCounts');
    countsEl.innerHTML = VEHICLE_CLASSES.map(c => `
        <div class="veh-count-row">
            <span class="veh-count-dot" style="background:${c.color}"></span>
            <span class="veh-count-name">${c.name}</span>
            <span class="veh-count-num">${counts[c.id]}</span>
        </div>
    `).join('');

    // Congestion
    const numVehicles = SIM.vehicles.length;
    const avgSpeed = SIM.vehicles.length > 0
        ? SIM.vehicles.reduce((a, v) => a + v.speed, 0) / SIM.vehicles.length
        : 0;

    let level, pct;
    if (numVehicles <= 10 && avgSpeed > 1.5) { level = 'low'; pct = 15; }
    else if (numVehicles <= 25 && avgSpeed > 0.8) { level = 'medium'; pct = 40; }
    else if (numVehicles <= 40) { level = 'high'; pct = 70; }
    else { level = 'severe'; pct = 95; }

    const levelEl = document.getElementById('congestionLevel');
    levelEl.textContent = level.toUpperCase();
    levelEl.className = 'congestion-level ' + level;

    const fillEl = document.getElementById('congestionFill');
    fillEl.style.width = pct + '%';
    fillEl.style.background = { low: '#2ecc71', medium: '#f39c12', high: '#e67e22', severe: '#e74c3c' }[level];

    document.getElementById('dataAvgSpeed').textContent = avgSpeed.toFixed(1) + ' px/f';
}

function updateCorridorPanel() {
    document.getElementById('corridorPhase').textContent =
        SIM.corridorPhase.charAt(0).toUpperCase() + SIM.corridorPhase.slice(1);
    document.getElementById('corridorAmbulance').textContent =
        SIM.ambulanceInScene ? 'Detected' : 'None';
    document.getElementById('corridorSignals').textContent =
        SIM.signals.filter(s => s.overridden).length;

    // Color the status
    const phaseEl = document.getElementById('corridorPhase');
    phaseEl.style.color = SIM.corridorActive ? '#2ecc71' : '#888';
    document.getElementById('corridorAmbulance').style.color =
        SIM.ambulanceInScene ? '#e74c3c' : '#888';
}

// ── Scenarios ─────────────────────────────────────────────
function loadScenario(name) {
    SIM.scenario = name;
    SIM.vehicles = [];
    deactivateGreenCorridor();
    SIM.nightMode = name === 'night';
    SIM.multiMode = name === 'multi';

    // Update button states
    document.querySelectorAll('.ctrl-btn[id^="btn-"]').forEach(b => b.classList.remove('active'));
    const btn = document.getElementById('btn-' + name);
    if (btn) btn.classList.add('active');

    switch (name) {
        case 'normal':
            SIM.density = 25;
            break;
        case 'ambulance':
            SIM.density = 25;
            // Spawn some traffic first, then inject ambulance after 2s
            setTimeout(() => injectAmbulance(), 2000);
            break;
        case 'heavy':
            SIM.density = 60;
            break;
        case 'multi':
            SIM.density = 20;
            break;
        case 'night':
            SIM.density = 15;
            break;
    }

    document.getElementById('densitySlider').value = SIM.density;
    document.getElementById('densityValue').textContent = SIM.density;
}

// ── Controls ──────────────────────────────────────────────
function setDensity(val) {
    SIM.density = parseInt(val);
    document.getElementById('densityValue').textContent = val;
}

function setSpeed(val) {
    SIM.speed = val;
    document.querySelectorAll('.spd-btn').forEach(b => {
        b.classList.toggle('active', parseFloat(b.textContent) === val);
    });
}

function toggleDetection(on) { SIM.showDetection = on; }
function toggleCorridor(on) { SIM.showCorridor = on; }
function toggleLabels(on) { SIM.showLabels = on; }

function togglePause() {
    SIM.paused = !SIM.paused;
    document.getElementById('pauseText').textContent = SIM.paused ? 'Resume' : 'Pause';
}

function resetSim() {
    SIM.vehicles = [];
    SIM.frame = 0;
    deactivateGreenCorridor();
    loadScenario(SIM.scenario);
}

// ── Canvas Click (Vehicle Placement) ──────────────────────
function setupCanvasClick() {
    SIM.canvas.addEventListener('click', (e) => {
        if (SIM.selectedVehicleType === null) return;

        const rect = SIM.canvas.getBoundingClientRect();
        const scaleX = SIM.canvas.width / rect.width;
        const scaleY = SIM.canvas.height / rect.height;
        const x = (e.clientX - rect.left) * scaleX;
        const y = (e.clientY - rect.top) * scaleY;

        // Determine direction based on quadrant
        const cx = SIM.centerX;
        const cy = SIM.centerY;
        let dir;
        if (y > cy) dir = 'north';
        else if (y < cy) dir = 'south';
        else if (x < cx) dir = 'east';
        else dir = 'west';

        const v = new Vehicle(SIM.selectedVehicleType, x, y, dir, 0);
        SIM.vehicles.push(v);

        if (SIM.selectedVehicleType === 5) {
            activateGreenCorridor(dir);
        }
    });
}

function setupVehiclePalette() {
    const palette = document.getElementById('vehiclePalette');
    palette.innerHTML = VEHICLE_CLASSES.map(c => `
        <button class="veh-btn" onclick="selectVehicleType(${c.id}, this)"
            style="border-left: 3px solid ${c.color}">
            ${c.name}
        </button>
    `).join('');
}

function selectVehicleType(id, btn) {
    if (SIM.selectedVehicleType === id) {
        SIM.selectedVehicleType = null;
        btn.classList.remove('selected');
        SIM.canvas.style.cursor = 'default';
        return;
    }
    SIM.selectedVehicleType = id;
    document.querySelectorAll('.veh-btn').forEach(b => b.classList.remove('selected'));
    btn.classList.add('selected');
    SIM.canvas.style.cursor = 'crosshair';
}

// ── FPS Counter ───────────────────────────────────────────
let lastFrameTime = performance.now();
let fps = 30;

function updateFPS() {
    const now = performance.now();
    const delta = now - lastFrameTime;
    lastFrameTime = now;
    fps = Math.round(1000 / delta);
    document.getElementById('dataFPS').textContent = fps;
}

// ── Main Loop ─────────────────────────────────────────────
function gameLoop() {
    if (!SIM.paused) {
        SIM.frame++;

        // Spawn vehicles based on density
        SIM.spawnTimer++;
        const spawnRate = Math.max(5, 60 - SIM.density);
        if (SIM.spawnTimer >= spawnRate && SIM.vehicles.length < SIM.density * 1.5) {
            spawnVehicle();
            SIM.spawnTimer = 0;
        }

        // Update signals
        SIM.signals.forEach(s => s.update());

        // Update vehicles
        SIM.vehicles.forEach(v => v.update(SIM.signals));

        // Remove off-screen vehicles
        SIM.vehicles = SIM.vehicles.filter(v => !v.isOffScreen());

        // Check ambulance status
        checkAmbulance();
    }

    // Render
    const ctx = SIM.ctx;
    drawRoads(ctx);
    SIM.vehicles.forEach(v => v.render(ctx));
    drawSignals(ctx);
    drawNightOverlay(ctx);
    drawHUD(ctx);

    // Update UI every 10 frames
    if (SIM.frame % 10 === 0) {
        updateDataPanel();
        updateCorridorPanel();
    }

    updateFPS();
    requestAnimationFrame(gameLoop);
}

// ── Init ──────────────────────────────────────────────────
function init() {
    SIM.canvas = document.getElementById('simCanvas');
    SIM.ctx = SIM.canvas.getContext('2d');

    function resize() {
        const wrap = SIM.canvas.parentElement;
        SIM.canvas.width = wrap.clientWidth;
        SIM.canvas.height = wrap.clientHeight;
        SIM.width = SIM.canvas.width;
        SIM.height = SIM.canvas.height;
        SIM.centerX = SIM.width / 2;
        SIM.centerY = SIM.height / 2;
        SIM.roadWidth = Math.min(SIM.width, SIM.height) * 0.12;
    }

    resize();
    window.addEventListener('resize', resize);

    // Create signals
    SIM.signals = DIRECTIONS.map(d => new TrafficSignal(0, 0, d));
    // Sync NS/EW pairs
    SIM.signals[0].state = 'green'; SIM.signals[0].timer = 0;
    SIM.signals[1].state = 'green'; SIM.signals[1].timer = 0;
    SIM.signals[2].state = 'red';   SIM.signals[2].timer = 0;
    SIM.signals[3].state = 'red';   SIM.signals[3].timer = 0;

    setupCanvasClick();
    setupVehiclePalette();

    gameLoop();
}

document.addEventListener('DOMContentLoaded', init);
