"""
Ethiopia Financial Inclusion Forecast — Interactive Dashboard
Task 5 deliverable. Run with: streamlit run dashboard/app.py
"""
import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(page_title="Ethiopia Financial Inclusion Forecast", layout="wide", page_icon="🇪🇹")

# ----------------------------------------------------------------------------
# Data loading (self-locating, robust to where streamlit is launched from)
# ----------------------------------------------------------------------------
@st.cache_data
def load_data():
    here = Path.cwd()
    candidates = [here, here.parent, here.parent.parent, Path(__file__).parent, Path(__file__).parent.parent]
    processed = next((c / "data" / "processed" for c in candidates if (c / "data" / "processed").exists()), None)
    if processed is None:
        st.error("Could not locate data/processed folder. Run streamlit from the project root.")
        st.stop()

    df = pd.read_csv(processed / "ethiopia_fi_unified_data_enriched.csv")
    df["observation_date"] = pd.to_datetime(df["observation_date"], errors="coerce")

    obs = df[df["record_type"] == "observation"].copy()
    events = df[df["record_type"] == "event"].copy()
    targets = df[df["record_type"] == "target"].copy()
    links = df[df["record_type"] == "impact_link"].copy()

    access_fc, usage_fc = None, None
    if (processed / "forecast_access.csv").exists():
        access_fc = pd.read_csv(processed / "forecast_access.csv")
    if (processed / "forecast_usage.csv").exists():
        usage_fc = pd.read_csv(processed / "forecast_usage.csv")

    return df, obs, events, targets, links, access_fc, usage_fc

df, obs, events, targets, links, access_fc, usage_fc = load_data()

# ----------------------------------------------------------------------------
# Sidebar navigation
# ----------------------------------------------------------------------------
st.sidebar.title("🇪🇹 FI Forecast")
page = st.sidebar.radio("Navigate", ["Overview", "Trends", "Forecasts", "Inclusion Projections"])
st.sidebar.markdown("---")
st.sidebar.caption("Selam Analytics — Week 11 Challenge\nData: Global Findex, Ethio Telecom, EthSwitch, NBE, Safaricom")

# ----------------------------------------------------------------------------
# Shared helper: latest value for an indicator
# ----------------------------------------------------------------------------
def latest(indicator_code, gender="all", location="national"):
    d = obs[(obs.indicator_code == indicator_code) & (obs.gender == gender) & (obs.location == location)]
    d = d.sort_values("observation_date")
    return d.iloc[-1] if len(d) else None

def prior(indicator_code, gender="all", location="national"):
    d = obs[(obs.indicator_code == indicator_code) & (obs.gender == gender) & (obs.location == location)]
    d = d.sort_values("observation_date")
    return d.iloc[-2] if len(d) >= 2 else None

# ============================================================================
# PAGE 1: OVERVIEW
# ============================================================================
if page == "Overview":
    st.title("Ethiopia Financial Inclusion — Overview")
    st.caption("Key metrics summary as of the latest available observation for each indicator.")

    col1, col2, col3, col4 = st.columns(4)

    acc_latest, acc_prior = latest("ACC_OWNERSHIP"), prior("ACC_OWNERSHIP")
    with col1:
        delta = f"+{acc_latest.value_numeric - acc_prior.value_numeric:.0f}pp" if acc_prior is not None else None
        st.metric("Account Ownership", f"{acc_latest.value_numeric:.0f}%", delta)

    mm_latest, mm_prior = latest("ACC_MM_ACCOUNT"), prior("ACC_MM_ACCOUNT")
    with col2:
        delta = f"+{mm_latest.value_numeric - mm_prior.value_numeric:.2f}pp" if mm_prior is not None else None
        st.metric("Mobile Money Account Rate", f"{mm_latest.value_numeric:.2f}%", delta)

    crossover = latest("USG_CROSSOVER")
    with col3:
        st.metric("P2P/ATM Crossover Ratio", f"{crossover.value_numeric:.2f}",
                   "P2P > ATM" if crossover.value_numeric > 1 else "ATM > P2P")

    gap = latest("GEN_GAP_ACC")
    with col4:
        st.metric("Gender Gap (Account Ownership)", f"{gap.value_numeric:.0f}pp")

    st.markdown("---")
    col5, col6 = st.columns(2)

    with col5:
        st.subheader("Growth Rate Highlights")
        acc_series = obs[(obs.indicator_code == "ACC_OWNERSHIP") & (obs.gender == "all") & (obs.location == "national")].sort_values("observation_date")
        acc_series["year"] = acc_series.observation_date.dt.year
        acc_series["growth_pp"] = acc_series.value_numeric.diff()
        acc_series["years_elapsed"] = acc_series.year.diff()
        acc_series["pp_per_year"] = (acc_series.growth_pp / acc_series.years_elapsed).round(2)
        st.dataframe(acc_series[["year", "value_numeric", "growth_pp", "pp_per_year"]].rename(
            columns={"value_numeric": "Account Ownership %", "growth_pp": "Change (pp)", "pp_per_year": "pp/year"}
        ), hide_index=True, use_container_width=True)

    with col6:
        st.subheader("P2P vs ATM Transaction Volume")
        p2p = obs[obs.indicator_code == "USG_P2P_COUNT"].sort_values("observation_date")
        atm = obs[obs.indicator_code == "USG_ATM_COUNT"].sort_values("observation_date")
        fig = go.Figure()
        fig.add_trace(go.Bar(x=["P2P"], y=[p2p.value_numeric.iloc[-1] / 1e6], name="P2P", marker_color="#1f6feb"))
        fig.add_trace(go.Bar(x=["ATM"], y=[atm.value_numeric.iloc[-1] / 1e6], name="ATM", marker_color="#d97706"))
        fig.update_layout(yaxis_title="Transactions (millions)", showlegend=False, height=350, margin=dict(t=10))
        st.plotly_chart(fig, use_container_width=True)

# ============================================================================
# PAGE 2: TRENDS
# ============================================================================
elif page == "Trends":
    st.title("Trends Explorer")

    indicator_options = sorted(obs["indicator_code"].dropna().unique().tolist())
    default_idx = indicator_options.index("ACC_OWNERSHIP") if "ACC_OWNERSHIP" in indicator_options else 0
    selected_indicators = st.multiselect("Select indicator(s) to compare", indicator_options,
                                          default=[indicator_options[default_idx]])

    min_date, max_date = obs.observation_date.min(), obs.observation_date.max()
    date_range = st.slider("Date range", min_value=min_date.to_pydatetime(), max_value=max_date.to_pydatetime(),
                            value=(min_date.to_pydatetime(), max_date.to_pydatetime()))

    show_events = st.checkbox("Overlay events", value=True)

    if selected_indicators:
        filtered = obs[(obs.indicator_code.isin(selected_indicators)) &
                        (obs.observation_date >= date_range[0]) & (obs.observation_date <= date_range[1]) &
                        (obs.gender == "all")]
        fig = px.line(filtered.sort_values("observation_date"), x="observation_date", y="value_numeric",
                       color="indicator_code", markers=True,
                       labels={"observation_date": "Date", "value_numeric": "Value", "indicator_code": "Indicator"})
        if show_events:
            ev_in_range = events[(events.observation_date >= date_range[0]) & (events.observation_date <= date_range[1])]
            for _, ev in ev_in_range.iterrows():
                fig.add_vline(x=ev.observation_date, line_dash="dash", line_color="gray", opacity=0.5)
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Select at least one indicator above.")

    st.markdown("---")
    st.subheader("Channel Comparison: Registered vs. Active Mobile Money Users")
    channel_data = pd.DataFrame({
        "Metric": ["Telebirr Registered", "M-Pesa Registered", "M-Pesa 90-day Active"],
        "Users (millions)": [54.84, 10.8, 7.1]
    })
    fig2 = px.bar(channel_data, x="Metric", y="Users (millions)", color="Metric",
                   color_discrete_sequence=["#1f6feb", "#d97706", "#9ca3af"])
    fig2.update_layout(showlegend=False, height=400)
    st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")
    st.subheader("Download Data")
    st.download_button("Download filtered observations (CSV)",
                        obs.to_csv(index=False).encode("utf-8"),
                        "ethiopia_fi_observations.csv", "text/csv")

# ============================================================================
# PAGE 3: FORECASTS
# ============================================================================
elif page == "Forecasts":
    st.title("Access & Usage Forecasts, 2025–2027")

    if access_fc is None or usage_fc is None:
        st.warning("Forecast files not found. Run Task 4's notebook and confirm "
                   "`forecast_access.csv` / `forecast_usage.csv` exist in data/processed/.")
    else:
        model_choice = st.selectbox("Forecast model", ["Event-augmented (recommended)", "Trend-only baseline"])

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Access: Account Ownership Rate")
            acc_hist = obs[(obs.indicator_code == "ACC_OWNERSHIP") & (obs.gender == "all") & (obs.location == "national")].sort_values("observation_date")
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=acc_hist.observation_date.dt.year, y=acc_hist.value_numeric,
                                      mode="lines+markers", name="Observed", line=dict(color="black", width=2)))
            y_col = "base_scenario" if model_choice.startswith("Event") else "trend_baseline"
            fig.add_trace(go.Scatter(x=access_fc.year, y=access_fc[y_col], mode="lines+markers",
                                      name="Forecast", line=dict(color="#1f6feb", width=2)))
            fig.add_trace(go.Scatter(x=list(access_fc.year) + list(access_fc.year[::-1]),
                                      y=list(access_fc.optimistic) + list(access_fc.pessimistic[::-1]),
                                      fill="toself", fillcolor="rgba(31,111,235,0.15)", line=dict(width=0),
                                      name="Scenario range", showlegend=True))
            fig.add_hline(y=70, line_dash="dot", line_color="#d97706", annotation_text="NFIS-II 2025 target")
            fig.update_layout(yaxis_title="% of adults", height=450)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("Usage: Mobile Money Account Rate")
            mm_hist = obs[obs.indicator_code == "ACC_MM_ACCOUNT"].sort_values("observation_date")
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=mm_hist.observation_date.dt.year, y=mm_hist.value_numeric,
                                       mode="lines+markers", name="Observed", line=dict(color="black", width=2)))
            fig2.add_trace(go.Scatter(x=usage_fc.year, y=usage_fc.base, mode="lines+markers",
                                       name="Forecast (base)", line=dict(color="#1f6feb", width=2)))
            fig2.add_trace(go.Scatter(x=list(usage_fc.year) + list(usage_fc.year[::-1]),
                                       y=list(usage_fc.optimistic) + list(usage_fc.pessimistic[::-1]),
                                       fill="toself", fillcolor="rgba(31,111,235,0.15)", line=dict(width=0),
                                       name="Scenario range", showlegend=True))
            fig2.update_layout(yaxis_title="% of adults", height=450)
            st.plotly_chart(fig2, use_container_width=True)

        st.markdown("---")
        st.subheader("Key Projected Milestones")
        m1, m2, m3 = st.columns(3)
        m1.metric("Access, 2027 (base)", f"{access_fc.loc[access_fc.year==2027, 'base_scenario'].values[0]:.1f}%")
        m2.metric("Usage, 2027 (base)", f"{usage_fc.loc[usage_fc.year==2027, 'base'].values[0]:.1f}%")
        gap_to_target = 70 - access_fc.loc[access_fc.year==2027, 'base_scenario'].values[0]
        m3.metric("Gap to 70% NFIS-II target (2027)", f"{gap_to_target:.1f}pp")

        st.download_button("Download Access forecast (CSV)", access_fc.to_csv(index=False).encode("utf-8"),
                            "forecast_access.csv", "text/csv")
        st.download_button("Download Usage forecast (CSV)", usage_fc.to_csv(index=False).encode("utf-8"),
                            "forecast_usage.csv", "text/csv")

# ============================================================================
# PAGE 4: INCLUSION PROJECTIONS
# ============================================================================
elif page == "Inclusion Projections":
    st.title("Inclusion Projections & Consortium Q&A")

    scenario = st.radio("Scenario", ["Optimistic", "Base", "Pessimistic"], horizontal=True)
    scenario_col = {"Optimistic": "optimistic", "Base": "base_scenario", "Pessimistic": "pessimistic"}[scenario]

    if access_fc is not None:
        target_2025 = targets[targets.indicator_code == "ACC_OWNERSHIP"].value_numeric.iloc[0] if len(targets[targets.indicator_code=="ACC_OWNERSHIP"]) else 70

        st.subheader(f"Progress Toward {target_2025:.0f}% Access Target ({scenario} scenario)")
        fig = go.Figure()
        acc_hist = obs[(obs.indicator_code == "ACC_OWNERSHIP") & (obs.gender == "all") & (obs.location=="national")].sort_values("observation_date")
        fig.add_trace(go.Scatter(x=acc_hist.observation_date.dt.year, y=acc_hist.value_numeric,
                                  mode="lines+markers", name="Observed", line=dict(color="black", width=2)))
        fig.add_trace(go.Scatter(x=access_fc.year, y=access_fc[scenario_col], mode="lines+markers",
                                  name=f"{scenario} forecast", line=dict(color="#1f6feb", width=2)))
        fig.add_hline(y=target_2025, line_dash="dot", line_color="#d97706",
                       annotation_text=f"NFIS-II target: {target_2025:.0f}%")
        fig.update_layout(yaxis_title="% of adults", height=450)
        st.plotly_chart(fig, use_container_width=True)

        final_val = access_fc.loc[access_fc.year==2027, scenario_col].values[0]
        st.progress(min(final_val / target_2025, 1.0))
        st.caption(f"Projected 2027 Access ({scenario.lower()}): {final_val:.1f}% of {target_2025:.0f}% target "
                   f"({final_val/target_2025*100:.0f}% of the way there).")

    st.markdown("---")
    st.subheader("Answers to the Consortium's Key Questions")

    with st.expander("What drives financial inclusion in Ethiopia?"):
        st.write("Infrastructure expansion (4G coverage nearly doubled, 37.5%→70.8%) and mobile money "
                 "product launches (Telebirr, M-Pesa) are the strongest observed correlates of Usage growth. "
                 "Access growth has been more constrained, suggesting drivers like KYC/documentation "
                 "requirements and the registered-vs-active usage gap matter more for account ownership "
                 "specifically than for mobile money adoption.")

    with st.expander("How did financial inclusion change in 2025, and what's projected for 2026-2027?"):
        if access_fc is not None:
            st.write(f"Access is projected to reach roughly {access_fc.loc[access_fc.year==2025,'base_scenario'].values[0]:.0f}% "
                     f"in 2025, rising to {access_fc.loc[access_fc.year==2027,'base_scenario'].values[0]:.0f}% by 2027 in the base "
                     "scenario — short of the 70% NFIS-II target even under optimistic assumptions. Usage "
                     f"(mobile money account rate) is projected to grow faster, from 9.45% (2024) to roughly "
                     f"{usage_fc.loc[usage_fc.year==2027,'base'].values[0]:.0f}% by 2027.")

    with st.expander("What is the biggest risk to these projections?"):
        st.write("No Global Findex survey has been conducted since late 2024, so every 2025–2027 figure is "
                 "an extrapolation, not a measurement. The registered-vs-active usage gap — millions of "
                 "mobile money sign-ups not translating into survey-measured account ownership — is not "
                 "explicitly modeled and could mean actual Access growth undershoots even the pessimistic scenario.")

    st.markdown("---")
    st.caption("Data limitations: sparse Findex time series (5 points, 2011–2024); most impact_link "
               "estimates carry medium/low confidence since 2024–2025 events are too recent for empirical "
               "Ethiopia-specific validation. See the final report for full methodology and caveats.")