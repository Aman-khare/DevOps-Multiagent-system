/**
 * DevOps AI Architect — Dashboard WebSocket Client
 * Handles real-time updates from the agent pipeline.
 */

class DashboardClient {
    constructor() {
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.reconnectDelay = 2000;
        this.toastContainer = null;
        this.liveFeedBody = null;

        this.init();
    }

    init() {
        // Create toast container
        this.toastContainer = document.getElementById('toast-container');
        if (!this.toastContainer) {
            this.toastContainer = document.createElement('div');
            this.toastContainer.id = 'toast-container';
            this.toastContainer.className = 'toast-container';
            document.body.appendChild(this.toastContainer);
        }

        // Get live feed element
        this.liveFeedBody = document.getElementById('live-feed-body');

        // Connect WebSocket
        this.connect();

        // Heartbeat interval
        setInterval(() => {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send('ping');
            }
        }, 30000);
    }

    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/incidents`;

        try {
            this.ws = new WebSocket(wsUrl);

            this.ws.onopen = () => {
                console.log('🟢 WebSocket connected');
                this.reconnectAttempts = 0;
                this.updateConnectionStatus(true);
            };

            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleMessage(data);
                } catch (e) {
                    console.warn('Failed to parse WebSocket message:', e);
                }
            };

            this.ws.onclose = () => {
                console.log('🔴 WebSocket disconnected');
                this.updateConnectionStatus(false);
                this.attemptReconnect();
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };

        } catch (e) {
            console.error('Failed to create WebSocket:', e);
            this.attemptReconnect();
        }
    }

    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = this.reconnectDelay * this.reconnectAttempts;
            console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})...`);
            setTimeout(() => this.connect(), delay);
        }
    }

    handleMessage(data) {
        switch (data.type) {
            case 'incident_update':
                this.handleIncidentUpdate(data);
                break;
            case 'agent_update':
                this.handleAgentUpdate(data);
                break;
            case 'pong':
                break;
            default:
                console.log('Unknown message type:', data.type);
        }
    }

    handleIncidentUpdate(data) {
        const { incident_id, status } = data;

        // Show toast notification
        const statusEmoji = {
            detected: '🚨',
            diagnosing: '🔍',
            remediating: '🔧',
            verifying: '✅',
            resolved: '🎉',
            failed: '❌',
        };

        this.showToast(
            `${statusEmoji[status] || '📋'} Incident ${incident_id}`,
            `Status changed to: ${status.toUpperCase()}`
        );

        // Update existing incident card if on dashboard
        this.updateIncidentCard(incident_id, status);

        // If a new incident is detected, add it to the grid
        if (status === 'detected' && data.data) {
            this.addIncidentCard(data.data);
        }

        // Update stat counters
        this.updateStats();
    }

    handleAgentUpdate(data) {
        const { incident_id, agent_name, action, status, details, timestamp } = data;

        // Add entry to live feed
        if (this.liveFeedBody) {
            const entry = document.createElement('div');
            entry.className = 'live-feed__entry';

            const time = new Date(timestamp).toLocaleTimeString();
            entry.innerHTML = `
                <span class="live-feed__timestamp">[${time}]</span>
                <span class="live-feed__agent-tag">${agent_name}</span>
                <span class="live-feed__action"> ${action}</span>
                ${details ? `<br><span style="color: var(--text-muted); padding-left: 1rem;">${this.escapeHtml(details.substring(0, 150))}</span>` : ''}
            `;

            this.liveFeedBody.appendChild(entry);
            this.liveFeedBody.scrollTop = this.liveFeedBody.scrollHeight;

            // Limit entries to prevent DOM bloat
            while (this.liveFeedBody.children.length > 100) {
                this.liveFeedBody.removeChild(this.liveFeedBody.firstChild);
            }
        }
    }

    updateIncidentCard(incidentId, status) {
        const card = document.querySelector(`[data-incident-id="${incidentId}"]`);
        if (!card) return;

        // Update status badge
        const badge = card.querySelector('.status-badge');
        if (badge) {
            badge.className = `status-badge status-badge--${status}`;
            badge.innerHTML = `<span class="status-badge__dot"></span>${status}`;
        }

        // Update card border style
        card.classList.remove('incident-card--active', 'incident-card--resolved', 'incident-card--failed');
        if (['diagnosing', 'remediating', 'verifying'].includes(status)) {
            card.classList.add('incident-card--active');
        } else if (status === 'resolved') {
            card.classList.add('incident-card--resolved');
        } else if (status === 'failed') {
            card.classList.add('incident-card--failed');
        }
    }

    addIncidentCard(data) {
        const grid = document.getElementById('incidents-grid');
        if (!grid) return;

        // Remove empty state if present
        const emptyState = grid.querySelector('.empty-state');
        if (emptyState) emptyState.remove();

        const severityEmoji = {
            critical: '🔴',
            warning: '🟡',
            info: '🔵',
        };

        const card = document.createElement('a');
        card.href = `/incident/${data.id}`;
        card.className = 'incident-card incident-card--active';
        card.dataset.incidentId = data.id;

        card.innerHTML = `
            <div class="incident-card__severity incident-card__severity--${data.severity || 'warning'}">
                ${severityEmoji[data.severity] || '🟡'}
            </div>
            <div class="incident-card__body">
                <div class="incident-card__id">${data.id}</div>
                <div class="incident-card__message">${this.escapeHtml(data.message || 'New incident')}</div>
                <div class="incident-card__meta">
                    <span class="incident-card__meta-item">📦 ${data.service || 'unknown'}</span>
                    <span class="incident-card__meta-item">🕐 Just now</span>
                </div>
            </div>
            <div class="incident-card__status">
                <span class="status-badge status-badge--detected">
                    <span class="status-badge__dot"></span>detected
                </span>
            </div>
        `;

        grid.prepend(card);
    }

    updateStats() {
        // Recount from DOM (simple approach)
        const cards = document.querySelectorAll('.incident-card');
        let active = 0, resolved = 0, failed = 0;

        cards.forEach(card => {
            if (card.classList.contains('incident-card--active')) active++;
            else if (card.classList.contains('incident-card--resolved')) resolved++;
            else if (card.classList.contains('incident-card--failed')) failed++;
        });

        const activeEl = document.getElementById('stat-active');
        const resolvedEl = document.getElementById('stat-resolved');
        const failedEl = document.getElementById('stat-failed');
        const totalEl = document.getElementById('stat-total');

        if (activeEl) activeEl.textContent = active;
        if (resolvedEl) resolvedEl.textContent = resolved;
        if (failedEl) failedEl.textContent = failed;
        if (totalEl) totalEl.textContent = cards.length;
    }

    showToast(title, body) {
        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.innerHTML = `
            <div class="toast__title">${title}</div>
            <div class="toast__body">${body}</div>
        `;
        this.toastContainer.appendChild(toast);

        // Auto-remove after animation
        setTimeout(() => {
            if (toast.parentNode) toast.parentNode.removeChild(toast);
        }, 5000);
    }

    updateConnectionStatus(connected) {
        const dot = document.getElementById('ws-status-dot');
        const text = document.getElementById('ws-status-text');
        if (dot) {
            dot.style.background = connected ? 'var(--status-success)' : 'var(--status-critical)';
        }
        if (text) {
            text.textContent = connected ? 'Live' : 'Disconnected';
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    window.dashboardClient = new DashboardClient();
});
