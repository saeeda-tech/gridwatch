"""GridWatch: grid reliability monitor (Kaduna pilot).
Data: NERC quarterly reports (public). See data/README in the dataset folder.
Run:  streamlit run app.py
"""
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

monthly, events, quarterly, kaduna = load()

# ---------------------------------------------------------------- header
st.title("⚡ GridWatch")
st.caption("Grid reliability monitor and risk outlook · Kaduna pilot · "
           "Built on public NERC quarterly reports (2019 to Q2 2026)")

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Grid stress", "Backtest", "Kaduna DisCo", "Local pilot log", "About and limits"])

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

# ================================================================ TAB 5
with tab5:
    st.subheader("What this is, and what it is not")
    st.markdown("""
**What it is**
- A reliability monitor that puts public grid data in one place: monthly frequency stress, generation, past collapses, Kaduna DisCo performance, and a local outage log.
- A transparent baseline rule you can test and improve.

**What it is not (yet)**
- It does **not** predict collapses minutes or hours ahead. Public data is monthly or quarterly, and many collapses began with a sudden plant or line trip.
- The backtest is in-sample on a few dozen months, so treat results as a weak baseline.

**Data**
- Source: NERC quarterly reports, 2019 Q1 to 2026 Q2. Monthly values were extracted from report charts and checked against the quarterly averages NERC states.
- Frequency values are monthly averages of daily highs and lows, not live readings.
- Gaps: no dates for 2019-2020 collapses, some event times blank, seven older PDFs were damaged and read with a repair tool.

**Next steps**
- Log real outages and voltage at a Kaduna pilot site and compare them with national events.
- Seek NISO daily operational reports for finer data.
- Improve the rule with more data and test it on months it has not seen.
""")
