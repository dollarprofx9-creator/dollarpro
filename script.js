/* ============================================
   TIME SCALE — Main JavaScript
   ============================================ */

// ==========================================
// PARTICLE BACKGROUND
// ==========================================
const canvas = document.getElementById('particleCanvas');
const ctx = canvas.getContext('2d');
let particles = [];
let animationId;

function resizeCanvas() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
}

class Particle {
    constructor() {
        this.reset();
    }
    
    reset() {
        this.x = Math.random() * canvas.width;
        this.y = Math.random() * canvas.height;
        this.size = Math.random() * 2 + 0.5;
        this.speedX = (Math.random() - 0.5) * 0.3;
        this.speedY = (Math.random() - 0.5) * 0.3;
        this.opacity = Math.random() * 0.5 + 0.1;
        this.life = Math.random() * 100 + 100;
        this.maxLife = this.life;
    }
    
    update() {
        this.x += this.speedX;
        this.y += this.speedY;
        this.life--;
        
        if (this.life <= 0 || this.x < 0 || this.x > canvas.width || this.y < 0 || this.y > canvas.height) {
            this.reset();
        }
    }
    
    draw() {
        const fadeRatio = this.life / this.maxLife;
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(0, 212, 255, ${this.opacity * fadeRatio})`;
        ctx.fill();
    }
}

function initParticles() {
    particles = [];
    const count = Math.min(100, Math.floor((canvas.width * canvas.height) / 15000));
    for (let i = 0; i < count; i++) {
        particles.push(new Particle());
    }
}

function animateParticles() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    particles.forEach(p => {
        p.update();
        p.draw();
    });
    
    // Draw connections
    for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
            const dx = particles[i].x - particles[j].x;
            const dy = particles[i].y - particles[j].y;
            const dist = Math.sqrt(dx * dx + dy * dy);
            
            if (dist < 120) {
                ctx.beginPath();
                ctx.moveTo(particles[i].x, particles[i].y);
                ctx.lineTo(particles[j].x, particles[j].y);
                ctx.strokeStyle = `rgba(0, 212, 255, ${0.08 * (1 - dist / 120)})`;
                ctx.lineWidth = 0.5;
                ctx.stroke();
            }
        }
    }
    
    animationId = requestAnimationFrame(animateParticles);
}

resizeCanvas();
initParticles();
animateParticles();

window.addEventListener('resize', () => {
    resizeCanvas();
    initParticles();
});

// ==========================================
// NAVIGATION
// ==========================================
const navbar = document.getElementById('navbar');
const mobileMenuBtn = document.getElementById('mobileMenuBtn');
const navLinks = document.getElementById('navLinks');
const navLinkItems = document.querySelectorAll('.nav-link');

// Mobile menu toggle
mobileMenuBtn.addEventListener('click', () => {
    navLinks.classList.toggle('active');
});

// Close mobile menu on link click
navLinkItems.forEach(link => {
    link.addEventListener('click', () => {
        navLinks.classList.remove('active');
    });
});

// Active nav on scroll
window.addEventListener('scroll', () => {
    if (window.scrollY > 50) {
        navbar.style.background = 'rgba(5, 5, 8, 0.95)';
    } else {
        navbar.style.background = 'rgba(5, 5, 8, 0.8)';
    }
    
    // Update active link
    const sections = document.querySelectorAll('section[id]');
    let current = '';
    
    sections.forEach(section => {
        const sectionTop = section.offsetTop - 100;
        if (window.scrollY >= sectionTop) {
            current = section.getAttribute('id');
        }
    });
    
    navLinkItems.forEach(link => {
        link.classList.remove('active');
        if (link.getAttribute('href') === `#${current}`) {
            link.classList.add('active');
        }
    });
});

// ==========================================
// TIME SCALE DATA
// ==========================================
const timeUnits = [
    { name: 'Millennium', symbol: 'M', seconds: 31536000000, desc: 'One thousand years. The span of ancient civilizations.' },
    { name: 'Century', symbol: 'C', seconds: 3153600000, desc: 'One hundred years. A human lifetime barely touches one.' },
    { name: 'Decade', symbol: 'D', seconds: 315360000, desc: 'Ten years. The rhythm of cultural shifts and generations.' },
    { name: 'Year', symbol: 'Y', seconds: 31536000, desc: 'Earth\'s full orbit around the Sun. 365.25 days.' },
    { name: 'Month', symbol: 'Mo', seconds: 2628000, desc: 'The Moon\'s cycle. Approximately 30.44 days.' },
    { name: 'Week', symbol: 'W', seconds: 604800, desc: 'Seven days. The rhythm of modern civilization.' },
    { name: 'Day', symbol: 'D', seconds: 86400, desc: 'One full rotation of Earth. Sunrise to sunrise.' },
    { name: 'Hour', symbol: 'H', seconds: 3600, desc: 'One twenty-fourth of a day. The unit of work and rest.' },
    { name: 'Minute', symbol: 'Min', seconds: 60, desc: 'Sixty seconds. The heartbeat of scheduling.' },
    { name: 'Second', symbol: 'S', seconds: 1, desc: 'The SI base unit of time. 9,192,631,770 caesium vibrations.' },
    { name: 'Millisecond', symbol: 'Ms', seconds: 0.001, desc: 'One thousandth of a second. The realm of perception and computing.' }
];

// ==========================================
// TIME SCALE VISUALIZATION
// ==========================================
const timeScaleVisual = document.getElementById('timeScaleVisual');
const detailTitle = document.getElementById('detailTitle');
const detailValue = document.getElementById('detailValue');
const detailDesc = document.getElementById('detailDesc');
const detailConversions = document.getElementById('detailConversions');
const detailIcon = document.getElementById('detailIcon');

function renderTimeScale() {
    timeScaleVisual.innerHTML = '';
    
    timeUnits.forEach((unit, index) => {
        const unitEl = document.createElement('div');
        unitEl.className = 'time-unit';
        unitEl.dataset.index = index;
        
        unitEl.innerHTML = `
            <div class="time-unit-name">${unit.name.toUpperCase()}</div>
            <div class="time-unit-value">1 ${unit.symbol}</div>
        `;
        
        unitEl.addEventListener('click', () => selectTimeUnit(index));
        timeScaleVisual.appendChild(unitEl);
        
        if (index < timeUnits.length - 1) {
            const arrow = document.createElement('div');
            arrow.className = 'time-unit-arrow';
            arrow.innerHTML = '→';
            arrow.style.display = 'flex';
            timeScaleVisual.appendChild(arrow);
        }
    });
}

function selectTimeUnit(index) {
    const units = document.querySelectorAll('.time-unit');
    units.forEach(u => u.classList.remove('active'));
    units[index].classList.add('active');
    
    const unit = timeUnits[index];
    detailTitle.textContent = unit.name;
    detailValue.textContent = `1 ${unit.name}`;
    detailDesc.textContent = unit.desc;
    detailIcon.textContent = ['◈','◉','◎','◐','◑','◒','◓','◔','◕','●','◐'][index] || '◈';
    
    // Generate conversions
    detailConversions.innerHTML = '';
    const conversions = [
        { label: 'Milliseconds', value: unit.seconds * 1000 },
        { label: 'Seconds', value: unit.seconds },
        { label: 'Minutes', value: unit.seconds / 60 },
        { label: 'Hours', value: unit.seconds / 3600 },
        { label: 'Days', value: unit.seconds / 86400 },
        { label: 'Weeks', value: unit.seconds / 604800 },
        { label: 'Months', value: unit.seconds / 2628000 },
        { label: 'Years', value: unit.seconds / 31536000 }
    ];
    
    conversions.forEach(conv => {
        if (conv.value >= 0.001 || conv.value === 0) {
            const item = document.createElement('div');
            item.className = 'conv-item';
            let displayValue;
            if (conv.value >= 1000000) {
                displayValue = conv.value.toExponential(3);
            } else if (conv.value >= 1) {
                displayValue = conv.value.toLocaleString('en-US', { maximumFractionDigits: 2 });
            } else if (conv.value >= 0.001) {
                displayValue = conv.value.toFixed(4);
            } else {
                displayValue = conv.value.toExponential(3);
            }
            item.innerHTML = `
                <div class="conv-item-label">${conv.label}</div>
                <div class="conv-item-value">${displayValue}</div>
            `;
            detailConversions.appendChild(item);
        }
    });
}

renderTimeScale();
selectTimeUnit(4); // Default to Month

// ==========================================
// LIVE TIME CLOCK
// ==========================================
function updateLiveTime() {
    const now = new Date();
    
    const timeStr = now.toLocaleTimeString('en-US', { hour12: false });
    const dateStr = now.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
    
    document.getElementById('liveTime').textContent = timeStr;
    document.getElementById('liveDate').textContent = dateStr;
    document.getElementById('liveDay').textContent = now.toLocaleDateString('en-US', { weekday: 'long' });
    document.getElementById('liveMonth').textContent = now.toLocaleDateString('en-US', { month: 'long' });
    document.getElementById('liveYear').textContent = now.getFullYear();
    document.getElementById('liveCentury').textContent = `${Math.ceil(now.getFullYear() / 100)}th Century`;
    document.getElementById('liveUnix').textContent = Math.floor(now.getTime() / 1000);
    
    // Week number calculation
    const startOfYear = new Date(now.getFullYear(), 0, 1);
    const daysPassed = (now - startOfYear) / 86400000;
    const weekNum = Math.ceil((daysPassed + startOfYear.getDay() + 1) / 7);
    document.getElementById('liveWeek').textContent = `Week ${weekNum}`;
}

updateLiveTime();
setInterval(updateLiveTime, 1000);

// ==========================================
// RANDOMIZER
// ==========================================
const modeBtns = document.querySelectorAll('.mode-btn');
const startBtn = document.getElementById('startRandomBtn');
const pauseBtn = document.getElementById('pauseRandomBtn');
const randomizerResult = document.getElementById('randomizerResult');
const randomizerStatus = document.getElementById('randomizerStatus');

let currentMode = 'moment';
let randomInterval = null;
let isRandomizing = false;

const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const daysOfWeek = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

modeBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        if (isRandomizing) return;
        modeBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentMode = btn.dataset.mode;
        randomizerResult.innerHTML = '<div class="result-placeholder">Press START to begin randomizing</div>';
    });
});

function getRandomYear() {
    return Math.floor(Math.random() * 10000) - 2000; // -2000 to 8000
}

function getRandomMonth() {
    return months[Math.floor(Math.random() * 12)];
}

function getRandomDay() {
    return Math.floor(Math.random() * 28) + 1;
}

function getRandomHour() {
    return String(Math.floor(Math.random() * 24)).padStart(2, '0');
}

function getRandomMinute() {
    return String(Math.floor(Math.random() * 60)).padStart(2, '0');
}

function getRandomSecond() {
    return String(Math.floor(Math.random() * 60)).padStart(2, '0');
}

function generateRandomResult() {
    switch(currentMode) {
        case 'moment':
            return `
                <div class="result-item highlight"><span class="result-label">Year</span><span class="result-value">${getRandomYear()}</span></div>
                <div class="result-item"><span class="result-label">Month</span><span class="result-value">${getRandomMonth()}</span></div>
                <div class="result-item"><span class="result-label">Day</span><span class="result-value">${getRandomDay()}</span></div>
                <div class="result-item"><span class="result-label">Time</span><span class="result-value">${getRandomHour()}:${getRandomMinute()}:${getRandomSecond()}</span></div>
                <div class="result-item"><span class="result-label">Time Scale</span><span class="result-value">${timeUnits[Math.floor(Math.random() * timeUnits.length)].name}</span></div>
            `;
        case 'year':
            return `<div class="result-item highlight"><span class="result-label">Random Year</span><span class="result-value">${getRandomYear()}</span></div>`;
        case 'date':
            return `
                <div class="result-item highlight"><span class="result-label">Date</span><span class="result-value">${getRandomMonth()} ${getRandomDay()}</span></div>
                <div class="result-item"><span class="result-label">Year</span><span class="result-value">${getRandomYear()}</span></div>
            `;
        case 'hour':
            return `<div class="result-item highlight"><span class="result-label">Random Hour</span><span class="result-value">${getRandomHour()}:00</span></div>`;
        case 'minute':
            return `<div class="result-item highlight"><span class="result-label">Random Minute</span><span class="result-value">${getRandomHour()}:${getRandomMinute()}</span></div>`

