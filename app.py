import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, time, timedelta

# ======================================================
# Page config + selector
# ======================================================
st.set_page_config(page_title="ECMO Trend Analyzer", layout="wide")

page = st.radio(
    "Page",
    ["Data Entry & Records Page", "Charts & Analysis Page"],
    horizontal=True
)

# ======================================================
# Background color by page
# ======================================================
page_bg = "#FFF9E6" if page == "Data Entry & Records Page" else "#EAF4FF"

# ======================================================
# UI Theme
# ======================================================
st.markdown(
    f"""
    <style>
      .stApp {{ background-color: {page_bg}; }}

      :root {{
        --entry-soft: rgba(255, 250, 230, 0.95);
        --analysis-soft: rgba(235, 245, 255, 0.95);
        --border-soft: rgba(0,0,0,0.08);
        --muted: rgba(0,0,0,0.55);
      }}

      body {{
        --soft-bg: {"var(--entry-soft)" if page == "Data Entry & Records Page" else "var(--analysis-soft)"};
      }}

      .block-container {{ padding-top: 1.0rem; padding-bottom: 2.0rem; }}

      .hero {{
        border: 1px solid var(--border-soft);
        background: var(--soft-bg);
        border-radius: 18px;
        padding: 16px 18px;
        margin-bottom: 12px;
      }}
      .hero-title {{ font-size: 28px; font-weight: 800; margin: 0; }}
      .hero-sub {{ margin-top: 6px; color: var(--muted); font-size: 14px; }}

      .card {{
        border: 1px solid var(--border-soft);
        background: rgba(255,255,255,0.92);
        border-radius: 16px;
        padding: 14px;
        margin: 10px 0 12px 0;
      }}

      label {{ font-size: 16px !important; }}
      .stNumberInput input, .stDateInput input, .stTimeInput input {{
        font-size: 18px !important;
        background-color: #fff !important;
      }}

      .stButton button, .stDownloadButton button {{
        font-size: 16px !important;
        padding: 10px 14px !important;
        border-radius: 12px !important;
        background-color: var(--soft-bg) !important;
        border: 1px solid var(--border-soft) !important;
      }}

      .stAlert {{
        background-color: var(--soft-bg) !important;
        border: 1px solid var(--border-soft) !important;
        border-radius: 14px !important;
      }}

      thead tr th {{
        font-size: 13px !important;
        background-color: var(--soft-bg) !important;
      }}
      tbody tr:nth-child(even) {{ background-color: rgba(0,0,0,0.02); }}
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown(
    """
    <div class="hero">
      <div class="hero-title">ECMO Trend Analyzer</div>
      <div class="hero-sub">
        r = ΔP / Flow • r/Hb = (ΔP/Flow)/Hb • RPM/Flow • All-record trend + Daily-first (last 7 days) • CSV restore
      </div>
    </div>
    """,
    unsafe_allow_html=True
)

# ======================================================
# Schema (Glucose removed)
# ======================================================
COLUMNS = [
    "No", "RecordedAt",
    "Flow", "RPM", "DeltaP", "Hb",
    "r", "r_hb", "RPM_per_Flow"
]

BASE_COLS = ["RecordedAt", "Flow", "RPM", "DeltaP", "Hb"]

def _to_num(s):
    return pd.to_numeric(s, errors="coerce")

def ensure_schema(df: pd.DataFrame) -> pd.DataFrame:
    """
    Make old CSV compatible:
    - Ensure required columns exist
    - Coerce numeric columns
    - Recompute derived columns r, r_hb, RPM_per_Flow whenever possible
    """
    if df is None or len(df) == 0:
        return pd.DataFrame(columns=COLUMNS)

    # Add missing columns
    for c in COLUMNS:
        if c not in df.columns:
            df[c] = pd.NA

    # Coerce numeric types for base columns
    df["Flow"] = _to_num(df["Flow"])
    df["RPM"] = _to_num(df["RPM"])
    df["DeltaP"] = _to_num(df["DeltaP"]).round(0)
    df["Hb"] = _to_num(df["Hb"])

    # Ensure No exists and is integer-ish
    df["No"] = _to_num(df["No"])
    if df["No"].isna().all():
        # if old CSV had no No, assign sequential
        df["No"] = range(1, len(df) + 1)

    # Recompute derived columns safely
    valid_flow = df["Flow"] > 0
    df.loc[valid_flow, "r"] = df.loc[valid_flow, "DeltaP"] / df.loc[valid_flow, "Flow"]
    df.loc[valid_flow, "RPM_per_Flow"] = df.loc[valid_flow, "RPM"] / df.loc[valid_flow, "Flow"]

    valid_hb = df["Hb"] > 0
    valid_rhb = valid_flow & valid_hb
    df.loc[valid_rhb, "r_hb"] = df.loc[valid_rhb, "r"] / df.loc[valid_rhb, "Hb"]

    # Keep only our columns (order)
    return df[COLUMNS].copy()

def next_no(df: pd.DataFrame) -> int:
    if len(df) == 0 or df["No"].dropna().empty:
        return 1
    return int(df["No"].dropna().max()) + 1

# ======================================================
# Session state
# ======================================================
if "data" not in st.session_state:
    st.session_state.data = pd.DataFrame(columns=COLUMNS)
st.session_state.data = ensure_schema(st.session_state.data)

if "restore_done" not in st.session_state:
    st.session_state.restore_done = False

# ======================================================
# PAGE 1
# ======================================================
if page == "Data Entry & Records Page":

    st.markdown(
        """
        <div class="card">
          <h3>➕ Add Record</h3>
          <p>Defaults to last saved values. Time defaults to 08:00 (SG/Taipei). Delta P integer, Hb 1 decimal.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    df_now = ensure_schema(st.session_state.data)
    if len(df_now) > 0 and df_now["No"].dropna().any():
        last = df_now.sort_values("No").iloc[-1]
        d_flow = float(last["Flow"]) if pd.notna(last["Flow"]) else 4.5
        d_rpm  = int(last["RPM"]) if pd.notna(last["RPM"]) else 3200
        d_dp   = int(last["DeltaP"]) if pd.notna(last["DeltaP"]) else 40
        d_hb   = float(last["Hb"]) if pd.notna(last["Hb"]) else 10.0
    else:
        d_flow, d_rpm, d_dp, d_hb = 4.5, 3200, 40, 10.0

    with st.form("input_form", clear_on_submit=False):
        rec_date = st.date_input("Date", value=datetime.now().date())
        rec_time = st.time_input("Time", value=time(8, 0))

        flow = st.number_input("ECMO Flow (L/min)", min_value=0.0, value=float(d_flow), step=0.1)
        rpm  = st.number_input("Pump RPM", min_value=0, value=int(d_rpm), step=10)
        dp   = st.number_input("Delta P (mmHg)", min_value=0, value=int(d_dp), step=1, format="%d")
        hb   = st.number_input("Hemoglobin (g/dL)", min_value=0.0, value=float(d_hb), step=0.1, format="%.1f")

        add = st.form_submit_button("Add record")

    if add:
        if flow <= 0:
            st.error("Flow must be > 0.")
        elif hb <= 0:
            st.error("Hb must be > 0.")
        else:
            with st.spinner("Saving..."):
                df_now = ensure_schema(st.session_state.data)
                rec_no = next_no(df_now)
                recorded_at = datetime.combine(rec_date, rec_time)

                r_val = float(dp) / float(flow)
                r_hb_val = r_val / float(hb)
                rpm_per_flow = float(rpm) / float(flow)

                new_row = {
                    "No": rec_no,
                    "RecordedAt": recorded_at.isoformat(timespec="minutes"),
                    "Flow": float(flow),
                    "RPM": int(rpm),
                    "DeltaP": int(dp),
                    "Hb": round(float(hb), 1),
                    "r": float(r_val),
                    "r_hb": float(r_hb_val),
                    "RPM_per_Flow": float(rpm_per_flow),
                }

                st.session_state.data = pd.concat([df_now, pd.DataFrame([new_row])], ignore_index=True)
                st.session_state.data = ensure_schema(st.session_state.data)

            st.success("✅ Saved successfully.")
            st.info(f"Total records: {len(st.session_state.data)} | Latest No: {rec_no}")

    # ---- Restore ----
    st.markdown(
        """
        <div class="card">
          <h3>💾 Restore from CSV</h3>
          <p>Upload a CSV exported from this app.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    uploaded = st.file_uploader("Upload CSV", type=["csv"], key="restore_csv")

    if uploaded is not None and not st.session_state.restore_done:
        with st.spinner("Restoring..."):
            try:
                loaded = pd.read_csv(uploaded)
                st.session_state.data = ensure_schema(loaded)
                st.session_state.restore_done = True
                st.success(f"✅ Restored {len(st.session_state.data)} records.")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to load CSV: {e}")

    if st.session_state.restore_done:
        if st.button("Restore another CSV"):
            st.session_state.restore_done = False
            st.session_state["restore_csv"] = None
            st.rerun()

    # ---- Records ----
    st.markdown(
        """
        <div class="card">
          <h3>🧾 Records</h3>
          <p>Edit data directly. (Derived columns will be recomputed automatically after Apply.)</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    df = ensure_schema(st.session_state.data)
    if len(df) == 0:
        st.info("No data yet.")
    else:
        df_disp = df.copy()
        df_disp["RecordedAt"] = pd.to_datetime(df_disp["RecordedAt"], errors="coerce").dt.strftime("%Y-%m-%d %H:%M")
        edited = st.data_editor(df_disp, use_container_width=True, hide_index=True)
        st.info("Edits are not saved until you click **Apply changes**.")

        if st.button("Apply changes"):
            with st.spinner("Applying changes..."):
                saved = edited.copy()
                parsed = pd.to_datetime(saved["RecordedAt"], errors="coerce")
                if parsed.isna().any():
                    st.error("Invalid datetime format. Use YYYY-MM-DD HH:MM.")
                else:
                    # Write back ISO format
                    saved["RecordedAt"] = parsed.dt.strftime("%Y-%m-%dT%H:%M")
                    st.session_state.data = ensure_schema(saved)
                    st.success("✅ Changes applied successfully.")
                    st.info(f"Total records: {len(st.session_state.data)}")

    # Export
    st.markdown("<div class='card'><h3>⬇️ Export</h3></div>", unsafe_allow_html=True)
    csv = ensure_schema(st.session_state.data).to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", data=csv, file_name="ecmo_trend_data.csv", mime="text/csv")

# ======================================================
# PAGE 2
# ======================================================
else:
    df = ensure_schema(st.session_state.data)
    if len(df) < 2:
        st.info("Not enough data yet.")
        st.stop()

    df["RecordedAt_dt"] = pd.to_datetime(df["RecordedAt"], errors="coerce")
    df = df.dropna(subset=["RecordedAt_dt"]).sort_values("RecordedAt_dt").reset_index(drop=True)

    if len(df) < 2:
        st.info("Not enough valid datetime records.")
        st.stop()

    plt.close("all")

    st.markdown("<div class='card'><h3>View Mode</h3></div>", unsafe_allow_html=True)
    mode = st.radio(
        "Choose analysis view",
        ["All records (trend)", "Daily-first (last 7 days)"],
        horizontal=True
    )

    def stats_text(series: pd.Series, fmt: str):
        s = pd.to_numeric(series, errors="coerce").dropna()
        if len(s) == 0:
            return "N=0"
        return f"Mean {fmt.format(s.mean())} | Max {fmt.format(s.max())} | Min {fmt.format(s.min())} | Median {fmt.format(s.median())} | N={len(s)}"

    df["date"] = df["RecordedAt_dt"].dt.date
    daily_first = df.groupby("date", as_index=False).first().sort_values("date").reset_index(drop=True)
    last7_daily = daily_first.tail(7).copy()

    # KPI
    d0 = daily_first["date"].iloc[0]
    d1 = daily_first["date"].iloc[-1]
    day_no = (d1 - d0).days + 1

    cur_dp = int(last7_daily["DeltaP"].iloc[-1])
    cur_r = float(last7_daily["r"].iloc[-1])
    cur_rhb = float(last7_daily["r_hb"].iloc[-1])

    st.markdown("<div class='card'><h3>📌 Current Status (Daily-first baseline)</h3></div>", unsafe_allow_html=True)
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Current ΔP (mmHg)", f"{cur_dp}")
    k2.metric("Current r", f"{cur_r:.2f}")
    k3.metric("Current r/Hb", f"{cur_rhb:.3f}")
    k4.metric("Day #", f"{day_no}")

    if mode == "All records (trend)":
        st.markdown("<div class='card'><h3>All-record Trend</h3></div>", unsafe_allow_html=True)

        cA, cB = st.columns(2)
        with cA:
            last_n_days = st.slider("Show last N days", min_value=1, max_value=60, value=14)
        with cB:
            win = st.slider("Smoothing window (points)", min_value=1, max_value=15, value=3)

        cutoff = df["RecordedAt_dt"].max() - timedelta(days=int(last_n_days))
        df_view = df[df["RecordedAt_dt"] >= cutoff].copy()
        if len(df_view) < 2:
            st.warning("Not enough points in this range. Increase N days.")
            st.stop()

        df_view["dp_s"] = df_view["DeltaP"].rolling(win, min_periods=1).mean()
        df_view["r_s"] = df_view["r"].rolling(win, min_periods=1).mean()
        df_view["rhb_s"] = df_view["r_hb"].rolling(win, min_periods=1).mean()
        df_view["rpmflow_s"] = df_view["RPM_per_Flow"].rolling(win, min_periods=1).mean()

        # ΔP 0–50
        fig, ax = plt.subplots()
        ax.plot(df_view["RecordedAt_dt"], df_view["DeltaP"], "--", alpha=0.25, label="Raw")
        ax.plot(df_view["RecordedAt_dt"], df_view["dp_s"], "-o", label=f"Smoothed (w={win})")
        ax.set_ylim(0, 50)
        ax.set_title("Delta P Trend (All records)")
        ax.set_xlabel("Time")
        ax.set_ylabel("Delta P (mmHg)")
        ax.legend()
        fig.autofmt_xdate()
        st.pyplot(fig, clear_figure=True)
        st.caption(stats_text(df_view["DeltaP"], "{:.1f}"))

        # r 0–30
        fig, ax = plt.subplots()
        ax.plot(df_view["RecordedAt_dt"], df_view["r"], "--", alpha=0.25, label="Raw")
        ax.plot(df_view["RecordedAt_dt"], df_view["r_s"], "-o", label=f"Smoothed (w={win})")
        ax.set_ylim(0, 30)
        ax.set_title("r Trend (All records)")
        ax.set_xlabel("Time")
        ax.set_ylabel("r (ΔP/Flow)")
        ax.legend()
        fig.autofmt_xdate()
        st.pyplot(fig, clear_figure=True)
        st.caption(stats_text(df_view["r"], "{:.2f}"))

        # r/Hb (0–5 default)
        fig, ax = plt.subplots()
        ax.plot(df_view["RecordedAt_dt"], df_view["r_hb"], "--", alpha=0.25, label="Raw")
        ax.plot(df_view["RecordedAt_dt"], df_view["rhb_s"], "-o", label=f"Smoothed (w={win})")
        ax.set_ylim(0, 5)
        ax.set_title("r/Hb Trend (All records)")
        ax.set_xlabel("Time")
        ax.set_ylabel("r/Hb (ΔP/Flow/Hb)")
        ax.legend()
        fig.autofmt_xdate()
        st.pyplot(fig, clear_figure=True)
        st.caption(stats_text(df_view["r_hb"], "{:.3f}"))

        # RPM/Flow (auto)
        fig, ax = plt.subplots()
        ax.plot(df_view["RecordedAt_dt"], df_view["RPM_per_Flow"], "--", alpha=0.25, label="Raw")
        ax.plot(df_view["RecordedAt_dt"], df_view["rpmflow_s"], "-o", label=f"Smoothed (w={win})")
        ax.set_title("RPM / Flow Trend (All records)")
        ax.set_xlabel("Time")
        ax.set_ylabel("RPM / Flow")
        ax.legend()
        fig.autofmt_xdate()
        st.pyplot(fig, clear_figure=True)
        st.caption(stats_text(df_view["RPM_per_Flow"], "{:.2f}"))

    else:
        st.markdown("<div class='card'><h3>Daily-first (Last 7 Days)</h3></div>", unsafe_allow_html=True)
        show7 = last7_daily[["date", "DeltaP", "r", "r_hb", "RPM_per_Flow"]].copy()
        st.dataframe(show7, use_container_width=True, hide_index=True)

        win = 1 if len(last7_daily) <= 5 else 2 if len(last7_daily) <= 10 else 3
        last7_daily["dp_s"] = last7_daily["DeltaP"].rolling(win, min_periods=1).mean()
        last7_daily["r_s"] = last7_daily["r"].rolling(win, min_periods=1).mean()
        last7_daily["rhb_s"] = last7_daily["r_hb"].rolling(win, min_periods=1).mean()
        last7_daily["rpmflow_s"] = last7_daily["RPM_per_Flow"].rolling(win, min_periods=1).mean()

        # ΔP 0–50
        fig, ax = plt.subplots()
        ax.plot(last7_daily["date"], last7_daily["DeltaP"], "--", alpha=0.35, label="Raw")
        ax.plot(last7_daily["date"], last7_daily["dp_s"], "-o", label=f"Smoothed (w={win})")
        ax.set_ylim(0, 50)
        ax.set_title("Delta P Trend (Daily-first)")
        ax.set_xlabel("Date")
        ax.set_ylabel("Delta P (mmHg)")
        ax.legend()
        st.pyplot(fig, clear_figure=True)
        st.caption(stats_text(last7_daily["DeltaP"], "{:.1f}"))

        # r 0–30
        fig, ax = plt.subplots()
        ax.plot(last7_daily["date"], last7_daily["r"], "--", alpha=0.35, label="Raw")
        ax.plot(last7_daily["date"], last7_daily["r_s"], "-o", label=f"Smoothed (w={win})")
        ax.set_ylim(0, 30)
        ax.set_title("r Trend (Daily-first)")
        ax.set_xlabel("Date")
        ax.set_ylabel("r (ΔP/Flow)")
        ax.legend()
        st.pyplot(fig, clear_figure=True)
        st.caption(stats_text(last7_daily["r"], "{:.2f}"))

        # r/Hb 0–5
        fig, ax = plt.subplots()
        ax.plot(last7_daily["date"], last7_daily["r_hb"], "--", alpha=0.35, label="Raw")
        ax.plot(last7_daily["date"], last7_daily["rhb_s"], "-o", label=f"Smoothed (w={win})")
        ax.set_ylim(0, 5)
        ax.set_title("r/Hb Trend (Daily-first)")
        ax.set_xlabel("Date")
        ax.set_ylabel("r/Hb (ΔP/Flow/Hb)")
        ax.legend()
        st.pyplot(fig, clear_figure=True)
        st.caption(stats_text(last7_daily["r_hb"], "{:.3f}"))

        # RPM/Flow
        fig, ax = plt.subplots()
        ax.plot(last7_daily["date"], last7_daily["RPM_per_Flow"], "--", alpha=0.35, label="Raw")
        ax.plot(last7_daily["date"], last7_daily["rpmflow_s"], "-o", label=f"Smoothed (w={win})")
        ax.set_title("RPM / Flow Trend (Daily-first)")
        ax.set_xlabel("Date")
        ax.set_ylabel("RPM / Flow")
        ax.legend()
        st.pyplot(fig, clear_figure=True)
        st.caption(stats_text(last7_daily["RPM_per_Flow"], "{:.2f}"))

    # RPM vs Flow (color=r fixed 0–30)
    st.markdown("<div class='card'><h3>🔎 RPM vs Flow (Color = r)</h3></div>", unsafe_allow_html=True)
    fig, ax = plt.subplots()
    sc = ax.scatter(df["RPM"], df["Flow"], c=df["r"], cmap="coolwarm", vmin=0, vmax=30)
    ax.set_xlabel("RPM")
    ax.set_ylabel("Flow (L/min)")
    ax.set_title("RPM vs Flow (Color = r)")
    cbar = plt.colorbar(sc, ax=ax)
    cbar.set_label("r (ΔP / Flow)")
    cbar.set_ticks([0, 5, 10, 15, 20, 25, 30])
    st.pyplot(fig, clear_figure=True)
