import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, time
from scipy.stats import pearsonr, spearmanr

# ======================================================
# Page config
# ======================================================
st.set_page_config(page_title="ECMO Trend Analyzer", layout="wide")

page = st.radio(
    "Page",
    ["Data Entry & Records Page", "Charts & Anysia Page"],
    horizontal=True
)

page_bg = "#FFF9E6" if page == "Data Entry & Records Page" else "#EAF4FF"

st.markdown(
    f"""
    <style>
      .stApp {{ background-color: {page_bg}; }}
      .card {{
        border: 1px solid rgba(0,0,0,0.08);
        background: rgba(255,255,255,0.9);
        border-radius: 16px;
        padding: 14px;
        margin: 12px 0;
      }}
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown(
    """
    <div class="card">
      <h2>ECMO Trend Analyzer</h2>
      <p>r = Delta P / Flow • Daily baseline • Trend & resistance visualization</p>
    </div>
    """,
    unsafe_allow_html=True
)

# ======================================================
# Schema
# ======================================================
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

def next_no(df):
    if len(df) == 0:
        return 1
    return int(pd.to_numeric(df["No"], errors="coerce").max()) + 1

if "data" not in st.session_state:
    st.session_state.data = pd.DataFrame(columns=COLUMNS)

st.session_state.data = ensure_schema(st.session_state.data)

# ======================================================
# PAGE 1: Data Entry
# ======================================================
if page == "Data Entry & Records Page":
    st.markdown("<div class='card'><h3>Add Record</h3></div>", unsafe_allow_html=True)

    df_now = st.session_state.data
    last = df_now.iloc[-1] if len(df_now) > 0 else {}

    with st.form("add_form"):
        rec_date = st.date_input("Date", datetime.now().date())
        rec_time = st.time_input("Time", time(8, 0))

        flow = st.number_input("Flow (L/min)", 0.0, value=float(last.get("Flow", 4.5)))
        rpm = st.number_input("RPM", 0, value=int(last.get("RPM", 3200)))
        dp = st.number_input("Delta P (mmHg)", 0, value=int(last.get("DeltaP", 50)), format="%d")
        hb = st.number_input("Hb (g/dL)", 0.0, value=float(last.get("Hb", 10.0)), format="%.1f")
        glu = st.number_input("Glucose (mmol/L)", 0.0, value=float(last.get("Glucose_mmol", 8.0)), format="%.1f")

        add = st.form_submit_button("Add record")

    if add:
        if flow <= 0:
            st.error("Flow must be > 0")
        else:
            with st.spinner("Saving..."):
                dt = datetime.combine(rec_date, rec_time)
                r = dp / flow
                new = {
                    "No": next_no(df_now),
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
                    [df_now, pd.DataFrame([new])], ignore_index=True
                )
            st.success("Saved")

    st.markdown("<div class='card'><h3>Records</h3></div>", unsafe_allow_html=True)
    st.data_editor(st.session_state.data, hide_index=True, use_container_width=True)

    csv = st.session_state.data.to_csv(index=False).encode()
    st.download_button("Download CSV", csv, "ecmo_data.csv")

# ======================================================
# PAGE 2: Analysis
# ======================================================
else:
    df = ensure_schema(st.session_state.data)
    if len(df) < 2:
        st.info("Not enough data")
        st.stop()

    df["dt"] = pd.to_datetime(df["RecordedAt"])
    df = df.sort_values("dt")

    # ---------- Daily first ----------
    df["date"] = df["dt"].dt.date
    daily = df.groupby("date").first().reset_index()
    last7 = daily.tail(7)

    # ---------- KPI ----------
    cur_dp = int(last7["DeltaP"].iloc[-1])
    cur_r = float(last7["r"].iloc[-1])

    def pct(series):
        if len(series) < 2:
            return None
        return (series.iloc[-1] - series.iloc[-2]) / abs(series.iloc[-2]) * 100

    dp_pct = pct(last7["DeltaP"])
    r_pct = pct(last7["r"])

    day_no = (daily["date"].iloc[-1] - daily["date"].iloc[0]).days + 1

    c1, c2, c3 = st.columns(3)
    c1.metric("Delta P", cur_dp, None if dp_pct is None else f"{dp_pct:+.1f}%")
    c2.metric("r", f"{cur_r:.2f}", None if r_pct is None else f"{r_pct:+.1f}%")
    c3.metric("Day #", day_no)

    st.markdown("<div class='card'><h3>Daily First (Last 7 Days)</h3></div>", unsafe_allow_html=True)
    st.dataframe(
        last7[["date", "DeltaP", "r"]],
        use_container_width=True
    )

    # ---------- Dynamic smoothing ----------
    n = len(df)
    win = 1 if n <= 5 else 2 if n <= 10 else 3

    df["dp_s"] = df["DeltaP"].rolling(win, min_periods=1).mean()
    df["r_s"] = df["r"].rolling(win, min_periods=1).mean()

    # ---------- Delta P plot ----------
    fig, ax = plt.subplots()
    ax.plot(df["dt"], df["DeltaP"], "--", alpha=0.3, label="Raw")
    ax.plot(df["dt"], df["dp_s"], "-o", label=f"Smoothed({win})")
    ax.set_ylim(0, 80)
    ax.set_title("Delta P Trend")
    ax.legend()
    st.pyplot(fig)
    st.caption(f"Mean {df['DeltaP'].mean():.1f} | Max {df['DeltaP'].max()} | Min {df['DeltaP'].min()} | Median {df['DeltaP'].median()} | N={len(df)}")

    # ---------- r plot ----------
    fig, ax = plt.subplots()
    ax.plot(df["dt"], df["r"], "--", alpha=0.3, label="Raw")
    ax.plot(df["dt"], df["r_s"], "-o", label=f"Smoothed({win})")
    ax.set_ylim(0, 30)
    ax.set_title("r Trend")
    ax.legend()
    st.pyplot(fig)
    st.caption(f"Mean {df['r'].mean():.2f} | Max {df['r'].max():.2f} | Min {df['r'].min():.2f} | Median {df['r'].median():.2f} | N={len(df)}")

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
    cbar.set_ticks([0,5,10,15,20,25,30])
    st.pyplot(fig)

    st.info("High r with rising RPM but limited Flow suggests increased circuit resistance.")
