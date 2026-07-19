/**
 * XAUUSD Signal Dashboard - JavaScript
 * Handles real-time data fetching, UI updates, countdown timers,
 * and auto-refresh functionality.
 */

(function() {
    'use strict';

    // =============================================================================
    // CONFIGURATION
    // =============================================================================

    const CONFIG = {
        refreshInterval: 60000,      // Auto-refresh every 60 seconds
        countdownInterval: 1000,     // Countdown update every 1 second
        watOffset: 1,                // WAT is UTC+1
        sessionStart: { hour: 14, minute: 30 },  // 2:30 PM WAT
        sessionEnd: { hour: 20, minute: 45 }     // 8:45 PM WAT
    };

    // =============================================================================
    // DOM ELEMENTS
    // =============================================================================

    const elements = {
        // Header
        lastUpdated: document.getElementById('lastUpdated'),

        // Session
        sessionBar: document.getElementById('sessionBar'),
        statusBadge: document.getElementById('statusBadge'),
        countdown: document.getElementById('countdown'),

        // Price
        currentPrice: document.getElementById('currentPrice'),

        // Signal Card
        signalCard: document.getElementById('signalCard'),
        signalBadge: document.getElementById('signalBadge'),
        signalEmpty: document.getElementById('signalEmpty'),
        signalDetails: document.getElementById('signalDetails'),
        detailEntry: document.getElementById('detailEntry'),
        detailSL: document.getElementById('detailSL'),
        detailTP: document.getElementById('detailTP'),
        detailDate: document.getElementById('detailDate'),
        detailTime: document.getElementById('detailTime'),

        // Opening Range
        orHigh: document.getElementById('orHigh'),
        orLow: document.getElementById('orLow'),
        orStatus: document.getElementById('orStatus'),
        orBarFill: document.getElementById('orBarFill'),
        orMarkerCurrent: document.getElementById('orMarkerCurrent'),
        orLabelLow: document.getElementById('orLabelLow'),
        orLabelHigh: document.getElementById('orLabelHigh'),

        // History
        historyCount: document.getElementById('historyCount'),
        historyBody: document.getElementById('historyBody')
    };

    // =============================================================================
    // UTILITY FUNCTIONS
    // =============================================================================

    /**
     * Get current time in WAT (West Africa Time, UTC+1)
     * @returns {Date} Current WAT time
     */
    function getWATTime() {
        const now = new Date();
        const utc = now.getTime() + (now.getTimezoneOffset() * 60000);
        return new Date(utc + (CONFIG.watOffset * 3600000));
    }

    /**
     * Format a number as price with 2 decimal places
     * @param {number} price - Price value
     * @returns {string} Formatted price
     */
    function formatPrice(price) {
        if (price === null || price === undefined || isNaN(price)) {
            return '--';
        }
        return price.toFixed(2);
    }

    /**
     * Format date for display
     * @param {string} dateStr - Date string
     * @returns {string} Formatted date
     */
    function formatDate(dateStr) {
        if (!dateStr) return '--';
        return dateStr;
    }

    /**
     * Check if trading session is currently active
     * @returns {boolean} True if session is active
     */
    function isSessionActive() {
        const wat = getWATTime();
        const currentMinutes = wat.getHours() * 60 + wat.getMinutes();
        const startMinutes = CONFIG.sessionStart.hour * 60 + CONFIG.sessionStart.minute;
        const endMinutes = CONFIG.sessionEnd.hour * 60 + CONFIG.sessionEnd.minute;

        return currentMinutes >= startMinutes && currentMinutes <= endMinutes;
    }

    /**
     * Check if today is weekend (Saturday or Sunday)
     * @returns {boolean} True if weekend
     */
    function isWeekend() {
        const wat = getWATTime();
        const day = wat.getDay();
        return day === 0 || day === 6; // Sunday = 0, Saturday = 6
    }

    /**
     * Get session countdown string
     * @returns {string} Countdown text
     */
    function getSessionCountdown() {
        const wat = getWATTime();
        const currentMinutes = wat.getHours() * 60 + wat.getMinutes();
        const endMinutes = CONFIG.sessionEnd.hour * 60 + CONFIG.sessionEnd.minute;
        const startMinutes = CONFIG.sessionStart.hour * 60 + CONFIG.sessionStart.minute;

        // Before session starts
        if (currentMinutes < startMinutes) {
            const diff = startMinutes - currentMinutes;
            const hours = Math.floor(diff / 60);
            const minutes = diff % 60;
            return `Starts in ${hours}h ${minutes}m`;
        }

        // During session
        if (currentMinutes >= startMinutes && currentMinutes <= endMinutes) {
            const diff = endMinutes - currentMinutes;
            const hours = Math.floor(diff / 60);
            const minutes = diff % 60;
            return `${hours}h ${minutes}m remaining`;
        }

        // After session
        return 'Session ended';
    }

    // =============================================================================
    // UI UPDATE FUNCTIONS
    // =============================================================================

    /**
     * Update the last updated timestamp
     */
    function updateLastUpdated() {
        const wat = getWATTime();
        const timeStr = wat.toLocaleTimeString('en-US', { 
            hour: '2-digit', 
            minute: '2-digit',
            second: '2-digit',
            hour12: true 
        });
        elements.lastUpdated.textContent = `Updated: ${timeStr} WAT`;
    }

    /**
     * Update session status badge and countdown
     */
    function updateSessionStatus() {
        const active = isSessionActive();
        const weekend = isWeekend();

        if (weekend) {
            elements.statusBadge.textContent = 'Weekend';
            elements.statusBadge.className = 'status-badge closed';
            elements.countdown.textContent = 'Markets closed';
            return;
        }

        if (active) {
            elements.statusBadge.textContent = 'Active';
            elements.statusBadge.className = 'status-badge active';
        } else {
            elements.statusBadge.textContent = 'Inactive';
            elements.statusBadge.className = 'status-badge inactive';
        }

        elements.countdown.textContent = getSessionCountdown();
    }

    /**
     * Update current price display
     * @param {number} price - Current price
     */
    function updatePrice(price) {
        elements.currentPrice.textContent = formatPrice(price);
    }

    /**
     * Update signal card display
     * @param {Object} signal - Signal data object
     * @param {Object} currentState - Current state object
     */
    function updateSignalCard(signal, currentState) {
        // Reset card styles
        elements.signalCard.classList.remove('has-buy', 'has-sell');

        // Check if there's an active signal
        const hasSignal = signal && signal.type;

        if (!hasSignal) {
            // Show empty state
            elements.signalEmpty.style.display = 'flex';
            elements.signalDetails.style.display = 'none';
            elements.signalBadge.textContent = 'WAITING';
            elements.signalBadge.className = 'signal-badge waiting';
            return;
        }

        // Hide empty state, show details
        elements.signalEmpty.style.display = 'none';
        elements.signalDetails.style.display = 'block';

        // Update badge
        const signalType = signal.type;
        elements.signalBadge.textContent = signalType;
        elements.signalBadge.className = `signal-badge ${signalType.toLowerCase()}`;

        // Apply card glow
        if (signalType === 'BUY') {
            elements.signalCard.classList.add('has-buy');
        } else if (signalType === 'SELL') {
            elements.signalCard.classList.add('has-sell');
        }

        // Update detail values
        elements.detailEntry.textContent = formatPrice(signal.entry);
        elements.detailSL.textContent = formatPrice(signal.stop_loss);
        elements.detailTP.textContent = formatPrice(signal.take_profit);
        elements.detailDate.textContent = formatDate(signal.date);
        elements.detailTime.textContent = signal.time || '--';
    }

    /**
     * Update Opening Range display
     * @param {Object} orData - Opening range data
     * @param {number} currentPrice - Current market price
     */
    function updateOpeningRange(orData, currentPrice) {
        const high = orData ? orData.high : null;
        const low = orData ? orData.low : null;
        const formed = orData ? orData.formed : false;

        elements.orHigh.textContent = formatPrice(high);
        elements.orLow.textContent = formatPrice(low);
        elements.orLabelHigh.textContent = formatPrice(high);
        elements.orLabelLow.textContent = formatPrice(low);

        if (!formed || high === null || low === null) {
            elements.orStatus.textContent = 'Waiting for Opening Range to form (2:30 - 2:45 PM WAT)...';
            elements.orBarFill.style.width = '0%';
            elements.orMarkerCurrent.style.display = 'none';
            return;
        }

        elements.orStatus.textContent = `Opening Range formed. Monitoring for breakout...`;
        elements.orBarFill.style.width = '100%';

        // Update marker position based on current price relative to OR
        if (currentPrice !== null && currentPrice !== undefined) {
            const range = high - low;
            if (range > 0) {
                const position = ((currentPrice - low) / range) * 100;
                const clampedPosition = Math.max(0, Math.min(100, position));
                elements.orMarkerCurrent.style.display = 'block';
                elements.orMarkerCurrent.style.left = `${clampedPosition}%`;
            }
        } else {
            elements.orMarkerCurrent.style.display = 'none';
        }
    }

    /**
     * Update signal history table
     * @param {Array} history - Array of signal history objects
     */
    function updateHistory(history) {
        const signals = history || [];

        // Update count
        elements.historyCount.textContent = `${signals.length} signal${signals.length !== 1 ? 's' : ''}`;

        // Clear table
        elements.historyBody.innerHTML = '';

        if (signals.length === 0) {
            elements.historyBody.innerHTML = `
                <tr class="empty-row">
                    <td colspan="6">No signals generated yet</td>
                </tr>
            `;
            return;
        }

        // Populate table with signals (newest first)
        signals.forEach(signal => {
            const row = document.createElement('tr');
            const typeClass = signal.type ? signal.type.toLowerCase() : '';

            row.innerHTML = `
                <td><span class="signal-type ${typeClass}">${signal.type || '--'}</span></td>
                <td>${formatPrice(signal.entry)}</td>
                <td>${formatPrice(signal.stop_loss)}</td>
                <td>${formatPrice(signal.take_profit)}</td>
                <td>${signal.date || '--'}</td>
                <td>${signal.time || '--'}</td>
            `;

            elements.historyBody.appendChild(row);
        });
    }

    // =============================================================================
    // DATA FETCHING
    // =============================================================================

    /**
     * Fetch signal data from signal.json
     * @returns {Promise<Object>} Signal data object
     */
    async function fetchSignalData() {
        try {
            // Add cache-busting query parameter to prevent caching
            const cacheBuster = `?_=${Date.now()}`;
            const response = await fetch('signal.json' + cacheBuster, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                    'Cache-Control': 'no-cache'
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Error fetching signal data:', error);
            return null;
        }
    }

    /**
     * Main update function - fetches data and updates all UI elements
     */
    async function updateDashboard() {
        console.log('Updating dashboard...');

        const data = await fetchSignalData();

        if (!data) {
            console.warn('No data received, skipping update');
            return;
        }

        // Update price
        const currentPrice = data.market_data ? data.market_data.current_price : null;
        updatePrice(currentPrice);

        // Update signal card
        const latestSignal = data.latest_signal;
        const currentState = data.current_state;
        updateSignalCard(latestSignal, currentState);

        // Update opening range
        const openingRange = data.opening_range;
        updateOpeningRange(openingRange, currentPrice);

        // Update history
        const history = data.signal_history;
        updateHistory(history);

        // Update timestamps
        updateLastUpdated();
        updateSessionStatus();

        console.log('Dashboard updated successfully');
    }

    // =============================================================================
    // INITIALIZATION
    // =============================================================================

    /**
     * Initialize the dashboard
     */
    function init() {
        console.log('Initializing XAUUSD Signal Dashboard...');

        // Initial update
        updateDashboard();

        // Set up auto-refresh
        setInterval(updateDashboard, CONFIG.refreshInterval);

        // Set up countdown timer
        setInterval(updateSessionStatus, CONFIG.countdownInterval);

        // Update countdown immediately
        updateSessionStatus();

        console.log('Dashboard initialized. Auto-refresh every 60 seconds.');
    }

    // Start when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
