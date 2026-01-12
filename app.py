import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from scipy.stats import pearsonr, spearmanr

st.set_page_config(page_title="ECMO Trend Analyzer", layout="wide")
st.title("ECMO Trend Analyzer")
st.caption(
    "Backfillable date/time • r = Delta P / Flow • Trends • RPM–Flow coupling (colored by r) • Correlations • CSV restore"
)

# -------------------------
# Session state
# -------------------------
COLUMNS = [
    "RecordedAt",
    "Flow", "RPM", "DeltaP", "Hb",
    "Glucose_mmol", "Glucose_mg_dL",
    "r",
    "RPM_per_Flow",
]

if "data" not in st.session_state:
    st.session_state.data = pd.DataFrame(columns=COLUMNS)

# -------------------------
# Data persistence (Option A): Restore from CSV
# -------------------------
st.subheader("Data Persistence (CSV Restore)")
st.caption(
    "To prevent data loss after refresh/closing the tab: download CSV regularly and restore via CSV upload."
)

uploaded = st.file_uploader("Restore from CSV", type=["csv"])
if uploaded is not None:
    try:
        loaded = pd.read_csv(uploaded)
        required_cols = set(COLUMNS)
        if not required_cols.issubset(set(loaded.columns)):
            st.error("CSV format mismatch. Please upload a CSV exported from this app.")
        else:
            loaded = loaded[COLUMNS].copy()
            st.session_state.data = loaded
            st.success(f"Restored {len(loaded)} records from CSV. You can continue adding records now.")
    except Exception as e:
        st.error(f"Failed to load CSV: {e}")

st.divider()

# -------------------------
# Input form
# -------------------------
with st.form("input_form", clear_on_submit=False):
    t1, t2 = st.columns(2)
    rec_date = t1.date_input("Date", value=datetime.now().date())
    rec_time = t2.time_input(
        "Time",
        value=datetime.now().time().replace(second=0, microsecond=0)
    )
    recorded_at = datetime.combine(rec_date, rec_time)

    c1, c2, c3, c4, c5 = st.columns(5)

    flow = c1.number_input(
        "ECMO Flow (L/min)", min_value=0.1, value=4.5, step=0.1
    )

    rpm = c2.number_input(
        "Pump RPM", min_value=0, value=3200, step=10
    )

    # Delta P as integer (machine-read)
    delta_p = c3.number_input(
        "Delta P (mmHg)", min_value=0, value=55, step=1, format="%d"
    )

    # Hb: 1 decimal
    hb = c4.number_input(
        "Hemoglobin (g/dL)", min_value=0.0, value=10.8, step=0.1, format="%.1f"
    )

    # Glucose: 1 decimal (mmol/L)
    glucose_mmol = c5.number_input(
        "Glucose (mmol/L)", min_value=0.0, value=8.0, step=0.1, format="%.1f"
    )

    add = st.form_submit_button("Add record")

# -------------------------
# Add row
# -------------------------
def compute_r(delta_p_val: float, flow_val: float) -> float:
    return delta_p_val / flow_val

if add:
    glucose_mg_dl = float(glucose_mmol) * 18.0
    r_val = compute_r(float(delta_p), float(flow))
    rpm_per_flow = float(rpm) / float(flow)

    new_row = {
        "RecordedAt": recorded_at.isoformat(timespec="minutes"),
        "Flow": float(flow),
        "RPM": int(rpm),
        "DeltaP": int(delta_p),
        "Hb": float(hb),
        "Glucose_mmol": float(glucose_mmol),
        "Glucose_mg_dL": float(glucose_mg_dl),
        "r": float(r_val),
        "RPM_per_Flow": float(rpm_per_flow),
    }

    st.session_state.data = pd.concat(
        [st.session_state.data, pd.DataFrame([new_row])],
        ignore_index=True
    )

    # Friendly reminder to backup
    try:
        st.toast("Record added. Tip: Download CSV to avoid losing data on refresh/close.", icon="💾")
    except Exception:
        st.info("Record added. Tip: Download CSV to avoid losing data on refresh/close.")

# -------------------------
# Controls
# -------------------------
ctrl1, ctrl2, _ = st.columns([1, 1, 3])
with ctrl1:
    if st.button("Delete last record") and len(st.session_state.data) > 0:
        st.session_state.data = st.session_state.data.iloc[:-1].reset_index(drop=True)

with ctrl2:
    confirm_clear = st.checkbox("I understand this will delete all records", value=False)
    if st.button("Clear all records"):
        if confirm_clear:
            st.session_state.data = st.session_state.data.iloc[0:0]
        else:
            st.warning("Please confirm before clearing all records.")

# -------------------------
# Table
# -------------------------
st.subheader("Records")
df = st.session_state.data.copy()

if len(df) == 0:
    st.info("No data yet. Add a record to begin.")
    st.stop()

show_df = df.copy()
show_df["RecordedAt"] = pd.to_datetime(
    show_df["RecordedAt"], errors="coerce"
).dt.strftime("%Y-%m-%d %H:%M")

show_df["DeltaP"] = show_df["DeltaP"].astype(int)
show_df["Hb"] = show_df["Hb"].map(lambda x: f"{x:.1f}")
show_df["Glucose_mmol"] = show_df["Glucose_mmol"].map(lambda x: f"{x:.1f}")
show_df["r"] = show_df["r"].map(lambda x: f"{x:.4f}")
show_df["RPM_per_Flow"] = show_df["RPM_per_Flow"].map(lambda x: f"{x:.2f}")

st.dataframe(show_df, use_container_width=True)

# -------------------------
# Prep for plots
# -------------------------
plot_df = df.copy()
plot_df["RecordedAt_dt"] = pd.to_datetime(plot_df["RecordedAt"], errors="coerce")
plot_df = plot_df.dropna(subset=["RecordedAt_dt"]).sort_values("RecordedAt_dt")

# -------------------------
# Trend plots
# -------------------------
st.subheader("Trends (X-axis: Time)")

p1, p2, p3 = st.columns(3)

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

with p3:
    fig, ax = plt.subplots()
    ax.plot(plot_df["RecordedAt_dt"], plot_df["RPM_per_Flow"], marker="o")
    ax.set_xlabel("Time")
    ax.set_ylabel("RPM / Flow")
    ax.set_title("RPM / Flow Trend Over Time")
    fig.autofmt_xdate()
    st.pyplot(fig, clear_figure=True)

# -------------------------
# RPM–Flow coupling (colored by r)
# -------------------------
st.subheader("RPM–Flow Coupling (Color-coded by r)")

fig, ax = plt.subplots()
sc = ax.scatter(
    df["RPM"],
    df["Flow"],
    c=df["r"],
    cmap="viridis"
)
ax.set_xlabel("Pump RPM")
ax.set_ylabel("ECMO Flow (L/min)")
ax.set_title("RPM vs Flow (Color = r = Delta P / Flow)")
cbar = plt.colorbar(sc, ax=ax)
cbar.set_label("r (Delta P / Flow)")
st.pyplot(fig, clear_figure=True)

st.markdown(
"""
**Interpretation**

- Under normal conditions, increasing RPM results in proportional increases in Flow.
- When this coupling weakens (RPM ↑ but Flow ↑ minimally), an elevated **r (ΔP / Flow)** suggests increased circuit resistance.
- **RPM / Flow** reflects pump inefficiency and complements r from a pump-centered perspective.
"""
)

# -------------------------
# Correlation analysis
# -------------------------
st.subheader("Correlation Analysis (r vs Hb, r vs Glucose)")

def corr_block(x: pd.Series, y: pd.Series, x_name: str, y_name: str):
    d = pd.DataFrame({"x": x, "y": y}).dropna()
    n = len(d)
    if n < 3:
        st.warning(f"Not enough data for correlation: {y_name} vs {x_name} (n={n}). Add more records.")
        return

    pr, pp = pearsonr(d["x"], d["y"])
    sr, sp = spearmanr(d["x"], d["y"])

    st.write(f"**{y_name} vs {x_name}** (n={n})")
    st.write(f"- Pearson r = {pr:.3f}, p = {pp:.4g}")
    st.write(f"- Spearman ρ = {sr:.3f}, p = {sp:.4g}")

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
st.download_button(
    "Download CSV",
    data=csv,
    file_name="ecmo_trend_data.csv",
    mime="text/csv"
)
