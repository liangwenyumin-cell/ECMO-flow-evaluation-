import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, time
from scipy.stats import pearsonr, spearmanr

# ================================
# Page config
# ================================
st.set_page_config(page_title="ECMO Trend Analyzer", layout="wide")

page = st.radio(
    "Page",
    ["Data Entry & Records Page", "Charts & Analysis Page"],
    horizontal=True
)

# ================================
# Session state
# ================================
COLUMNS = [
    "No", "RecordedAt",
    "Flow", "RPM", "DeltaP",
    "Hb", "Glucose_mmol",
    "Glucose_mg_dL",
    "r", "RPM_per_Flow"
]

def ensure_schema(df):
    if df is None or len(df) == 0:
        return pd.DataFrame(columns=COLUMNS)
    for c in COLUMNS:
        if c not in df.columns:
            df[c] = pd.NA
    return df[COLUMNS].copy()

if "data" not in st.session_state:
    st.session_state.data = pd.DataFrame(columns=COLUMNS)

st.session_state.data = ensure_schema(st.session_state.data)

# ================================
# PAGE 1 – Data Entry
# ================================
if page == "Data Entry & Records Page":
    st.header("Data Entry")

    last = st.session_state.data.iloc[-1] if len(st.session_state.data) > 0 else {}

    with st.form("add"):
        d = st.date_input("Date", datetime.now().date())
        t = st.time_input("Time", time(8, 0))
        flow = st.number_input("Flow (L/min)", 0.0, value=float(last.get("Flow", 4.5)))
        rpm = st.number_input("RPM", 0, value=int(last.get("RPM", 3200)))
        dp = st.number_input("Delta P (mmHg)", 0, value=int(last.get("DeltaP", 40)), format="%d")
        hb = st.number_input("Hb (g/dL)", 0.0, value=float(last.get("Hb", 10.0)), format="%.1f")
        glu = st.number_input("Glucose (mmol/L)", 0.0, value=float(last.get("Glucose_mmol", 8.0)), format="%.1f")
        ok = st.form_submit_button("Add record")

    if ok and flow > 0:
        dt = datetime.combine(d, t)
        r = dp / flow
        new = {
            "No": len(st.session_state.data) + 1,
            "RecordedAt": dt.isoformat(timespec="minutes"),
            "Flow": flow,
            "RPM": rpm,
            "DeltaP": dp,
            "Hb": round(hb, 1),
            "Glucose_mmol": round(glu, 1),
            "Glucose_mg_dL": glu * 18,
            "r": r,
            "RPM_per_Flow": rpm / flow
        }
        st.session_state.data = pd.concat(
            [st.session_state.data, pd.DataFrame([new])],
            ignore_index=True
        )
        st.success("Saved")

    st.data_editor(st.session_state.data, use_container_width=True, hide_index=True)

# ================================
# PAGE 2 – Analysis
# ================================
else:
    df = ensure_schema(st.session_state.data)
    if len(df) < 2:
        st.info("Not enough data")
        st.stop()

    # 🔒 HARD RESET matplotlib state
    plt.close("all")

    df["dt"] = pd.to_datetime(df["RecordedAt"])
    df = df.sort_values("dt")

    # ---------- daily first ----------
    df["date"] = df["dt"].dt.date
    daily = df.groupby("date", as_index=False).first()
    last7 = daily.tail(7)

    # ---------- smoothing ----------
    win = 1 if len(last7) <= 5 else 2 if len(last7) <= 10 else 3
    last7["dp_s"] = last7["DeltaP"].rolling(win, min_periods=1).mean()
    last7["r_s"] = last7["r"].rolling(win, min_periods=1).mean()

    st.header("Trend (Daily First – Last 7 Days)")

    # ---------- Delta P plot (LOCKED 0–50) ----------
    fig, ax = plt.subplots()
    ax.plot(last7["date"], last7["DeltaP"], "--", alpha=0.4, label="Raw")
    ax.plot(last7["date"], last7["dp_s"], "-o", label="Smoothed")
    ax.set_ylim(0, 50)                 # 🔒 FINAL
    ax.set_ylabel("Delta P (mmHg)")
    ax.set_title("Delta P Trend (0–50 mmHg)")
    ax.legend()
    st.pyplot(fig, clear_figure=True)

    # ---------- r plot (LOCKED 0–30) ----------
    fig, ax = plt.subplots()
    ax.plot(last7["date"], last7["r"], "--", alpha=0.4, label="Raw")
    ax.plot(last7["date"], last7["r_s"], "-o", label="Smoothed")
    ax.set_ylim(0, 30)                  # 🔒 FINAL
    ax.set_ylabel("r (ΔP / Flow)")
    ax.set_title("r Trend (0–30)")
    ax.legend()
    st.pyplot(fig, clear_figure=True)

    # ---------- RPM vs Flow ----------
    fig, ax = plt.subplots()
    sc = ax.scatter(
        df["RPM"], df["Flow"],
        c=df["r"],
        cmap="coolwarm",
        vmin=0, vmax=30
    )
    ax.set_xlabel("RPM")
    ax.set_ylabel("Flow (L/min)")
    ax.set_title("RPM vs Flow (color = r)")
    cbar = plt.colorbar(sc, ax=ax)
    cbar.set_label("r")
    cbar.set_ticks([0, 5, 10, 15, 20, 25, 30])
    st.pyplot(fig, clear_figure=True)
