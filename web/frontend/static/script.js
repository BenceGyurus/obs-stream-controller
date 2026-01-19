document.addEventListener('DOMContentLoaded', () => {
    const youtubeStatusEl = document.getElementById('youtube-status');
    const obsStatusEl = document.getElementById('obs-status');
    const checkIntervalInput = document.getElementById('check-interval');
    const effectiveIntervalEl = document.getElementById('effective-interval');
    const liveModeSwitch = document.getElementById('live-mode');
    const obsEnabledSwitch = document.getElementById('obs-enabled');
    const youtubeEnabledSwitch = document.getElementById('youtube-enabled');
    const savingIndicator = document.getElementById('saving-indicator');
    const languageSwitcher = document.getElementById('language-switcher');
    const lastCheckEl = document.getElementById('last-check');
    const nextCheckCountdownEl = document.getElementById('next-check-countdown');
    const checkNowBtn = document.getElementById('check-now-btn');

    let ws = new WebSocket(`ws://${window.location.host}/ws`);
    let currentLanguage = 'en';
    let translations = {};
    let statusChart;
    let countdownInterval;

    async function loadLanguage(lang) {
        try {
            const response = await fetch(`/locales/${lang}.json`);
            translations = await response.json();
            translatePage();
            currentLanguage = lang;
            localStorage.setItem('language', lang);
            // Re-render chart labels if chart exists
            if (statusChart) {
                updateChartLabels();
            }
        } catch (error) {
            console.error(`Could not load language: ${lang}`, error);
        }
    }

    function translatePage() {
        document.querySelectorAll('[data-translate]').forEach(element => {
            const key = element.getAttribute('data-translate');
            if (translations[key]) {
                if (key === 'effective_interval') {
                    const seconds = element.getAttribute('data-seconds');
                    element.textContent = translations[key].replace('{seconds}', seconds);
                } else {
                    element.textContent = translations[key];
                }
            }
        });
        // Special case for dynamic status texts
        updateStatus(youtubeStatusEl, youtubeStatusEl.classList.contains('bg-success') ? true : (youtubeStatusEl.classList.contains('bg-danger') ? false : undefined));
        updateStatus(obsStatusEl, obsStatusEl.classList.contains('bg-success') ? true : (obsStatusEl.classList.contains('bg-danger') ? false : undefined));
        
        // Update countdown text
        if (countdownInterval) {
            clearInterval(countdownInterval);
            countdownInterval = null;
        }
        updateCountdownDisplay(lastCheckEl.dataset.timestamp, parseInt(checkIntervalInput.value, 10), liveModeSwitch.checked);
    }

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        updateStatus(youtubeStatusEl, data.youtube_is_live);
        updateStatus(obsStatusEl, data.obs_is_streaming);
        checkIntervalInput.value = data.check_interval;
        liveModeSwitch.checked = data.live_mode;
        obsEnabledSwitch.checked = data.obs_enabled;
        youtubeEnabledSwitch.checked = data.youtube_enabled;

        obsEnabledSwitch.disabled = !data.youtube_enabled;
        updateEffectiveIntervalDisplay(data.check_interval, data.live_mode);
        
        if (data.last_check_timestamp) {
            lastCheckEl.dataset.timestamp = data.last_check_timestamp;
            updateCountdownDisplay(data.last_check_timestamp, data.check_interval, data.live_mode);
        }

        fetchHistoryAndRenderChart();
        hideSavingIndicator();
    };

    function updateStatus(element, isOnline) {
        element.classList.remove('bg-success', 'bg-danger', 'bg-secondary');
        let statusKey;
        if (isOnline === true) {
            statusKey = 'status_online';
            element.classList.add('bg-success');
        } else if (isOnline === false) {
            statusKey = 'status_offline';
            element.classList.add('bg-danger');
        } else {
            statusKey = 'status_unknown';
            element.classList.add('bg-secondary');
        }
        element.textContent = translations[statusKey] || statusKey;
        element.setAttribute('data-translate', statusKey);
    }

    function updateEffectiveIntervalDisplay(baseInterval, isLiveMode) {
        const effective = isLiveMode ? 60 : baseInterval;
        effectiveIntervalEl.setAttribute('data-seconds', effective);
        if (translations.effective_interval) {
            effectiveIntervalEl.textContent = translations.effective_interval.replace('{seconds}', effective);
        } else {
            effectiveIntervalEl.textContent = `Effective: ${effective} seconds`;
        }
    }

    function updateCountdownDisplay(lastCheckTimestamp, baseInterval, isLiveMode) {
        if (countdownInterval) {
            clearInterval(countdownInterval);
        }
        
        const lastCheckTime = new Date(lastCheckTimestamp);
        const effectiveInterval = isLiveMode ? 60 : baseInterval;

        countdownInterval = setInterval(() => {
            const now = new Date();
            const elapsed = Math.floor((now - lastCheckTime) / 1000);
            const remaining = effectiveInterval - (elapsed % effectiveInterval);

            lastCheckEl.textContent = `${formatTimeAgo(lastCheckTime)}`;
            nextCheckCountdownEl.textContent = `${formatSeconds(remaining)}`;

            // If remaining is 0 or less, a new check should have started.
            // Force a refresh from the server to get the latest lastCheckTimestamp
            if (remaining <= 0) {
                clearInterval(countdownInterval);
                fetchHistoryAndRenderChart(); // Refresh chart and status via history fetch
                // Optionally, trigger a message to fetch current state immediately
                sendMessage({}); 
            }
        }, 1000);
    }

    function formatTimeAgo(date) {
        const seconds = Math.floor((new Date() - date) / 1000);
        let interval = seconds / 31536000;
        if (interval > 1) return Math.floor(interval) + (currentLanguage === 'hu' ? " éve" : " years ago");
        interval = seconds / 2592000;
        if (interval > 1) return Math.floor(interval) + (currentLanguage === 'hu' ? " hónapja" : " months ago");
        interval = seconds / 86400;
        if (interval > 1) return Math.floor(interval) + (currentLanguage === 'hu' ? " napja" : " days ago");
        interval = seconds / 3600;
        if (interval > 1) return Math.floor(interval) + (currentLanguage === 'hu' ? " órája" : " hours ago");
        interval = seconds / 60;
        if (interval > 1) return Math.floor(interval) + (currentLanguage === 'hu' ? " perce" : " minutes ago");
        return Math.floor(seconds) + (currentLanguage === 'hu' ? " másodperce" : " seconds ago");
    }

    function formatSeconds(secs) {
        const minutes = Math.floor(secs / 60);
        const seconds = secs % 60;
        return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }

    languageSwitcher.addEventListener('change', (event) => {
        loadLanguage(event.target.value);
    });

    checkIntervalInput.addEventListener('change', (event) => {
        showSavingIndicator();
        const interval = parseInt(event.target.value, 10);
        sendMessage({ check_interval: interval });
        updateEffectiveIntervalDisplay(interval, liveModeSwitch.checked);
    });

    liveModeSwitch.addEventListener('change', (event) => {
        showSavingIndicator();
        sendMessage({ live_mode: event.target.checked });
        updateEffectiveIntervalDisplay(parseInt(checkIntervalInput.value, 10), event.target.checked);
    });

    obsEnabledSwitch.addEventListener('change', (event) => {
        showSavingIndicator();
        sendMessage({ obs_enabled: event.target.checked });
    });

    youtubeEnabledSwitch.addEventListener('change', (event) => {
        showSavingIndicator();
        const isEnabled = event.target.checked;
        sendMessage({ youtube_enabled: isEnabled });
        if (!isEnabled) {
            obsEnabledSwitch.checked = false;
            sendMessage({ obs_enabled: false });
        }
    });

    checkNowBtn.addEventListener('click', async () => {
        showSavingIndicator();
        try {
            await fetch('/api/check-now', { method: 'POST' });
            // Backend will broadcast state, which will update UI
        } catch (error) {
            console.error("Failed to trigger manual check:", error);
            hideSavingIndicator();
        }
    });
    
    function sendMessage(message) {
        if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify(message));
        } else {
            console.error("WebSocket not open. Reconnecting...");
            ws = new WebSocket(`ws://${window.location.host}/ws`);
            ws.onopen = () => {
                ws.send(JSON.stringify(message));
            };
            ws.onerror = (error) => {
                console.error("WebSocket error:", error);
                hideSavingIndicator();
            };
        }
    }

    function showSavingIndicator() {
        savingIndicator.classList.add('show');
    }

    function hideSavingIndicator() {
        savingIndicator.classList.remove('show');
    }

    async function fetchHistoryAndRenderChart() {
        try {
            const response = await fetch('/api/history');
            const historyData = await response.json();
            
            const labels = historyData.map(entry => new Date(entry.last_check_timestamp).toLocaleTimeString());
            const youtubeData = historyData.map(entry => entry.youtube_is_live ? 1 : 0);
            const obsData = historyData.map(entry => entry.obs_is_streaming ? 1 : 0);

            if (!statusChart) {
                const ctx = document.getElementById('statusChart').getContext('2d');
                statusChart = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: labels,
                        datasets: [{
                            label: 'YouTube Live',
                            data: youtubeData,
                            borderColor: 'rgb(255, 99, 132)',
                            tension: 0.1,
                            stepped: true
                        }, {
                            label: 'OBS Streaming',
                            data: obsData,
                            borderColor: 'rgb(54, 162, 235)',
                            tension: 0.1,
                            stepped: true
                        }]
                    },
                    options: {
                        responsive: true,
                        scales: {
                            y: {
                                beginAtZero: true,
                                max: 1.2,
                                ticks: {
                                    callback: function(value, index, ticks) {
                                        if (value === 1) return translations.status_online || 'Online';
                                        if (value === 0) return translations.status_offline || 'Offline';
                                        return '';
                                    }
                                }
                            }
                        }
                    }
                });
            } else {
                statusChart.data.labels = labels;
                statusChart.data.datasets[0].data = youtubeData;
                statusChart.data.datasets[1].data = obsData;
                updateChartLabels(); // Update labels after fetching new data
                statusChart.update();
            }
        } catch (error) {
            console.error("Failed to fetch history data:", error);
        }
    }

    function updateChartLabels() {
        if (statusChart) {
            statusChart.data.datasets[0].label = translations.youtube_live_label || 'YouTube Live';
            statusChart.data.datasets[1].label = translations.obs_streaming_label || 'OBS Streaming';
            statusChart.options.scales.y.ticks.callback = function(value, index, ticks) {
                if (value === 1) return translations.status_online || 'Online';
                if (value === 0) return translations.status_offline || 'Offline';
                return '';
            };
            statusChart.update();
        }
    }

    // --- Initial Load ---
    const savedLang = localStorage.getItem('language') || 'en';
    languageSwitcher.value = savedLang;
    loadLanguage(savedLang);
    fetchHistoryAndRenderChart(); // Initial chart render
});