/**
 * DollarProFx - Verification Page JavaScript
 * Handles the multi-step verification flow
 */

(function() {
  'use strict';

  // ── DOM Elements ────────────────────────────────────────────────
  const navbar = document.getElementById('navbar');
  const mobileToggle = document.getElementById('mobileToggle');
  const navLinks = document.getElementById('navLinks');

  const stepEmail = document.getElementById('stepEmail');
  const stepInstructions = document.getElementById('stepInstructions');
  const stepLoading = document.getElementById('stepLoading');
  const stepSuccess = document.getElementById('stepSuccess');
  const stepFailure = document.getElementById('stepFailure');

  const verificationForm = document.getElementById('verificationForm');
  const exnessEmail = document.getElementById('exnessEmail');
  const finishedBtn = document.getElementById('finishedBtn');
  const tryAgainBtn = document.getElementById('tryAgainBtn');
  const partnerLinkBox = document.getElementById('partnerLinkBox');

  let storedEmail = '';
  const API_BASE = window.location.origin;

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

  // ── Copy Partner Link ───────────────────────────────────────────
  if (partnerLinkBox) {
    partnerLinkBox.addEventListener('click', function() {
      const text = this.textContent.trim();

      if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(() => {
          showCopyFeedback(this);
        }).catch(() => {
          fallbackCopy(text, this);
        });
      } else {
        fallbackCopy(text, this);
      }
    });
  }

  function fallbackCopy(text, element) {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.opacity = '0';
    document.body.appendChild(textarea);
    textarea.select();

    try {
      document.execCommand('copy');
      showCopyFeedback(element);
    } catch (err) {
      console.error('Copy failed:', err);
    }

    document.body.removeChild(textarea);
  }

  function showCopyFeedback(element) {
    const original = element.innerHTML;
    element.innerHTML = '<i class="fas fa-check"></i> Copied to clipboard!';
    element.style.color = 'var(--buy-green)';
    element.style.borderStyle = 'solid';

    setTimeout(() => {
      element.innerHTML = original;
      element.style.color = '';
      element.style.borderStyle = '';
    }, 2000);
  }

  // ── Step Navigation ─────────────────────────────────────────────
  function showStep(stepElement) {
    stepEmail.style.display = 'none';
    stepInstructions.style.display = 'none';
    stepLoading.style.display = 'none';
    stepSuccess.style.display = 'none';
    stepFailure.style.display = 'none';

    stepElement.style.display = 'block';

    // Scroll to top of card smoothly
    const card = document.getElementById('verificationCard');
    if (card) {
      setTimeout(() => {
        card.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }, 50);
    }
  }

  // ── Email Validation ────────────────────────────────────────────
  function validateEmail(email) {
    if (!email || typeof email !== 'string') return false;
    email = email.trim().toLowerCase();

    if (email.length === 0 || email.length > 254) return false;
    if (!email.includes('@') || !email.includes('.')) return false;
    if (email.split('@').length !== 2) return false;

    const [local, domain] = email.split('@');
    if (!local || !domain) return false;
    if (domain.includes('..') || domain.startsWith('.') || domain.endsWith('.')) return false;
    if (!domain.includes('.')) return false;

    return true;
  }

  function showFieldError(input, message) {
    input.style.borderColor = 'var(--sell-red)';

    let tooltip = input.parentNode.querySelector('.field-error');
    if (!tooltip) {
      tooltip = document.createElement('div');
      tooltip.className = 'field-error';
      tooltip.style.cssText = 'color: var(--sell-red); font-size: 0.85rem; margin-top: 0.5rem; animation: fadeInUp 0.2s ease;';
      input.parentNode.appendChild(tooltip);
    }
    tooltip.textContent = message;

    setTimeout(() => {
      input.style.borderColor = '';
      if (tooltip) tooltip.remove();
    }, 4000);
  }

  // ── Form Submission (Step 1 → Step 2) ──────────────────────────
  if (verificationForm) {
    verificationForm.addEventListener('submit', function(e) {
      e.preventDefault();

      const email = exnessEmail.value.trim();

      if (!validateEmail(email)) {
        showFieldError(exnessEmail, 'Please enter a valid email address');
        return;
      }

      storedEmail = email;
      showStep(stepInstructions);
    });
  }

  // ── Finished Button (Step 2 → Step 3) ─────────────────────────
  if (finishedBtn) {
    finishedBtn.addEventListener('click', function() {
      showStep(stepLoading);

      // Call verification API after brief delay for UX
      setTimeout(() => {
        verifyAccount(storedEmail);
      }, 1500);
    });
  }

  // ── API Verification ────────────────────────────────────────────
  async function verifyAccount(email) {
    try {
      const response = await fetch(`${API_BASE}/api/verify`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({ email: email })
      });

      const result = await response.json();

      if (result.success) {
        showStep(stepSuccess);
      } else {
        showStep(stepFailure);
      }

    } catch (error) {
      console.error('Verification error:', error);
      showStep(stepFailure);
    }
  }

  // ── Try Again Button ────────────────────────────────────────────
  if (tryAgainBtn) {
    tryAgainBtn.addEventListener('click', function() {
      storedEmail = '';
      if (exnessEmail) {
        exnessEmail.value = '';
        exnessEmail.style.borderColor = '';
      }
      showStep(stepEmail);
    });
  }

  // ── Initialize ──────────────────────────────────────────────────
  // Ensure only step 1 is visible on load
  showStep(stepEmail);

})();
