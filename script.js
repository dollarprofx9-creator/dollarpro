/**
 * XAUUSD Signal Dashboard - Monetization Edition
 * Handles authentication, subscription tiers, paywall logic,
 * payment simulation, and full dashboard functionality.
 */

(function() {
    'use strict';

    // =============================================================================
    // CONFIGURATION
    // =============================================================================
    const CONFIG = {
        refreshInterval: 60000,
        countdownInterval: 1000,
        watOffset: 1,
        sessionStart: { hour: 14, minute: 30 },
        sessionEnd: { hour: 20, minute: 45 },
        // Subscription tiers
        TIERS: {
            FREE: 'free',
            PRO: 'pro',
            ELITE: 'elite'
        },
        // Feature flags per tier
        FEATURES: {
            free: {
                seeCurrentPrice: true,
                seeSessionStatus: true,
                seeSignalType: false,      // Only sees "Pro Signal Active" blur
                seeSignalDetails: false,   // Entry/SL/TP hidden
                seeHistory: false,         // History table blurred
                seeStats: false,
                telegramAlerts: false,
                emailAlerts: false,
                apiAccess: false
            },
            pro: {
                seeCurrentPrice: true,
                seeSessionStatus: true,
                seeSignalType: true,
                seeSignalDetails: true,
                seeHistory: true,
                seeStats: true,
                telegramAlerts: true,
                emailAlerts: true,
                apiAccess: false
            },
            elite: {
                seeCurrentPrice: true,
                seeSessionStatus: true,
                seeSignalType: true,
                seeSignalDetails: true,
                seeHistory: true,
                seeStats: true,
                telegramAlerts: true,
                emailAlerts: true,
                apiAccess: true
            }
        },
        PRICING: {
            pro: { price: 29, period: 'month' },
            elite: { price: 79, period: 'month' }
        }
    };

    // =============================================================================
    // STATE MANAGEMENT
    // =============================================================================
    const state = {
        user: null,           // { id, name, email, tier, expiryDate }
        isGuest: false,
        currentPlan: null,
        signalData: null
    };

    // =============================================================================
    // DOM ELEMENTS
    // =============================================================================
    const el = {
        // Modals
        authModal: document.getElementById('authModal'),
        upgradeModal: document.getElementById('upgradeModal'),
        accountModal: document.getElementById('accountModal'),

        // Auth forms
        loginForm: document.getElementById('loginForm'),
        registerForm: document.getElementById('registerForm'),
        loginEmail: document.getElementById('loginEmail'),
        loginPassword: document.getElementById('loginPassword'),
        regName: document.getElementById('regName'),
        regEmail: document.getElementById('regEmail'),
        regPassword: document.getElementById('regPassword'),
        loginError: document.getElementById('loginError'),
        registerError: document.getElementById('registerError'),
        guestBtn: document.getElementById('guestBtn'),
        authTabs: document.querySelectorAll('.auth-tab'),

        // Upgrade modal
        closeUpgrade: document.getElementById('closeUpgrade'),
        upgradeProBtn: document.getElementById('upgradeProBtn'),
        upgradeEliteBtn: document.getElementById('upgradeEliteBtn'),
        paymentSection: document.getElementById('paymentSection'),
        cardNumber: document.getElementById('cardNumber'),
        cardExpiry: document.getElementById('cardExpiry'),
        cardCvc: document.getElementById('cardCvc'),
        cardName: document.getElementById('cardName'),
        payBtn: document.getElementById('payBtn'),
        payBtnText: document.getElementById('payBtnText'),
        paySpinner: document.getElementById('paySpinner'),
        paymentError: document.getElementById('paymentError'),

        // Account modal
        closeAccount: document.getElementById('closeAccount'),
        accountAvatar: document.getElementById('accountAvatar'),
        accountName: document.getElementById('accountName'),
        accountEmail: document.getElementById('accountEmail'),
        accountPlanBadge: document.getElementById('accountPlanBadge'),
        subName: document.getElementById('subName'),
        subStatus: document.getElementById('subStatus'),
        subPrice: document.getElementById('subPrice'),
        subRenewal: document.getElementById('subRenewal'),
        accountUpgradeBtn: document.getElementById('accountUpgradeBtn'),
        logoutBtn: document.getElementById('logoutBtn'),

        // Header
        lastUpdated: document.getElementById('lastUpdated'),
        upgradeHeaderBtn: document.getElementById('upgradeHeaderBtn'),
        userMenu: document.getElementById('userMenu'),
        userAvatarBtn: document.getElementById('userAvatarBtn'),
        userDropdown: document.getElementById('userDropdown'),
        accountBtn: document.getElementById('accountBtn'),
        headerLogoutBtn: document.getElementById('headerLogoutBtn'),

        // Paywall
        paywallBanner: document.getElementById('paywallBanner'),
        bannerUpgradeBtn: document.getElementById('bannerUpgradeBtn'),
        signalBlur: document.getElementById('signalBlur'),
        blurUpgradeBtn: document.getElementById('blurUpgradeBtn'),
        historyBlur: document.getElementById('historyBlur'),
        historyUpgradeBtn: document.getElementById('historyUpgradeBtn'),

        // Dashboard
        sessionBar: document.getElementById('sessionBar'),
        statusBadge: document.getElementById('statusBadge'),
        countdown: document.getElementById('countdown'),
        currentPrice: document.getElementById('currentPrice'),
        signalCard: document.getElementById('signalCard'),
        signalBadge: document.getElementById('signalBadge'),
        signalEmpty: document.getElementById('signalEmpty'),
        signalDetails: document.getElementById('signalDetails'),
        detailEntry: document.getElementById('detailEntry'),
        detailSL: document.getElementById('detailSL'),
        detailTP: document.getElementById('detailTP'),
        detailDate: document.getElementById('detailDate'),
        detailTime: document.getElementById('detailTime'),
        orHigh: document.getElementById('orHigh'),
        orLow: document.getElementById('orLow'),
        orStatus: document.getElementById('orStatus'),
        orBarFill: document.getElementById('orBarFill'),
        orMarkerCurrent: document.getElementById('orMarkerCurrent'),
        orLabelLow: document.getElementById('orLabelLow'),
        orLabelHigh: document.getElementById('orLabelHigh'),
        historyCount: document.getElementById('historyCount'),
        historyBody: document.getElementById('historyBody'),
        statsSection: document.getElementById('statsSection'),
        statTotalSignals: document.getElementById('statTotalSignals'),
        statWinRate: document.getElementById('statWinRate'),
        statAvgRisk: document.getElementById('statAvgRisk'),
        statAvgReward: document.getElementById('statAvgReward'),

        // Footer
        footerPricing: document.getElementById('footerPricing'),

        // Toast
        toastContainer: document.getElementById('toastContainer')
    };

    // =============================================================================
    // AUTHENTICATION SYSTEM
    // =============================================================================

    /**
     * Initialize auth state from localStorage
     */
    function initAuth() {
        const saved = localStorage.getItem('xauusd_user');
        if (saved) {
            try {
                state.user = JSON.parse(saved);
                state.isGuest = false;
                showDashboard();
            } catch (e) {
                localStorage.removeItem('xauusd_user');
                showAuthModal();
            }
        } else {
            showAuthModal();
        }
    }

    function showAuthModal() {
        el.authModal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
    }

    function hideAuthModal() {
        el.authModal.classList.add('hidden');
        document.body.style.overflow = '';
    }

    function showDashboard() {
        hideAuthModal();
        updateHeaderForUser();
        applyTierFeatures();
        updateDashboard();
    }

    function updateHeaderForUser() {
        if (state.isGuest) {
            el.upgradeHeaderBtn.classList.remove('hidden');
            el.userMenu.classList.add('hidden');
            return;
        }

        el.upgradeHeaderBtn.classList.add('hidden');
        el.userMenu.classList.remove('hidden');

        const initials = state.user.name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
        el.userAvatarBtn.textContent = initials;

        // Show upgrade button for free users
        if (state.user.tier === CONFIG.TIERS.FREE) {
            el.upgradeHeaderBtn.classList.remove('hidden');
        }
    }

    // Login handler
    el.loginForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const email = el.loginEmail.value.trim();
        const password = el.loginPassword.value;

        if (!email || !password) {
            el.loginError.textContent = 'Please fill in all fields';
            return;
        }

        // Simulate login - in production, this calls your backend API
        const users = JSON.parse(localStorage.getItem('xauusd_users') || '[]');
        const user = users.find(u => u.email === email && u.password === password);

        if (user) {
            state.user = { ...user, password: undefined };
            state.isGuest = false;
            localStorage.setItem('xauusd_user', JSON.stringify(state.user));
            el.loginError.textContent = '';
            showToast('Welcome back, ' + user.name + '!', 'success');
            showDashboard();
        } else {
            el.loginError.textContent = 'Invalid email or password';
        }
    });

    // Register handler
    el.registerForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const name = el.regName.value.trim();
        const email = el.regEmail.value.trim();
        const password = el.regPassword.value;

        if (!name || !email || !password) {
            el.registerError.textContent = 'Please fill in all fields';
            return;
        }

        if (password.length < 8) {
            el.registerError.textContent = 'Password must be at least 8 characters';
            return;
        }

        // Simulate registration
        let users = JSON.parse(localStorage.getItem('xauusd_users') || '[]');

        if (users.find(u => u.email === email)) {
            el.registerError.textContent = 'Email already registered';
            return;
        }

        const newUser = {
            id: 'user_' + Date.now(),
            name: name,
            email: email,
            password: password,  // In production: hash this!
            tier: CONFIG.TIERS.FREE,
            createdAt: new Date().toISOString(),
            expiryDate: null
        };

        users.push(newUser);
        localStorage.setItem('xauusd_users', JSON.stringify(users));

        state.user = { ...newUser, password: undefined };
        state.isGuest = false;
        localStorage.setItem('xauusd_user', JSON.stringify(state.user));

        el.registerError.textContent = '';
        showToast('Account created! Welcome, ' + name + '!', 'success');
        showDashboard();
    });

    // Guest mode
    el.guestBtn.addEventListener('click', function() {
        state.isGuest = true;
        state.user = null;
        showToast('Browsing as guest. Limited preview mode.', 'info');
        showDashboard();
    });

    // Auth tab switching
    el.authTabs.forEach(tab => {
        tab.addEventListener('click', function() {
            el.authTabs.forEach(t => t.classList.remove('active'));
            this.classList.add('active');

            const target = this.dataset.tab;
            if (target === 'login') {
                el.loginForm.classList.remove('hidden');
                el.registerForm.classList.add('hidden');
            } else {
                el.loginForm.classList.add('hidden');
                el.registerForm.classList.remove('hidden');
            }
        });
    });

    // Logout
    function logout() {
        state.user = null;
        state.isGuest = false;
        localStorage.removeItem('xauusd_user');
        el.accountModal.classList.add('hidden');
        showToast('Signed out successfully', 'info');
        showAuthModal();
    }

    el.logoutBtn.addEventListener('click', logout);
    el.headerLogoutBtn.addEventListener('click', logout);

    // User dropdown toggle
    el.userAvatarBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        el.userDropdown.classList.toggle('hidden');
    });

    document.addEventListener('click', function() {
        el.userDropdown.classList.add('hidden');
    });

    // Account modal
    el.accountBtn.addEventListener('click', function() {
        el.userDropdown.classList.add('hidden');
        openAccountModal();
    });

    el.closeAccount.addEventListener('click', function() {
        el.accountModal.classList.add('hidden');
    });

    function openAccountModal() {
        if (!state.user) return;

        const initials = state.user.name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
        el.accountAvatar.textContent = initials;
        el.accountName.textContent = state.user.name;
        el.accountEmail.textContent = state.user.email;

        const tier = state.user.tier;
        el.accountPlanBadge.textContent = tier.charAt(0).toUpperCase() + tier.slice(1);
        el.accountPlanBadge.className = 'account-plan-badge ' + tier;

        el.subName.textContent = tier.charAt(0).toUpperCase() + tier.slice(1);

        if (tier === CONFIG.TIERS.FREE) {
            el.subStatus.textContent = 'Active';
            el.subStatus.className = 'sub-status active';
            el.subPrice.textContent = '$0/month';
            el.subRenewal.textContent = 'Free forever';
            el.accountUpgradeBtn.textContent = 'Upgrade';
            el.accountUpgradeBtn.onclick = openUpgradeModal;
        } else {
            el.subStatus.textContent = 'Active';
            el.subStatus.className = 'sub-status active';
            const price = CONFIG.PRICING[tier].price;
            el.subPrice.textContent = '$' + price + '/month';
            el.subRenewal.textContent = 'Renews ' + (state.user.expiryDate ? formatDate(state.user.expiryDate) : 'monthly');
            el.accountUpgradeBtn.textContent = 'Manage Subscription';
            el.accountUpgradeBtn.onclick = openUpgradeModal;
        }

        el.accountModal.classList.remove('hidden');
    }

    // =============================================================================
    // UPGRADE & PAYMENT SYSTEM
    // =============================================================================

    function openUpgradeModal() {
        el.upgradeModal.classList.remove('hidden');
        el.paymentSection.classList.add('hidden');
        state.currentPlan = null;
    }

    el.closeUpgrade.addEventListener('click', function() {
        el.upgradeModal.classList.add('hidden');
    });

    el.upgradeHeaderBtn.addEventListener('click', openUpgradeModal);
    el.bannerUpgradeBtn.addEventListener('click', openUpgradeModal);
    el.blurUpgradeBtn.addEventListener('click', openUpgradeModal);
    el.historyUpgradeBtn.addEventListener('click', openUpgradeModal);
    el.footerPricing.addEventListener('click', function(e) {
        e.preventDefault();
        openUpgradeModal();
    });

    // Plan selection
    function selectPlan(plan) {
        state.currentPlan = plan;
        el.paymentSection.classList.remove('hidden');

        const price = CONFIG.PRICING[plan].price;
        el.payBtnText.textContent = 'Pay $' + price + '.00';
        el.paymentError.textContent = '';

        // Scroll to payment section
        el.paymentSection.scrollIntoView({ behavior: 'smooth' });
    }

    el.upgradeProBtn.addEventListener('click', function() {
        selectPlan(CONFIG.TIERS.PRO);
    });

    el.upgradeEliteBtn.addEventListener('click', function() {
        selectPlan(CONFIG.TIERS.ELITE);
    });

    // Card input formatting
    el.cardNumber.addEventListener('input', function(e) {
        let value = e.target.value.replace(/\D/g, '').substring(0, 16);
        value = value.match(/.{1,4}/g)?.join(' ') || value;
        e.target.value = value;
    });

    el.cardExpiry.addEventListener('input', function(e) {
        let value = e.target.value.replace(/\D/g, '').substring(0, 4);
        if (value.length >= 2) {
            value = value.substring(0, 2) + '/' + value.substring(2);
        }
        e.target.value = value;
    });

    el.cardCvc.addEventListener('input', function(e) {
        e.target.value = e.target.value.replace(/\D/g, '').substring(0, 4);
    });

    // Payment processing (simulated)
    el.payBtn.addEventListener('click', async function() {
        const cardNum = el.cardNumber.value.replace(/\s/g, '');
        const expiry = el.cardExpiry.value;
        const cvc = el.cardCvc.value;
        const name = el.cardName.value.trim();

        // Validation
        if (cardNum.length !== 16) {
            el.paymentError.textContent = 'Please enter a valid 16-digit card number';
            return;
        }
        if (!expiry.match(/^\d{2}\/\d{2}$/)) {
            el.paymentError.textContent = 'Please enter expiry as MM/YY';
            return;
        }
        if (cvc.length < 3) {
            el.paymentError.textContent = 'Please enter a valid CVC';
            return;
        }
        if (!name) {
            el.paymentError.textContent = 'Please enter the name on card';
            return;
        }

        // Show loading
        el.payBtn.disabled = true;
        el.paySpinner.classList.remove('hidden');
        el.payBtnText.textContent = 'Processing...';

        // Simulate API call
        await new Promise(r => setTimeout(r, 2000));

        // Success - upgrade user
        const plan = state.currentPlan;
        const expiryDate = new Date();
        expiryDate.setMonth(expiryDate.getMonth() + 1);

        if (state.user) {
            state.user.tier = plan;
            state.user.expiryDate = expiryDate.toISOString();
            localStorage.setItem('xauusd_user', JSON.stringify(state.user));

            // Update stored users
            let users = JSON.parse(localStorage.getItem('xauusd_users') || '[]');
            const idx = users.findIndex(u => u.id === state.user.id);
            if (idx >= 0) {
                users[idx].tier = plan;
                users[idx].expiryDate = expiryDate.toISOString();
                localStorage.setItem('xauusd_users', JSON.stringify(users));
            }
        }

        el.payBtn.disabled = false;
        el.paySpinner.classList.add('hidden');
        el.payBtnText.textContent = 'Pay $' + CONFIG.PRICING[plan].price + '.00';

        el.upgradeModal.classList.add('hidden');
        showToast('Welcome to ' + plan.charAt(0).toUpperCase() + plan.slice(1) + '! Payment successful.', 'success');

        applyTierFeatures();
        updateHeaderForUser();
    });

    // =============================================================================
    // TIER-BASED FEATURE GATING
    // =============================================================================

    function getEffectiveTier() {
        if (state.isGuest) return CONFIG.TIERS.FREE;
        if (!state.user) return CONFIG.TIERS.FREE;

        // Check expiry
        if (state.user.expiryDate) {
            const expiry = new Date(state.user.expiryDate);
            if (expiry < new Date()) {
                // Expired - downgrade to free
                state.user.tier = CONFIG.TIERS.FREE;
                state.user.expiryDate = null;
                localStorage.setItem('xauusd_user', JSON.stringify(state.user));
                showToast('Your subscription has expired. Downgraded to Free.', 'info');
                return CONFIG.TIERS.FREE;
            }
        }
        return state.user.tier;
    }

    function applyTierFeatures() {
        const tier = getEffectiveTier();
        const features = CONFIG.FEATURES[tier];

        // Paywall banner (show for free/guest)
        if (tier === CONFIG.TIERS.FREE) {
            el.paywallBanner.classList.remove('hidden');
        } else {
            el.paywallBanner.classList.add('hidden');
        }

        // Stats section (pro/elite only)
        if (features.seeStats) {
            el.statsSection.classList.remove('hidden');
        } else {
            el.statsSection.classList.add('hidden');
        }

        // Signal details visibility is handled in updateSignalCard
        // History visibility is handled in updateHistory
    }

    // =============================================================================
    // TIME UTILITIES
    // =============================================================================
    function getWATTime() {
        const now = new Date();
        const utc = now.getTime() + (now.getTimezoneOffset() * 60000);
        return new Date(utc + (CONFIG.watOffset * 3600000));
    }
    function formatPrice(price) {
        if (price === null || price === undefined || isNaN(price)) return '--';
        return price.toFixed(2);
    }
    function formatDate(dateStr) {
        if (!dateStr) return '--';
        const d = new Date(dateStr);
        return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    }
    function isSessionActive() {
        const wat = getWATTime();
        const currentMinutes = wat.getHours() * 60 + wat.getMinutes();
        const startMinutes = CONFIG.sessionStart.hour * 60 + CONFIG.sessionStart.minute;
        const endMinutes = CONFIG.sessionEnd.hour * 60 + CONFIG.sessionEnd.minute;
        return currentMinutes >= startMinutes && currentMinutes <= endMinutes;
    }
    function isWeekend() {
        const wat = getWATTime();
        return wat.getDay() === 0 || wat.getDay() === 6;
    }
    function getSessionCountdown() {
        const wat = getWATTime();
        const currentMinutes = wat.getHours() * 60 + wat.getMinutes();
        const endMinutes = CONFIG.sessionEnd.hour * 60 + CONFIG.sessionEnd.minute;
        const startMinutes = CONFIG.sessionStart.hour * 60 + CONFIG.sessionStart.minute;

        if (currentMinutes < startMinutes) {
            const diff = startMinutes - currentMinutes;
            return 'Starts in ' + Math.floor(diff / 60) + 'h ' + (diff % 60) + 'm';
        }
        if (currentMinutes > endMinutes) return 'Session ended';
        const diff = endMinutes - currentMinutes;
        return Math.floor(diff / 60) + 'h ' + (diff % 60) + 'm remaining';
    }

    // =============================================================================
    // UI UPDATES
    // =============================================================================
    function updateLastUpdated() {
        const wat = getWATTime();
        el.lastUpdated.textContent = 'Updated: ' + wat.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true }) + ' WAT';
    }
    function updateSessionStatus() {
        const active = isSessionActive();
        const weekend = isWeekend();

        if (weekend) {
            el.statusBadge.textContent = 'Weekend';
            el.statusBadge.className = 'status-badge closed';
            el.countdown.textContent = 'Markets closed';
            return;
        }
        if (active) {
            el.statusBadge.textContent = 'Active';
            el.statusBadge.className = 'status-badge active';
        } else {
            el.statusBadge.textContent = 'Inactive';
            el.statusBadge.className = 'status-badge inactive';
        }
        el.countdown.textContent = getSessionCountdown();
    }
    function updatePrice(price) {
        el.currentPrice.textContent = formatPrice(price);
    }

    function updateSignalCard(signal) {
        const tier = getEffectiveTier();
        const features = CONFIG.FEATURES[tier];

        el.signalCard.classList.remove('has-buy', 'has-sell');

        const hasSignal = signal && signal.type;

        if (!hasSignal) {
            el.signalEmpty.style.display = 'flex';
            el.signalDetails.style.display = 'none';
            el.signalBlur.classList.add('hidden');
            el.signalBadge.textContent = 'WAITING';
            el.signalBadge.className = 'signal-badge waiting';
            return;
        }

        // Free/Guest users: show blur overlay when signal exists
        if (!features.seeSignalDetails) {
            el.signalEmpty.style.display = 'none';
            el.signalDetails.style.display = 'none';
            el.signalBlur.classList.remove('hidden');
            el.signalBadge.textContent = 'PRO SIGNAL';
            el.signalBadge.className = 'signal-badge buy';  // Green to indicate active
            return;
        }

        // Pro/Elite: show full signal
        el.signalEmpty.style.display = 'none';
        el.signalDetails.style.display = 'block';
        el.signalBlur.classList.add('hidden');

        const signalType = signal.type;
        el.signalBadge.textContent = signalType;
        el.signalBadge.className = 'signal-badge ' + signalType.toLowerCase();

        if (signalType === 'BUY') el.signalCard.classList.add('has-buy');
        else if (signalType === 'SELL') el.signalCard.classList.add('has-sell');

        el.detailEntry.textContent = formatPrice(signal.entry);
        el.detailSL.textContent = formatPrice(signal.stop_loss);
        el.detailTP.textContent = formatPrice(signal.take_profit);
        el.detailDate.textContent = signal.date || '--';
        el.detailTime.textContent = signal.time || '--';
    }

    function updateOpeningRange(orData, currentPrice) {
        const high = orData ? orData.high : null;
        const low = orData ? orData.low : null;
        const formed = orData ? orData.formed : false;

        el.orHigh.textContent = formatPrice(high);
        el.orLow.textContent = formatPrice(low);
        el.orLabelHigh.textContent = formatPrice(high);
        el.orLabelLow.textContent = formatPrice(low);

        if (!formed || high === null || low === null) {
            el.orStatus.textContent = 'Waiting for Opening Range to form (2:30 - 2:45 PM WAT)...';
            el.orBarFill.style.width = '0%';
            el.orMarkerCurrent.style.display = 'none';
            return;
        }

        el.orStatus.textContent = 'Opening Range formed. Monitoring for breakout...';
        el.orBarFill.style.width = '100%';

        if (currentPrice !== null && currentPrice !== undefined) {
            const range = high - low;
            if (range > 0) {
                const position = ((currentPrice - low) / range) * 100;
                const clamped = Math.max(0, Math.min(100, position));
                el.orMarkerCurrent.style.display = 'block';
                el.orMarkerCurrent.style.left = clamped + '%';
            }
        } else {
            el.orMarkerCurrent.style.display = 'none';
        }
    }

    function updateHistory(history) {
        const tier = getEffectiveTier();
        const features = CONFIG.FEATURES[tier];
        const signals = history || [];

        el.historyCount.textContent = signals.length + ' signal' + (signals.length !== 1 ? 's' : '');
        el.historyBody.innerHTML = '';

        if (signals.length === 0) {
            el.historyBody.innerHTML = '<tr class="empty-row"><td colspan="6">No signals generated yet</td></tr>';
            el.historyBlur.classList.add('hidden');
            return;
        }

        // Free/Guest: blur the history
        if (!features.seeHistory) {
            // Show first 3 rows blurred, then overlay
            signals.slice(0, 3).forEach(signal => {
                const row = document.createElement('tr');
                row.style.filter = 'blur(4px)';
                row.style.opacity = '0.5';
                row.innerHTML = '<td colspan="6" style="text-align:center;padding:20px;">••••••••••</td>';
                el.historyBody.appendChild(row);
            });
            el.historyBlur.classList.remove('hidden');
            return;
        }

        el.historyBlur.classList.add('hidden');

        signals.forEach(signal => {
            const row = document.createElement('tr');
            const typeClass = signal.type ? signal.type.toLowerCase() : '';
            row.innerHTML = '<td><span class="signal-type ' + typeClass + '">' + (signal.type || '--') + '</span></td><td>' + formatPrice(signal.entry) + '</td><td>' + formatPrice(signal.stop_loss) + '</td><td>' + formatPrice(signal.take_profit) + '</td><td>' + (signal.date || '--') + '</td><td>' + (signal.time || '--') + '</td>';
            el.historyBody.appendChild(row);
        });
    }

    function updateStats(signals) {
        const tier = getEffectiveTier();
        if (!CONFIG.FEATURES[tier].seeStats) return;

        const count = signals ? signals.length : 0;
        el.statTotalSignals.textContent = count;

        // Calculate mock stats (in production, track actual outcomes)
        if (count > 0) {
            let totalRisk = 0, totalReward = 0;
            signals.forEach(s => {
                if (s.entry && s.stop_loss) {
                    totalRisk += Math.abs(s.entry - s.stop_loss);
                }
                if (s.entry && s.take_profit) {
                    totalReward += Math.abs(s.take_profit - s.entry);
                }
            });
            el.statWinRate.textContent = 'N/A';
            el.statAvgRisk.textContent = count > 0 ? (totalRisk / count).toFixed(2) : '--';
            el.statAvgReward.textContent = count > 0 ? (totalReward / count).toFixed(2) : '--';
        } else {
            el.statWinRate.textContent = '--';
            el.statAvgRisk.textContent = '--';
            el.statAvgReward.textContent = '--';
        }
    }

    // =============================================================================
    // DATA FETCHING
    // =============================================================================
    async function fetchSignalData() {
        try {
            const cacheBuster = '?_=' + Date.now();
            const response = await fetch('signal.json' + cacheBuster, {
                method: 'GET',
                headers: { 'Accept': 'application/json', 'Cache-Control': 'no-cache' }
            });
            if (!response.ok) throw new Error('HTTP ' + response.status);
            return await response.json();
        } catch (error) {
            console.error('Error fetching signal data:', error);
            return null;
        }
    }

    async function updateDashboard() {
        const data = await fetchSignalData();
        if (!data) return;

        state.signalData = data;

        updatePrice(data.market_data ? data.market_data.current_price : null);
        updateSignalCard(data.latest_signal);
        updateOpeningRange(data.opening_range, data.market_data ? data.market_data.current_price : null);
        updateHistory(data.signal_history);
        updateStats(data.signal_history);
        updateLastUpdated();
        updateSessionStatus();
    }

    // =============================================================================
    // TOAST NOTIFICATIONS
    // =============================================================================
    function showToast(message, type) {
        const toast = document.createElement('div');
        toast.className = 'toast ' + type;
        toast.innerHTML = '<span>' + message + '</span>';
        el.toastContainer.appendChild(toast);

        setTimeout(() => {
            toast.classList.add('toast-out');
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }

    // =============================================================================
    // INITIALIZATION
    // =============================================================================
    function init() {
        initAuth();
        updateSessionStatus();
        setInterval(updateDashboard, CONFIG.refreshInterval);
        setInterval(updateSessionStatus, CONFIG.countdownInterval);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
