/**
 * DollarProFx - Main JavaScript
 * Handles navigation, scroll animations, FAQ accordion, and live dashboard updates
 */

(function() {
  'use strict';

  // ── DOM Elements ────────────────────────────────────────────────
  const navbar = document.getElementById('navbar');
  const mobileToggle = document.getElementById('mobileToggle');
  const navLinks = document.getElementById('navLinks');
  const revealElements = document.querySelectorAll('.reveal');
  const faqItems = document.querySelectorAll('.faq-item');

  // ── Navigation Scroll Effect ────────────────────────────────────
  function handleNavScroll() {
    if (window.scrollY > 50) {
      navbar.classList.add('scrolled');
    } else {
      navbar.classList.remove('scrolled');
    }
  }

  window.addEventListener('scroll', handleNavScroll, { passive: true });

  // ── Mobile Menu Toggle ──────────────────────────────────────────
  if (mobileToggle) {
    mobileToggle.addEventListener('click', function() {
      this.classList.toggle('active');
      navLinks.classList.toggle('active');
      document.body.style.overflow = navLinks.classList.contains('active') ? 'hidden' : '';
    });
  }

  // Close mobile menu when clicking a link
  document.querySelectorAll('.nav-links a').forEach(link => {
    link.addEventListener('click', () => {
      mobileToggle.classList.remove('active');
      navLinks.classList.remove('active');
      document.body.style.overflow = '';
    });
  });

  // ── Active Navigation Link ──────────────────────────────────────
  function updateActiveNav() {
    const sections = document.querySelectorAll('section[id]');
    const scrollPos = window.scrollY + 100;

    sections.forEach(section => {
      const top = section.offsetTop;
      const height = section.offsetHeight;
      const id = section.getAttribute('id');

      if (scrollPos >= top && scrollPos < top + height) {
        document.querySelectorAll('.nav-links a').forEach(link => {
          link.classList.remove('active');
          if (link.getAttribute('href') === '#' + id) {
            link.classList.add('active');
          }
        });
      }
    });
  }

  window.addEventListener('scroll', updateActiveNav, { passive: true });

  // ── Scroll Reveal Animation ─────────────────────────────────────
  function revealOnScroll() {
    revealElements.forEach(el => {
      const elementTop = el.getBoundingClientRect().top;
      const windowHeight = window.innerHeight;
      const revealPoint = 100;

      if (elementTop < windowHeight - revealPoint) {
        el.classList.add('active');
      }
    });
  }

  window.addEventListener('scroll', revealOnScroll, { passive: true });
  // Trigger once on load
  revealOnScroll();

  // ── FAQ Accordion ───────────────────────────────────────────────
  faqItems.forEach(item => {
    const question = item.querySelector('.faq-question');
    if (question) {
      question.addEventListener('click', () => {
        const isActive = item.classList.contains('active');

        // Close all other items
        faqItems.forEach(other => {
          if (other !== item) {
            other.classList.remove('active');
          }
        });

        // Toggle current item
        item.classList.toggle('active', !isActive);
      });
    }
  });

  // ── Smooth Scroll for Anchor Links ──────────────────────────────
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
      const href = this.getAttribute('href');
      if (href === '#') return;

      const target = document.querySelector(href);
      if (target) {
        e.preventDefault();
        const offset = 80; // Account for fixed navbar
        const targetPosition = target.getBoundingClientRect().top + window.pageYOffset - offset;

        window.scrollTo({
          top: targetPosition,
          behavior: 'smooth'
        });
      }
    });
  });

  // ── Live Dashboard ──────────────────────────────────────────────
  const API_BASE = window.location.origin;
  let refreshInterval = null;

  // Dashboard elements
  const els = {
    signalCard: document.getElementById('signalCard'),
    signalDirection: document.getElementById('signalDirection'),
    signalStatusText: document.getElementById('signalStatusText'),
    entryPrice: document.getElementById('entryPrice'),
    stopLoss: document.getElementById('stopLoss'),
    takeProfit: document.getElementById('takeProfit'),
    signalTime: document.getElementById('signalTime'),
    signalDate: document.getElementById('signalDate'),
    currentPrice: document.getElementById('currentPrice'),
    sessionStatus: document.getElementById('sessionStatus'),
    timeRemaining: document.getElementById('timeRemaining'),
    lastUpdated: document.getElementById('lastUpdated'),
    orHigh: document.getElementById('orHigh'),
    orLow: document.getElementById('orLow'),
    statusDot: document.getElementById('statusDot'),
    statusText: document.getElementById('statusText'),
    historyBody: document.getElementById('historyBody')
  };

  function formatPrice(price) {
    if (price === null || price === undefined) return '--';
    return price.toFixed(2);
  }

  function formatDateTime(isoString) {
    if (!isoString) return '--';
    try {
      const date = new Date(isoString);
      return date.toLocaleTimeString('en-US', { 
        hour: '2-digit', 
        minute: '2-digit',
        hour12: true 
      }) + ' WAT';
    } catch {
      return '--';
    }
  }

  function getSessionStatusText(status) {
    const statusMap = {
      'WAITING': 'Waiting for Session',
      'BEFORE_SESSION': 'Before Session',
      'OPENING_RANGE': 'Opening Range Active',
      'MONITORING': 'Monitoring Breakouts',
      'ACTIVE_TRADE': 'Active Trade',
      'SESSION_ENDED': 'Session Ended',
      'WEEKEND': 'Weekend - No Trading'
    };
    return statusMap[status] || status;
  }

  function getStatusClass(status) {
    const classMap = {
      'ACTIVE_TRADE': 'active',
      'MONITORING': 'waiting',
      'WAITING': 'waiting',
      'BEFORE_SESSION': 'waiting',
      'OPENING_RANGE': 'waiting',
      'SESSION_ENDED': 'ended',
      'WEEKEND': 'weekend'
    };
    return classMap[status] || 'waiting';
  }

  function updateSignalCard(signal) {
    if (!signal) {
      els.signalCard.className = 'signal-card waiting';
      els.signalDirection.textContent = 'WAITING';
      els.signalDirection.className = 'signal-direction waiting';
      els.signalStatusText.textContent = 'Waiting for confirmed breakout...';
      els.entryPrice.textContent = '--';
      els.stopLoss.textContent = '--';
      els.takeProfit.textContent = '--';
      els.signalTime.textContent = '--';
      els.signalDate.textContent = '--';
      return;
    }

    const direction = signal.direction;
    els.signalCard.className = `signal-card ${direction.toLowerCase()}`;
    els.signalDirection.textContent = direction;
    els.signalDirection.className = `signal-direction ${direction.toLowerCase()}`;

    const statusText = signal.status === 'ACTIVE' ? 'Active Trade' : signal.status;
    els.signalStatusText.textContent = statusText;

    els.entryPrice.textContent = formatPrice(signal.entry);
    els.stopLoss.textContent = formatPrice(signal.stop_loss);
    els.takeProfit.textContent = formatPrice(signal.take_profit);
    els.signalTime.textContent = signal.time || '--';
    els.signalDate.textContent = signal.date || '--';
  }

  function updateHistory(history) {
    if (!history || history.length === 0) {
      els.historyBody.innerHTML = `
        <tr>
          <td colspan="7" style="text-align: center; color: var(--text-muted);">No trade history available</td>
        </tr>
      `;
      return;
    }

    const rows = history.slice(0, 10).map(trade => {
      const directionClass = trade.direction === 'BUY' ? 'badge-buy' : 'badge-sell';
      let resultBadge = '';

      if (trade.status === 'TP_HIT') {
        resultBadge = '<span class="badge badge-tp">TP Hit</span>';
      } else if (trade.status === 'SL_HIT') {
        resultBadge = '<span class="badge badge-sl">SL Hit</span>';
      } else if (trade.status === 'SESSION_CLOSED') {
        resultBadge = '<span class="badge" style="background: rgba(160,160,176,0.15); color: var(--text-muted);">Closed</span>';
      } else {
        resultBadge = '<span class="badge" style="background: rgba(74,144,217,0.15); color: var(--accent-blue);">Active</span>';
      }

      return `
        <tr>
          <td><span class="badge ${directionClass}">${trade.direction}</span></td>
          <td>${formatPrice(trade.entry)}</td>
          <td>${formatPrice(trade.stop_loss)}</td>
          <td>${formatPrice(trade.take_profit)}</td>
          <td>${trade.date || '--'}</td>
          <td>${trade.time || '--'}</td>
          <td>${resultBadge}</td>
        </tr>
      `;
    }).join('');

    els.historyBody.innerHTML = rows;
  }

  function updateTimeRemaining(sessionStatus) {
    // WAT is UTC+1
    const now = new Date();
    const watOffset = 60; // minutes
    const watNow = new Date(now.getTime() + watOffset * 60000);

    const sessionEnd = new Date(watNow);
    sessionEnd.setHours(20, 45, 0, 0); // 8:45 PM WAT

    const sessionStart = new Date(watNow);
    sessionStart.setHours(14, 30, 0, 0); // 2:30 PM WAT

    const day = watNow.getDay();

    if (day === 0 || day === 6) {
      els.timeRemaining.textContent = 'Weekend';
      return;
    }

    if (sessionStatus === 'SESSION_ENDED') {
      els.timeRemaining.textContent = 'Session Ended';
      return;
    }

    if (watNow < sessionStart) {
      const diff = sessionStart - watNow;
      const hours = Math.floor(diff / 3600000);
      const minutes = Math.floor((diff % 3600000) / 60000);
      els.timeRemaining.textContent = `Starts in ${hours}h ${minutes}m`;
      return;
    }

    if (watNow > sessionEnd) {
      els.timeRemaining.textContent = 'Session Ended';
      return;
    }

    const diff = sessionEnd - watNow;
    const hours = Math.floor(diff / 3600000);
    const minutes = Math.floor((diff % 3600000) / 60000);
    els.timeRemaining.textContent = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`;
  }

  // ── Verification Gate ───────────────────────────────────────────
  const TOKEN_KEY = 'dollarprofx_verify_token';
  const verifyGate = document.getElementById('verifyGate');
  const dashboardContent = document.getElementById('dashboardContent');

  function getToken() {
    try {
      return localStorage.getItem(TOKEN_KEY) || '';
    } catch (e) {
      return '';
    }
  }

  async function checkVerification() {
    const token = getToken();

    if (!token) {
      // No token - show gate, hide dashboard
      if (verifyGate) verifyGate.style.display = 'block';
      if (dashboardContent) dashboardContent.style.display = 'none';
      return false;
    }

    // Client-side token check - works on GitHub Pages without backend
    if (token.startsWith('client_')) {
      if (verifyGate) verifyGate.style.display = 'none';
      if (dashboardContent) dashboardContent.style.display = 'block';
      return true;
    }

    // If token exists but is not client token, clear it
    if (verifyGate) verifyGate.style.display = 'block';
    if (dashboardContent) dashboardContent.style.display = 'none';
    try { localStorage.removeItem(TOKEN_KEY); } catch (e) {}
    return false;
  }

  // ── Fetch Signal Data ───────────────────────────────────────────
  // For GitHub Pages: reads signal.json directly from the repo
  // For Flask backend: would call the API endpoint
  async function fetchSignalData() {
    const token = getToken();
    if (!token) return; // Don't fetch if not verified

    // Only fetch if verified with client token
    if (!token.startsWith('client_')) return;

    try {
      // Try to fetch signal.json directly from the repository
      const response = await fetch('signal.json?t=' + Date.now());

      if (!response.ok) {
        // signal.json not accessible or not found - show demo data
        showDemoData();
        return;
      }

      const data = await response.json();

      // Update signal card
      updateSignalCard(data.latest_signal);

      // Update market info
      els.currentPrice.textContent = formatPrice(data.current_gold_price);
      els.sessionStatus.textContent = getSessionStatusText(data.session_status);
      els.lastUpdated.textContent = formatDateTime(data.last_updated);

      // Update OR levels
      if (data.opening_range) {
        els.orHigh.textContent = formatPrice(data.opening_range.high);
        els.orLow.textContent = formatPrice(data.opening_range.low);
      }

      // Update status indicator
      const statusClass = getStatusClass(data.session_status);
      els.statusDot.className = `status-dot ${statusClass}`;
      els.statusText.textContent = getSessionStatusText(data.session_status);

      // Update history
      updateHistory(data.signal_history);

      // Calculate time remaining
      updateTimeRemaining(data.session_status);

    } catch (error) {
      console.error('Error fetching signal data:', error);
      showDemoData();
    }
  }

  // ── Demo Data (fallback when signal.json unavailable) ───────────
  function showDemoData() {
    els.currentPrice.textContent = "--";
    els.sessionStatus.textContent = "WAITING";
    els.lastUpdated.textContent = new Date().toLocaleTimeString();
    els.orHigh.textContent = "--";
    els.orLow.textContent = "--";
    els.statusDot.className = 'status-dot waiting';
    els.statusText.textContent = 'Monitoring Market...';
    updateTimeRemaining('WAITING');
  }

  // ── Initialize ──────────────────────────────────────────────────
  (async function init() {
    const isVerified = await checkVerification();

    if (isVerified && els.signalDirection) {
      fetchSignalData();
      refreshInterval = setInterval(fetchSignalData, 60000);
    }
  })();

  // Cleanup on page unload
  window.addEventListener('beforeunload', () => {
    if (refreshInterval) {
      clearInterval(refreshInterval);
    }
  });

})();
