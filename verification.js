/**
 * DollarProFx Verification Page JavaScript
 * Handles the multi-step verification flow
 */

// =============================================================================
// DOM ELEMENTS
// =============================================================================

const step1 = document.getElementById('step1');
const step2 = document.getElementById('step2');
const step3 = document.getElementById('step3');
const step4 = document.getElementById('step4');
const step5 = document.getElementById('step5');

const verificationForm = document.getElementById('verificationForm');
const emailInput = document.getElementById('emailInput');
const verifyBtn = document.getElementById('verifyBtn');
const finishedBtn = document.getElementById('finishedBtn');
const tryAgainBtn = document.getElementById('tryAgainBtn');
const copyLinkBtn = document.getElementById('copyLinkBtn');
const partnerLink = document.getElementById('partnerLink');

// Store email for verification
let verificationEmail = '';

// =============================================================================
// STEP NAVIGATION
// =============================================================================

function showStep(stepElement) {
    // Hide all steps
    [step1, step2, step3, step4, step5].forEach(step => {
        if (step) step.classList.add('hidden');
    });

    // Show target step with animation
    if (stepElement) {
        stepElement.classList.remove('hidden');
        stepElement.style.opacity = '0';
        stepElement.style.transform = 'translateY(20px)';

        requestAnimationFrame(() => {
            stepElement.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
            stepElement.style.opacity = '1';
            stepElement.style.transform = 'translateY(0)';
        });
    }
}

// =============================================================================
// FORM HANDLING - STEP 1
// =============================================================================

function isValidEmail(email) {
    const pattern = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
    return pattern.test(email);
}

function setLoading(loading) {
    if (!verifyBtn) return;
    const btnText = verifyBtn.querySelector('.btn-text');
    const btnLoader = verifyBtn.querySelector('.btn-loader');

    if (loading) {
        verifyBtn.disabled = true;
        if (btnText) btnText.style.display = 'none';
        if (btnLoader) btnLoader.style.display = 'flex';
    } else {
        verifyBtn.disabled = false;
        if (btnText) btnText.style.display = 'block';
        if (btnLoader) btnLoader.style.display = 'none';
    }
}

if (verificationForm) {
    verificationForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const email = emailInput.value.trim();

        if (!email) {
            showError('Please enter your email address');
            return;
        }

        if (!isValidEmail(email)) {
            showError('Please enter a valid email address');
            return;
        }

        verificationEmail = email.toLowerCase();

        // Move to step 2 (instructions)
        showStep(step2);
    });
}

function showError(message) {
    // Remove existing error
    const existingError = document.querySelector('.form-error');
    if (existingError) existingError.remove();

    // Create error element
    const errorEl = document.createElement('div');
    errorEl.className = 'form-error';
    errorEl.style.cssText = `
        color: #ef4444;
        font-size: 0.85rem;
        margin-top: 8px;
        padding: 8px 12px;
        background: rgba(239, 68, 68, 0.1);
        border: 1px solid rgba(239, 68, 68, 0.2);
        border-radius: 8px;
    `;
    errorEl.textContent = message;

    const formGroup = document.querySelector('.form-group');
    if (formGroup) {
        formGroup.appendChild(errorEl);
    }

    // Auto remove after 5 seconds
    setTimeout(() => {
        errorEl.remove();
    }, 5000);
}

// =============================================================================
// STEP 2 - FINISHED BUTTON
// =============================================================================

if (finishedBtn) {
    finishedBtn.addEventListener('click', async () => {
        // Move to step 3 (processing)
        showStep(step3);

        // Simulate processing delay then verify
        setTimeout(async () => {
            await performVerification();
        }, 2000);
    });
}

// =============================================================================
// VERIFICATION API CALL
// =============================================================================

async function performVerification() {
    try {
        const response = await fetch(`${window.location.origin}/api/verify`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email: verificationEmail }),
        });

        const data = await response.json();

        if (data.verified) {
            // Show success
            showStep(step4);
        } else {
            // Show failure
            showStep(step5);
        }
    } catch (error) {
        console.error('Verification error:', error);
        // Show failure on error
        showStep(step5);
    }
}

// =============================================================================
// TRY AGAIN BUTTON
// =============================================================================

if (tryAgainBtn) {
    tryAgainBtn.addEventListener('click', () => {
        // Reset and go back to step 1
        verificationEmail = '';
        if (emailInput) emailInput.value = '';
        showStep(step1);
    });
}

// =============================================================================
// COPY PARTNER LINK
// =============================================================================

if (copyLinkBtn && partnerLink) {
    copyLinkBtn.addEventListener('click', async () => {
        const linkText = partnerLink.textContent.trim();

        try {
            await navigator.clipboard.writeText(linkText);

            // Show copied state
            copyLinkBtn.classList.add('copied');
            copyLinkBtn.innerHTML = `
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="20 6 9 17 4 12"></polyline>
                </svg>
            `;

            setTimeout(() => {
                copyLinkBtn.classList.remove('copied');
                copyLinkBtn.innerHTML = `
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                    </svg>
                `;
            }, 2000);
        } catch (err) {
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = linkText;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);

            copyLinkBtn.classList.add('copied');
            setTimeout(() => {
                copyLinkBtn.classList.remove('copied');
            }, 2000);
        }
    });
}

// =============================================================================
// INPUT VALIDATION ON TYPE
// =============================================================================

if (emailInput) {
    emailInput.addEventListener('input', () => {
        // Remove error on type
        const existingError = document.querySelector('.form-error');
        if (existingError) existingError.remove();
    });

    emailInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            if (verifyBtn) verifyBtn.click();
        }
    });
}
