/* AIMCRS God Mode — Admin Panel JavaScript */

// ── Tab Navigation ────────────────────────────────────────
document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
        tab.classList.add('active');
        document.getElementById('panel-' + tab.dataset.panel).classList.add('active');
    });
});

// ── Pipeline Control ──────────────────────────────────────
let pipelineSteps = [];
let activeTasks = {};

async function loadPipeline() {
    try {
        const [stepsRes, statusRes] = await Promise.all([
            fetch('/admin/api/pipeline/steps'),
            fetch('/admin/api/pipeline/status')
        ]);
        pipelineSteps = await stepsRes.json();
        const status = await statusRes.json();
        renderPipeline(pipelineSteps);
        renderPipelineStatus(status);
    } catch (e) {
        console.error('Failed to load pipeline:', e);
    }
}

function renderPipeline(steps) {
    const flow = document.getElementById('pipelineFlow');
    flow.innerHTML = '';
    steps.forEach((step, i) => {
        if (i > 0) {
            const arrow = document.createElement('span');
            arrow.className = 'pipe-arrow';
            arrow.textContent = '\u2192';
            flow.appendChild(arrow);
        }
        const el = document.createElement('div');
        el.className = 'pipe-step';
        el.id = 'step-' + step.id;
        el.innerHTML = `
            <div class="step-phase">${step.phase}</div>
            <div class="step-name">${step.name}</div>
            <div class="step-action">
                <button class="btn btn-sm btn-green" onclick="runStep('${step.id}')"
                    ${!step.script_exists ? 'disabled title="Script not found"' : ''}>
                    Run
                </button>
            </div>
        `;
        flow.appendChild(el);
    });
}

function renderPipelineStatus(status) {
    const grid = document.getElementById('pipelineStatus');
    const cards = [
        { label: 'YouTube Videos', value: status.download.youtube_videos, group: 'Download' },
        { label: 'Government Files', value: status.download.government_files, group: 'Download' },
        { label: 'Academic Files', value: status.download.academic_files, group: 'Download' },
        { label: 'Kaggle Files', value: status.download.kaggle_files, group: 'Download' },
        { label: 'Unlabelled Images', value: status.process.unlabelled_images, group: 'Process' },
        { label: 'Labelled Images', value: status.process.labelled_images, group: 'Process' },
        { label: 'Augmented Images', value: status.process.augmented_images, group: 'Process' },
        { label: 'Train Images', value: status.train.train_images, group: 'Train' },
        { label: 'Validation Images', value: status.train.val_images, group: 'Train' },
        { label: 'Test Images', value: status.train.test_images, group: 'Train' },
    ];
    grid.innerHTML = cards.map(c => `
        <div class="status-card">
            <h4>${c.group}</h4>
            <div class="stat-value">${c.value}</div>
            <div class="stat-label">${c.label}</div>
        </div>
    `).join('');
}

async function runStep(stepId) {
    const stepEl = document.getElementById('step-' + stepId);
    stepEl.className = 'pipe-step running';
    appendConsole(`Starting ${stepId}...`, 'info');

    try {
        const res = await fetch(`/admin/api/pipeline/run/${stepId}`, { method: 'POST' });
        const data = await res.json();
        if (data.error) {
            appendConsole(`Error: ${data.error}`, 'error');
            stepEl.className = 'pipe-step error';
            return;
        }
        activeTasks[data.task_id] = stepId;
        pollTask(data.task_id);
    } catch (e) {
        appendConsole(`Failed to start ${stepId}: ${e}`, 'error');
        stepEl.className = 'pipe-step error';
    }
}

async function runAllSteps() {
    for (const step of pipelineSteps) {
        if (step.script_exists) {
            await runStep(step.id);
            // Wait for completion before next step
            await new Promise(resolve => {
                const check = setInterval(async () => {
                    const tasks = await (await fetch('/admin/api/pipeline/tasks')).json();
                    const running = tasks.some(t => t.status === 'running');
                    if (!running) { clearInterval(check); resolve(); }
                }, 2000);
            });
        }
    }
}

let lastOutputLength = {};

async function pollTask(taskId) {
    lastOutputLength[taskId] = 0;
    const interval = setInterval(async () => {
        try {
            const res = await fetch(`/admin/api/pipeline/task/${taskId}`);
            const task = await res.json();

            // Show new output lines
            const newLines = task.output.slice(lastOutputLength[taskId] || 0);
            newLines.forEach(line => appendConsole(line));
            lastOutputLength[taskId] = task.output.length;

            if (task.status !== 'running') {
                clearInterval(interval);
                const stepEl = document.getElementById('step-' + task.step);
                stepEl.className = 'pipe-step ' + task.status;
                appendConsole(`${task.name} ${task.status} (exit code: ${task.exit_code})`,
                    task.status === 'complete' ? 'info' : 'error');
                delete activeTasks[taskId];
                loadPipeline(); // Refresh counts
            }
        } catch (e) {
            clearInterval(interval);
        }
    }, 1500);
}

function appendConsole(text, type) {
    const body = document.getElementById('consoleBody');
    if (body.querySelector('.console-placeholder')) {
        body.innerHTML = '';
    }
    const line = document.createElement('div');
    if (type === 'error') line.className = 'line-error';
    else if (type === 'warn') line.className = 'line-warn';
    line.textContent = text;
    body.appendChild(line);
    body.scrollTop = body.scrollHeight;
}

function clearConsole() {
    document.getElementById('consoleBody').innerHTML =
        '<p class="console-placeholder">Console cleared.</p>';
}

// ── Logs ──────────────────────────────────────────────────
let currentLogSSE = null;

async function loadLogsList() {
    try {
        const res = await fetch('/admin/api/logs/list');
        const logs = await res.json();
        const select = document.getElementById('logSelect');
        select.innerHTML = '<option value="">Select log file...</option>';
        logs.forEach(log => {
            const opt = document.createElement('option');
            opt.value = log.name;
            opt.textContent = `${log.name} (${log.size_kb} KB)`;
            select.appendChild(opt);
        });
    } catch (e) {
        console.error('Failed to load logs list:', e);
    }
}

async function loadLog(filename) {
    if (!filename) return;
    if (currentLogSSE) { currentLogSSE.close(); currentLogSSE = null; }

    document.getElementById('logFileName').textContent = filename;
    const body = document.getElementById('logBody');
    body.innerHTML = '<p class="console-placeholder">Loading...</p>';

    try {
        const res = await fetch(`/admin/api/logs/${filename}?tail=300`);
        const data = await res.json();
        body.innerHTML = data.lines.map(l => `<div>${escapeHtml(l)}</div>`).join('');
        body.scrollTop = body.scrollHeight;

        // Start SSE for live updates
        currentLogSSE = new EventSource(`/admin/api/logs/stream/${filename}`);
        currentLogSSE.onmessage = (event) => {
            const line = document.createElement('div');
            line.textContent = event.data;
            body.appendChild(line);
            if (document.getElementById('autoScroll').checked) {
                body.scrollTop = body.scrollHeight;
            }
        };
    } catch (e) {
        body.innerHTML = `<div class="line-error">Failed to load log: ${e}</div>`;
    }
}

function refreshLog() {
    const select = document.getElementById('logSelect');
    if (select.value) loadLog(select.value);
}

// ── Models ────────────────────────────────────────────────
async function loadModels() {
    try {
        const [modelsRes, classesRes] = await Promise.all([
            fetch('/admin/api/models/status'),
            fetch('/admin/api/vehicle-classes')
        ]);
        const models = await modelsRes.json();
        const classes = await classesRes.json();
        renderModels(models);
        renderClasses(classes);
    } catch (e) {
        console.error('Failed to load models:', e);
    }
}

function renderModels(models) {
    document.getElementById('modelsGrid').innerHTML = models.map(m => `
        <div class="model-card">
            <h3>${m.name}</h3>
            <span class="model-status ${m.trained ? 'trained' : 'pending'}">
                ${m.trained ? 'TRAINED' : 'NOT TRAINED'}
            </span>
            <div class="model-detail">Accuracy: ${m.accuracy}</div>
            <div class="model-detail">Target: ${m.target}</div>
            ${m.weights_size_mb ? `<div class="model-detail">Weights: ${m.weights_size_mb} MB</div>` : ''}
        </div>
    `).join('');
}

function renderClasses(classes) {
    document.getElementById('classGrid').innerHTML = classes.map(c => `
        <div class="class-chip">
            <span class="class-dot" style="background:${c.color}"></span>
            <span>${c.id}: ${c.name}</span>
        </div>
    `).join('');
}

function refreshModels() { loadModels(); }

// ── System ────────────────────────────────────────────────
async function loadSystem() {
    try {
        const [infoRes, healthRes] = await Promise.all([
            fetch('/admin/api/system/info'),
            fetch('/admin/api/system/health')
        ]);
        const info = await infoRes.json();
        const health = await healthRes.json();
        renderSystem(info);
        renderHealth(health);
        updateHealthDot(health.status);
    } catch (e) {
        console.error('Failed to load system info:', e);
    }
}

function renderSystem(info) {
    const pct = ((info.disk_used_gb / info.disk_total_gb) * 100).toFixed(0);
    document.getElementById('systemGrid').innerHTML = `
        <div class="sys-card">
            <h4>Python</h4>
            <div class="sys-value">${info.python_version.split(' ')[0]}</div>
        </div>
        <div class="sys-card">
            <h4>GPU</h4>
            <div class="sys-value">${info.gpu_available ? 'Available' : 'CPU Only'}</div>
        </div>
        <div class="sys-card">
            <h4>Disk Usage</h4>
            <div class="sys-value">${info.disk_used_gb} / ${info.disk_total_gb} GB</div>
            <div class="disk-bar"><div class="disk-bar-fill" style="width:${pct}%"></div></div>
        </div>
        <div class="sys-card">
            <h4>Raw Data</h4>
            <div class="sys-value">${info.data_sizes.raw_mb} MB</div>
        </div>
        <div class="sys-card">
            <h4>Processed Data</h4>
            <div class="sys-value">${info.data_sizes.processed_mb} MB</div>
        </div>
        <div class="sys-card">
            <h4>Models</h4>
            <div class="sys-value">${info.data_sizes.models_mb} MB</div>
        </div>
    `;
}

function renderHealth(health) {
    const rows = [];
    for (const [k, v] of Object.entries(health.directories)) {
        rows.push(`<tr><td>${k}</td><td class="${v ? 'check-ok' : 'check-fail'}">${v ? 'OK' : 'MISSING'}</td></tr>`);
    }
    rows.push('<tr><td colspan="2" style="color:var(--text-dim);padding-top:12px">Dependencies</td></tr>');
    for (const [k, v] of Object.entries(health.dependencies)) {
        rows.push(`<tr><td>${k}</td><td class="${v ? 'check-ok' : 'check-fail'}">${v ? 'Installed' : 'Missing'}</td></tr>`);
    }
    document.getElementById('healthDetails').innerHTML =
        `<table class="health-table">${rows.join('')}</table>`;
}

function updateHealthDot(status) {
    const dot = document.getElementById('healthDot');
    const text = document.getElementById('healthText');
    dot.className = 'health-dot ' + status;
    text.textContent = status.charAt(0).toUpperCase() + status.slice(1);
}

function refreshSystem() { loadSystem(); }

// ── Utilities ─────────────────────────────────────────────
function escapeHtml(text) {
    const d = document.createElement('div');
    d.textContent = text;
    return d.innerHTML;
}

// ── Init ──────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    loadPipeline();
    loadLogsList();
    loadModels();
    loadSystem();
});
