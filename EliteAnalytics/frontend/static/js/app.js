const API_BASE = "/api";
let currentMatchId = null;
let currentMatchEvents = [];

// DOM Elements
const matchSelector = document.getElementById("match-selector");
const exportPdfBtn = document.getElementById("export-pdf");

const els = {
    homeName: document.getElementById("home-name"),
    awayName: document.getElementById("away-name"),
    score: document.getElementById("score-text"),
    xg: document.getElementById("kpi-xg"),
    poss: document.getElementById("kpi-poss"),
    tilt: document.getElementById("kpi-tilt"),
    ppda: document.getElementById("kpi-ppda"),

    pitchLoading: document.getElementById("pitch-loading"),
    pitchContainer: document.getElementById("pitch-container"),

    networkLoading: document.getElementById("network-loading"),
    networkContainer: document.getElementById("network-container"),

    momentumContainer: document.getElementById("momentum-container"),

    tableBody: document.getElementById("player-table-body"),

    overlayRadios: document.querySelectorAll('input[name="overlay"]'),
    progPassesCheck: document.getElementById("prog-passes-only")
};

// Initialize Dashboard
async function init() {
    await loadMatchList();
    if (matchSelector.options.length > 0) {
        matchSelector.value = matchSelector.options[1].value; // Auto-select first real match
        loadMatch(matchSelector.value);
    }

    matchSelector.addEventListener("change", (e) => loadMatch(e.target.value));

    document.querySelectorAll('input[name="shotmap_overlay"]').forEach(radio => {
        radio.addEventListener("change", () => renderShotMaps());
    });

    document.querySelectorAll('input[name="passmap_overlay"]').forEach(radio => {
        radio.addEventListener("change", () => renderPassMaps());
    });

    els.progPassesCheck.addEventListener("change", () => renderPassNetwork());

    exportPdfBtn.addEventListener("click", exportPDF);

    loadSeasonLeaderboard();
}

// 1. Fetch & Populate Match List
async function loadMatchList() {
    try {
        const res = await fetch(`${API_BASE}/matches`);
        const matches = await res.json();

        matchSelector.innerHTML = '<option value="" disabled>Select a match...</option>';
        matches.forEach(m => {
            const opt = document.createElement("option");
            opt.value = m.id;
            const dateStr = m.date ? m.date.split('T')[0] : "";
            opt.textContent = `[${dateStr}] ${m.home_team} ${m.home_score} - ${m.away_score} ${m.away_team} (${m.competition})`;
            matchSelector.appendChild(opt);
        });
    } catch (e) {
        console.error("Failed to load matches", e);
        matchSelector.innerHTML = '<option value="" disabled>Error loading matches API</option>';
    }
}

// 2. Load Selected Match Data
async function loadMatch(matchId) {
    currentMatchId = matchId;

    // Fetch stats, events, momentum, zones concurrently
    try {
        const [statsRes, eventsRes, momentumRes, zonesRes] = await Promise.all([
            fetch(`${API_BASE}/matches/${matchId}/stats`),
            fetch(`${API_BASE}/matches/${matchId}/events`),
            fetch(`${API_BASE}/matches/${matchId}/momentum`),
            fetch(`${API_BASE}/tactics/zones?match_id=${matchId}`)
        ]);

        const stats = await statsRes.json();
        currentMatchEvents = await eventsRes.json();
        const momentum = await momentumRes.json();
        const zones = await zonesRes.json();

        updateKPIs(stats);
        renderShotMaps();
        renderPassMaps();
        renderMomentum(momentum, stats);
        renderPlayerTable();
        renderPassNetwork(); // D3

    } catch (e) {
        console.error("Failed loading match data", e);
    }
}

// 3. Update KPI Header
function updateKPIs(stats) {
    els.homeName.textContent = stats.home_team;
    els.awayName.textContent = stats.away_team;
    els.score.textContent = stats.score;

    els.xg.textContent = `${stats.home_xg.toFixed(2)} - ${stats.away_xg.toFixed(2)}`;
    els.poss.textContent = `${stats.home_possession}% - ${stats.away_possession}%`;
    els.tilt.textContent = `${stats.home_field_tilt}% - ${stats.away_field_tilt}%`;
    els.ppda.textContent = `${stats.home_ppda.toFixed(1)} - ${stats.away_ppda.toFixed(1)}`;
}

// 4. Render Interactive Shot Maps
function renderShotMaps() {
    const container = document.getElementById("shotmap-container");
    const overlayType = document.querySelector('input[name="shotmap_overlay"]:checked').value;

    if (overlayType === "shot_map_ws") {
        container.innerHTML = `<iframe src="/assets/html/${currentMatchId}_shotmap_ws.html" class="w-full h-[600px] border-0 rounded-lg"></iframe>`;
    } else if (overlayType === "shot_map_us") {
        container.innerHTML = `<iframe src="/assets/html/${currentMatchId}_shotmap_ws.html" class="w-full h-[600px] border-0 rounded-lg"></iframe>`;
    }
}

// 4.5 Render Static Pass Maps (Embedded Python Images)
function renderPassMaps() {
    const container = document.getElementById("passmap-container");
    const overlayType = document.querySelector('input[name="passmap_overlay"]:checked').value;

    if (overlayType === "total") {
        container.innerHTML = `
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 h-full bg-[#0d0d1a] border border-gray-800 rounded-lg items-center text-center p-4 min-h-[500px]">
            <div>
                <img src="/assets/png/${currentMatchId}_home_total_passes.png" onerror="this.src='/assets/png/placeholder.png'" class="w-full h-auto max-h-[500px] object-contain mx-auto rounded shadow-lg">
            </div>
            <div>
                <img src="/assets/png/${currentMatchId}_away_total_passes.png" onerror="this.src='/assets/png/placeholder.png'" class="w-full h-auto max-h-[500px] object-contain mx-auto rounded shadow-lg">
            </div>
        </div>`;
    } else if (overlayType === "final_third") {
        container.innerHTML = `
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 h-full bg-[#0d0d1a] border border-gray-800 rounded-lg items-center text-center p-4 min-h-[500px]">
            <div>
                <img src="/assets/png/${currentMatchId}_home_final_third.png" onerror="this.src='/assets/png/placeholder.png'" class="w-full h-auto max-h-[500px] object-contain mx-auto mix-blend-screen rounded shadow-lg">
            </div>
            <div>
                <img src="/assets/png/${currentMatchId}_away_final_third.png" onerror="this.src='/assets/png/placeholder.png'" class="w-full h-auto max-h-[500px] object-contain mx-auto mix-blend-screen rounded shadow-lg">
            </div>
        </div>`;
    } else if (overlayType === "progressive") {
        container.innerHTML = `
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 h-full bg-[#0d0d1a] border border-gray-800 rounded-lg items-center text-center p-4 min-h-[500px]">
            <div>
                <img src="/assets/png/${currentMatchId}_home_progressive_passes.png" onerror="this.src='/assets/png/placeholder.png'" class="w-full h-auto max-h-[500px] object-contain mx-auto rounded shadow-lg">
            </div>
            <div>
                <img src="/assets/${currentMatchId}_away_progressive_passes.png" onerror="this.src='/assets/placeholder.png'" class="w-full h-auto max-h-[500px] object-contain mx-auto rounded shadow-lg">
            </div>
        </div>`;
    } else if (overlayType === "dribbles") {
        container.innerHTML = `
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 h-full bg-[#0d0d1a] border border-gray-800 rounded-lg items-center text-center p-4 min-h-[500px]">
            <div>
                <img src="/assets/png/${currentMatchId}_home_dribbles.png" onerror="this.src='/assets/png/placeholder.png'" class="w-full h-auto max-h-[500px] object-contain mx-auto rounded shadow-lg">
            </div>
            <div>
                <img src="/assets/png/${currentMatchId}_away_dribbles.png" onerror="this.src='/assets/png/placeholder.png'" class="w-full h-auto max-h-[500px] object-contain mx-auto rounded shadow-lg">
            </div>
        </div>`;
    }
}

// 5. Render Momentum Graph (Plotly)
function renderMomentum(momentum, stats) {
    const layout = {
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        margin: { l: 40, r: 20, t: 30, b: 30 },
        xaxis: { title: "Minute", color: '#888', gridcolor: '#333' },
        yaxis: { title: "Danger Level", color: '#888', gridcolor: '#333' },
        showlegend: true,
        legend: { orientation: "h", y: 1.1, x: 0 },
        font: { family: "Inter", color: "#ccc" }
    };

    const traceHome = {
        x: momentum.minutes,
        y: momentum.home_danger,
        fill: 'tozeroy',
        type: 'scatter',
        name: stats.home_team,
        line: { color: '#a50044', width: 2 },
        fillcolor: 'rgba(165, 0, 68, 0.2)'
    };

    const traceAway = {
        x: momentum.minutes,
        y: momentum.away_danger,
        fill: 'tozeroy',
        type: 'scatter',
        name: stats.away_team,
        line: { color: '#004d98', width: 2 },
        fillcolor: 'rgba(0, 77, 152, 0.2)'
    };

    Plotly.newPlot("momentum-container", [traceHome, traceAway], layout, { displayModeBar: false });
}

// 6. Render Player Table
function renderPlayerTable() {
    // Aggregate event data per player
    const pStats = {};
    currentMatchEvents.forEach(e => {
        if (!e.player || e.player === "Unknown") return;
        if (!pStats[e.player]) {
            pStats[e.player] = { team: e.team, xg: 0, xt: 0, passes: 0, prog_passes: 0 };
        }

        if (e.is_shot && e.xg) pStats[e.player].xg += e.xg;
        if (e.type === "Pass") {
            if (e.outcome === "Successful") pStats[e.player].passes += 1;
            if (e.xt > 0) {
                pStats[e.player].xt += e.xt;
                pStats[e.player].prog_passes += 1;
            }
        }
    });

    const sortedPlayers = Object.entries(pStats).sort((a, b) => b[1].xt - a[1].xt);

    els.tableBody.innerHTML = "";
    sortedPlayers.forEach(([name, s]) => {
        if (s.passes < 5 && s.xg === 0) return; // Skip minor subs for brevity

        const tr = document.createElement("tr");
        tr.className = "border-b border-gray-800 hover:bg-white hover:bg-opacity-5 cursor-pointer transition-colors";
        tr.innerHTML = `
            <td class="px-6 py-3 font-medium text-white">${name}</td>
            <td class="px-6 py-3">${s.team}</td>
            <td class="px-6 py-3">${s.xg.toFixed(2)}</td>
            <td class="px-6 py-3 font-bold text-[#edbb00]">${s.xt.toFixed(3)}</td>
            <td class="px-6 py-3">${s.passes}</td>
            <td class="px-6 py-3">${s.prog_passes}</td>
        `;
        els.tableBody.appendChild(tr);
    });
}

async function renderPassNetwork() {
    els.networkLoading.style.display = 'none';
    const container = document.getElementById("network-container");

    container.innerHTML = `
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 p-4 w-full h-full">
            <div class="bg-[#111128] border border-[#222244] rounded-xl overflow-hidden shadow-lg transition-all duration-300 hover:border-[#4444aa] hover:shadow-2xl">
                <div class="px-5 py-4 border-b border-[#222244] flex items-center gap-3">
                    <div class="w-2.5 h-2.5 rounded-full bg-[#a50044] shrink-0"></div>
                    <h4 class="text-sm font-semibold tracking-wide text-[#ccccee]">${els.homeName.textContent} Pass Network</h4>
                </div>
                <img src="/assets/png/${currentMatchId}_home_passnetwork.png" onerror="this.src='/assets/png/placeholder.png'" class="w-full block bg-white border-t border-[#111128]">
            </div>
            <div class="bg-[#111128] border border-[#222244] rounded-xl overflow-hidden shadow-lg transition-all duration-300 hover:border-[#4444aa] hover:shadow-2xl">
                <div class="px-5 py-4 border-b border-[#222244] flex items-center gap-3">
                    <div class="w-2.5 h-2.5 rounded-full bg-[#004d98] shrink-0"></div>
                    <h4 class="text-sm font-semibold tracking-wide text-[#ccccee]">${els.awayName.textContent} Pass Network</h4>
                </div>
                <img src="/assets/png/${currentMatchId}_away_passnetwork.png" onerror="this.src='/assets/png/placeholder.png'" class="w-full block bg-white border-t border-[#111128]">
            </div>
        </div>
    `;
}

// 8. Season Leaderboard
async function loadSeasonLeaderboard() {
    try {
        const res = await fetch(`${API_BASE}/season/leaderboard`);
        const data = await res.json();

        const tbody = document.getElementById("season-leaderboard-body");
        tbody.innerHTML = "";

        data.forEach((p, idx) => {
            const tr = document.createElement("tr");
            tr.className = "border-b border-gray-800 hover:bg-white hover:bg-opacity-5 transition-colors";
            tr.innerHTML = `
                <td class="px-6 py-4 text-gray-400">${idx + 1}</td>
                <td class="px-6 py-4 font-bold text-white">${p.player}</td>
                <td class="px-6 py-4">${p.team}</td>
                <td class="px-6 py-4 text-green-400 font-medium">${p.xt.toFixed(3)}</td>
                <td class="px-6 py-4 text-[#edbb00] font-bold">${p.prog_passes}</td>
                <td class="px-6 py-4 text-blue-400 font-medium">${p.xg.toFixed(2)}</td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        console.error("Failed to load leaderboard", e);
    }
}

// 9. PDF Export
function exportPDF() {
    const element = document.getElementById('dashboard-content');
    const opt = {
        margin: 0.5,
        filename: 'Elite_Barca_Match_Report.pdf',
        image: { type: 'jpeg', quality: 0.98 },
        html2canvas: { scale: 2, useCORS: true, backgroundColor: '#0d0d1a' },
        jsPDF: { unit: 'in', format: 'a3', orientation: 'landscape' }
    };

    html2pdf().set(opt).from(element).save();
}

// Boot
init();
