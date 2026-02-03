document.addEventListener('DOMContentLoaded', () => {
    // Start game on load
    startGame();

    // Bind buttons
    document.getElementById('btn-share').addEventListener('click', shareReport);
    document.getElementById('btn-smuggle-trigger').addEventListener('click', () => {
        showSmuggleOptions();
    });

    const buttons = document.querySelectorAll('.btn[data-action]');
    buttons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const action = e.currentTarget.getAttribute('data-action');
            handleMove(action, 1);
        });
    });
});

function showSmuggleOptions() {
    document.getElementById('smuggle-options').classList.remove('hidden');
    document.getElementById('btn-smuggle-trigger').classList.add('hidden');
}

function hideSmuggleOptions() {
    document.getElementById('smuggle-options').classList.add('hidden');
    document.getElementById('btn-smuggle-trigger').classList.remove('hidden');
}

function triggerSmuggle(amount) {
    hideSmuggleOptions();
    handleMove(1, amount); // Action 1 = Smuggle
}

let isProcessing = false;

async function startGame() {
    log('Initializing core systems...', 'system');
    document.getElementById('game-over-screen').classList.add('hidden');
    document.getElementById('game-log').innerHTML = ''; // Request clear

    try {
        const res = await fetch('/api/start', { method: 'POST' });
        const data = await res.json();
        updateState(data);
        log('Connection established. Smuggling operation active.', 'success');
        typewriter("I'm watching you closely...", document.getElementById('inspector-text'));
    } catch (e) {
        log('Connection error.', 'fail');
    }
}

async function handleMove(action, amount = 1) {
    if (isProcessing) return;
    isProcessing = true;
    disableControls(true);

    // Log player intent immediately
    const actionMap = { 1: 'Smuggle', 2: 'Lay Low', 3: 'Offer Bribe', 4: 'Signal Truce' };
    let actionName = actionMap[action];
    if (action == 1) actionName += ` (x${amount})`;

    log(`> Initiating: ${actionName}...`, 'player');

    // Show inspector "thinking"
    document.getElementById('inspector-status').innerText = "ANALYZING...";
    document.getElementById('inspector-status').classList.add('blink');

    try {
        const res = await fetch('/api/move', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: action, amount: amount })
        });

        const result = await res.json();

        if (result.error) {
            log(`Error: ${result.error}`, 'fail');
            return;
        }

        // Delay for effect (Simulate network/reveal)
        setTimeout(() => {
            processRoundResult(result);
        }, 800);

    } catch (e) {
        log('Transmission failure.', 'fail');
        isProcessing = false;
        disableControls(false);
    }
}

function processRoundResult(result) {
    document.getElementById('inspector-status').classList.remove('blink');
    document.getElementById('inspector-status').innerText = "VIGILANT";

    // Update Score & Round
    animateValue('score-val', parseInt(document.getElementById('score-val').innerText), result.total_score, 1000);
    document.getElementById('round-val').innerText = `${result.round}/20`;

    // Log Outcome
    let outcomeClass = 'neutral';
    if (result.payoff > 0) outcomeClass = 'success';
    if (result.payoff < 0) outcomeClass = 'fail';

    const pAction = result.player_action_name;
    const iAction = result.inspector_action_name;

    // Specific Alerts
    if (result.was_trap) {
        showAlert("IT'S A TRAP!", "alert-red");
    } else if (result.player_action == 1 && result.inspector_action == 1) { // Caught
        showAlert("BUSTED! INSPECTION CAUGHT CONTRABAND!", "alert-red");
    } else if (result.player_action == 1 && result.inspector_action == 2) { // Success
        showAlert("SMUGGLE SUCCESSFUL", "primary-green");
    }

    // Log Construction
    // Log Construction
    let logHTML = `Op: ${pAction} | Inspector: ${iAction} <br> Outcome: ${result.payoff > 0 ? '+' : ''}${result.payoff}`;
    if (result.player_action == 1) logHTML += ` (Vol: ${result.amount})`;
    log(logHTML, outcomeClass);
    log(`Insight: ${result.insight}`, 'system');

    // Inspector Dialogue
    if (result.flavor && result.flavor.reaction) {
        typewriter(result.flavor.reaction, document.getElementById('inspector-text'));
    }

    // Trust Meter Update
    // Fetch state to get updated trust (could be optimized)
    fetch('/api/state')
        .then(r => r.json())
        .then(state => {
            document.getElementById('trust-fill').style.width = `${state.trust_level * 100}%`;

            if (state.game_over) {
                endGame(state);
            } else {
                isProcessing = false;
                disableControls(false);
            }
        })
        .catch(e => {
            log('State sync error: ' + e, 'fail');
            isProcessing = false;
            disableControls(false);
        });
}

function updateState(data) {
    document.getElementById('round-val').innerText = `${data.round}/${data.max_rounds}`;
    document.getElementById('score-val').innerText = data.score;
    document.getElementById('trust-fill').style.width = `${data.trust_level * 100}%`;
}

function endGame(state) {
    setTimeout(() => {
        document.getElementById('game-over-screen').classList.remove('hidden');
        document.getElementById('final-score').innerText = `FINAL SCORE: ${state.score}`;

        let verdict = "OPERATIVE";
        if (state.score > 50) verdict = "MASTERMIND";
        if (state.score < 0) verdict = "COMPROMISED";

        document.getElementById('final-verdict').innerText = verdict;

        // Render Insights
        const reportContainer = document.getElementById('debrief-report');
        reportContainer.innerHTML = ''; // Clear previous

        if (state.tutor_report) {
            state.tutor_report.forEach(item => {
                const card = document.createElement('div');
                card.className = `insight-card rank-${item.rating}`;
                card.innerHTML = `
                    <div class="insight-header">
                        <span class="concept">${item.concept}</span>
                        <span class="rating-badge">${item.rating}</span>
                    </div>
                    <div class="insight-body">
                        <p class="definition">${item.definition}</p>
                        <p class="analysis">${item.analysis}</p>
                    </div>
                `;
                reportContainer.appendChild(card);
            });
        }
    }, 1500);
}

// UTILS
function log(msg, type = 'neutral') {
    const consoleEl = document.getElementById('game-log');
    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;
    entry.innerHTML = msg; // Allow HTML
    consoleEl.appendChild(entry);
    consoleEl.scrollTop = consoleEl.scrollHeight;
}

function disableControls(disabled) {
    document.querySelectorAll('.btn').forEach(b => b.disabled = disabled);
    if (!disabled) {
        // Ensure options logic is reset
        hideSmuggleOptions();

        // Hide options if they were open during disable
        document.getElementById('smuggle-options').classList.add('hidden');
        document.getElementById('btn-smuggle-trigger').classList.remove('hidden');
    }
}

function showAlert(msg, colorVar) {
    const box = document.getElementById('alert-box');
    const txt = document.getElementById('alert-msg');
    txt.innerText = msg;
    box.style.borderColor = `var(--${colorVar})`;
    box.style.boxShadow = `0 0 30px var(--${colorVar})`;

    box.classList.remove('hidden', 'visible');
    void box.offsetWidth; // trigger reflow
    box.classList.add('visible');

    setTimeout(() => {
        box.classList.remove('visible');
        setTimeout(() => box.classList.add('hidden'), 300);
    }, 2000);
}

function typewriter(text, element) {
    let i = 0;
    const speed = 30;

    function type() {
        if (i <= text.length) {
            element.textContent = text.substring(0, i);
            i++;
            setTimeout(type, speed);
        }
    }
    type();
}

function animateValue(id, start, end, duration) {
    const obj = document.getElementById(id);
    let startTimestamp = null;
    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        obj.innerHTML = Math.floor(progress * (end - start) + start);
        if (progress < 1) {
            window.requestAnimationFrame(step);
        }
    };
    window.requestAnimationFrame(step);
}

// SOCIAL SHARING
async function shareReport() {
    const btn = document.getElementById('btn-share');
    const originalText = btn.innerText;
    btn.innerText = "CAPTURING...";
    btn.disabled = true;

    // Image Capture Function
    const captureImage = async () => {
        if (typeof html2canvas === 'undefined') throw new Error("html2canvas not loaded");

        const scanline = document.querySelector('.scanline');
        const crt = document.querySelector('.crt-overlay');
        if (scanline) scanline.style.display = 'none';
        if (crt) crt.style.display = 'none';

        try {
            const element = document.getElementById('game-over-screen');
            // 5s Timeout Protection
            const canvasPromise = html2canvas(element, {
                backgroundColor: "#050505",
                scale: 2,
                logging: false,
                useCORS: true
            });

            const timeoutPromise = new Promise((_, reject) =>
                setTimeout(() => reject(new Error("Timeout")), 5000)
            );

            const canvas = await Promise.race([canvasPromise, timeoutPromise]);
            const blob = await new Promise(resolve => canvas.toBlob(resolve));
            if (!blob) throw new Error("Blob failed");

            await navigator.clipboard.write([new ClipboardItem({ "image/png": blob })]);
            return true;

        } finally {
            if (scanline) scanline.style.display = 'block';
            if (crt) crt.style.display = 'block';
        }
    };

    // Execution Flow (Copy Only)
    try {
        await captureImage();

        // Success feedback
        btn.innerText = "COPIED!";
        alert("✅ SCORECARD COPIED!\n\nImage is ready to paste anywhere.");

    } catch (e) {
        console.error("Image Capture Failed:", e);
        alert("⚠️ Image capture failed: " + e.message);
    } finally {
        setTimeout(() => {
            btn.innerText = originalText;
            btn.disabled = false;
        }, 1500);
    }
}
