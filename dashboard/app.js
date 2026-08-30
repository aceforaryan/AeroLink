document.addEventListener('DOMContentLoaded', () => {
    const feedList = document.getElementById('feedList');
    const btnFailNode = document.getElementById('btnFailNode');
    const btnDegradeLink = document.getElementById('btnDegradeLink');
    const btnAnomaly = document.getElementById('btnAnomaly');

    // Utility to add events to the feed
    function addEvent(message, type = 'info') {
        const item = document.createElement('div');
        item.className = `feed-item ${type}`;
        
        const time = new Date().toLocaleTimeString([], {hour12: false});
        item.innerHTML = `<strong>[${time}]</strong> ${message}`;
        
        feedList.prepend(item);
        
        // Keep feed bounded
        if (feedList.children.length > 8) {
            feedList.removeChild(feedList.lastChild);
        }
    }

    // Mock interactive triggers for the judging demonstration
    btnFailNode.addEventListener('click', () => {
        addEvent('CRITICAL: Node UAV-2 offline.', 'danger');
        setTimeout(() => {
            addEvent('AUTONOMY: Route recomputed. Swarm healing...', 'warning');
        }, 800);
        setTimeout(() => {
            addEvent('SUCCESS: Network recovered in 1.2s.', 'success');
        }, 2000);
    });

    btnDegradeLink.addEventListener('click', () => {
        addEvent('WARNING: Link quality degrading on GATEWAY link.', 'warning');
        setTimeout(() => {
            addEvent('PREDICTION: Relay candidate scored. Transition pending.', 'info');
        }, 1000);
    });

    btnAnomaly.addEventListener('click', () => {
        addEvent('RF ALERT: Spectral anomaly detected. Adjusting baseline.', 'danger');
    });
    
    // In a full implementation, this script would connect to the backend 
    // WebSocket or poll the /api/swarm REST endpoint to dynamically update 
    // the topology map and metrics.
});
