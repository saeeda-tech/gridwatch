"""GridWatch: grid reliability monitor (Kaduna pilot).
Data: NERC quarterly reports (public). See data/README in the dataset folder.
Run:  streamlit run app.py
"""
import math
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

DATA = Path(__file__).parent / "data"
st.set_page_config(page_title="GridWatch", page_icon="⚡", layout="wide")

# ---------------------------------------------------------------- data
@st.cache_data
def load():
    m = pd.read_csv(DATA / "monthly_grid_nerc.csv")
    m["date"] = pd.to_datetime(m["month"] + "-15")
    m = m.rename(columns={
        "avg_upper_daily_frequency_hz": "upper",
        "avg_lower_daily_frequency_hz": "lower",
        "avg_hourly_generation_mwh_per_h": "gen"})
    m["range"] = m["upper"] - m["lower"]
    e = pd.read_csv(DATA / "collapse_events.csv", parse_dates=["date"])
    e["month"] = e["date"].dt.strftime("%Y-%m")
    q = pd.read_csv(DATA / "collapses_per_quarter.csv")
    k = pd.read_csv(DATA / "kaduna_disco_nerc.csv")
    return m, e, q, k


# ---------------------------------------------------------------- transformer ageing
# Simplified steady-state thermal model in the style of IEC 60076-7 for oil-immersed
# distribution transformers (ONAN). Engineering estimate only. Check parameters against the
# nameplate or test report.
def tx_temps(K, amb, d_or=55.0, R=5.0, x=0.8, hg=23.0, y=1.6):
    """Return (top-oil temp, hot-spot temp) in deg C at load factor K and ambient amb."""
    top = amb + d_or * ((1 + R * K ** 2) / (1 + R)) ** x
    hot = top + hg * K ** y
    return top, hot

def tx_aging(hot, paper="Normal paper"):
    """Relative ageing rate V (1.0 = ageing at the design reference temperature)."""
    if paper == "Thermally upgraded paper":
        return math.exp(15000 / 383 - 15000 / (hot + 273))
    return 2 ** ((hot - 98) / 6)

def tx_daily(rated, base, peak, hours, amb, paper, **p):
    kb, kp = base / rated, peak / rated
    hb = tx_temps(kb, amb, **p)[1]; hp = tx_temps(kp, amb, **p)[1]
    vb, vp = tx_aging(hb, paper), tx_aging(hp, paper)
    vavg = (vp * hours + vb * (24 - hours)) / 24
    return hb, hp, vb, vp, vavg

def risk_label(v):
    if v < 1: return "Low", "success"
    if v < 2: return "Elevated", "warning"
    if v < 5: return "High", "warning"
    return "Severe", "error"

monthly, events, quarterly, kaduna = load()

# ---------------------------------------------------------------- header
st.title("⚡ GridWatch")
st.caption("Grid reliability monitor and risk outlook · Kaduna pilot · "
           "Built on public NERC quarterly reports (2019 to Q2 2026)")

tab1, tab2, tab3, tab4, tab_tx, tab5 = st.tabs(
    ["Grid stress", "Backtest", "Kaduna DisCo", "Local pilot log", "Transformer risk", "About and limits"])

# ================================================================ TAB 1
with tab1:
    last = monthly.iloc[-1]
    recent = events[events["date"] >= events["date"].max() - pd.DateOffset(years=1) - pd.Timedelta(days=1)]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Latest month", last["month"])
    c2.metric("Frequency range", f"{last['range']:.2f} Hz",
              help="Average upper daily frequency minus average lower daily frequency. Wider means more stress.")
    c3.metric("Avg hourly generation", f"{last['gen']:,.0f} MWh/h")
    c4.metric("Collapses, last 12 months of data", len(recent))

    st.subheader("Monthly system frequency and collapse events")
    fig = go.Figure()
    fig.add_hrect(y0=49.75, y1=50.25, fillcolor="green", opacity=0.10, line_width=0,
                  annotation_text="Normal band 49.75-50.25 Hz", annotation_position="top left")
    fig.add_hline(y=48.75, line_dash="dot", line_color="red", annotation_text="Lower stress limit 48.75 Hz")
    fig.add_hline(y=51.25, line_dash="dot", line_color="red", annotation_text="Upper stress limit 51.25 Hz")
    fig.add_trace(go.Scatter(x=monthly["date"], y=monthly["upper"], mode="lines+markers",
                             name="Avg upper daily frequency"))
    fig.add_trace(go.Scatter(x=monthly["date"], y=monthly["lower"], mode="lines+markers",
                             name="Avg lower daily frequency"))
    ev_in = events[events["date"] >= monthly["date"].min() - pd.Timedelta(days=15)]
    fig.add_trace(go.Scatter(
        x=ev_in["date"], y=[48.55] * len(ev_in), mode="markers", name="Collapse event",
        marker=dict(symbol="x", size=11, color="red"),
        text=ev_in["type"] + " · " + ev_in["note"].fillna(""), hovertemplate="%{x|%d %b %Y}<br>%{text}<extra></extra>"))
    fig.update_layout(height=470, yaxis_title="Hz", margin=dict(l=10, r=10, t=30, b=10),
                      legend=dict(orientation="h", y=-0.15))
    st.plotly_chart(fig, width="stretch")
    st.caption("Frequency values are monthly averages of the daily highest and lowest readings, not live data.")

    g = monthly.dropna(subset=["gen"])
    st.subheader("Average hourly generation")
    fig2 = go.Figure(go.Bar(x=g["date"], y=g["gen"], name="MWh/h", marker_color="#2E75B6"))
    ev_g = events[events["date"] >= g["date"].min() - pd.Timedelta(days=15)]
    fig2.add_trace(go.Scatter(x=ev_g["date"], y=[g["gen"].min() * 0.93] * len(ev_g), mode="markers",
                              name="Collapse event", marker=dict(symbol="x", size=10, color="red")))
    fig2.update_layout(height=340, yaxis_title="MWh/h", margin=dict(l=10, r=10, t=10, b=10),
                       legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(fig2, width="stretch")

    st.subheader("Collapses per year (NERC count)")
    quarterly["year"] = quarterly["quarter"].str[:4]
    yr = quarterly.groupby("year")[["total_collapses", "partial_collapses", "type_not_stated"]].sum()
    st.bar_chart(yr)
    st.caption("2026 covers January to June only. 2019-2020 are counts without dates.")

    with st.expander("Collapse event table"):
        st.dataframe(events.drop(columns=["month"]), width="stretch", hide_index=True)

# ================================================================ TAB 2
with tab2:
    st.subheader("Simple stress rule: how well does it match past collapse months?")
    st.write("A month is flagged **elevated** if its frequency range is at or above the threshold"
             " (optionally also if generation is low). Then we compare flagged months with months that had a collapse.")
    a, b = st.columns(2)
    thr = a.slider("Frequency range threshold (Hz)", 1.2, 2.0, 1.6, 0.05)
    use_gen = b.checkbox("Also flag low generation", value=False)
    gthr = b.slider("Generation threshold (MWh/h)", 3600, 4600, 4000, 50, disabled=not use_gen)

    d = monthly.copy()
    d["flag"] = d["range"] >= thr
    if use_gen:
        d["flag"] = d["flag"] | (d["gen"].notna() & (d["gen"] < gthr))
    d["collapse_month"] = d["month"].isin(events["month"])
    tp = int((d.flag & d.collapse_month).sum()); fn = int((~d.flag & d.collapse_month).sum())
    fp = int((d.flag & ~d.collapse_month).sum()); tn = int((~d.flag & ~d.collapse_month).sum())
    caught = tp / max(tp + fn, 1); prec = tp / max(tp + fp, 1)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Collapse months caught", f"{tp} of {tp + fn}", f"{caught:.0%}")
    m2.metric("Missed", fn)
    m3.metric("False alarms", fp, help="Flagged months with no collapse")
    m4.metric("Share of flags that were right", f"{prec:.0%}")
    st.dataframe(pd.DataFrame([[tp, fn], [fp, tn]], index=["Flagged", "Not flagged"],
                              columns=["Collapse month", "No collapse"]), width="stretch")
    st.warning("Read this carefully: this is an in-sample check on only %d months (%d with a collapse). "
               "The rule was chosen by looking at the same data. It shows a weak pattern, not a validated predictor. "
               "Monthly data cannot give minutes or hours of warning." % (len(d), int(d.collapse_month.sum())))
    fig3 = go.Figure()
    fig3.add_trace(go.Bar(x=d["date"], y=d["range"], marker_color=["#C00000" if c else "#9DB7D5" for c in d["collapse_month"]],
                          name="Frequency range"))
    fig3.add_hline(y=thr, line_dash="dash", annotation_text="threshold")
    fig3.update_layout(height=340, yaxis_title="Hz (upper minus lower)", margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig3, width="stretch")
    st.caption("Red bars are months with at least one collapse.")

# ================================================================ TAB 3
with tab3:
    st.subheader("Kaduna DisCo (Kaduna Electricity Distribution), NERC Q1 and Q2 2026")
    kd = kaduna.set_index("metric")
    def val(metric, col): return float(kd.loc[metric, col])
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("ATC&C loss (Q2)", f"{val('ATC&C loss actual','2026Q2'):.1f}%",
              f"{val('ATC&C loss actual','2026Q2') - val('ATC&C loss actual','2026Q1'):+.1f} pp vs Q1", delta_color="inverse")
    c2.metric("Collection efficiency (Q2)", f"{val('Collection efficiency','2026Q2'):.1f}%",
              f"{val('Collection efficiency','2026Q2') - val('Collection efficiency','2026Q1'):+.1f} pp vs Q1")
    c3.metric("Metering rate (Q2)", f"{val('Metering rate','2026Q2'):.1f}%",
              f"{val('Metering rate','2026Q2') - val('Metering rate','2026Q1'):+.1f} pp vs Q1")
    c4.metric("Offtake performance (Q2)", f"{val('Energy offtake performance','2026Q2'):.1f}%",
              f"{val('Energy offtake performance','2026Q2') - val('Energy offtake performance','2026Q1'):+.1f} pp vs Q1")
    st.write("The 2026 target ATC&C loss for Kaduna is 18.18%. Kaduna is a hard environment: high losses, low collection and"
             " low metering. That is a reason to pilot here, and a risk to any partnership with the DisCo.")
    st.dataframe(kaduna, width="stretch", hide_index=True)

# ================================================================ TAB 4
with tab4:
    st.subheader("Local pilot: outage log")
    st.write("Upload a CSV with two columns, **start** and **end** (date and time, for example `2026-10-15 14:20`)."
             " One row per outage at your pilot site.")
    tmpl = "start,end\n2026-10-15 14:20,2026-10-15 17:05\n2026-10-16 09:10,2026-10-16 09:40\n"
    st.download_button("Download template", tmpl, file_name="outage_log_template.csv", mime="text/csv")
    up = st.file_uploader("Outage log CSV", type=["csv"])
    if up:
        try:
            lg = pd.read_csv(up, parse_dates=["start", "end"])
            lg["hours"] = (lg["end"] - lg["start"]).dt.total_seconds() / 3600
            lg = lg[lg["hours"] > 0].sort_values("start")
            span_days = max((lg["end"].max() - lg["start"].min()).total_seconds() / 86400, 1e-9)
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Outages", len(lg))
            c2.metric("Total hours without power", f"{lg['hours'].sum():.1f}")
            c3.metric("Longest outage (h)", f"{lg['hours'].max():.1f}")
            c4.metric("Outages per day", f"{len(lg) / span_days:.1f}")
            fig4 = go.Figure(go.Bar(x=lg["start"], y=lg["hours"], marker_color="#C00000"))
            fig4.update_layout(height=320, yaxis_title="Hours", margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig4, width="stretch")
            st.dataframe(lg, width="stretch", hide_index=True)
            st.caption("Compare these dates with the national collapse list to see which outages were national events "
                       "and which look local.")
        except Exception as ex:
            st.error(f"Could not read the file: {ex}. Check the column names (start, end) and date format.")
    else:
        st.info("No log uploaded yet. Your real pilot data goes here.")

# ================================================================ TAB TX
with tab_tx:
    st.subheader("Transformer ageing risk")
    st.info("**What this is:** an engineering estimate of how fast a distribution transformer's insulation ages under a given load "
            "and ambient temperature, using the standard steady-state thermal method (IEC 60076-7 style). Failures that build up "
            "slowly, like overload and heat, can be scored this way. **What it is not:** a model trained on Nigerian failure data. "
            "It ignores moisture, lightning, faults, oil leaks and maintenance quality. Treat it as a ranking aid, "
            "and verify the thermal parameters with the transformer's test report.")
    a1, a2, a3 = st.columns(3)
    rated = a1.number_input("Rated size (kVA)", 25, 5000, 500, step=25, key="tx_rated")
    base = a2.number_input("Normal load (kVA)", 0, 8000, 250, step=25, key="tx_base")
    peak = a3.number_input("Peak load (kVA)", 0, 8000, 500, step=25, key="tx_peak")
    b1, b2, b3 = st.columns(3)
    hours = b1.slider("Hours per day at peak load", 0, 24, 4, key="tx_hours")
    amb = b2.slider("Average ambient temperature (deg C)", 15, 45, 28, key="tx_amb",
                    help="Assumed value. Set your site's weighted average ambient temperature.")
    paper = b3.selectbox("Insulation paper", ["Normal paper", "Thermally upgraded paper"], key="tx_paper")
    with st.expander("Advanced thermal parameters (typical ONAN distribution transformer defaults)"):
        p1, p2, p3 = st.columns(3)
        d_or = p1.number_input("Top-oil rise at rated load (K)", 30.0, 80.0, 55.0, 1.0, key="tx_dor")
        Rr = p2.number_input("Load loss / no-load loss ratio R", 1.0, 15.0, 5.0, 0.5, key="tx_R")
        hg = p3.number_input("Hot-spot to top-oil gradient (K)", 5.0, 40.0, 23.0, 1.0, key="tx_hg")
        q1, q2, q3 = st.columns(3)
        xx = q1.number_input("Oil exponent x", 0.5, 1.0, 0.8, 0.05, key="tx_x")
        yy = q2.number_input("Winding exponent y", 1.0, 2.0, 1.6, 0.05, key="tx_y")
        life = q3.number_input("Reference insulation life (years)", 5.0, 40.0, 20.55, 0.5, key="tx_life",
                               help="IEEE C57.91 uses 180,000 hours (20.55 years) as normal insulation life. Use your own value if known.")
    prm = dict(d_or=d_or, R=Rr, x=xx, hg=hg, y=yy)
    hb, hp, vb, vp, vavg = tx_daily(rated, base, peak, hours, amb, paper, **prm)
    label, kind = risk_label(vavg)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Hot-spot at peak", f"{hp:.0f} deg C", help="IEC 60076-7 gives a maximum of about 120 deg C for normal cyclic loading. Verify against the standard.")
    m2.metric("Hot-spot at normal load", f"{hb:.0f} deg C")
    m3.metric("Average ageing rate", f"{vavg:.2f}x normal", help="1.0 means the insulation ages at its design rate. 2.0 means twice as fast.")
    m4.metric("Insulation life at this loading", f"{life / max(vavg, 1e-9):.1f} years" if vavg > 0.05 else "more than design life",
              help="Reference life divided by the ageing rate. A scaling of an assumed reference life, not a prediction of the failure date.")
    getattr(st, kind)(f"GridWatch risk band: **{label}**. Bands (our own, not from the standard): below 1x low, 1-2x elevated, 2-5x high, above 5x severe."
                      + (" Peak hot-spot is above the roughly 120 deg C normal cyclic limit." if hp > 120 else ""))
    if hours > 0 and hours < 8 and vp > 4:
        st.caption("Note: this steady-state estimate overstates short peaks, because the oil takes a few hours to heat up. "
                   "It is conservative for peaks shorter than about 3 hours.")

    ks = [i / 20 for i in range(6, 37)]
    fig_tx = go.Figure()
    fig_tx.add_trace(go.Scatter(x=ks, y=[tx_aging(tx_temps(k, amb, **prm)[1], paper) for k in ks], mode="lines",
                                name=f"Ambient {amb} deg C", line=dict(color="#C0392B")))
    fig_tx.add_trace(go.Scatter(x=ks, y=[tx_aging(tx_temps(k, 20, **prm)[1], paper) for k in ks], mode="lines",
                                name="Ambient 20 deg C (IEC design reference)", line=dict(color="#8FA3B8", dash="dash")))
    fig_tx.add_trace(go.Scatter(x=[base / rated, peak / rated], y=[max(vb, 1e-3), max(vp, 1e-3)], mode="markers+text",
                                text=["normal", "peak"], textposition="top center", name="Your loads",
                                marker=dict(size=12, color="#0B1F33")))
    fig_tx.add_hline(y=1, line_dash="dot", annotation_text="design ageing rate")
    fig_tx.update_layout(height=380, yaxis_type="log", xaxis_title="Load factor (load / rated)",
                         yaxis_title="Ageing rate (times normal, log scale)", margin=dict(l=10, r=10, t=30, b=10),
                         legend=dict(orientation="h", y=-0.25))
    st.plotly_chart(fig_tx, width="stretch")
    st.caption("Check built in: at rated load and 20 deg C ambient, this model gives a 98 deg C hot-spot and an ageing rate of 1.0, "
               "which matches the IEC design reference. Hotter ambient moves the whole curve up.")

    st.markdown("#### Rank many transformers (for a DisCo or a feeder)")
    st.write("Upload a CSV with columns: `id, rated_kva, base_load_kva, peak_load_kva, peak_hours, ambient_c`. "
             "The tool ranks them by ageing rate, so maintenance can start with the riskiest.")
    tmpl_tx = ("id,rated_kva,base_load_kva,peak_load_kva,peak_hours,ambient_c\n"
               "EXAMPLE-A,500,300,550,4,28\nEXAMPLE-B,300,250,400,5,28\nEXAMPLE-C,200,90,160,3,28\n")
    st.download_button("Download template (example rows are made up, for format only)", tmpl_tx,
                       file_name="transformer_template.csv", mime="text/csv")
    up_tx = st.file_uploader("Transformer list CSV", type=["csv"], key="tx_up")
    if up_tx:
        try:
            tl = pd.read_csv(up_tx)
            rows = []
            for _, r in tl.iterrows():
                _, hp_, _, vp_, va_ = tx_daily(float(r.rated_kva), float(r.base_load_kva), float(r.peak_load_kva),
                                               float(r.peak_hours), float(r.ambient_c), paper, **prm)
                rows.append({"id": r["id"], "peak load factor": round(float(r.peak_load_kva) / float(r.rated_kva), 2),
                             "peak hot-spot (C)": round(hp_), "ageing rate (x normal)": round(va_, 2),
                             "risk band": risk_label(va_)[0]})
            rk = pd.DataFrame(rows).sort_values("ageing rate (x normal)", ascending=False)
            st.dataframe(rk, width="stretch", hide_index=True)
        except Exception as ex:
            st.error(f"Could not read the file: {ex}. Check the column names.")

# ================================================================ TAB 5
with tab5:
    st.subheader("What this is, and what it is not")
    st.markdown("""
**What it is**
- A reliability monitor that puts public grid data in one place: monthly frequency stress, generation, past collapses, Kaduna DisCo performance, and a local outage log.
- A transparent baseline rule you can test and improve.
- A transformer ageing-risk estimator based on the standard IEC 60076-7 thermal method, for ranking which transformers to inspect first.

**What it is not (yet)**
- It does **not** predict collapses minutes or hours ahead. Public data is monthly or quarterly, and many collapses began with a sudden plant or line trip.
- The backtest is in-sample on a few dozen months, so treat results as a weak baseline.
- The transformer tab is a physics-based estimate, not a model trained on Nigerian failure records. It needs validation with real transformer data from the pilot.

**Data**
- Source: NERC quarterly reports, 2019 Q1 to 2026 Q2. Monthly values were extracted from report charts and checked against the quarterly averages NERC states.
- Frequency values are monthly averages of daily highs and lows, not live readings.
- Gaps: no dates for 2019-2020 collapses, some event times blank, seven older PDFs were damaged and read with a repair tool.

**Next steps**
- Log real outages and voltage at a Kaduna pilot site and compare them with national events.
- Seek NISO daily operational reports for finer data.
- Improve the rule with more data and test it on months it has not seen.
""")
