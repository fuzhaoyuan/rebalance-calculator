// ── Constants ────────────────────────────────────────────────────────────────
const BOND_ETF = "FXNAX";
const US_ETF = "FXAIX";
const INTL_ETF = "FZILX";
const ETF_ORDER = [BOND_ETF, INTL_ETF, US_ETF];
const LABELS = {
  [BOND_ETF]: `Bonds (${BOND_ETF})`,
  [US_ETF]: `US Stocks (${US_ETF})`,
  [INTL_ETF]: `Intl Stocks (${INTL_ETF})`,
};
const ETF_COLOR = { [BOND_ETF]: "#3498db", [US_ETF]: "#e74c3c", [INTL_ETF]: "#2ecc71" };

const REBALANCE_ABS_THRESHOLD = 5.0;
const REBALANCE_REL_THRESHOLD = 0.25;
// 7:3 US/Intl fixed split — S&P 500 earns ~62% US / ~38% intl revenue;
// MSCI ACWI ex-US earns ~22% US / ~78% intl revenue.
// At 70/30, blended US-sourced revenue ≈ 50%, achieving ~50/50 true geographic exposure.
const US_STOCK_WEIGHT = 70.0;

// ── Calculation helpers ─────────────────────────────────────────────────────
function computeTargets(age) {
  const stockPct = 110 - age;
  const bondPct = 100.0 - stockPct;
  return {
    [BOND_ETF]: bondPct,
    [US_ETF]: (stockPct * US_STOCK_WEIGHT) / 100.0,
    [INTL_ETF]: (stockPct * (100.0 - US_STOCK_WEIGHT)) / 100.0,
  };
}

function rebalanceBand(targetPct) {
  const trigger = Math.min(REBALANCE_ABS_THRESHOLD, targetPct * REBALANCE_REL_THRESHOLD);
  return [Math.max(0.0, targetPct - trigger), targetPct + trigger];
}

function fmtUsd(v) {
  return `$${Math.round(v).toLocaleString("en-US")}`;
}

function holdingStatus(current, lo, hi) {
  if (current < lo) return "🔴 Low";
  if (current > hi) return "🟠 High";
  return "🟢 OK";
}

function clamp(value, min, max) {
  if (Number.isNaN(value)) return min;
  let v = value;
  if (min !== undefined) v = Math.max(min, v);
  if (max !== undefined) v = Math.min(max, v);
  return v;
}

// ── DOM refs ─────────────────────────────────────────────────────────────────
const el = (id) => document.getElementById(id);
const ageInput = el("age");
const totalPortfolioInput = el("totalPortfolio");
const cashInput = el("cash");
const currentBondInput = el("currentBond");
const currentIntlInput = el("currentIntl");

const computedUsValueEl = el("computedUsValue");
const metricsRowEl = el("metricsRow");
const mTotalEl = el("mTotal");
const mCashEl = el("mCash");
const mCashDeltaEl = el("mCashDelta");
const mInvestableEl = el("mInvestable");
const mSplitEl = el("mSplit");
const tableContainerEl = el("tableContainer");
const bulletSectionEl = el("bulletSection");

// ── Render ───────────────────────────────────────────────────────────────────
function render() {
  const age = clamp(Number(ageInput.value), 18, 80);
  const totalPortfolio = clamp(Number(totalPortfolioInput.value) || 0, 0);
  const cash = clamp(Number(cashInput.value) || 0, 0);
  const currentBond = clamp(Number(currentBondInput.value) || 0, 0);
  const currentIntl = clamp(Number(currentIntlInput.value) || 0, 0);

  const investable = Math.max(0.0, totalPortfolio - cash);
  const targets = computeTargets(age);

  const targetUsd = {};
  const bandLoUsd = {};
  const bandHiUsd = {};
  for (const etf of ETF_ORDER) {
    targetUsd[etf] = (investable * targets[etf]) / 100.0;
    const [lo, hi] = rebalanceBand(targets[etf]);
    bandLoUsd[etf] = (investable * lo) / 100.0;
    bandHiUsd[etf] = (investable * hi) / 100.0;
  }

  const currentUs = Math.max(0.0, investable - currentBond - currentIntl);
  const currentHoldings = { [BOND_ETF]: currentBond, [US_ETF]: currentUs, [INTL_ETF]: currentIntl };
  const hasHoldings = investable > 0 && (currentBond > 0 || currentIntl > 0);

  computedUsValueEl.textContent = fmtUsd(currentUs);

  // ── Top metrics ──────────────────────────────────────────────────────────
  if (totalPortfolio > 0) {
    metricsRowEl.style.display = "grid";
    const cashPct = (cash / totalPortfolio) * 100;
    mTotalEl.textContent = fmtUsd(totalPortfolio);
    mCashEl.textContent = fmtUsd(cash);
    mCashDeltaEl.textContent = `${cashPct.toFixed(1)}% of total`;
    mInvestableEl.textContent = fmtUsd(investable);
    mSplitEl.textContent = `${110 - age} / ${age - 10}`;
  } else {
    metricsRowEl.style.display = "none";
  }

  // ── Pie chart ────────────────────────────────────────────────────────────
  Plotly.react(
    "pieChart",
    [
      {
        type: "pie",
        labels: ETF_ORDER.map((k) => LABELS[k]),
        values: ETF_ORDER.map((k) => targets[k]),
        hole: 0.45,
        marker: { colors: ETF_ORDER.map((k) => ETF_COLOR[k]) },
        textinfo: "label+percent",
        hovertemplate: "%{label}: %{value:.1f}%<extra></extra>",
      },
    ],
    { showlegend: false, height: 300, margin: { t: 10, b: 10, l: 10, r: 10 } },
    { displayModeBar: false, responsive: true }
  );

  // ── Target table ─────────────────────────────────────────────────────────
  if (totalPortfolio === 0) {
    tableContainerEl.innerHTML = `<div class="info-box">Enter your portfolio value on the left.</div>`;
  } else {
    const rows = ETF_ORDER.map((etf) => {
      const cells = [
        `<td>${LABELS[etf]}</td>`,
        `<td>${fmtUsd(targetUsd[etf])}</td>`,
        `<td>${fmtUsd(bandLoUsd[etf])}</td>`,
        `<td>${fmtUsd(bandHiUsd[etf])}</td>`,
      ];
      if (hasHoldings) {
        cells.push(`<td>${holdingStatus(currentHoldings[etf], bandLoUsd[etf], bandHiUsd[etf])}</td>`);
      }
      return `<tr>${cells.join("")}</tr>`;
    }).join("");

    const statusHeader = hasHoldings ? "<th>Status</th>" : "";
    tableContainerEl.innerHTML = `
      <table class="rebalance-table">
        <thead>
          <tr><th>ETF</th><th>Target $</th><th>Lower limit</th><th>Upper limit</th>${statusHeader}</tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>`;
  }

  // ── Bullet chart ─────────────────────────────────────────────────────────
  if (totalPortfolio > 0) {
    bulletSectionEl.style.display = "block";

    const traces = [
      {
        name: "Target & Band",
        y: ETF_ORDER.map((k) => LABELS[k]),
        x: ETF_ORDER.map((k) => targetUsd[k]),
        mode: "markers",
        type: "scatter",
        marker: { symbol: "line-ns", size: 24, color: "#2c3e50", line: { width: 3, color: "#2c3e50" } },
        error_x: {
          type: "data",
          symmetric: false,
          array: ETF_ORDER.map((k) => bandHiUsd[k] - targetUsd[k]),
          arrayminus: ETF_ORDER.map((k) => targetUsd[k] - bandLoUsd[k]),
          color: "#b0bec5",
          thickness: 12,
          width: 0,
        },
        hovertemplate: "%{y}<br>Target: $%{x:,.0f}<extra></extra>",
      },
    ];

    if (hasHoldings) {
      traces.push({
        name: "Current",
        y: ETF_ORDER.map((k) => LABELS[k]),
        x: ETF_ORDER.map((k) => currentHoldings[k]),
        mode: "markers",
        type: "scatter",
        marker: {
          symbol: "diamond",
          size: 14,
          color: ETF_ORDER.map((k) => ETF_COLOR[k]),
          line: { color: "#2c3e50", width: 2 },
        },
        hovertemplate: "%{y}<br>Current: $%{x:,.0f}<extra></extra>",
      });
    }

    Plotly.react("bulletChart", traces, {
      xaxis: { title: "Amount (USD)", tickformat: "$,.0f" },
      height: 220,
      margin: { t: 10, b: 30, l: 10, r: 20 },
      showlegend: true,
    }, { displayModeBar: false, responsive: true });
  } else {
    bulletSectionEl.style.display = "none";
  }
}

const BOUNDS = new Map([
  [ageInput, [18, 80]],
  [totalPortfolioInput, [0, undefined]],
  [cashInput, [0, undefined]],
  [currentBondInput, [0, undefined]],
  [currentIntlInput, [0, undefined]],
]);

BOUNDS.forEach(([min, max], input) => {
  input.addEventListener("input", render);
  input.addEventListener("change", () => {
    if (input.value === "") return;
    const corrected = clamp(Number(input.value), min, max);
    if (corrected !== Number(input.value)) {
      input.value = corrected;
      render();
    }
  });
});

render();
