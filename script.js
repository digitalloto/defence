// ============================================
// AIMCRS — Vision 2047 Alignment Tool
// Interactive Script
// ============================================

// --- DATA: All 8 Vision 2047 Priorities mapped to AIMCRS ---
const alignmentData = [
    {
        id: 1,
        priority: "PRIORITY 1",
        title: "Data-Centric Warfare & Decision Superiority",
        visionQuote: "Transit from information superiority to decision superiority (Net Centric to Data Centric Warfare).",
        summary: "NETRA processes raw multi-source data into actionable intelligence — delivering decision superiority, not information overload.",
        detail: {
            visionText: "The Vision 2047 document mandates a fundamental doctrinal shift from Net Centric operations (focused on information superiority) to Data Centric Warfare (focused on decision superiority). This means the military needs AI systems that don't just collect data — they must process it into decisions.",
            capabilities: [
                "Multi-source intelligence processing (SIGINT, HUMINT, OSINT, GEOINT) through AI algorithms",
                "Automated threat prioritisation reducing the OODA loop from hours to seconds",
                "Actionable decision support — not raw data dumps",
                "Real-time threat assessment enabling commanders to act immediately"
            ],
            phase: "Phase I (Now–2030) — Immediate deployment readiness"
        }
    },
    {
        id: 2,
        priority: "PRIORITY 2",
        title: "Data Force — New Tri-Service Entity",
        visionQuote: "A dedicated Data Force integrated with quantum-resistant encryption and edge computing to enable real-time battle management systems by 2030.",
        summary: "AIMCRS can serve as the foundational AI technology layer for the proposed Data Force — reducing development time by leveraging existing patent-protected IP.",
        detail: {
            visionText: "Vision 2047 proposes creating a brand-new entity called the Data Force — a tri-service (Army + Navy + Air Force) organisation dedicated to data-centric warfare. This Force needs AI systems that can process battle data in real time.",
            capabilities: [
                "Purpose-built AI architecture for real-time battle management data processing",
                "Multi-domain data ingestion, correlation, and fusion",
                "Edge-deployable modules for forward operating bases and tactical HQs",
                "Indigenous alternative to foreign battle management systems",
                "Full data sovereignty — no data leaves Indian networks"
            ],
            phase: "Phase I (Now–2030) — Core technology ready for integration"
        }
    },
    {
        id: 3,
        priority: "PRIORITY 3",
        title: "Defence Geo-Spatial Agency (DGA)",
        visionQuote: "Seamlessly integrates satellite imagery, advanced mapping technologies, and real-time geospatial data to bolster battlefield intelligence, navigation, and strategic planning.",
        summary: "NETRA integrates satellite feeds, terrain data, and real-time sensor inputs into a unified Common Operating Picture for geo-spatial intelligence.",
        detail: {
            visionText: "The Defence Geo-Spatial Agency will be the nerve centre for location-based intelligence. It needs AI systems that can process satellite images, maps, and sensor data to give commanders a clear picture of the battlefield.",
            capabilities: [
                "Integration of satellite feeds, terrain data, and real-time sensor inputs",
                "Unified Common Operating Picture (COP) for all forces",
                "Geo-spatial threat mapping with AI-driven anomaly detection",
                "Real-time situational awareness overlays for operational planning",
                "Compatible with Indian satellite systems (ISRO assets)"
            ],
            phase: "Phase I–II — Progressive integration with national geo-spatial infrastructure"
        }
    },
    {
        id: 4,
        priority: "PRIORITY 4",
        title: "Mission Sudarshan Chakra — Integrated Air Defence",
        visionQuote: "A nationwide network of radars, command-and-control centres, interceptor missiles that can identify, track, and destroy incoming missiles, drones, and swarms in real time.",
        summary: "NETRA's AI engine can serve as the predictive intelligence backbone — running threat probability calculations and recommending counter-strategies in real time.",
        detail: {
            visionText: "Mission Sudarshan Chakra is India's most ambitious air defence programme — a nationwide shield against missiles, drones, and aerial threats. The Vision says AI will perform 'permutations and combinations of multiple possibilities and military manoeuvres to estimate the likelihood of future conflicts.'",
            capabilities: [
                "AI-driven threat detection and classification across multiple sensor types",
                "Predictive analytics engine calculating threat probabilities",
                "Automatic counter-measure recommendations",
                "Real-time multi-sensor data fusion for tracking aerial threats",
                "Indigenous command-and-control software for Indian defence networks"
            ],
            phase: "Phase I (Now–2030) — Sudarshan Chakra targeted operational by 2030"
        }
    },
    {
        id: 5,
        priority: "PRIORITY 5",
        title: "Cognitive Warfare Action Force",
        visionQuote: "Conduct psychological operations, perception management, and information warfare — domains increasingly viewed as decisive in shaping strategic outcomes without direct kinetic conflict.",
        summary: "AIMCRS provides AI-driven information monitoring, pattern recognition, and threat assessment across the cognitive and information domains.",
        detail: {
            visionText: "Cognitive Warfare means winning battles through information, psychology, and perception — not just weapons. The Vision recognises that shaping how people think and what they believe is now as important as physical military operations.",
            capabilities: [
                "Multi-source information monitoring and analysis",
                "AI-driven pattern recognition for detecting disinformation campaigns",
                "Social media and open-source intelligence analysis",
                "Threat assessment across the cognitive domain",
                "Situational awareness tools for information operations commanders"
            ],
            phase: "Phase I–II — Building cognitive warfare awareness capabilities"
        }
    },
    {
        id: 6,
        priority: "PRIORITY 6",
        title: "Drone Force & Counter-UAS Operations",
        visionQuote: "Dedicated to UCAVs, ISR drones, loitering munitions, and swarm warfare, consolidating fragmented drone programmes under a unified tri-service command.",
        summary: "NETRA serves as the AI-driven data processing and decision support layer for drone fleet management, ISR integration, and counter-UAS operations.",
        detail: {
            visionText: "The Drone Force will unify all drone operations across the three services — from combat drones (UCAVs) to surveillance drones (ISR) to swarm attacks. This force needs AI to process drone data and coordinate operations.",
            capabilities: [
                "Integration of drone ISR feeds into the operational picture",
                "AI-driven drone swarm detection and tracking",
                "Counter-UAS threat assessment and engagement prioritisation",
                "Data processing backbone for drone fleet management",
                "Mission planning support with AI-driven route optimisation"
            ],
            phase: "Phase I (Now–2030) — Drone integration capabilities operational"
        }
    },
    {
        id: 7,
        priority: "PRIORITY 7",
        title: "Space & Cyber Commands",
        visionQuote: "Exercise control over Space, EM spectrum and Cyber — dedicated Space and Cyber Commands for satellite operations, cyber defence and offensive cyber warfare.",
        summary: "AIMCRS provides cyber threat detection, space-based sensor data integration, and electromagnetic spectrum monitoring capabilities.",
        detail: {
            visionText: "India plans to create full military commands for Space and Cyber — similar to how there are separate commands for different regions. These commands will protect India's satellites, defend against cyber attacks, and control the electromagnetic spectrum.",
            capabilities: [
                "Cyber threat detection and analysis capabilities",
                "Integration of space-based sensor data into operational intelligence",
                "Electromagnetic spectrum monitoring and analysis",
                "Multi-domain situational awareness spanning space, cyber, and EM domains",
                "Data fusion across all operational domains"
            ],
            phase: "Phase II (2030–2040) — Deep space and cyber integration"
        }
    },
    {
        id: 8,
        priority: "PRIORITY 8",
        title: "Atmanirbhar Bharat — Indigenous Defence Technology",
        visionQuote: "The concept of self-reliance or 'Atmanirbharta' is not restricted to defence manufacturing only. It must permeate from strategic thinking to capability development.",
        summary: "AIMCRS is 100% indigenous — three Indian patents, zero foreign dependencies, designed for Indian threat scenarios, built in Chennai.",
        detail: {
            visionText: "Self-reliance is the backbone of Vision 2047. The document says India must not just manufacture weapons locally — the entire way India thinks about defence strategy must be indigenous. This is exactly what AIMCRS represents.",
            capabilities: [
                "100% Indian design and development — no foreign technology dependencies",
                "Three Indian patents protecting core intellectual property",
                "Built in Chennai — supporting Indian defence manufacturing ecosystem",
                "Algorithms trained on Indian operational scenarios and geography",
                "Full data sovereignty — no data leaves Indian networks, no foreign backdoors",
                "Indian strategic thinking turned into Indian technology"
            ],
            phase: "All Phases — Atmanirbhar from Day 1"
        }
    }
];

// --- RENDER ALIGNMENT CARDS ---
function renderCards() {
    const grid = document.getElementById('alignmentGrid');
    grid.innerHTML = '';

    alignmentData.forEach(item => {
        const card = document.createElement('div');
        card.className = 'alignment-card';
        card.setAttribute('data-id', item.id);

        card.innerHTML = `
            <div class="card-header">
                <span class="card-number">${item.priority}</span>
                <span class="card-status status-aligned">ALIGNED</span>
            </div>
            <h3 class="card-vision-title">${item.title}</h3>
            <p class="card-vision-text">"${item.visionQuote}"</p>
            <p class="card-aimcrs-label">AIMCRS RESPONSE</p>
            <p class="card-aimcrs-text">${item.summary}</p>
            <span class="card-expand">CLICK FOR FULL DETAILS →</span>
        `;

        card.addEventListener('click', () => showDetail(item));
        grid.appendChild(card);
    });
}

// --- SHOW DETAIL PANEL ---
function showDetail(item) {
    const overlay = document.getElementById('detailOverlay');
    const content = document.getElementById('detailContent');

    let capabilitiesHTML = item.detail.capabilities
        .map(cap => `<li>${cap}</li>`)
        .join('');

    content.innerHTML = `
        <h2>${item.priority}: ${item.title}</h2>

        <h3>What Vision 2047 Says</h3>
        <blockquote>"${item.visionQuote}"</blockquote>
        <p style="color: var(--text-dim); font-size: 0.9rem; line-height: 1.6; margin-top: 0.75rem;">
            ${item.detail.visionText}
        </p>

        <h3>How AIMCRS / NETRA Delivers</h3>
        <ul>${capabilitiesHTML}</ul>

        <div class="detail-phase">${item.detail.phase}</div>
    `;

    overlay.classList.add('active');
    document.body.style.overflow = 'hidden';
}

// --- CLOSE DETAIL PANEL ---
function closeDetail() {
    const overlay = document.getElementById('detailOverlay');
    overlay.classList.remove('active');
    document.body.style.overflow = '';
}

document.getElementById('detailClose').addEventListener('click', closeDetail);
document.getElementById('detailOverlay').addEventListener('click', (e) => {
    if (e.target === e.currentTarget) closeDetail();
});

// Close on Escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeDetail();
});

// --- INITIALISE ---
renderCards();
