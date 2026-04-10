document.addEventListener('DOMContentLoaded', () => {
    const youtubeStatusEl = document.getElementById('youtube-status');
    const statusBadge = document.getElementById('status-badge');
    const youtubeApiKeyInput = document.getElementById('youtube-api-key');
    const youtubeChannelIdInput = document.getElementById('youtube-channel-id');
    const checkIntervalInput = document.getElementById('check-interval');
    const savingIndicator = document.getElementById('saving-indicator');
    const languageSwitcher = document.getElementById('language-switcher');
    const lastCheckEl = document.getElementById('last-check');
    const nextCheckCountdownEl = document.getElementById('next-check-countdown');
    const checkNowBtn = document.getElementById('check-now-btn');
    const telegramEnabledSwitch = document.getElementById('telegram-enabled');
    const telegramBotTokenInput = document.getElementById('telegram-bot-token');
    const telegramChatIdInput = document.getElementById('telegram-chat-id');
    const telegramNotifyStatusSwitch = document.getElementById('telegram-notify-status');
    const tgNotifyLabel = document.getElementById('tg-notify-label');
    const telegramTestBtn = document.getElementById('telegram-test-btn');

    let ws;
    let reconnectTimeout;
    let currentLanguage = 'hu';
    let translations = {};
    let nextCheckCountdownInterval;
    let statusChart;
    let lastProcessedCheckTimestamp = null;

    function initChart() {
        const ctx = document.getElementById('statusChart').getContext('2d');
        const gradient = ctx.createLinearGradient(0, 0, 0, 200);
        gradient.addColorStop(0, 'rgba(0, 122, 255, 0.3)');
        gradient.addColorStop(1, 'rgba(0, 122, 255, 0)');

        statusChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        data: [],
                        borderColor: '#007aff',
                        borderWidth: 3,
                        backgroundColor: gradient,
                        fill: true,
                        stepped: true,
                        tension: 0,
                        pointRadius: 0,
                        pointHoverRadius: 6,
                        pointBackgroundColor: '#fff'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        display: true,
                        grid: { display: false },
                        ticks: { color: 'rgba(255,255,255,0.3)', font: { size: 10 }, maxTicksLimit: 8 }
                    },
                    y: {
                        min: -0.1,
                        max: 1.1,
                        display: false
                    }
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: '#1e293b',
                        titleColor: '#fff',
                        bodyColor: '#fff',
                        borderColor: 'rgba(255,255,255,0.1)',
                        borderWidth: 1,
                        displayColors: false,
                        callbacks: {
                            label: function(context) {
                                return context.parsed.y === 1 ? 'LIVE' : 'OFFLINE';
                            }
                        }
                    }
                }
            }
        });
    }

    async function fetchHistory() {
        try {
            const response = await fetch('/api/history');
            const data = await response.json();
            updateChartData(data);
        } catch (error) {
            console.error('Error fetching history:', error);
        }
    }

    function updateChartData(historyEntries) {
        if (!statusChart || !historyEntries.length) return;

        const labels = historyEntries.map(entry => {
            if (!entry.last_check_timestamp) return '';
            const date = new Date(entry.last_check_timestamp);
            return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        });
        const youtubeData = historyEntries.map(entry => entry.youtube_is_live ? 1 : 0);

        statusChart.data.labels = labels;
        statusChart.data.datasets[0].data = youtubeData;
        statusChart.update();
    }

    function connectWebSocket() {
        if (ws) {
            ws.onclose = null;
            ws.close();
        }
        
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        ws = new WebSocket(`${protocol}//${window.location.host}/ws`);

        ws.onopen = () => {
            console.log('WebSocket connected');
            if (reconnectTimeout) clearTimeout(reconnectTimeout);
            document.body.classList.remove('ws-disconnected');
        };

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            if (data.last_check_timestamp && data.last_check_timestamp !== lastProcessedCheckTimestamp) {
                lastProcessedCheckTimestamp = data.last_check_timestamp;
                fetchHistory();
            }

            updateStatusUI(data.youtube_is_live);
            
            if (document.activeElement !== youtubeApiKeyInput) youtubeApiKeyInput.value = data.youtube_api_key || '';
            if (document.activeElement !== youtubeChannelIdInput) youtubeChannelIdInput.value = data.youtube_channel_id || '';
            if (document.activeElement !== checkIntervalInput) checkIntervalInput.value = data.check_interval;
            
            telegramEnabledSwitch.checked = data.telegram_enabled;
            
            if (document.activeElement !== telegramBotTokenInput) telegramBotTokenInput.value = data.telegram_bot_token || '';
            if (document.activeElement !== telegramChatIdInput) telegramChatIdInput.value = data.telegram_chat_id || '';
            
            telegramNotifyStatusSwitch.checked = data.telegram_notify_on_status_change;
            updateSwitchLabel(telegramNotifyStatusSwitch.checked);

            updateNextCheckCountdown(data.last_check_timestamp, data.check_interval);
            
            hideSavingIndicator();
        };

        ws.onclose = () => {
            console.log('WebSocket disconnected, retrying in 3s...');
            document.body.classList.add('ws-disconnected');
            reconnectTimeout = setTimeout(connectWebSocket, 3000);
        };

        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            ws.close();
        };
    }

    async function loadLanguage(lang) {
        try {
            const response = await fetch(`/locales/${lang}.json`);
            translations = await response.json();
            translatePage();
            currentLanguage = lang;
            localStorage.setItem('language', lang);
        } catch (error) {
            console.error(`Could not load language: ${lang}`, error);
        }
    }

    function translatePage() {
        document.querySelectorAll('[data-translate]').forEach(element => {
            const key = element.getAttribute('data-translate');
            if (translations[key]) {
                element.textContent = translations[key];
            }
        });
        
        updateStatusUI(statusBadge.dataset.status === 'true');
        updateSwitchLabel(telegramNotifyStatusSwitch.checked);
    }

    function updateStatusUI(isOnline) {
        statusBadge.classList.remove('status-online', 'status-offline');
        if (isOnline === true || isOnline === 'true') {
            statusBadge.classList.add('status-online');
            youtubeStatusEl.textContent = translations.status_online || 'LIVE';
        } else {
            statusBadge.classList.add('status-offline');
            youtubeStatusEl.textContent = translations.status_offline || 'OFFLINE';
        }
        statusBadge.dataset.status = isOnline;
    }

    function updateSwitchLabel(isChecked) {
        if (!tgNotifyLabel) return;
        if (isChecked) {
            tgNotifyLabel.textContent = translations.status_active || 'Aktív';
            tgNotifyLabel.classList.add('status-label-active');
        } else {
            tgNotifyLabel.textContent = translations.status_disabled || 'Kikapcsolva';
            tgNotifyLabel.classList.remove('status-label-active');
        }
    }

    function updateNextCheckCountdown(lastCheckTimestamp, baseInterval) {
        if (nextCheckCountdownInterval) clearInterval(nextCheckCountdownInterval);
        if (!lastCheckTimestamp) return;

        const lastCheckTime = new Date(lastCheckTimestamp);
        const effectiveInterval = baseInterval;

        function refresh() {
            const now = new Date();
            const elapsed = Math.floor((now - lastCheckTime) / 1000);
            const remaining = Math.max(0, effectiveInterval - elapsed);
            lastCheckEl.textContent = formatTimeAgo(lastCheckTime);
            nextCheckCountdownEl.textContent = formatSeconds(remaining);
        }
        
        refresh();
        nextCheckCountdownInterval = setInterval(refresh, 1000);
    }

    function formatTimeAgo(date) {
        const seconds = Math.floor((new Date() - date) / 1000);
        if (seconds < 60) return `${seconds}s ago`;
        const minutes = Math.floor(seconds / 60);
        return `${minutes}m ${seconds % 60}s ago`;
    }

    function formatSeconds(secs) {
        const minutes = Math.floor(secs / 60);
        const seconds = secs % 60;
        return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }

    function sendMessage(message) {
        showSavingIndicator();
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify(message));
        }
    }

    function showSavingIndicator() { 
        savingIndicator.classList.add('show'); 
    }
    function hideSavingIndicator() { 
        setTimeout(() => {
            savingIndicator.classList.remove('show');
        }, 800);
    }

    // Event Listeners
    languageSwitcher.addEventListener('change', (event) => loadLanguage(event.target.value));
    
    const debouncedSend = (key) => {
        let timeout;
        return (event) => {
            clearTimeout(timeout);
            timeout = setTimeout(() => {
                sendMessage({ [key]: event.target.value.trim() });
            }, 500);
        };
    };

    youtubeApiKeyInput.addEventListener('input', debouncedSend('youtube_api_key'));
    youtubeChannelIdInput.addEventListener('input', debouncedSend('youtube_channel_id'));
    checkIntervalInput.addEventListener('input', (event) => sendMessage({ check_interval: parseInt(event.target.value) }));
    
    telegramEnabledSwitch.addEventListener('change', (event) => sendMessage({ telegram_enabled: event.target.checked }));
    telegramBotTokenInput.addEventListener('input', debouncedSend('telegram_bot_token'));
    telegramChatIdInput.addEventListener('input', debouncedSend('telegram_chat_id'));
    
    telegramNotifyStatusSwitch.addEventListener('change', (event) => {
        updateSwitchLabel(event.target.checked);
        sendMessage({ telegram_notify_on_status_change: event.target.checked });
    });

    telegramTestBtn.addEventListener('click', async () => {
        telegramTestBtn.disabled = true;
        showSavingIndicator();
        try {
            const response = await fetch('/api/telegram-test', { method: 'POST' });
            const result = await response.json();
            if (!result.ok) {
                alert(buildTelegramErrorMessage(result));
            } else {
                alert(translations.telegram_test_success || 'Test message sent');
            }
        } catch (error) {
            alert(translations.telegram_test_failed || 'Telegram test failed');
        } finally {
            telegramTestBtn.disabled = false;
            hideSavingIndicator();
        }
    });

    function buildTelegramErrorMessage(result) {
        if (!result) return 'Error';
        const detail = result.detail ? ` (${result.detail})` : '';
        return (translations.telegram_test_failed || 'Telegram test failed') + detail;
    }

    checkNowBtn.addEventListener('click', () => {
        checkNowBtn.disabled = true;
        fetch('/api/check-now', { method: 'POST' })
            .finally(() => {
                setTimeout(() => { checkNowBtn.disabled = false; }, 2000);
            });
    });

    // Initial Load
    const savedLang = localStorage.getItem('language') || 'hu';
    languageSwitcher.value = savedLang;
    initChart();
    loadLanguage(savedLang).then(() => {
        fetchHistory();
        connectWebSocket();
    });
});
