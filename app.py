import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Rebalance Calculator",
    page_icon="📊",
    layout="wide",
)

# ── Constants ──────────────────────────────────────────────────────────────────
BOND_ETF  = "FXNAX"
US_ETF    = "FXAIX"
INTL_ETF  = "FSPSX"
ETF_ORDER = [BOND_ETF, INTL_ETF, US_ETF]
LABELS    = {
    BOND_ETF: f"Bonds ({BOND_ETF})",
    US_ETF:   f"US Stocks ({US_ETF})",
    INTL_ETF: f"Intl Stocks ({INTL_ETF})",
}
ETF_COLOR = {BOND_ETF: "#3498db", US_ETF: "#e74c3c", INTL_ETF: "#2ecc71"}

REBALANCE_ABS_THRESHOLD = 5.0
REBALANCE_REL_THRESHOLD = 0.25
DEFAULT_US_WEIGHT       = 71.24  # MSCI ACWI as of 2026-02-28


# ── Calculation helpers ────────────────────────────────────────────────────────
def compute_targets(age: int, us_weight_pct: float) -> dict[str, float]:
    """Returns target % for each ETF. Stocks = 110 - age, Bonds = age - 10."""
    stock_pct = float(110 - age)
    bond_pct  = 100.0 - stock_pct
    return {
        BOND_ETF: bond_pct,
        US_ETF:   stock_pct * us_weight_pct / 100.0,
        INTL_ETF: stock_pct * (1.0 - us_weight_pct / 100.0),
    }


def rebalance_band(target_pct: float) -> tuple[float, float]:
    """5/25 rule band in percentage points."""
    trigger = min(REBALANCE_ABS_THRESHOLD, target_pct * REBALANCE_REL_THRESHOLD)
    return max(0.0, target_pct - trigger), target_pct + trigger


def fmt_usd(v: float) -> str:
    return f"${v:,.0f}"


def holding_status(current_usd: float, lo_usd: float, hi_usd: float) -> str:
    if current_usd < lo_usd:
        return "🔴 Low"
    if current_usd > hi_usd:
        return "🟠 High"
    return "🟢 OK"


# ── UI ─────────────────────────────────────────────────────────────────────────
st.title("📊 Rebalance Calculator")
st.caption(
    "Strategy: Stocks = 110 − age  |  Bonds = age − 10  |  "
    "US/Intl split follows MSCI ACWI country weights"
)

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Settings")

    col_age, col_us = st.columns(2)
    age = col_age.number_input(
        "Age", min_value=18, max_value=80, value=27, step=1,
    )
    us_weight = col_us.number_input(
        "US weight (%)",
        min_value=0.0, max_value=100.0,
        value=DEFAULT_US_WEIGHT,
        step=0.1, format="%.1f",
        help="MSCI ACWI US weight. Default: 71.2% (2026-02-28).",
    )

    st.divider()
    st.subheader("Portfolio (USD)")
    total_portfolio = st.number_input(
        "Total portfolio value",
        min_value=0.0, value=0.0, step=1000.0, format="%.2f",
        help="Total value of all assets including cash",
    )
    cash = st.number_input(
        "Cash / money market",
        min_value=0.0, value=0.0, step=100.0, format="%.2f",
        help="Portion held as cash — excluded from ETF allocation",
    )

    st.divider()
    st.subheader("Current Holdings (USD)")
    current_bond = st.number_input(
        f"Bonds ({BOND_ETF})",
        min_value=0.0, value=0.0, step=100.0, format="%.2f",
    )
    current_intl = st.number_input(
        f"Intl Stocks ({INTL_ETF})",
        min_value=0.0, value=0.0, step=100.0, format="%.2f",
    )
    # FXAIX is computed after investable is known — shown via st.sidebar.metric below


# ── Derived values ─────────────────────────────────────────────────────────────
investable  = max(0.0, total_portfolio - cash)
targets     = compute_targets(age, us_weight)

target_usd  = {etf: investable * targets[etf] / 100.0 for etf in ETF_ORDER}
band_lo_usd = {etf: investable * rebalance_band(targets[etf])[0] / 100.0 for etf in ETF_ORDER}
band_hi_usd = {etf: investable * rebalance_band(targets[etf])[1] / 100.0 for etf in ETF_ORDER}

current_us = max(0.0, investable - current_bond - current_intl)
current_holdings = {BOND_ETF: current_bond, US_ETF: current_us, INTL_ETF: current_intl}
has_holdings = investable > 0 and (current_bond > 0 or current_intl > 0)

st.sidebar.metric(
    f"US Stocks ({US_ETF}) — computed",
    fmt_usd(current_us),
    help="Investable − Bonds − Intl Stocks",
)


# ── Top metrics ────────────────────────────────────────────────────────────────
if total_portfolio > 0:
    cash_pct = cash / total_portfolio * 100
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Portfolio", fmt_usd(total_portfolio))
    m2.metric("Cash", fmt_usd(cash), delta=f"{cash_pct:.1f}% of total", delta_color="off")
    m3.metric("Investable", fmt_usd(investable))
    m4.metric("Stock / Bond split", f"{110-age} / {age-10}")
    st.divider()


# ── Layout ─────────────────────────────────────────────────────────────────────
col_pie, col_table = st.columns([1, 1], gap="large")

# ── Pie chart ─────────────────────────────────────────────────────────────────
with col_pie:
    st.subheader("Target Allocation")
    fig = go.Figure(go.Pie(
        labels=[LABELS[k] for k in ETF_ORDER],
        values=[targets[k] for k in ETF_ORDER],
        hole=0.45,
        marker_colors=[ETF_COLOR[k] for k in ETF_ORDER],
        textinfo="label+percent",
        hovertemplate="%{label}: %{value:.1f}%<extra></extra>",
    ))
    fig.update_layout(showlegend=False, height=300, margin=dict(t=10, b=10, l=10, r=10))
    st.plotly_chart(fig, use_container_width=True)


# ── Target table ───────────────────────────────────────────────────────────────
with col_table:
    st.subheader("Target Ranges (5/25 Rule)")

    if total_portfolio == 0:
        st.info("Enter your portfolio value on the left.")
    else:
        rows = []
        for etf in ETF_ORDER:
            row = {
                "ETF":           LABELS[etf],
                "Target $":      target_usd[etf],
                "Lower limit":   band_lo_usd[etf],
                "Upper limit":   band_hi_usd[etf],
            }
            if has_holdings:
                cur = current_holdings[etf]
                row["Status"] = holding_status(cur, band_lo_usd[etf], band_hi_usd[etf])
            rows.append(row)

        df = pd.DataFrame(rows)
        fmt = {
            "Target $":    "${:,.0f}",
            "Lower limit": "${:,.0f}",
            "Upper limit": "${:,.0f}",
        }
        styled = (
            df.style
            .format(fmt)
            .set_properties(**{"text-align": "right"})
            .set_properties(subset=["ETF"], **{"text-align": "left"})
        )
        st.dataframe(styled, use_container_width=True, hide_index=True)


# ── Bullet chart ───────────────────────────────────────────────────────────────
if total_portfolio > 0:
    st.divider()
    st.subheader("Dollar Target Ranges")

    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(
        name="Target & Band",
        y=[LABELS[k] for k in ETF_ORDER],
        x=[target_usd[k] for k in ETF_ORDER],
        mode="markers",
        marker=dict(symbol="line-ns", size=24, color="#2c3e50",
                    line=dict(width=3, color="#2c3e50")),
        error_x=dict(
            type="data", symmetric=False,
            array=[band_hi_usd[k] - target_usd[k] for k in ETF_ORDER],
            arrayminus=[target_usd[k] - band_lo_usd[k] for k in ETF_ORDER],
            color="#b0bec5", thickness=12, width=0,
        ),
        hovertemplate="%{y}<br>Target: $%{x:,.0f}<extra></extra>",
    ))
    if has_holdings:
        fig3.add_trace(go.Scatter(
            name="Current",
            y=[LABELS[k] for k in ETF_ORDER],
            x=[current_holdings[k] for k in ETF_ORDER],
            mode="markers",
            marker=dict(
                symbol="diamond", size=14,
                color=[ETF_COLOR[k] for k in ETF_ORDER],
                line=dict(color="#2c3e50", width=2),
            ),
            hovertemplate="%{y}<br>Current: $%{x:,.0f}<extra></extra>",
        ))
    fig3.update_layout(
        xaxis_title="Amount (USD)", xaxis_tickformat="$,.0f",
        height=220, margin=dict(t=10, b=30, l=10, r=20),
        showlegend=True,
    )
    st.plotly_chart(fig3, use_container_width=True)
    st.caption("Grey bar = 5/25 tolerance band  |  tick = target  |  diamond = current holdings.")


# ── Footer ─────────────────────────────────────────────────────────────────────
st.caption(
    "[110 rule](https://www.bogleheads.org/wiki/Asset_allocation) · "
    "[5/25 rebalancing rule](https://www.bogleheads.org/wiki/Rebalancing)"
)
