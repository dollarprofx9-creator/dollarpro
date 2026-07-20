/**
 * DollarProFx Frontend JavaScript
 * Handles navigation, signal fetching, session countdown, FAQ, and mobile menu
 */

// =============================================================================
// CONFIGURATION
// =============================================================================

const CONFIG = {
    API_BASE_URL: window.location.origin,
    REFRESH_INTERVAL: 60000, // 1 minute
    SESSION_START_HOUR: 14,
    SESSION_START_MINUTE: 30,
    SESSION_END_HOUR: 20,
    SESSION_END_MINUTE: 45,
    TIMEZONE_OFFSET: 1 // WAT is UTC+1
};

// =============================================================================
// DOM ELEMENTS
// =============================================================================

const navbar = document.getElementById('navbar');
const mobileMenuBtn = document.getElementById('mobileMenuBtn');
const navLinks = document.getElementById('navLinks');
const tickerContent = document.getElementById('tickerContent');
const statusDot = document.getElementById('statusDot');
const statusText = document.getElementById('statusText');
const countdownValue = document.getElementById('countdownValue');
const heroGoldPrice = document.getElementById('heroGoldPrice');

// =============================================================================
// NAVIGATION
// =============================================================================

function initNavigation() {
    // Navbar scroll effect
    window.addEventListener('scroll', () => {
        if (window.scrollY > 50) {
            navbar.classList.add('scrolled');
        } else {
            navbar.classList.remove('scrolled');
        }
    });

    // Mobile menu toggle
    if (mobileMenuBtn) {
        mobileMenuBtn.addEventListener('click', () => {
            mobileMenuBtn.classList.toggle('active');
            navLinks.classList.toggle('active');
            document.body.style.overflow = navLinks.classList.contains('active') ? 'hidden' : '';
        });
    }

    // Close mobile menu on link click
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', () => {
            mobileMenuBtn.classList.remove('active');
            navLinks.classList.remove('active');
            document.body.style.overflow = '';
        });
    });

    // Active nav link highlighting
    const currentPath = window.location.pathname;
    document.querySelectorAll('.nav-link').forEach(link => {
        const href = link.getAttribute('href');
        if (href === currentPath || (currentPath === '/' && href === '/')) {
            link.classList.add('active');
        } else {
            link.classList.remove('active');
        }
    });
}

// =============================================================================
// SIGNAL FETCHING
// =============================================================================

async function fetchSignal() {
    try {
        const response = await fetch(`${CONFIG.API_BASE_URL}/api/signal`);
        if (!response.ok) throw new Error('Failed to fetch signal');
        return await response.json();
    } catch (error) {
        console.error('Error fetching signal:', error);
        return null;
    }
}

function formatPrice(price) {
    if (price === null || price === undefined) return '--';
    return price.toFixed(2);
}

function updateTicker(signal) {
    if (!tickerContent) return;

    if (!signal || signal.direction === 'WAITING') {
        tickerContent.innerHTML = `
            <span class="ticker-signal">
                <span class="ticker-direction waiting">WAITING</span>
                <span>Monitoring for confirmed breakout...</span>
            </span>
        `;
        return;
    }

    const isBuy = signal.direction === 'BUY';
    const directionClass = isBuy ? 'buy' : 'sell';
    const directionEmoji = isBuy ? '🟢' : '🔴';

    tickerContent.innerHTML = `
        <span class="ticker-signal">
            <span class="ticker-direction ${directionClass}">${directionEmoji} ${signal.direction}</span>
            <span>Entry: ${formatPrice(signal.entry)}</span>
            <span>SL: ${formatPrice(signal.stop_loss)}</span>
            <span>TP: ${formatPrice(signal.take_profit)}</span>
            <span>${signal.time || ''}</span>
        </span>
    `;
}

function updateHeroPrice(signal) {
    if (!heroGoldPrice) return;
    if (signal && signal.current_price) {
        heroGoldPrice.textContent = formatPrice(signal.current_price);
    }
}

async function refreshSignal() {
    const signal = await fetchSignal();
    updateTicker(signal);
    updateHeroPrice(signal);
}

// =============================================================================
// SESSION COUNTDOWN
// =============================================================================

function getWATDate() {
    const now = new Date();
    const utc = now.getTime() + (now.getTimezoneOffset() * 60000);
    return new Date(utc + (CONFIG.TIMEZONE_OFFSET * 3600000));
}

function isWeekend() {
    const wat = getWATDate();
    const day = wat.getDay();
    return day === 0 || day === 6; // Sunday = 0, Saturday = 6
}

function isSessionActive() {
    if (isWeekend()) return false;

    const wat = getWATDate();
    const hour = wat.getHours();
    const minute = wat.getMinutes();
    const currentTime = hour * 60 + minute;
    const startTime = CONFIG.SESSION_START_HOUR * 60 + CONFIG.SESSION_START_MINUTE;
    const endTime = CONFIG.SESSION_END_HOUR * 60 + CONFIG.SESSION_END_MINUTE;

    return currentTime >= startTime && currentTime <= endTime;
}

function getTimeUntilSessionEnd() {
    const wat = getWATDate();
    const hour = wat.getHours();
    const minute = wat.getMinutes();
    const second = wat.getSeconds();

    const currentTime = hour * 3600 + minute * 60 + second;
    const endTime = CONFIG.SESSION_END_HOUR * 3600 + CONFIG.SESSION_END_MINUTE * 60;

    return Math.max(0, endTime - currentTime);
}

function getTimeUntilSessionStart() {
    const wat = getWATDate();
    const hour = wat.getHours();
    const minute = wat.getMinutes();
    const second = wat.getSeconds();

    const currentTime = hour * 3600 + minute * 60 + second;
    const startTime = CONFIG.SESSION_START_HOUR * 3600 + CONFIG.SESSION_START_MINUTE * 60;

    if (currentTime < startTime) {
        return startTime - currentTime;
    }
    return 0;
}

function formatCountdown(seconds) {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

function updateSessionStatus() {
    if (!statusDot || !statusText || !countdownValue) return;

    if (isWeekend()) {
        statusDot.className = 'status-dot inactive';
        statusText.textContent = 'Market Closed (Weekend)';
        countdownValue.textContent = '--:--:--';
        return;
    }

    if (isSessionActive()) {
        statusDot.className = 'status-dot active';
        statusText.textContent = 'Session Active';
        const remaining = getTimeUntilSessionEnd();
        countdownValue.textContent = formatCountdown(remaining);
    } else {
        statusDot.className = 'status-dot inactive';
        statusText.textContent = 'Session Inactive';
        const untilStart = getTimeUntilSessionStart();
        if (untilStart > 0) {
            countdownValue.textContent = `Starts in ${formatCountdown(untilStart)}`;
        } else {
            countdownValue.textContent = 'Next session tomorrow';
        }
    }
}

// =============================================================================
// FAQ ACCORDION
// =============================================================================

function initFAQ() {
    const faqItems = document.querySelectorAll('.faq-item');

    faqItems.forEach(item => {
        const question = item.querySelector('.faq-question');
        if (question) {
            question.addEventListener('click', () => {
                const isActive = item.classList.contains('active');

                // Close all other items
                faqItems.forEach(otherItem => {
                    otherItem.classList.remove('active');
                });

                // Toggle current item
                if (!isActive) {
                    item.classList.add('active');
                }
            });
        }
    });
}

// =============================================================================
// SCROLL ANIMATIONS
// =============================================================================

function initScrollAnimations() {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in-up');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    // Observe cards and sections
    document.querySelectorAll('.glass-card, .step-card, .faq-item').forEach(el => {
        el.style.opacity = '0';
        observer.observe(el);
    });
}

// =============================================================================
// SMOOTH SCROLL FOR ANCHOR LINKS
// =============================================================================

function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                const offset = 80; // Navbar height
                const targetPosition = target.getBoundingClientRect().top + window.pageYOffset - offset;
                window.scrollTo({
                    top: targetPosition,
                    behavior: 'smooth'
                });
            }
        });
    });
}

// =============================================================================
// LIVE SIGNALS DASHBOARD (if on live-signals page)
// =============================================================================

function initDashboard() {
    const dashboardContainer = document.getElementById('dashboardContainer');
    if (!dashboardContainer) return;

    // Dashboard-specific elements
    const signalDirection = document.getElementById('signalDirection');
    const signalEntry = document.getElementById('signalEntry');
    const signalSL = document.getElementById('signalSL');
    const signalTP = document.getElementById('signalTP');
    const signalDate = document.getElementById('signalDate');
    const signalTime = document.getElementById('signalTime');
    const signalStatus = document.getElementById('signalStatus');
    const orHigh = document.getElementById('orHigh');
    const orLow = document.getElementById('orLow');
    const currentPrice = document.getElementById('currentPrice');
    const signalHistory = document.getElementById('signalHistory');
    const liveStatus = document.getElementById('liveStatus');

    async function updateDashboard() {
        const signal = await fetchSignal();
        if (!signal) return;

        // Update main signal card
        if (signalDirection) {
            signalDirection.textContent = signal.direction || 'WAITING';
            signalDirection.className = `signal-direction ${signal.direction?.toLowerCase() || 'waiting'}`;
        }
        if (signalEntry) signalEntry.textContent = formatPrice(signal.entry);
        if (signalSL) signalSL.textContent = formatPrice(signal.stop_loss);
        if (signalTP) signalTP.textContent = formatPrice(signal.take_profit);
        if (signalDate) signalDate.textContent = signal.date || '--';
        if (signalTime) signalTime.textContent = signal.time || '--';
        if (signalStatus) {
            signalStatus.textContent = signal.status || 'WAITING';
            signalStatus.className = `status-badge ${(signal.status || 'waiting').toLowerCase()}`;
        }
        if (orHigh) orHigh.textContent = formatPrice(signal.opening_range_high);
        if (orLow) orLow.textContent = formatPrice(signal.opening_range_low);
        if (currentPrice) currentPrice.textContent = formatPrice(signal.current_price);

        // Update live status
        if (liveStatus) {
            if (isSessionActive()) {
                liveStatus.innerHTML = '<span class="pulse-dot"></span> Live';
            } else {
                liveStatus.innerHTML = '<span class="status-dot inactive"></span> Offline';
            }
        }

        // Update history
        if (signalHistory && signal.signal_history) {
            signalHistory.innerHTML = signal.signal_history.map(hist => `
                <div class="history-item">
                    <span class="history-direction ${hist.direction?.toLowerCase()}">${hist.direction}</span>
                    <span class="history-entry">${formatPrice(hist.entry)}</span>
                    <span class="history-status ${(hist.status || '').toLowerCase()}">${hist.status}</span>
                    <span class="history-date">${hist.date || ''}</span>
                </div>
            `).join('');
        }
    }

    updateDashboard();
    setInterval(updateDashboard, CONFIG.REFRESH_INTERVAL);
}

// =============================================================================
// INITIALIZATION
// =============================================================================

document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initFAQ();
    initSmoothScroll();
    initScrollAnimations();
    initDashboard();

    // Initial signal fetch
    refreshSignal();

    // Periodic updates
    setInterval(refreshSignal, CONFIG.REFRESH_INTERVAL);
    setInterval(updateSessionStatus, 1000);

    // Initial session status
    updateSessionStatus();
});

// Handle window resize
window.addEventListener('resize', () => {
    if (window.innerWidth > 768) {
        navLinks.classList.remove('active');
        mobileMenuBtn.classList.remove('active');
        document.body.style.overflow = '';
    }
});
