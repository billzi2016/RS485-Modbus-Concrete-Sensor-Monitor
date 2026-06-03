(function () {
    const body = document.body;
    const refreshMs = Number(body.dataset.refreshMs || "1000");
    const defaultMetric = body.dataset.defaultMetric || "strain";

    const metricLabels = {
        strain: "应变",
        max_strain: "最大应变",
        temp: "温度",
        freq: "频率",
    };

    // dataSource: "real" | "fastapi" | "mock"
    const state = {
        currentMetric: defaultMetric,
        selectedGatewayIp: null,
        selectedSensorIndex: null,
        selectedSensorKey: null,
        sparklineHistory: {},
        currentRange: { min: 0, max: 1 },
        dataSource: "real",
    };

    const summaryOnline = document.getElementById("summary-online");
    const summaryOffline = document.getElementById("summary-offline");
    const summaryError = document.getElementById("summary-error");
    const summarySensors = document.getElementById("summary-sensors");
    const currentMetricLabel = document.getElementById("current-metric-label");
    const metricRange = document.getElementById("metric-range");
    const dataSource = document.getElementById("data-source");
    const lastUpdated = document.getElementById("last-updated");
    const matrixBody = document.getElementById("matrix-body");
    const detailMeta = document.getElementById("detail-meta");
    const historyLine = document.getElementById("history-line");
    const chartMinLabel = document.getElementById("chart-min-label");
    const chartMaxLabel = document.getElementById("chart-max-label");
    const sourceBtns = document.querySelectorAll(".source-btn");

    function sourceParam() {
        if (state.dataSource === "mock") return "?source=mock";
        if (state.dataSource === "fastapi") return "?source=fastapi";
        return "";
    }

    function setDataSource(source) {
        state.dataSource = source;
        sourceBtns.forEach((btn) => {
            btn.classList.toggle("is-active", btn.dataset.source === source);
        });
    }

    function formatMetricValue(value) {
        if (value === null || value === undefined) {
            return "Err";
        }
        if (typeof value === "number") {
            return value.toFixed(2).replace(/\.00$/, "");
        }
        return String(value);
    }

    function escapeHtml(value) {
        return String(value)
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#39;");
    }

    function formatTimestamp(value) {
        if (!value) {
            return "--";
        }
        return new Date(value * 1000).toLocaleTimeString("zh-CN", { hour12: false });
    }

    async function fetchJson(url) {
        const response = await fetch(url, { headers: { Accept: "application/json" } });
        if (!response.ok) {
            throw new Error(`Request failed: ${response.status}`);
        }
        return response.json();
    }

    async function refreshSummary() {
        const data = await fetchJson("/api/summary" + sourceParam());
        summaryOnline.textContent = data.gateway_online;
        summaryOffline.textContent = data.gateway_offline;
        summaryError.textContent = data.error_sensors;
        summarySensors.textContent = data.sensor_total;
        dataSource.textContent = data.source || "unknown";
        lastUpdated.textContent = formatTimestamp(data.last_updated);
    }

    function updateSparklineHistory(cellData) {
        const historyKey = `${state.currentMetric}:${cellData.key}`;
        const bucket = state.sparklineHistory[historyKey] || [];
        const nextValue = typeof cellData.value === "number" ? cellData.value : null;

        bucket.push(nextValue);
        if (bucket.length > 600) {
            bucket.shift();
        }

        state.sparklineHistory[historyKey] = bucket;
        return bucket;
    }

    function buildSparklineSvg(history, range, isError) {
        const width = 104;
        const height = 52;
        const left = 2;
        const top = 2;
        const chartWidth = width - 4;
        const chartHeight = height - 4;
        const min = Number(range.min);
        const max = Number(range.max);
        const safeSpan = Math.max(max - min, 1);
        const display = history;

        if (isError) {
            return `
                <svg class="cell-chart" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" aria-hidden="true">
                    <rect x="0" y="0" width="${width}" height="${height}" class="cell-chart-bg"></rect>
                    <line x1="${left}" y1="${top + chartHeight / 2}" x2="${left + chartWidth}" y2="${top + chartHeight / 2}" class="cell-chart-grid"></line>
                </svg>
            `;
        }

        const values = display.map((point, index) => {
            if (typeof point === "number") {
                return point;
            }
            if (index === 0) {
                return min;
            }
            return typeof display[index - 1] === "number" ? display[index - 1] : min;
        });
        const totalSlots = 600;
        const cellOffset = totalSlots - values.length;
        const polylinePoints = values.map((point, index) => {
            const x = left + (chartWidth * (cellOffset + index)) / (totalSlots - 1);
            const ratio = (point - min) / safeSpan;
            const y = top + chartHeight - ratio * chartHeight;
            return `${x.toFixed(2)},${y.toFixed(2)}`;
        });

        const firstX = left + (chartWidth * cellOffset) / (totalSlots - 1);
        const lastX = left + (chartWidth * (cellOffset + values.length - 1)) / (totalSlots - 1);
        const areaPoints = [
            `${firstX.toFixed(2)},${(top + chartHeight).toFixed(2)}`,
            ...polylinePoints,
            `${lastX.toFixed(2)},${(top + chartHeight).toFixed(2)}`,
        ];

        return `
            <svg class="cell-chart" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" aria-hidden="true">
                <rect x="0" y="0" width="${width}" height="${height}" class="cell-chart-bg"></rect>
                <line x1="${left}" y1="${top + chartHeight / 2}" x2="${left + chartWidth}" y2="${top + chartHeight / 2}" class="cell-chart-grid"></line>
                <polygon points="${areaPoints.join(" ")}" class="cell-chart-fill"></polygon>
                <polyline points="${polylinePoints.join(" ")}" class="cell-chart-line"></polyline>
            </svg>
        `;
    }

    function buildCell(cellData, gatewayIp) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "cell";
        const isError = cellData.display === "Err";
        if (isError) {
            button.classList.add("is-error");
        }
        if (cellData.key === state.selectedSensorKey) {
            button.classList.add("is-selected");
        }

        button.dataset.gatewayIp = gatewayIp;
        button.dataset.sensorIndex = String(cellData.sensor_index);
        button.dataset.sensorKey = cellData.key;

        const chart = document.createElement("div");
        chart.className = "cell-chart-shell";
        chart.innerHTML = buildSparklineSvg(updateSparklineHistory(cellData), cellData.range, isError);

        const value = document.createElement("div");
        value.className = "cell-value";
        if (isError) {
            value.classList.add("is-error");
        }
        value.textContent = isError ? "Err" : formatMetricValue(cellData.value);
        value.title = isError
            ? `${gatewayIp} / ${cellData.sensor_index} / Err`
            : `${gatewayIp} / ${cellData.sensor_index} / ${escapeHtml(formatMetricValue(cellData.value))}`;

        chart.appendChild(value);
        button.appendChild(chart);
        button.addEventListener("click", () => {
            state.selectedGatewayIp = gatewayIp;
            state.selectedSensorIndex = cellData.sensor_index;
            state.selectedSensorKey = cellData.key;
            refreshMatrix();
            refreshHistory();
        });
        return button;
    }

    function renderMatrix(data) {
        matrixBody.innerHTML = "";
        currentMetricLabel.textContent = metricLabels[data.metric] || data.metric;
        metricRange.textContent = `${data.range.min} ~ ${data.range.max}`;
        state.currentRange = data.range;

        data.rows.forEach((row) => {
            const rowNode = document.createElement("div");
            rowNode.className = "matrix-row";

            const gatewayLabel = document.createElement("div");
            gatewayLabel.className = "gateway-label";
            gatewayLabel.textContent = row.gateway_ip;

            const cellGrid = document.createElement("div");
            cellGrid.className = "cell-grid";
            row.cells.forEach((cell) => {
                cell.range = data.range;
                cellGrid.appendChild(buildCell(cell, row.gateway_ip));
            });

            rowNode.appendChild(gatewayLabel);
            rowNode.appendChild(cellGrid);
            matrixBody.appendChild(rowNode);
        });

        if (!state.selectedGatewayIp && data.rows.length > 0 && data.rows[0].cells.length > 0) {
            const firstCell = data.rows[0].cells[0];
            state.selectedGatewayIp = data.rows[0].gateway_ip;
            state.selectedSensorIndex = firstCell.sensor_index;
            state.selectedSensorKey = firstCell.key;
        }
    }

    function renderHistory() {
        if (!state.selectedSensorKey || !state.selectedGatewayIp) {
            return;
        }
        const historyKey = `${state.currentMetric}:${state.selectedSensorKey}`;
        const history = state.sparklineHistory[historyKey];
        if (!history || history.length === 0) {
            historyLine.setAttribute("points", "");
            return;
        }

        const min = state.currentRange.min;
        const max = state.currentRange.max;
        chartMinLabel.textContent = String(min);
        chartMaxLabel.textContent = String(max);
        detailMeta.textContent = `${state.selectedGatewayIp} / 传感器 ${state.selectedSensorIndex} / ${metricLabels[state.currentMetric] || state.currentMetric} / ${min} ~ ${max}`;

        const width = 660;
        const height = 190;
        const startX = 40;
        const startY = 20;

        const totalSlots = 600;
        const histOffset = totalSlots - history.length;
        const polylinePoints = history.map((value, index) => {
            const safeValue = value !== null ? Math.max(min, Math.min(max, value)) : min;
            const x = startX + (width * (histOffset + index)) / (totalSlots - 1);
            const ratio = (safeValue - min) / Math.max(max - min, 1);
            const y = startY + height - ratio * height;
            return `${x.toFixed(2)},${y.toFixed(2)}`;
        });

        historyLine.setAttribute("points", polylinePoints.join(" "));
    }

    async function refreshMatrix() {
        const data = await fetchJson(`/api/matrix/${state.currentMetric}${sourceParam()}`);
        renderMatrix(data);
        dataSource.textContent = data.source || dataSource.textContent;
    }

    function refreshHistory() {
        renderHistory();
    }

    async function switchDataSource(source) {
        if (source === state.dataSource) return;
        setDataSource(source);

        // 切换数据源时清空历史，避免不同来源的曲线混叠
        state.sparklineHistory = {};
        state.selectedGatewayIp = null;
        state.selectedSensorIndex = null;
        state.selectedSensorKey = null;
        matrixBody.innerHTML = `<div class="loading-row">切换中…</div>`;

        try {
            await refreshSummary();
            await refreshMatrix();
            refreshHistory();
        } catch (error) {
            console.error(error);
            matrixBody.innerHTML = `<div class="loading-row">加载失败: ${error.message}</div>`;
        }
    }

    function bindTabs() {
        document.querySelectorAll(".tab-button").forEach((button) => {
            button.addEventListener("click", () => {
                const metric = button.dataset.metric;
                if (!metric || metric === state.currentMetric) {
                    return;
                }

                state.currentMetric = metric;
                document.querySelectorAll(".tab-button").forEach((item) => item.classList.remove("is-active"));
                button.classList.add("is-active");
                refreshMatrix().then(refreshHistory).catch(console.error);
            });
        });

        sourceBtns.forEach((btn) => {
            btn.addEventListener("click", () => {
                switchDataSource(btn.dataset.source).catch(console.error);
            });
        });
    }

    async function boot() {
        setDataSource("real");
        bindTabs();

        try {
            await refreshSummary();
            await refreshMatrix();
            refreshHistory();
        } catch (error) {
            matrixBody.innerHTML = `<div class="loading-row">加载失败: ${error.message}</div>`;
        }

        window.setInterval(() => {
            refreshSummary().catch(console.error);
            refreshMatrix().then(refreshHistory).catch(console.error);
        }, refreshMs);
    }

    boot().catch((error) => {
        matrixBody.innerHTML = `<div class="loading-row">加载失败: ${error.message}</div>`;
    });
})();
