// ETF Monitor - Frontend Application

let monitoringInProgress = false;

// DOM Elements
const startBtn = document.getElementById('startMonitoring');
const progressContainer = document.getElementById('progress');
const progressBar = document.getElementById('progressBar');
const progressText = document.getElementById('progressText');
const resultsContainer = document.getElementById('resultsContainer');
const resultsList = document.getElementById('resultsList');
const slackWebhookInput = document.getElementById('slackWebhook');
const saveSettingsBtn = document.getElementById('saveSettings');

// Stats elements
const totalChecked = document.getElementById('totalChecked');
const totalMatches = document.getElementById('totalMatches');
const totalMismatches = document.getElementById('totalMismatches');
const totalMissing = document.getElementById('totalMissing');
const lastUpdate = document.getElementById('lastUpdate');

// Load settings from localStorage
function loadSettings() {
    const slackWebhook = localStorage.getItem('slackWebhook');
    if (slackWebhook) {
        slackWebhookInput.value = slackWebhook;
    }
}

// Save settings to localStorage
function saveSettings() {
    const slackWebhook = slackWebhookInput.value.trim();
    localStorage.setItem('slackWebhook', slackWebhook);

    // Show feedback
    const originalText = saveSettingsBtn.textContent;
    saveSettingsBtn.textContent = '✓ Gespeichert!';
    saveSettingsBtn.disabled = true;

    setTimeout(() => {
        saveSettingsBtn.textContent = originalText;
        saveSettingsBtn.disabled = false;
    }, 2000);
}

// Start monitoring
async function startMonitoring() {
    if (monitoringInProgress) return;

    monitoringInProgress = true;
    startBtn.disabled = true;
    startBtn.innerHTML = '<span class="btn-icon">⏳</span> Läuft...';
    progressContainer.style.display = 'block';
    resultsContainer.style.display = 'none';

    try {
        // Get Slack webhook from settings
        const slackWebhook = localStorage.getItem('slackWebhook') || '';

        // Call API to start monitoring
        progressText.textContent = 'Starte Monitoring...';
        progressBar.style.width = '10%';

        const response = await fetch('/api/monitor', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                slack_webhook: slackWebhook
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        progressBar.style.width = '50%';
        progressText.textContent = 'Analysiere Websites...';

        const data = await response.json();

        progressBar.style.width = '100%';
        progressText.textContent = 'Fertig!';

        // Display results
        setTimeout(() => {
            displayResults(data);
            progressContainer.style.display = 'none';
        }, 500);

    } catch (error) {
        console.error('Error:', error);
        progressText.textContent = '❌ Fehler: ' + error.message;
        progressBar.style.width = '0%';

        setTimeout(() => {
            progressContainer.style.display = 'none';
        }, 3000);
    } finally {
        monitoringInProgress = false;
        startBtn.disabled = false;
        startBtn.innerHTML = '<span class="btn-icon">▶</span> Check starten';
    }
}

// Display results
function displayResults(data) {
    resultsContainer.style.display = 'block';

    // Update stats
    const stats = calculateStats(data.results);
    totalChecked.textContent = stats.total;
    totalMatches.textContent = stats.matches;
    totalMismatches.textContent = stats.mismatches;
    totalMissing.textContent = stats.missing;

    // Update last update time
    const now = new Date();
    lastUpdate.textContent = `Zuletzt aktualisiert: ${now.toLocaleString('de-DE')}`;

    // Clear previous results
    resultsList.innerHTML = '';

    // Group by ISIN
    const groupedResults = groupByISIN(data.results);

    // Display each ISIN group
    for (const [isin, results] of Object.entries(groupedResults)) {
        const reference = data.reference[isin];
        const isinHeader = createISINHeader(isin, reference);
        resultsList.appendChild(isinHeader);

        // Display each result
        results.forEach(result => {
            const resultItem = createResultItem(result, reference);
            resultsList.appendChild(resultItem);
        });
    }

    // Scroll to results
    resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// Calculate statistics
function calculateStats(results) {
    const stats = {
        total: results.length,
        matches: 0,
        mismatches: 0,
        missing: 0
    };

    results.forEach(result => {
        if (result.status === 'MATCH') {
            stats.matches++;
        } else if (['NAME_MISMATCH', 'TER_MISMATCH', 'BOTH_MISMATCH'].includes(result.status)) {
            stats.mismatches++;
        } else {
            stats.missing++;
        }
    });

    return stats;
}

// Group results by ISIN
function groupByISIN(results) {
    const grouped = {};
    results.forEach(result => {
        if (!grouped[result.isin]) {
            grouped[result.isin] = [];
        }
        grouped[result.isin].push(result);
    });
    return grouped;
}

// Create ISIN header
function createISINHeader(isin, reference) {
    const header = document.createElement('div');
    header.style.cssText = 'background: #f3f4f6; padding: 1rem; border-radius: 0.5rem; margin-bottom: 1rem;';
    header.innerHTML = `
        <div style="font-weight: 700; font-size: 1.125rem; margin-bottom: 0.25rem;">
            ${reference.name}
        </div>
        <div style="color: #6b7280; font-size: 0.875rem;">
            ISIN: ${isin} • Soll-TER: ${reference.ter}%
        </div>
    `;
    return header;
}

// Create result item
function createResultItem(result, reference) {
    const item = document.createElement('div');
    item.className = 'result-item';

    // Determine status class and label
    let statusClass, statusLabel;
    if (result.status === 'MATCH') {
        statusClass = 'status-match';
        statusLabel = '✓ Korrekt';
    } else if (['NAME_MISMATCH', 'TER_MISMATCH', 'BOTH_MISMATCH'].includes(result.status)) {
        statusClass = 'status-mismatch';
        statusLabel = '✗ Fehler';
    } else {
        statusClass = 'status-missing';
        statusLabel = '⚠ Unvollständig';
    }

    // Build details HTML
    let detailsHTML = '';

    // Name details
    if (result.status === 'NAME_MISMATCH' || result.status === 'BOTH_MISMATCH') {
        detailsHTML += `
            <div class="result-detail-row">
                <span class="result-label">Name (Soll):</span>
                <span class="result-value">${escapeHtml(reference.name)}</span>
            </div>
            <div class="result-detail-row">
                <span class="result-label">Name (Ist):</span>
                <span class="result-value mismatch">${escapeHtml(result.name || 'N/A')}</span>
            </div>
        `;
    } else if (result.name) {
        detailsHTML += `
            <div class="result-detail-row">
                <span class="result-label">Name:</span>
                <span class="result-value">${escapeHtml(result.name)}</span>
            </div>
        `;
    }

    // TER details
    if (result.status === 'TER_MISMATCH' || result.status === 'BOTH_MISMATCH') {
        detailsHTML += `
            <div class="result-detail-row">
                <span class="result-label">TER (Soll):</span>
                <span class="result-value">${reference.ter}%</span>
            </div>
            <div class="result-detail-row">
                <span class="result-label">TER (Ist):</span>
                <span class="result-value mismatch">${result.ter !== null ? result.ter + '%' : 'N/A'}</span>
            </div>
        `;
    } else if (result.ter !== null) {
        detailsHTML += `
            <div class="result-detail-row">
                <span class="result-label">TER:</span>
                <span class="result-value">${result.ter}%</span>
            </div>
        `;
    }

    // Source and error info
    if (result.name_source) {
        detailsHTML += `
            <div class="result-detail-row">
                <span class="result-label">Quelle:</span>
                <span class="result-value">${result.name_source}</span>
            </div>
        `;
    }

    if (result.error) {
        detailsHTML += `
            <div class="result-detail-row">
                <span class="result-label">Fehler:</span>
                <span class="result-value mismatch">${escapeHtml(result.error)}</span>
            </div>
        `;
    }

    item.innerHTML = `
        <div class="result-header">
            <div class="result-etf">${getDomainFromURL(result.url)}</div>
            <span class="result-status ${statusClass}">${statusLabel}</span>
        </div>
        <div class="result-url">${escapeHtml(result.url)}</div>
        <div class="result-details">
            ${detailsHTML}
        </div>
    `;

    return item;
}

// Helper function to get domain from URL
function getDomainFromURL(url) {
    try {
        const urlObj = new URL(url);
        return urlObj.hostname.replace('www.', '');
    } catch {
        return url;
    }
}

// Helper function to escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Event listeners
startBtn.addEventListener('click', startMonitoring);
saveSettingsBtn.addEventListener('click', saveSettings);

// Load settings on page load
loadSettings();

// Check if we have recent results in sessionStorage
const recentResults = sessionStorage.getItem('recentResults');
if (recentResults) {
    try {
        const data = JSON.parse(recentResults);
        displayResults(data);
    } catch (e) {
        console.error('Failed to load recent results:', e);
    }
}
