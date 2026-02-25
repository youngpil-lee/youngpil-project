const API_BASE = '/api/kr';

// -- Utility Functions --
function log(message, type = 'info') {
    const consoleLog = document.getElementById('console-log');
    const time = new Date().toLocaleTimeString('ko-KR', { hour12: false });
    const div = document.createElement('div');
    div.className = 'log-entry';

    let color = '#fff';
    if (type === 'error') color = 'var(--accent-red)';
    if (type === 'success') color = 'var(--accent-green)';
    if (type === 'warn') color = 'var(--accent-cyan)';

    div.innerHTML = `<span class="log-time">${time}</span> <span style="color: ${color}">[${type.toUpperCase()}] ${message}</span>`;
    consoleLog.appendChild(div);
    consoleLog.scrollTop = consoleLog.scrollHeight;
}

// -- API Callers --
async function callAPI(endpoint, method = 'POST', body = null) {
    try {
        const options = {
            method,
            headers: { 'Content-Type': 'application/json' }
        };
        if (body) options.body = JSON.stringify(body);

        const response = await fetch(`${API_BASE}${endpoint}`, options);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        return await response.json();
    } catch (e) {
        log(`API Error: ${e.message}`, 'error');
        return null;
    }
}

// -- UI Feedback --
function showLoading() {
    document.getElementById('loading-overlay').style.display = 'flex';
    document.body.style.cursor = 'wait';
}

function hideLoading() {
    document.getElementById('loading-overlay').style.display = 'none';
    document.body.style.cursor = 'default';
}

// -- Dashboard Functions --
async function runFunction(name) {
    showLoading();
    log(`${name.toUpperCase()} 기능을 시작합니다...`, 'warn');

    try {
        switch (name) {
            case 'screening':
                const screeningData = await callAPI('/screening');
                if (screeningData && screeningData.data) {
                    renderScreener(screeningData.data);
                    log(`[SUCCESS] 스크리닝 완료: ${screeningData.count} 종목 탐지`, 'success');
                    screeningData.data.slice(0, 3).forEach(s => log(` > ${s.name}(${s.ticker}): 외인수급 ${formatNumber(s.foreign_buy)}`));
                }
                break;

            case 'vcp':
                const vcpData = await callAPI('/vcp-signals');
                if (vcpData && vcpData.signals) {
                    renderVCP(vcpData.signals);
                    log(`[SUCCESS] VCP 스캔 완료: ${vcpData.count} 시그널 발견`, 'success');
                    vcpData.signals.slice(0, 3).forEach(s => log(` > ${s.name}(${s.ticker}): 점수 ${s.score || 0}점`));
                }
                break;

            case 'closing-bet':
                log('[WARN] CLOSING-BET 분석을 시작합니다... (약 1-2분 소요)', 'warn');
                const v2Data = await callAPI('/closing-bet-v2');
                if (v2Data && v2Data.signals) {
                    renderPremium(v2Data.signals);
                    log(`[SUCCESS] 종가V2 시그널 완료: ${v2Data.filtered_count}개 생성`, 'success');
                    v2Data.signals.slice(0, 3).forEach(s => log(` > ${s.stock_name}: ${s.grade}급 (${s.score.total}점)`));
                }
                break;

            case 'ai-market':
                const aiData = await callAPI('/ai/analyze-market');
                if (aiData && aiData.analysis) {
                    renderAI(aiData.analysis);
                    log(`[SUCCESS] AI 시장 분석 리포트 생성 완료`, 'success');
                    const summary = aiData.analysis.summary || "";
                    log(` > AI 요약: ${summary.substring(0, 50)}...`);
                }
                break;

            case 'backtest':
                const backtestData = await callAPI('/backtest/run');
                if (backtestData) {
                    log(`[SUCCESS] 백테스트 실행 완료. 성과 데이터를 시각화합니다.`, 'success');
                    if (backtestData.performance) updateChart(backtestData.performance);
                }
                break;

            case 'update-data':
                const updateRes = await callAPI('/update');
                if (updateRes) log(`[SUCCESS] 전체 데이터 업데이트 루틴 완료`, 'success');
                break;
        }
    } catch (e) {
        log(`Error in runFunction: ${e.message}`, 'error');
    } finally {
        hideLoading();
    }
}

// -- Rendering --
function renderScreener(data) {
    const container = document.getElementById('screener-preview');
    container.innerHTML = '';

    if (!data || data.length === 0) {
        container.innerHTML = '<p style="color: var(--text-secondary); font-size: 0.85rem;">조건에 맞는 종목이 없습니다.</p>';
        return;
    }

    data.slice(0, 5).forEach(item => {
        const div = document.createElement('div');
        div.className = 'signal-item';
        div.innerHTML = `
            <div class="stock-info">
                <div class="name">${item.name}</div>
                <div class="code">${item.ticker}</div>
            </div>
            <div class="score">${formatNumber(item.foreign_buy)}</div>
        `;
        container.appendChild(div);
    });
}

function renderVCP(signals) {
    const container = document.getElementById('vcp-preview');
    container.innerHTML = '';

    if (!signals || signals.length === 0) {
        container.innerHTML = '<p style="color: var(--text-secondary); font-size: 0.85rem;">발견된 시그널이 없습니다.</p>';
        return;
    }

    signals.slice(0, 5).forEach(sig => {
        const div = document.createElement('div');
        div.className = 'signal-item';
        div.innerHTML = `
            <div class="stock-info">
                <div class="name">${sig.name || sig.stock_name}</div>
                <div class="code">${sig.ticker || sig.stock_code}</div>
            </div>
            <div class="score" style="color: var(--accent-cyan)">${sig.score || 0}점</div>
        `;
        container.appendChild(div);
    });
}

function renderPremium(signals) {
    const container = document.getElementById('premium-signals');
    container.innerHTML = '';

    if (!signals || signals.length === 0) {
        container.innerHTML = '<p style="color: var(--text-secondary); font-size: 0.85rem;">추출된 시그널이 없습니다.</p>';
        return;
    }

    signals.slice(0, 5).forEach(sig => {
        const div = document.createElement('div');
        div.className = 'signal-item';
        div.style.borderLeft = `3px solid ${getGradeColor(sig.grade)}`;
        div.innerHTML = `
            <div class="stock-info">
                <div class="name">${sig.stock_name} <span style="font-size:0.7rem; color:var(--accent-blue)">[${sig.grade}]</span></div>
                <div class="code">${sig.stock_code} | ${sig.sector || ''}</div>
            </div>
            <div class="score">${sig.score?.total || 0}점</div>
        `;
        container.appendChild(div);
    });
}

function getGradeColor(grade) {
    if (grade === 'S') return '#ffD700'; // Gold
    if (grade === 'A') return 'var(--accent-cyan)';
    if (grade === 'B') return 'var(--text-secondary)';
    return 'transparent';
}

function formatNumber(num) {
    if (!num) return '0';
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num.toLocaleString();
}

function renderAI(analysis) {
    const container = document.getElementById('ai-outlook');
    if (!analysis) return;

    const outlook = analysis.outlook || 'Neutral';
    const summary = analysis.summary || '분석 내용이 없습니다.';
    const strategy = analysis.strategy || '';
    const reason = analysis.reason || '';

    container.innerHTML = `
        <div style="font-size: 0.85rem; line-height: 1.5;">
            <div style="font-weight: bold; margin-bottom: 4px; color: ${outlook === 'Bullish' ? 'var(--accent-cyan)' : outlook === 'Error' ? 'var(--accent-red)' : 'var(--accent-yellow)'}">
                전망: ${outlook}
            </div>
            <p style="margin-bottom: 8px;">${summary}</p>
            ${outlook === 'Error' && reason ? `<div style="color: var(--accent-red); font-size: 0.75rem; margin-top: 5px;">사유: ${reason}</div>` : ''}
            ${strategy ? `<div style="color: var(--text-secondary); font-size: 0.8rem;"><strong>전략:</strong> ${strategy}</div>` : ''}
        </div>
    `;
}

// -- Chart Initialization --
function updateChart(perf) {
    const ctx = document.getElementById('perfChart').getContext('2d');
    if (window.myChart) window.myChart.destroy();

    let labels = ['No Data'];
    let chartData = [0];

    if (perf && perf.equity_curve) {
        // 샘플링: 데이터가 너무 많으면 20개 정도로 축소
        const step = Math.max(1, Math.floor(perf.equity_curve.length / 20));
        const sampled = perf.equity_curve.filter((_, i) => i % step === 0);

        labels = sampled.map(e => e.date.substring(5)); // MM-DD
        chartData = sampled.map(e => {
            const initial = perf.summary.initial_capital;
            return ((e.total_equity - initial) / initial * 100).toFixed(2);
        });
    } else {
        // Default Mock for initial view
        labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'];
        chartData = [0, 2, 5, 4, 8, 12];
    }

    window.myChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: '익스포저 수익률 (%)',
                data: chartData,
                borderColor: '#1fd5f9',
                backgroundColor: 'rgba(31, 213, 249, 0.1)',
                fill: true,
                tension: 0.3,
                pointRadius: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                }
            },
            scales: {
                y: {
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    border: { display: false },
                    ticks: { color: 'var(--text-secondary)', font: { size: 10 } }
                },
                x: {
                    grid: { display: false },
                    border: { display: false },
                    ticks: { color: 'var(--text-secondary)', font: { size: 10 } }
                }
            }
        }
    });
}

// Init
window.onload = async () => {
    updateChart();
    log('Smart Money Terminal Initialized.', 'success');

    // Fetch Market Gate Status
    try {
        const gateData = await callAPI('/market-gate', 'GET');
        if (gateData) {
            const gateEl = document.getElementById('market-gate-status');
            const statusColor = gateData.status === 'GREEN' ? 'var(--accent-green)' :
                gateData.status === 'RED' ? 'var(--accent-red)' : 'var(--accent-yellow)';

            gateEl.style.color = statusColor;
            gateEl.innerHTML = `<i data-lucide="shield"></i> <span>KR MARKET GATE: ${gateData.label || gateData.status} (${gateData.score}점)</span>`;
            lucide.createIcons();
            log(`시장 마켓 게이트: ${gateData.status} [${gateData.score}점]`, 'info');
        }
    } catch (e) {
        console.error("Market gate error", e);
    }
};
