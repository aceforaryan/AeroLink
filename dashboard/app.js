document.addEventListener('DOMContentLoaded', () => {
    // Canvas & Contexts
    const topologyCanvas = document.getElementById('topologyCanvas');
    const ctx = topologyCanvas.getContext('2d');
    const spectrumCanvas = document.getElementById('spectrumCanvas');
    const specCtx = spectrumCanvas.getContext('2d');
    
    // UI Elements
    const activeRouteDisplay = document.getElementById('activeRouteDisplay');
    const kpiActiveNodes = document.getElementById('kpiActiveNodes');
    const kpiPdr = document.getElementById('kpiPdr');
    const kpiLatency = document.getElementById('kpiLatency');
    const barActiveNodes = document.getElementById('barActiveNodes');
    const barPdr = document.getElementById('barPdr');
    const barLatency = document.getElementById('barLatency');
    const swarmOverallHealth = document.getElementById('swarmOverallHealth');
    const rfAnomalyBadge = document.getElementById('rfAnomalyBadge');
    const eventFeedList = document.getElementById('eventFeedList');
    const nodeTooltip = document.getElementById('nodeTooltip');
    const c2ConnectionStatus = document.getElementById('c2ConnectionStatus');

    // Buttons
    const btnFailRelay = document.getElementById('btnFailRelay');
    const btnDegradeLink = document.getElementById('btnDegradeLink');
    const btnTriggerAnomaly = document.getElementById('btnTriggerAnomaly');
    const btnResetSwarm = document.getElementById('btnResetSwarm');
    const btnManualRefresh = document.getElementById('btnManualRefresh');

    let currentStates = {};
    let activeRoute = [];
    let currentPsd = [1.2, 1.4, 1.1, 1.3, 1.5, 1.2, 1.4, 1.3, 1.1, 1.2];
    let psdBaseline = new Array(10).fill(1.2);
    let hoveredNode = null;
    let animOffset = 0;

    // Resize canvas to parent
    function resizeCanvases() {
        const rect = topologyCanvas.parentElement.getBoundingClientRect();
        topologyCanvas.width = rect.width;
        topologyCanvas.height = rect.height;

        const specRect = spectrumCanvas.parentElement.getBoundingClientRect();
        spectrumCanvas.width = specRect.width;
        spectrumCanvas.height = specRect.height;
    }
    window.addEventListener('resize', resizeCanvases);
    resizeCanvases();

    // Event Feed Logger
    function addFeedEvent(tag, message, type = 'info') {
        const item = document.createElement('div');
        item.className = `feed-item ${type}`;
        
        const now = new Date();
        const timeStr = now.toTimeString().split(' ')[0] + '.' + Math.floor(now.getMilliseconds() / 100);
        
        item.innerHTML = `
            <span class="feed-time">${timeStr}</span>
            <span class="feed-tag">[${tag.toUpperCase()}]</span>
            <span class="feed-msg">${message}</span>
        `;
        
        eventFeedList.prepend(item);
        if (eventFeedList.children.length > 25) {
            eventFeedList.removeChild(eventFeedList.lastChild);
        }
    }

    // Initial log entries
    addFeedEvent('SYSTEM', 'AeroLink Swarm Intelligence C2 Online.', 'info');
    addFeedEvent('MISSION', 'Disaster Response Comm Coverage active (Target PDR > 90%).', 'success');

    // Coordinate mapping from simulation 1000x1000m to Canvas Width x Height
    function toCanvasCoords(pos) {
        const margin = 50;
        const xRange = topologyCanvas.width - margin * 2;
        const yRange = topologyCanvas.height - margin * 2;
        
        const cx = margin + (pos[0] / 1000.0) * xRange;
        const cy = margin + (pos[1] / 1000.0) * yRange;
        return { x: cx, y: cy };
    }

    // Draw Radar & Tactical Grid
    function drawTacticalGrid() {
        const w = topologyCanvas.width;
        const h = topologyCanvas.height;

        // Subtle Grid
        ctx.strokeStyle = 'rgba(0, 240, 255, 0.04)';
        ctx.lineWidth = 1;
        const step = 40;
        for (let x = 0; x < w; x += step) {
            ctx.beginPath();
            ctx.moveTo(x, 0);
            ctx.lineTo(x, h);
            ctx.stroke();
        }
        for (let y = 0; y < h; y += step) {
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(w, y);
            ctx.stroke();
        }

        // Concentric Radar Rings around Gateway or Center
        const centerX = w * 0.35;
        const centerY = h * 0.5;
        ctx.strokeStyle = 'rgba(0, 240, 255, 0.06)';
        for (let r = 80; r < Math.max(w, h); r += 80) {
            ctx.beginPath();
            ctx.arc(centerX, centerY, r, 0, Math.PI * 2);
            ctx.stroke();
        }
    }

    // Draw Dynamic Mesh Links
    function drawMeshLinks() {
        const drawnPairs = new Set();

        // 1. Draw standard neighbor links
        for (const [nodeId, node] of Object.entries(currentStates)) {
            if (node.health === 'Offline') continue;
            const p1 = toCanvasCoords(node.position);

            for (const neighborId of (node.neighbors || [])) {
                const neighbor = currentStates[neighborId];
                if (!neighbor || neighbor.health === 'Offline') continue;

                const pairKey = [nodeId, neighborId].sort().join('-');
                if (drawnPairs.has(pairKey)) continue;
                drawnPairs.add(pairKey);

                const p2 = toCanvasCoords(neighbor.position);

                ctx.beginPath();
                ctx.moveTo(p1.x, p1.y);
                ctx.lineTo(p2.x, p2.y);

                // Style based on quality
                if (node.link_quality < 0.4 || neighbor.link_quality < 0.4) {
                    ctx.strokeStyle = 'rgba(255, 183, 0, 0.45)'; // Degraded
                    ctx.lineWidth = 1.5;
                    ctx.setLineDash([4, 4]);
                } else {
                    ctx.strokeStyle = 'rgba(0, 240, 255, 0.25)'; // Healthy
                    ctx.lineWidth = 1.2;
                    ctx.setLineDash([]);
                }
                ctx.stroke();
                ctx.setLineDash([]);
            }
        }

        // 2. Highlight Active Route (Gold Neon Flow)
        if (activeRoute && activeRoute.length > 1) {
            for (let i = 0; i < activeRoute.length - 1; i++) {
                const n1 = currentStates[activeRoute[i]];
                const n2 = currentStates[activeRoute[i + 1]];
                if (!n1 || !n2 || n1.health === 'Offline' || n2.health === 'Offline') continue;

                const p1 = toCanvasCoords(n1.position);
                const p2 = toCanvasCoords(n2.position);

                // Glow backing
                ctx.beginPath();
                ctx.moveTo(p1.x, p1.y);
                ctx.lineTo(p2.x, p2.y);
                ctx.strokeStyle = 'rgba(255, 208, 0, 0.25)';
                ctx.lineWidth = 6;
                ctx.stroke();

                // Core animated route line
                ctx.beginPath();
                ctx.moveTo(p1.x, p1.y);
                ctx.lineTo(p2.x, p2.y);
                ctx.strokeStyle = '#ffd000';
                ctx.lineWidth = 2.5;
                ctx.setLineDash([8, 6]);
                ctx.lineDashOffset = -animOffset;
                ctx.stroke();
                ctx.setLineDash([]);
            }
        }
    }

    // Draw UAV Nodes
    function drawNodes() {
        for (const [nodeId, node] of Object.entries(currentStates)) {
            const p = toCanvasCoords(node.position);
            const isHovered = hoveredNode && hoveredNode.node_id === nodeId;

            // Palette based on Role and Health
            let color = '#00f0ff'; // Relay
            let glow = 'rgba(0, 240, 255, 0.5)';

            if (node.health === 'Offline') {
                color = '#ff3366';
                glow = 'rgba(255, 51, 102, 0.4)';
            } else if (node.health === 'Degraded' || node.connectivity_risk > 0.6) {
                color = '#ffb700';
                glow = 'rgba(255, 183, 0, 0.5)';
            } else if (node.role === 'Gateway') {
                color = '#00ff9d';
                glow = 'rgba(0, 255, 157, 0.6)';
            } else if (node.role === 'Worker') {
                color = '#cbd5e1';
                glow = 'rgba(203, 213, 225, 0.3)';
            }

            // Radar pulse ring for Gateway & Relays
            if (node.health !== 'Offline' && (node.role === 'Gateway' || node.role === 'Relay')) {
                const pulseR = 14 + (Math.sin(animOffset * 0.1) * 3);
                ctx.beginPath();
                ctx.arc(p.x, p.y, pulseR, 0, Math.PI * 2);
                ctx.strokeStyle = glow;
                ctx.lineWidth = 1;
                ctx.stroke();
            }

            // Node Core Glyph (Hexagon / Diamond)
            ctx.save();
            ctx.translate(p.x, p.y);
            ctx.shadowColor = glow;
            ctx.shadowBlur = isHovered ? 18 : 10;

            ctx.fillStyle = color;
            ctx.beginPath();
            if (node.role === 'Gateway') {
                // Square
                ctx.rect(-7, -7, 14, 14);
            } else if (node.role === 'Relay') {
                // Diamond
                ctx.moveTo(0, -9);
                ctx.lineTo(8, 0);
                ctx.lineTo(0, 9);
                ctx.lineTo(-8, 0);
                ctx.closePath();
            } else {
                // Circle
                ctx.arc(0, 0, 6, 0, Math.PI * 2);
            }
            ctx.fill();

            // Inner dark dot
            ctx.fillStyle = '#060a12';
            ctx.beginPath();
            ctx.arc(0, 0, 2.5, 0, Math.PI * 2);
            ctx.fill();

            ctx.restore();

            // Node Labels
            ctx.font = '600 11px "JetBrains Mono", monospace';
            ctx.fillStyle = color;
            ctx.textAlign = 'center';
            ctx.fillText(node.node_id, p.x, p.y - 13);

            ctx.font = '500 9px "Outfit", sans-serif';
            ctx.fillStyle = '#94a3b8';
            ctx.fillText(node.role.toUpperCase(), p.x, p.y + 18);

            // Battery mini indicator below node
            if (node.health !== 'Offline') {
                const batW = 20;
                const batH = 2.5;
                ctx.fillStyle = 'rgba(255,255,255,0.15)';
                ctx.fillRect(p.x - batW / 2, p.y + 22, batW, batH);
                ctx.fillStyle = node.battery > 30 ? '#00ff9d' : '#ff3366';
                ctx.fillRect(p.x - batW / 2, p.y + 22, (node.battery / 100) * batW, batH);
            }
        }
    }

    // Render RF Spectrum & EWMA Baseline
    function drawSpectrum() {
        const w = spectrumCanvas.width;
        const h = spectrumCanvas.height;
        specCtx.clearRect(0, 0, w, h);

        if (!currentPsd || currentPsd.length === 0) return;

        const barCount = currentPsd.length;
        const barWidth = (w - (barCount * 4)) / barCount;
        const maxVal = 25.0; // Dynamic scale max

        // 1. Draw Instantaneous PSD Bars
        for (let i = 0; i < barCount; i++) {
            const val = currentPsd[i];
            const barH = Math.min(h, (val / maxVal) * (h - 15));
            const x = 4 + i * (barWidth + 4);
            const y = h - barH - 5;

            // Gradient for bar
            const grad = specCtx.createLinearGradient(0, y, 0, h);
            if (val > 10.0) {
                grad.addColorStop(0, '#ff3366');
                grad.addColorStop(1, 'rgba(255, 51, 102, 0.2)');
            } else {
                grad.addColorStop(0, '#00f0ff');
                grad.addColorStop(1, 'rgba(0, 240, 255, 0.15)');
            }

            specCtx.fillStyle = grad;
            specCtx.fillRect(x, y, barWidth, barH);
        }

        // 2. Draw EWMA Baseline Curve
        if (psdBaseline && psdBaseline.length === barCount) {
            specCtx.beginPath();
            specCtx.strokeStyle = '#00ff9d';
            specCtx.lineWidth = 2;
            for (let i = 0; i < barCount; i++) {
                const bVal = psdBaseline[i];
                const by = h - Math.min(h, (bVal / maxVal) * (h - 15)) - 5;
                const bx = 4 + i * (barWidth + 4) + barWidth / 2;
                if (i === 0) specCtx.moveTo(bx, by);
                else specCtx.lineTo(bx, by);
            }
            specCtx.stroke();
        }

        // 3. Draw Threshold Line
        const thY = h - (10.0 / maxVal) * (h - 15) - 5;
        specCtx.beginPath();
        specCtx.strokeStyle = 'rgba(255, 51, 102, 0.6)';
        specCtx.lineWidth = 1;
        specCtx.setLineDash([4, 4]);
        specCtx.moveTo(0, thY);
        specCtx.lineTo(w, thY);
        specCtx.stroke();
        specCtx.setLineDash([]);
    }

    // Animation Render Loop
    function renderLoop() {
        animOffset += 0.8;
        ctx.clearRect(0, 0, topologyCanvas.width, topologyCanvas.height);

        drawTacticalGrid();
        drawMeshLinks();
        drawNodes();
        drawSpectrum();

        requestAnimationFrame(renderLoop);
    }
    requestAnimationFrame(renderLoop);

    // Node Hover Detection
    topologyCanvas.addEventListener('mousemove', (e) => {
        const rect = topologyCanvas.getBoundingClientRect();
        const mx = e.clientX - rect.left;
        const my = e.clientY - rect.top;

        hoveredNode = null;
        for (const node of Object.values(currentStates)) {
            const p = toCanvasCoords(node.position);
            const dist = Math.hypot(p.x - mx, p.y - my);
            if (dist < 18) {
                hoveredNode = node;
                nodeTooltip.style.display = 'block';
                nodeTooltip.style.left = `${mx + 15}px`;
                nodeTooltip.style.top = `${my - 15}px`;
                nodeTooltip.innerHTML = `
                    <div style="color: var(--accent-cyan); font-weight: 700; margin-bottom: 3px;">${node.node_id} [${node.role}]</div>
                    <div>Health: <span style="color:${node.health === 'Healthy' ? '#00ff9d' : '#ff3366'}">${node.health}</span></div>
                    <div>Battery: <strong>${node.battery.toFixed(1)}%</strong></div>
                    <div>Link Quality: ${(node.link_quality * 100).toFixed(0)}% | RSSI: ${node.rssi.toFixed(1)} dBm</div>
                    <div>Latency: ${node.latency.toFixed(1)} ms | Loss: ${(node.packet_loss * 100).toFixed(1)}%</div>
                    <div>Failure Risk: <strong style="color:${node.connectivity_risk > 0.5 ? '#ff3366' : '#00ff9d'}">${(node.connectivity_risk * 100).toFixed(0)}%</strong></div>
                `;
                break;
            }
        }

        if (!hoveredNode) {
            nodeTooltip.style.display = 'none';
        }
    });

    topologyCanvas.addEventListener('mouseleave', () => {
        hoveredNode = null;
        nodeTooltip.style.display = 'none';
    });

    // Main Telemetry Polling Routine
    let lastActionCount = 0;
    async function fetchTelemetry() {
        try {
            const res = await fetch('/api/swarm');
            if (!res.ok) throw new Error(`HTTP ${res.status}`);

            const data = await res.json();
            currentStates = data.states || {};
            activeRoute = data.active_route || [];
            currentPsd = data.current_psd || currentPsd;
            psdBaseline = data.psd_baseline || psdBaseline;

            // Route display
            if (activeRoute.length > 0) {
                activeRouteDisplay.textContent = 'ROUTE: ' + activeRoute.join(' ➔ ');
            } else {
                activeRouteDisplay.textContent = 'ROUTE: RECOMPUTING DYNAMIC PATH...';
            }

            // Health & Metrics — derived from authoritative backend data
            const activeCnt = data.active_count || Object.values(currentStates).filter(n => n.health !== 'Offline').length;
            const totalCnt = data.total_count || Object.keys(currentStates).length;
            kpiActiveNodes.textContent = activeCnt;
            barActiveNodes.style.width = `${(activeCnt / Math.max(1, totalCnt)) * 100}%`;

            const pdrPct = (data.mission_pdr * 100).toFixed(1);
            kpiPdr.textContent = `${pdrPct}%`;
            barPdr.style.width = `${Math.min(100, pdrPct)}%`;

            kpiLatency.textContent = data.avg_latency != null ? data.avg_latency.toFixed(1) : '0.0';
            const latPct = Math.min(100, (data.avg_latency || 0) / 5.0);
            barLatency.style.width = `${latPct}%`;

            // Overall Status — from backend mission_status
            const missionStatus = data.mission_status || 'Unknown';
            if (missionStatus === 'Degraded') {
                swarmOverallHealth.textContent = 'DEGRADED';
                swarmOverallHealth.className = 'badge-status warning';
            } else if (missionStatus === 'Recovering') {
                swarmOverallHealth.textContent = 'RECOVERING';
                swarmOverallHealth.className = 'badge-status warning';
            } else if (activeCnt < totalCnt) {
                swarmOverallHealth.textContent = 'HEALING';
                swarmOverallHealth.className = 'badge-status warning';
            } else {
                swarmOverallHealth.textContent = 'HEALTHY';
                swarmOverallHealth.className = 'badge-status healthy';
            }

            // Topology status
            const kpiTopology = document.getElementById('kpiTopology');
            const barTopology = document.getElementById('barTopology');
            if (kpiTopology) {
                if (activeRoute.length > 1) {
                    kpiTopology.textContent = 'CONNECTED';
                    if (barTopology) barTopology.style.width = '100%';
                } else {
                    kpiTopology.textContent = 'PARTITIONED';
                    if (barTopology) barTopology.style.width = '20%';
                }
            }

            // RF Status Badge
            const isAnomaly = currentPsd.some(v => v > 10.0);
            if (isAnomaly) {
                rfAnomalyBadge.textContent = 'ALERT: SPECTRAL ANOMALY';
                rfAnomalyBadge.className = 'rf-badge-status anomaly';
            } else {
                rfAnomalyBadge.textContent = 'BASELINE NORMAL';
                rfAnomalyBadge.className = 'rf-badge-status';
            }

            // Process Actions from Engine — only show new actions
            if (data.actions && data.actions.length > 0) {
                data.actions.forEach(act => {
                    if (act.type === 'WARNING') {
                        addFeedEvent('PREDICT', act.message, 'warning');
                    } else if (act.type === 'ACTION') {
                        addFeedEvent('SELECT', act.message, 'info');
                    } else if (act.type === 'RECONFIGURE') {
                        addFeedEvent('ROLE', `${act.old_relay} demoted ➔ ${act.new_relay} promoted to RELAY`, 'success');
                        addFeedEvent('ROUTE', 'Dynamic mesh route recomputation triggered', 'info');
                    }
                });
            }

            // Mission status in header
            const headerMissionStatus = document.getElementById('headerMissionStatus');
            if (headerMissionStatus) {
                headerMissionStatus.textContent = missionStatus.toUpperCase();
            }

            c2ConnectionStatus.textContent = 'CONNECTED (0.8s)';
            c2ConnectionStatus.style.color = 'var(--accent-cyan)';
        } catch (err) {
            c2ConnectionStatus.textContent = 'RECONNECTING...';
            c2ConnectionStatus.style.color = 'var(--accent-crimson)';
        }
    }

    setInterval(fetchTelemetry, 800);
    fetchTelemetry();

    btnManualRefresh.addEventListener('click', () => {
        fetchTelemetry();
        addFeedEvent('TELEMETRY', 'Manual state sync forced.', 'info');
    });

    // =========================================================================
    // Deterministic Failure Injection Triggers
    // =========================================================================
    btnFailRelay.addEventListener('click', async () => {
        addFeedEvent('TRIGGER', 'Injecting hard failure on Primary Relay (UAV-2)...', 'danger');
        try {
            await fetch('/api/c2/fail_node', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ node_id: 'UAV-2', severity: 1.0 })
            });
            fetchTelemetry();
        } catch (e) {
            addFeedEvent('ERROR', 'Failed to dispatch failure command.', 'danger');
        }
    });

    btnDegradeLink.addEventListener('click', async () => {
        addFeedEvent('TRIGGER', 'Placing RF interference over Gateway link (UAV-1)...', 'warning');
        try {
            await fetch('/api/c2/degrade_link', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ node_id: 'UAV-1', severity: 1.5 })
            });
            fetchTelemetry();
        } catch (e) {
            addFeedEvent('ERROR', 'Failed to dispatch degradation command.', 'danger');
        }
    });

    btnTriggerAnomaly.addEventListener('click', async () => {
        addFeedEvent('TRIGGER', 'Injecting High-Power Spectral Jamming Spike...', 'danger');
        try {
            await fetch('/api/c2/degrade_link', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ node_id: 'UAV-2', severity: 2.0 })
            });
            fetchTelemetry();
        } catch (e) {
            addFeedEvent('ERROR', 'Spectral trigger failed.', 'danger');
        }
    });

    btnResetSwarm.addEventListener('click', async () => {
        addFeedEvent('RESET', 'Resetting swarm formation to nominal Disaster Response mesh.', 'success');
        try {
            await fetch('/api/c2/reset', { method: 'POST' });
            fetchTelemetry();
        } catch (e) {
            addFeedEvent('ERROR', 'Reset failed.', 'danger');
        }
    });
});
