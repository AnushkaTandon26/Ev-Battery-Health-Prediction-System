const appState = {
    socChart: null,
    autoRefreshTimer: null,
    settings: {
        autoRefresh: true,
        geoEnabled: true
    },
    latestRecords: [],
    latestPrediction: null,
    agentTasks: []
};

const panelMeta = {
    overview: {
        label: "Live battery dashboard",
        title: "AI pack monitoring cockpit"
    },
    vehicle: {
        label: "Vehicle telemetry",
        title: "Realtime pack snapshot"
    },
    configuration: {
        label: "Prediction controls",
        title: "Battery health configuration"
    },
    history: {
        label: "Prediction archive",
        title: "Saved battery scan history"
    },
    messages: {
        label: "Operations feed",
        title: "Recommendations and system notices"
    },
    settings: {
        label: "Runtime settings",
        title: "Dashboard controls"
    },
    favorite: {
        label: "Pinned metrics",
        title: "Favorite battery KPIs"
    }
};

document.addEventListener("DOMContentLoaded", () => {
    bindUI();
    refreshDashboard();
    updateAutoRefresh();
});

function bindUI() {
    document.querySelectorAll(".menu-item").forEach((button) => {
        button.addEventListener("click", () => activatePanel(button.dataset.tab));
    });

    document.getElementById("refresh-btn")?.addEventListener("click", refreshDashboard);
    document.getElementById("prediction-form")?.addEventListener("submit", handlePrediction);
    document.getElementById("open-location-popup")?.addEventListener("click", openGeoModal);
    document.getElementById("location-btn")?.addEventListener("click", requestGeolocation);
    document.getElementById("close-location-popup")?.addEventListener("click", closeGeoModal);
    document.querySelectorAll("[data-close-geo='true']").forEach((node) => {
        node.addEventListener("click", closeGeoModal);
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            closeGeoModal();
        }
    });

    document.getElementById("auto-refresh-toggle")?.addEventListener("change", (event) => {
        appState.settings.autoRefresh = event.target.checked;
        updateAutoRefresh();
        showToast(
            appState.settings.autoRefresh ? "Auto refresh enabled." : "Auto refresh paused.",
            "success"
        );
    });

    document.getElementById("geo-toggle")?.addEventListener("change", (event) => {
        appState.settings.geoEnabled = event.target.checked;
        if (appState.settings.geoEnabled) {
            setGeoStatus("Standby");
        } else {
            setGeoStatus("Disabled");
            document.getElementById("geo-coords").textContent = "Geolocation paused";
        }
    });
}

function activatePanel(panelName) {
    document.querySelectorAll(".menu-item").forEach((button) => {
        button.classList.toggle("is-active", button.dataset.tab === panelName);
    });

    document.querySelectorAll(".screen-panel").forEach((panel) => {
        panel.classList.toggle("is-active", panel.dataset.panel === panelName);
    });

    const meta = panelMeta[panelName];
    if (meta) {
        document.getElementById("screen-label").textContent = meta.label;
        document.getElementById("screen-title").textContent = meta.title;
    }
}

async function refreshDashboard() {
    try {
        setSystemStatus("Syncing");
        const [stats, detailedStats, history, agentTasks] = await Promise.all([
            fetchJSON("/api/stats"),
            fetchJSON("/api/detailed-stats"),
            fetchJSON("/api/history?limit=12"),
            fetchJSON("/api/agent/tasks?limit=4")
        ]);

        appState.latestRecords = Array.isArray(history) ? history : [];
        appState.agentTasks = Array.isArray(agentTasks) ? agentTasks : [];
        renderStats(stats, detailedStats, appState.latestRecords);
        renderHistory(appState.latestRecords);
        renderChart(appState.latestRecords);
        renderMessages(appState.latestPrediction, detailedStats, appState.latestRecords, appState.agentTasks);
        setSystemStatus("Connected");
    } catch (error) {
        console.error(error);
        setSystemStatus("Offline");
        showToast("Could not load live dashboard data. Check backend server.", "error");
    }
}

async function handlePrediction(event) {
    event.preventDefault();

    const payload = {
        voltage: getNumberValue("voltage"),
        current: getNumberValue("current"),
        soc: getNumberValue("soc"),
        temp: getNumberValue("temp"),
        degradation_level: getNumberValue("degradation")
    };

    if (Object.values(payload).some((value) => Number.isNaN(value))) {
        showToast("Please enter valid battery values before prediction.", "error");
        return;
    }

    const resultNode = document.getElementById("prediction-result");
    resultNode.className = "result-card";
    resultNode.textContent = "Running prediction...";

    try {
        const result = await fetchJSON("/api/predict", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        });

        appState.latestPrediction = {
            ...result,
            input: payload,
            createdAt: new Date().toISOString()
        };

        resultNode.className = `result-card result-card--${result.status.toLowerCase()}`;
        resultNode.innerHTML = `
            <strong>${result.status} battery condition</strong>
            <p>Health score: ${formatPercent(result.health_score)}</p>
            <p>Battery degradation input: ${formatPercent(result.degradation_level)}</p>
            <p>Record ID: ${result.record_id}</p>
            <div>${renderRecommendationMarkup(result.recommendations)}</div>
            ${renderAgentPlanMarkup(result.agent_plan)}
        `;

        updateLatestInputDetails(payload, result);
        renderMessages(appState.latestPrediction, null, appState.latestRecords, appState.agentTasks);
        activatePanel("overview");
        await refreshDashboard();
        showToast("Prediction completed and dashboard updated.", "success");
    } catch (error) {
        console.error(error);
        resultNode.className = "result-card result-card--critical";
        resultNode.textContent = "Prediction failed. Make sure the backend is running.";
        showToast("Prediction failed. Backend may be unavailable.", "error");
    }
}

function renderStats(stats, detailedStats, history) {
    const latest = history[0] || detailedStats?.records?.[0] || null;
    const averageHealth = Number(stats?.average_health ?? detailedStats?.avg_health ?? 0);
    const latestSoc = Number(latest?.soc ?? detailedStats?.avg_soc ?? 83);
    const totalRecords = Number(stats?.total_records ?? 0);
    const criticalCount = Number(stats?.critical_count ?? 0);
    const safeCount = Number(stats?.safe_count ?? 0);
    const avgTemp = Number(detailedStats?.avg_temp ?? latest?.temp ?? 0);
    const avgVoltage = Number(detailedStats?.avg_voltage ?? latest?.voltage ?? 0);
    const avgCurrent = Number(detailedStats?.avg_current ?? latest?.current ?? 0);
    const avgDegradation = Number(detailedStats?.avg_degradation ?? latest?.degradation_level ?? Math.max(0, 100 - averageHealth));
    const estRideHours = Math.max(1, Math.round(totalRecords * 0.6));
    const estUptimeHours = Math.max(4, Math.min(18, Math.round(safeCount + 6)));
    const estRange = Math.max(12, Math.round(latestSoc * 0.98));
    const estDistance = Math.round(
        history.reduce((sum, record) => sum + Number(record.soc || 0) * 0.42, 0)
    );

    document.getElementById("soc-score").textContent = formatPercent(latestSoc);
    document.getElementById("ride-hours").textContent = `${estRideHours} hrs`;
    document.getElementById("ride-hours-note").textContent = `${totalRecords} scans processed`;
    document.getElementById("uptime-hours").textContent = `${estUptimeHours} hrs`;
    document.getElementById("uptime-hours-note").textContent = `${safeCount} safe cycles tracked`;
    document.getElementById("distance-cover").textContent = `${estRange} km`;
    document.getElementById("distance-note").textContent = "estimated from live SOC";
    document.getElementById("health-score").textContent = formatPercent(averageHealth);
    document.getElementById("degradation-label").textContent = formatPercent(avgDegradation);
    document.getElementById("critical-count").textContent = String(criticalCount);
    document.getElementById("total-records").textContent = String(totalRecords);
    document.getElementById("total-distance").textContent = `${estDistance || estRange} km`;
    document.getElementById("total-distance-note").textContent = latest
        ? `Latest record ${formatTimestamp(latest.timestamp)}`
        : "Waiting for live records";
    document.getElementById("soc-range-label").textContent = `Recent ${history.length || 0} records`;
    document.getElementById("chart-legend-label").textContent = `${Math.max(1, Math.round(totalRecords / 2) || 1)} average hours`;

    document.getElementById("favorite-health").textContent = formatPercent(averageHealth);
    document.getElementById("favorite-soc").textContent = formatPercent(detailedStats?.avg_soc ?? latestSoc);
    document.getElementById("favorite-temp").textContent = `${roundValue(avgTemp)} C`;
    document.getElementById("favorite-voltage").textContent = `${roundValue(avgVoltage)} V`;

    if (latest) {
        updateLatestInputDetails(latest, {
            status: latest.status,
            health_score: latest.health_score
        });
    } else {
        document.getElementById("detail-voltage").textContent = `${roundValue(avgVoltage)} V`;
        document.getElementById("detail-current").textContent = `${roundValue(avgCurrent)} A`;
        document.getElementById("detail-temp").textContent = `${roundValue(avgTemp)} C`;
        document.getElementById("detail-status").textContent = "Awaiting data";
    }

    setGaugeValue(averageHealth);
}

function updateLatestInputDetails(source, result) {
    document.getElementById("detail-voltage").textContent = `${roundValue(source.voltage)} V`;
    document.getElementById("detail-current").textContent = `${roundValue(source.current)} A`;
    document.getElementById("detail-temp").textContent = `${roundValue(source.temp)} C`;
    const degradationText = source.degradation_level !== undefined && source.degradation_level !== null
        ? ` | Deg ${formatPercent(source.degradation_level)}`
        : "";
    document.getElementById("detail-status").textContent = `${result.status || "Safe"}${degradationText}`;
}

function renderHistory(history) {
    const tbody = document.getElementById("history-body");

    if (!history.length) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8">No prediction history available yet.</td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = history
        .map((record) => {
            return `
                <tr>
                    <td>${record.id}</td>
                    <td>${record.status}</td>
                    <td>${formatPercent(record.health_score)}</td>
                    <td>${roundValue(record.voltage)} V</td>
                    <td>${roundValue(record.current)} A</td>
                    <td>${formatPercent(record.soc)}</td>
                    <td>${roundValue(record.temp)} C</td>
                    <td>${formatTimestamp(record.timestamp)}</td>
                </tr>
            `;
        })
        .join("");
}

function renderMessages(prediction, detailedStats, history, agentTasks) {
    const feed = document.getElementById("message-feed");
    const items = [];

    if (prediction?.agent_plan) {
        items.push(renderTaskFeedItem(prediction.agent_plan, "Latest agent action"));
    }

    if (Array.isArray(agentTasks) && agentTasks.length) {
        agentTasks.slice(0, 2).forEach((task) => {
            items.push(renderTaskFeedItem(task, "Scheduled maintenance"));
        });
    }

    if (prediction?.recommendations?.length) {
        prediction.recommendations.forEach((recommendation) => {
            items.push(`
                <div class="message-feed__item">
                    <strong>Prediction recommendation</strong>
                    <p>${recommendation}</p>
                </div>
            `);
        });
    }

    const latest = history?.[0];
    if (latest) {
        items.push(`
            <div class="message-feed__item">
                <strong>Latest backend record</strong>
                <p>${latest.status} at ${formatPercent(latest.health_score)} battery health.</p>
            </div>
        `);
    }

    if (detailedStats?.avg_temp !== undefined) {
        items.push(`
            <div class="message-feed__item">
                <strong>Thermal summary</strong>
                <p>Average battery temperature is ${roundValue(detailedStats.avg_temp)} C across recent records.</p>
            </div>
        `);
    }

    if (detailedStats?.avg_degradation !== undefined) {
        items.push(`
            <div class="message-feed__item">
                <strong>Degradation summary</strong>
                <p>Average battery degradation input is ${formatPercent(detailedStats.avg_degradation)} across recent records.</p>
            </div>
        `);
    }

    if (!items.length) {
        items.push('<div class="message-feed__item">System ready for the next scan.</div>');
    }

    feed.innerHTML = items.slice(0, 4).join("");
}

function renderChart(history) {
    const canvas = document.getElementById("socChart");
    if (!canvas || typeof Chart === "undefined") {
        return;
    }

    const labels = [...history].reverse().map((record, index) => {
        if (!record.timestamp) {
            return `Scan ${index + 1}`;
        }

        const date = new Date(record.timestamp);
        return `${date.getDate()} ${date.toLocaleString([], { month: "short" })}`;
    });

    const socValues = [...history].reverse().map((record) => Number(record.soc || 0));

    if (appState.socChart) {
        appState.socChart.destroy();
    }

    appState.socChart = new Chart(canvas, {
        type: "line",
        data: {
            labels,
            datasets: [
                {
                    label: "SOC",
                    data: socValues,
                    borderColor: "#5ad47d",
                    backgroundColor: "rgba(90, 212, 125, 0.18)",
                    tension: 0.35,
                    fill: true,
                    pointRadius: 0,
                    pointHoverRadius: 4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: "#101520",
                    borderColor: "rgba(255,255,255,0.08)",
                    borderWidth: 1,
                    titleColor: "#ffffff",
                    bodyColor: "#d5dceb"
                }
            },
            scales: {
                x: {
                    ticks: {
                        color: "#7f879c",
                        maxRotation: 0
                    },
                    grid: {
                        color: "rgba(255,255,255,0.04)"
                    }
                },
                y: {
                    min: 0,
                    max: 100,
                    ticks: {
                        color: "#7f879c"
                    },
                    grid: {
                        color: "rgba(255,255,255,0.06)"
                    }
                }
            }
        }
    });
}

function setGaugeValue(value) {
    const normalized = Math.max(0, Math.min(100, Number(value || 0)));
    document.getElementById("gauge-ring")?.style.setProperty("--value", normalized);
}

function openGeoModal() {
    const modal = document.getElementById("geo-modal");
    if (!modal) {
        return;
    }

    modal.hidden = false;
    document.body.style.overflow = "hidden";

    if (appState.settings.geoEnabled) {
        requestGeolocation();
    }
}

function closeGeoModal() {
    const modal = document.getElementById("geo-modal");
    if (!modal || modal.hidden) {
        return;
    }

    modal.hidden = true;
    document.body.style.overflow = "";
}

async function requestGeolocation() {
    if (!appState.settings.geoEnabled) {
        setGeoStatus("Disabled");
        return;
    }

    if (!("geolocation" in navigator)) {
        document.getElementById("geo-coords").textContent = "Geolocation unavailable";
        setGeoStatus("Unsupported");
        return;
    }

    setGeoStatus("Requesting");

    navigator.geolocation.getCurrentPosition(
        (position) => {
            const { latitude, longitude } = position.coords;
            document.getElementById("geo-coords").textContent = `${latitude.toFixed(4)}, ${longitude.toFixed(4)}`;
            setGeoStatus("Live");
        },
        () => {
            document.getElementById("geo-coords").textContent = "Permission denied";
            setGeoStatus("Blocked");
        },
        {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 30000
        }
    );
}

function setGeoStatus(status) {
    document.getElementById("geo-status").textContent = status;
}

function setSystemStatus(status) {
    document.getElementById("system-status").textContent = status;
}

function updateAutoRefresh() {
    if (appState.autoRefreshTimer) {
        clearInterval(appState.autoRefreshTimer);
        appState.autoRefreshTimer = null;
    }

    if (appState.settings.autoRefresh) {
        appState.autoRefreshTimer = setInterval(refreshDashboard, 30000);
    }
}

async function fetchJSON(url, options = {}) {
    const response = await fetch(url, options);
    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.error || "Request failed");
    }

    return data;
}

function getNumberValue(id) {
    return Number.parseFloat(document.getElementById(id)?.value ?? "");
}

function renderRecommendationMarkup(recommendations) {
    if (!recommendations?.length) {
        return "<p>No urgent recommendations. Battery is operating within expected limits.</p>";
    }

    return `
        <ul>
            ${recommendations.map((item) => `<li>${item}</li>`).join("")}
        </ul>
    `;
}

function renderAgentPlanMarkup(plan) {
    if (!plan) {
        return "";
    }

    const actions = Array.isArray(plan.recommended_actions) && plan.recommended_actions.length
        ? `<ul>${plan.recommended_actions.map((item) => `<li>${item}</li>`).join("")}</ul>`
        : "<p>No additional maintenance steps scheduled.</p>";

    return `
        <div class="agent-plan">
            <strong>Agentic maintenance plan</strong>
            <p>${plan.title}</p>
            <p>${plan.summary}</p>
            <div class="agent-plan__meta">
                <span>${plan.priority} priority</span>
                <span>${plan.execution_mode}</span>
                <span>${formatDateTime(plan.scheduled_for)}</span>
            </div>
            ${actions}
        </div>
    `;
}

function renderTaskFeedItem(task, label) {
    const scheduledFor = formatDateTime(task.scheduled_for);
    const detail = task.schedule_label || task.action_status || "Scheduled";

    return `
        <div class="message-feed__item">
            <strong>${label}: ${task.title}</strong>
            <p>${task.summary}</p>
            <div class="message-feed__meta">
                <span>${task.priority} priority</span>
                <span>${detail}</span>
                <span>${scheduledFor}</span>
            </div>
        </div>
    `;
}

function showToast(message, tone = "success") {
    const toast = document.getElementById("toast");
    if (!toast) {
        return;
    }

    toast.hidden = false;
    toast.dataset.tone = tone;
    toast.textContent = message;

    window.clearTimeout(showToast.timeoutId);
    showToast.timeoutId = window.setTimeout(() => {
        toast.hidden = true;
    }, 3200);
}

function roundValue(value) {
    const number = Number(value);
    if (Number.isNaN(number)) {
        return "--";
    }

    return number % 1 === 0 ? String(number) : number.toFixed(1);
}

function formatPercent(value) {
    const number = Number(value);
    if (Number.isNaN(number)) {
        return "--";
    }

    return `${Math.round(number)}%`;
}

function formatTimestamp(value) {
    if (!value) {
        return "--";
    }

    return new Date(value).toLocaleString([], {
        day: "2-digit",
        month: "short",
        hour: "2-digit",
        minute: "2-digit"
    });
}

function formatDateTime(value) {
    if (!value) {
        return "Schedule pending";
    }

    return new Date(value).toLocaleString([], {
        day: "2-digit",
        month: "short",
        hour: "2-digit",
        minute: "2-digit"
    });
}
