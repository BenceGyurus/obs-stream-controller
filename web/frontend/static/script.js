document.addEventListener('DOMContentLoaded', () => {
    const youtubeStatusEl = document.getElementById('youtube-status');
    const obsStatusEl = document.getElementById('obs-status');
    const checkIntervalInput = document.getElementById('check-interval');
    const effectiveIntervalEl = document.getElementById('effective-interval');
    const liveModeSwitch = document.getElementById('live-mode');
    const liveModeTimeoutInput = document.getElementById('live-mode-timeout');
    const liveModeCountdownEl = document.getElementById('live-mode-countdown');
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
    let nextCheckCountdownInterval;
    let liveModeCountdownInterval;

    async function loadLanguage(lang) {
        try {
            const response = await fetch(`/locales/${lang}.json`);
            translations = await response.json();
            translatePage();
            currentLanguage = lang;
            localStorage.setItem('language', lang);
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
                element.textContent = translations[key];
            }
        });
        updateStatus(youtubeStatusEl, youtubeStatusEl.dataset.status);
        updateStatus(obsStatusEl, obsStatusEl.dataset.status);
    }

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        updateStatus(youtubeStatusEl, data.youtube_is_live);
        updateStatus(obsStatusEl, data.obs_is_streaming);
        checkIntervalInput.value = data.check_interval;
        liveModeSwitch.checked = data.live_mode;
        liveModeTimeoutInput.value = data.live_mode_timeout;
        obsEnabledSwitch.checked = data.obs_enabled;
        youtubeEnabledSwitch.checked = data.youtube_enabled;
        obsEnabledSwitch.disabled = !data.youtube_enabled;

        updateEffectiveIntervalDisplay(data.check_interval, data.live_mode);
        updateNextCheckCountdown(data.last_check_timestamp, data.check_interval, data.live_mode);
        updateLiveModeCountdown(data.live_mode, data.live_mode_end_timestamp);
        
        fetchHistoryAndRenderChart();
        hideSavingIndicator();
    };

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
        element.textContent = translations[statusKey] || statusKey.replace('status_', '').charAt(0).toUpperCase() + statusKey.slice(8);
    }

    function updateEffectiveIntervalDisplay(baseInterval, isLiveMode) {
        const effective = isLiveMode ? 60 : baseInterval;
        effectiveIntervalEl.textContent = (translations.effective_interval || "Effective: {seconds} seconds").replace('{seconds}', effective);
    }

    function updateNextCheckCountdown(lastCheckTimestamp, baseInterval, isLiveMode) {
        if (nextCheckCountdownInterval) clearInterval(nextCheckCountdownInterval);
        if (!lastCheckTimestamp) return;

        const lastCheckTime = new Date(lastCheckTimestamp);
        const effectiveInterval = isLiveMode ? 60 : baseInterval;

        nextCheckCountdownInterval = setInterval(() => {
            const now = new Date();
            const elapsed = Math.floor((now - lastCheckTime) / 1000);
            const remaining = effectiveInterval - (elapsed % effectiveInterval);
            lastCheckEl.textContent = `${formatTimeAgo(lastCheckTime)}`;
            nextCheckCountdownEl.textContent = `${formatSeconds(remaining)}`;
        }, 1000);
    }

    function updateLiveModeCountdown(isLive, endTime) {
        if (liveModeCountdownInterval) clearInterval(liveModeCountdownInterval);
        if (isLive && endTime) {
            const end = new Date(endTime);
            liveModeCountdownEl.style.display = 'block';
            liveModeCountdownInterval = setInterval(() => {
                const now = new Date();
                const remaining = Math.max(0, Math.floor((end - now) / 1000));
                liveModeCountdownEl.textContent = (translations.live_mode_countdown || "Auto-disable in: {time}").replace('{time}', formatSeconds(remaining));
                if (remaining <= 0) clearInterval(liveModeCountdownInterval);
            }, 1000);
        } else {
            liveModeCountdownEl.style.display = 'none';
        }
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

    languageSwitcher.addEventListener('change', (event) => loadLanguage(event.target.value));
    checkIntervalInput.addEventListener('change', (event) => sendMessage({ check_interval: parseInt(event.target.value) }));
    liveModeSwitch.addEventListener('change', (event) => sendMessage({ live_mode: event.target.checked }));
    liveModeTimeoutInput.addEventListener('change', (event) => sendMessage({ live_mode_timeout: parseInt(event.target.value) }));
    obsEnabledSwitch.addEventListener('change', (event) => sendMessage({ obs_enabled: event.target.checked }));
    youtubeEnabledSwitch.addEventListener('change', (event) => {
        sendMessage({ youtube_enabled: event.target.checked });
        if (!event.target.checked) {
            obsEnabledSwitch.checked = false;
            sendMessage({ obs_enabled: false });
        }
    });
    checkNowBtn.addEventListener('click', () => fetch('/api/check-now', { method: 'POST' }));

    function sendMessage(message) {
        showSavingIndicator();
        if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(message));
    }

    function showSavingIndicator() { savingIndicator.classList.add('show'); }
    function hideSavingIndicator() { savingIndicator.classList.remove('show'); }

    async function fetchHistoryAndRenderChart() {
        // ... (Chart.js logic remains the same)
    }

    // --- Initial Load ---
    const savedLang = localStorage.getItem('language') || 'en';
    languageSwitcher.value = savedLang;
    loadLanguage(savedLang);
    fetchHistoryAndRenderChart();
});