// ETF Monitor - Frontend Application (Naro Style)

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

    const originalText = saveSettingsBtn.textContent;
    saveSettingsBtn.textContent = '✓ Gespeichert!';
    saveSettingsBtn.disabled = true;

    setTimeout(() => {
        saveSettingsBtn.textContent = originalText;
        saveSettingsBtn.disabled = false;
    }, 2000);
}

// Start monitoring (two sequential requests for 18 URLs total)
async function startMonitoring() {
    if (monitoringInProgress) return;

    monitoringInProgress = true;
    startBtn.disabled = true;
    startBtn.textContent = 'Läuft...';
    progressContainer.style.display = 'block';
    resultsContainer.style.display = 'none';

    try {
        const slackWebhook = localStorage.getItem('slackWebhook') || '';
        const allResults = [];

        // Request 1: Check TEQ (9 URLs)
        progressText.textContent = 'Prüfe TEQ ETF... (1/2)';
        progressBar.style.width = '10%';

        const response1 = await fetch('/api/monitor', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                isin: 'LU3098954871',
                slack_webhook: slackWebhook
            })
        });

        if (!response1.ok) {
            throw new Error(`HTTP error! status: ${response1.status}`);
        }

        const data1 = await response1.json();
        allResults.push(...data1.results);

        progressBar.style.width = '50%';
        progressText.textContent = 'Prüfe Inyova ETF... (2/2)';

        // Request 2: Check Inyova (9 URLs)
        const response2 = await fetch('/api/monitor', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                isin: 'LU3075459852',
                slack_webhook: slackWebhook
            })
        });

        if (!response2.ok) {
            throw new Error(`HTTP error! status: ${response2.status}`);
        }

        const data2 = await response2.json();
        allResults.push(...data2.results);

        progressBar.style.width = '100%';
        progressText.textContent = 'Fertig! 18 URLs geprüft.';

        // Combine results from both requests
        const combinedData = {
            success: true,
            results: allResults,
            reference: data1.reference,  // Same for both
            note: 'Agentic workflow (parallel) - intelligent extraction with Claude Haiku'
        };

        setTimeout(() => {
            displayResults(combinedData);
            progressContainer.style.display = 'none';
        }, 500);

    } catch (error) {
        console.error('Error:', error);
        progressText.textContent = '✗ Fehler: ' + error.message;
        progressBar.style.width = '0%';

        setTimeout(() => {
            progressContainer.style.display = 'none';
        }, 3000);
    } finally {
        monitoringInProgress = false;
        startBtn.disabled = false;
        startBtn.textContent = 'Check starten';
    }
}

// Display results
function displayResults(data) {
    resultsContainer.style.display = 'block';

    const stats = calculateStats(data.results);
    totalChecked.textContent = stats.total;
    totalMatches.textContent = stats.matches;
    totalMismatches.textContent = stats.mismatches;
    totalMissing.textContent = stats.missing;

    const now = new Date();
    lastUpdate.textContent = `Zuletzt aktualisiert: ${now.toLocaleString('de-DE')}`;

    resultsList.innerHTML = '';

    const groupedResults = groupByISIN(data.results);

    for (const [isin, results] of Object.entries(groupedResults)) {
        const reference = data.reference[isin];
        const isinHeader = createISINHeader(isin, reference);
        resultsList.appendChild(isinHeader);

        results.forEach(result => {
            const resultItem = createResultItem(result, reference);
            resultsList.appendChild(resultItem);
        });
    }

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
    header.style.cssText = 'padding: 1rem; border-bottom: 1px solid #E0E0E0; margin-bottom: 1.25rem; background: #FAFAFA;';
    header.innerHTML = `
        <div style="font-weight: 600; font-size: 1rem; margin-bottom: 0.25rem; color: #000;">
            ${escapeHtml(reference.name)}
        </div>
        <div style="color: #757575; font-size: 0.8125rem;">
            ISIN: ${isin} • Soll-TER: ${reference.ter}%
        </div>
    `;
    return header;
}

// Create result item with detailed error messages
function createResultItem(result, reference) {
    const item = document.createElement('div');
    item.className = 'result-item';

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

    let detailsHTML = '';

    // Show agent explanation (main insight)
    if (result.explanation) {
        detailsHTML += `
            <div class="detail-section" style="background: #FAFAFA; padding: 0.75rem; border-radius: 4px; margin-bottom: 0.75rem;">
                <div style="color: #424242; font-size: 0.875rem; line-height: 1.6;">
                    ${escapeHtml(result.explanation)}
                </div>
            </div>
        `;
    }

    // Show extracted values
    if (result.status === 'MATCH') {
        detailsHTML += `
            <div class="detail-section">
                <div style="color: #2E7D32;">
                    ✓ Name: ${escapeHtml(result.name)}<br>
                    ✓ TER: ${result.ter}%
                </div>
            </div>
        `;
    } else if (result.status === 'NAME_MISMATCH' || result.status === 'BOTH_MISMATCH') {
        detailsHTML += `
            <div class="detail-section">
                <div class="detail-label">Name:</div>
                <div style="color: #757575; margin-top: 0.25rem;">
                    <div>Soll: <strong>${escapeHtml(reference.name)}</strong></div>
                    <div style="margin-top: 0.25rem;">Ist: <span style="color: #C62828; font-weight: 500;">${escapeHtml(result.name || 'Nicht gefunden')}</span></div>
                </div>
            </div>
        `;
    }

    if (result.status === 'TER_MISMATCH' || result.status === 'BOTH_MISMATCH') {
        detailsHTML += `
            <div class="detail-section">
                <div class="detail-label">TER:</div>
                <div style="color: #757575; margin-top: 0.25rem;">
                    <div>Soll: <strong>${reference.ter}%</strong></div>
                    <div style="margin-top: 0.25rem;">Ist: <span style="color: #C62828; font-weight: 500;">${result.ter !== null ? result.ter + '%' : 'Nicht gefunden'}</span></div>
                </div>
            </div>
        `;
    }

    if (result.status === 'TER_MISSING') {
        detailsHTML += `
            <div class="detail-section">
                <div style="color: #757575;">
                    ${result.name ? '✓ Name: ' + escapeHtml(result.name) + '<br>' : ''}
                    ⚠ TER: Nicht gefunden
                </div>
            </div>
        `;
    }

    // Error cases
    if (result.error) {
        detailsHTML += `
            <div class="detail-section">
                <div class="detail-label">Fehler:</div>
                <div style="color: #C62828; margin-top: 0.25rem;">
                    ${escapeHtml(result.error)}
                </div>
            </div>
        `;
    }

    item.innerHTML = `
        <div class="result-header">
            <div class="result-domain">${getDomainFromURL(result.url)}</div>
            <span class="result-status ${statusClass}">${statusLabel}</span>
        </div>
        <div class="result-url">${escapeHtml(result.url)}</div>
        <div class="result-details">
            ${detailsHTML}
        </div>
    `;

    return item;
}

// Get name difference description
function getNameDifference(expected, actual) {
    if (!actual) return 'Name nicht gefunden';

    const expectedLower = expected.toLowerCase();
    const actualLower = actual.toLowerCase();

    if (expectedLower.includes(actualLower)) {
        const missing = expected.replace(new RegExp(actual.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i'), '').trim();
        return `Fehlt: "${missing}"`;
    } else if (actualLower.includes(expectedLower)) {
        return 'Enthält zusätzliche Zeichen';
    } else {
        return 'Komplett unterschiedlich';
    }
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
