document.addEventListener('DOMContentLoaded', () => {
    const youtubeStatusEl = document.getElementById('youtube-status');
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
    const telegramTestBtn = document.getElementById('telegram-test-btn');

    let ws;
    let reconnectTimeout;
    let currentLanguage = 'en';
    let translations = {};
    let nextCheckCountdownInterval;
    let statusChart;
    let lastProcessedCheckTimestamp = null;

    function initChart() {
        const ctx = document.getElementById('statusChart').getContext('2d');
        statusChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'YouTube Live',
                        data: [],
                        borderColor: '#dc3545',
                        backgroundColor: 'rgba(220, 53, 69, 0.1)',
                        fill: true,
                        stepped: true,
                        tension: 0
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        display: true,
                        title: { display: false },
                        ticks: {
                            maxRotation: 0,
                            autoSkip: true,
                            maxTicksLimit: 10
                        }
                    },
                    y: {
                        min: -0.1,
                        max: 1.1,
                        ticks: {
                            stepSize: 1,
                            callback: function(value) {
                                if (value === 1) return translations.status_online || 'Online';
                                if (value === 0) return translations.status_offline || 'Offline';
                                return '';
                            }
                        }
                    }
                },
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) label += ': ';
                                label += context.parsed.y === 1 ? (translations.status_online || 'Online') : (translations.status_offline || 'Offline');
                                return label;
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
        if (!statusChart) return;

        const labels = historyEntries.map(entry => {
            const date = new Date(entry.last_check_timestamp);
            return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        });
        const youtubeData = historyEntries.map(entry => entry.youtube_is_live ? 1 : 0);

        statusChart.data.labels = labels;
        statusChart.data.datasets[0].data = youtubeData;
        statusChart.data.datasets[0].label = translations.youtube_live_label || 'YouTube Live';

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

            youtubeStatusEl.dataset.status = data.youtube_is_live;
            updateStatus(youtubeStatusEl, data.youtube_is_live);
            
            if (document.activeElement !== youtubeApiKeyInput) youtubeApiKeyInput.value = data.youtube_api_key || '';
            if (document.activeElement !== youtubeChannelIdInput) youtubeChannelIdInput.value = data.youtube_channel_id || '';
            if (document.activeElement !== checkIntervalInput) checkIntervalInput.value = data.check_interval;
            
            telegramEnabledSwitch.checked = data.telegram_enabled;
            
            if (document.activeElement !== telegramBotTokenInput) telegramBotTokenInput.value = data.telegram_bot_token || '';
            if (document.activeElement !== telegramChatIdInput) telegramChatIdInput.value = data.telegram_chat_id || '';
            
            telegramNotifyStatusSwitch.checked = data.telegram_notify_on_status_change;

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
        
        if (youtubeStatusEl.dataset.status !== undefined) {
            updateStatus(youtubeStatusEl, youtubeStatusEl.dataset.status);
        }
        
        if (statusChart) {
            statusChart.data.datasets[0].label = translations.youtube_live_label || 'YouTube Live';
            statusChart.update();
        }
    }

    function updateStatus(element, isOnline) {
        element.classList.remove('bg-success', 'bg-danger', 'bg-secondary');
        let statusKey;
        if (isOnline === true || isOnline === 'true') {
            statusKey = 'status_online';
            element.classList.add('bg-success');
        } else if (isOnline === false || isOnline === 'false') {
            statusKey = 'status_offline';
            element.classList.add('bg-danger');
        } else {
            statusKey = 'status_unknown';
            element.classList.add('bg-secondary');
        }
        element.dataset.status = isOnline;
        element.textContent = translations[statusKey] || (isOnline === true || isOnline === 'true' ? 'Online' : 'Offline');
    }

    function updateNextCheckCountdown(lastCheckTimestamp, baseInterval) {
        if (nextCheckCountdownInterval) clearInterval(nextCheckCountdownInterval);
        if (!lastCheckTimestamp) return;

        const lastCheckTime = new Date(lastCheckTimestamp);
        const effectiveInterval = baseInterval;

        nextCheckCountdownInterval = setInterval(() => {
            const now = new Date();
            const elapsed = Math.floor((now - lastCheckTime) / 1000);
            const remaining = Math.max(0, effectiveInterval - (elapsed % effectiveInterval));
            lastCheckEl.textContent = formatTimeAgo(lastCheckTime);
            nextCheckCountdownEl.textContent = formatSeconds(remaining);
        }, 1000);
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

    function showSavingIndicator() { savingIndicator.classList.add('show'); }
    function hideSavingIndicator() { savingIndicator.classList.remove('show'); }

    // Event Listeners
    languageSwitcher.addEventListener('change', (event) => loadLanguage(event.target.value));
    
    youtubeApiKeyInput.addEventListener('change', (event) => sendMessage({ youtube_api_key: event.target.value.trim() }));
    youtubeChannelIdInput.addEventListener('change', (event) => sendMessage({ youtube_channel_id: event.target.value.trim() }));
    checkIntervalInput.addEventListener('change', (event) => sendMessage({ check_interval: parseInt(event.target.value) }));
    
    telegramEnabledSwitch.addEventListener('change', (event) => sendMessage({ telegram_enabled: event.target.checked }));
    telegramBotTokenInput.addEventListener('change', (event) => sendMessage({ telegram_bot_token: event.target.value.trim() }));
    telegramChatIdInput.addEventListener('change', (event) => sendMessage({ telegram_chat_id: event.target.value.trim() }));
    telegramNotifyStatusSwitch.addEventListener('change', (event) => sendMessage({ telegram_notify_on_status_change: event.target.checked }));

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
        if (!result || !result.code) return translations.telegram_test_failed || 'Telegram test failed';
        const detail = result.detail ? ` (${result.detail})` : '';
        switch (result.code) {
            case 'disabled':
                return (translations.telegram_error_disabled || 'Telegram alerts are disabled') + detail;
            case 'missing_credentials':
                return (translations.telegram_error_missing || 'Telegram bot token or chat id missing') + detail;
            case 'send_failed':
                return (translations.telegram_error_send || 'Telegram API error') + detail;
            default:
                return (translations.telegram_test_failed || 'Telegram test failed') + detail;
        }
    }

    checkNowBtn.addEventListener('click', () => fetch('/api/check-now', { method: 'POST' }));

    // Initial Load
    const savedLang = localStorage.getItem('language') || 'en';
    languageSwitcher.value = savedLang;
    initChart();
    loadLanguage(savedLang);
    fetchHistory();
    connectWebSocket();
});
