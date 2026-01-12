import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from scipy.stats import pearsonr, spearmanr

st.set_page_config(page_title="ECMO Trend Analyzer", layout="wide")
st.title("ECMO Trend Analyzer")
st.caption("Backfillable date/time input • r = Delta P / Flow • Trend plots • Correlation tests (r vs Hb, r vs Glucose)")

# -------------------------
# Session state: data store
# -------------------------
COLUMNS = [
    "RecordedAt",          # user-entered datetime (for backfilling)
    "Flow", "RPM", "DeltaP", "Hb",
    "Glucose_mmol", "Glucose_mg_dL",
    "r"                    # r = DeltaP / Flow
]

if "data" not in st.session_state:
    st.session_state.data = pd.DataFrame(columns=COLUMNS)

# -------------------------
# Input form
# -------------------------
with st.form("input_form", clear_on_submit=False):
    t1, t2 = st.columns(2)
    rec_date = t1.date_input("Date", value=datetime.now().date())
    rec_time = t2.time_input("Time", value=datetime.now().time().replace(second=0, microsecond=0))
    recorded_at = datetime.combine(rec_date, rec_time)

    c1, c2, c3, c4, c5 = st.columns(5)
    flow = c1.number_input("ECMO Flow (L/min)", min_value=0.1, value=4.5, step=0.1)
    rpm = c2.number_input("Pump RPM", min_value=0, value=3200, step=10)
    delta_p = c3.number_input("Delta P (mmHg)", min_value=0.1, value=55.0, step=0.5)
    hb = c4.number_input("Hemoglobin (g/dL)", min_value=0.1, value=10.8, step=0.1)
    glucose_mmol = c5.number_input("Glucose (mmol/L)", min_value=0.1, value=8.0, step=0.1)

    add = st.form_submit_button("Add record")

def compute_r(delta_p_val: float, flow_val: float) -> float:
    return delta_p_val / flow_val

if add:
    glucose_mg_dl = glucose_mmol * 18.0
    r_val = compute_r(delta_p, flow)

    new_row = {
        "RecordedAt": recorded_at.isoformat(timespec="minutes"),
        "Flow": float(flow),
        "RPM": int(rpm),
        "DeltaP": float(delta_p),
        "Hb": float(hb),
        "Glucose_mmol": float(glucose_mmol),
        "Glucose_mg_dL": float(glucose_mg_dl),
        "r": float(r_val),
    }

    st.session_state.data = pd.concat(
        [st.session_state.data, pd.DataFrame([new_row])],
        ignore_index=True
    )

# -------------------------
# Controls
# -------------------------
ctrl1, ctrl2, ctrl3 = st.columns([1, 1, 3])
with ctrl1:
    if st.button("Delete last record") and len(st.session_state.data) > 0:
        st.session_state.data = st.session_state.data.iloc[:-1].reset_index(drop=True)
with ctrl2:
    if st.button("Clear all records"):
        st.session_state.data = st.session_state.data.iloc[0:0]

# -------------------------
# Table
# -------------------------
st.subheader("Records")
df = st.session_state.data.copy()

if len(df) == 0:
    st.info("No data yet. Add a record to begin.")
    st.stop()

show_df = df.copy()
show_df["RecordedAt"] = pd.to_datetime(show_df["RecordedAt"], errors="coerce").dt.strftime("%Y-%m-%d %H:%M")
show_df["r"] = show_df["r"].map(lambda x: f"{x:.4f}")
show_df["Glucose_mg_dL"] = show_df["Glucose_mg_dL"].map(lambda x: f"{x:.1f}")
st.dataframe(show_df, use_container_width=True)

# -------------------------
# Trend plots: X = time
# -------------------------
st.subheader("Trends (X-axis: Time)")

plot_df = df.copy()
plot_df["RecordedAt_dt"] = pd.to_datetime(plot_df["RecordedAt"], errors="coerce")
plot_df = plot_df.dropna(subset=["RecordedAt_dt"]).sort_values("RecordedAt_dt")

p1, p2 = st.columns(2)

with p1:
    fig, ax = plt.subplots()
    ax.plot(plot_df["RecordedAt_dt"], plot_df["DeltaP"], marker="o")
    ax.set_xlabel("Time")
    ax.set_ylabel("Delta P (mmHg)")
    ax.set_title("Delta P Trend Over Time")
    fig.autofmt_xdate()
    st.pyplot(fig, clear_figure=True)

with p2:
    fig, ax = plt.subplots()
    ax.plot(plot_df["RecordedAt_dt"], plot_df["r"], marker="o")
    ax.set_xlabel("Time")
    ax.set_ylabel("r (Delta P / Flow)")
    ax.set_title("r Trend Over Time")
    fig.autofmt_xdate()
    st.pyplot(fig, clear_figure=True)

# -------------------------
# Correlation tests: r vs Hb, r vs Glucose
# -------------------------
st.subheader("Correlation (r vs Hb, r vs Glucose)")

def corr_block(x: pd.Series, y: pd.Series, x_name: str, y_name: str):
    d = pd.DataFrame({"x": x, "y": y}).dropna()
    n = len(d)
    if n < 3:
        st.warning(f"Not enough data for correlation: {y_name} vs {x_name} (n={n}). Add more records.")
        return

    # Pearson (linear)
    pear_r, pear_p = pearsonr(d["x"], d["y"])
    # Spearman (rank-based, robust to non-linearity/outliers)
    spea_r, spea_p = spearmanr(d["x"], d["y"])

    st.write(f"**{y_name} vs {x_name}** (n={n})")
    st.write(f"- Pearson r = {pear_r:.3f}, p = {pear_p:.4g}")
    st.write(f"- Spearman ρ = {spea_r:.3f}, p = {spea_p:.4g}")

    fig, ax = plt.subplots()
    ax.scatter(d["x"], d["y"])
    ax.set_xlabel(x_name)
    ax.set_ylabel(y_name)
    ax.set_title(f"{y_name} vs {x_name}")
    st.pyplot(fig, clear_figure=True)

c1, c2 = st.columns(2)
with c1:
    corr_block(df["Hb"], df["r"], "Hemoglobin (g/dL)", "r (Delta P / Flow)")
with c2:
    corr_block(df["Glucose_mmol"], df["r"], "Glucose (mmol/L)", "r (Delta P / Flow)")

# -------------------------
# Export
# -------------------------
st.divider()
st.subheader("Export")
csv = df.to_csv(index=False).encode("utf-8")
st.download_button("Download CSV", data=csv, file_name="ecmo_trend_data.csv", mime="text/csv")
