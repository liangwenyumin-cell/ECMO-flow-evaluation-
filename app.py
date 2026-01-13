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
        r = Delta P / Flow • r/Hb (Delta P / Flow / Hb) • RPM/Flow • All-record trend + Daily-first (last 7 days) • CSV restore
      </div>
    </div>
    """,
    unsafe_allow_html=True
)

# ======================================================
# Data schema helpers (Glucose removed)
# ======================================================
COLUMNS = [
    "No", "RecordedAt",
    "Flow", "RPM", "DeltaP", "Hb",
    "r", "r_hb", "RPM_per_Flow"
]

def ensure_schema(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or len(df) == 0:
        return pd.DataFrame(columns=COLUMNS)
    for c in COLUMNS:
        if c not in df.columns:
            df[c] = pd.NA
    df["No"] = pd.to_numeric(df["No"], errors="coerce")
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
# PAGE 1: Data Entry & Records
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
        def pick(val, fallback):
            return fallback if pd.isna(val) else val
        d_flow = float(pick(last.get("Flow"), 4.5))
        d_rpm  = int(pick(last.get("RPM"), 3200))
        d_dp   = int(pick(last.get("DeltaP"), 40))
        d_hb   = float(pick(last.get("Hb"), 10.0))
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

            st.success("✅ Saved successfully.")
            st.info(f"Total records: {len(st.session_state.data)} | Latest No: {rec_no}")

    # ---- Restore from CSV ----
    st.markdown(
        """
        <div class="card">
          <h3>💾 Restore from CSV</h3>
          <p>Upload a CSV exported from this app. (Prevents data loss after refresh/close.)</p>
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

    # ---- Records (Editable) ----
    st.markdown(
        """
        <div class="card">
          <h3>🧾 Records (Editable)</h3>
          <p>Edit cells and click <b>Apply changes</b>. Derived metrics (r, r/Hb, RPM/Flow) will be recalculated.</p>
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
                    saved["RecordedAt"] = parsed.dt.strftime("%Y-%m-%dT%H:%M")
                    saved["Flow"] = pd.to_numeric(saved["Flow"], errors="coerce")
                    saved["RPM"] = pd.to_numeric(saved["RPM"], errors="coerce")
                    saved["DeltaP"] = pd.to_numeric(saved["DeltaP"], errors="coerce").round(0).astype("Int64")
                    saved["Hb"] = pd.to_numeric(saved["Hb"], errors="coerce")

                    if (saved["Flow"] <= 0).any():
                        st.error("Flow must be > 0 for all rows.")
                    elif (saved["Hb"] <= 0).any():
                        st.error("Hb must be > 0 for all rows.")
                    else:
                        saved["r"] = saved["DeltaP"].astype(float) / saved["Flow"].astype(float)
                        saved["r_hb"] = saved["r"].astype(float) / saved["Hb"].astype(float)
                        saved["RPM_per_Flow"] = saved["RPM"].astype(float) / saved["Flow"].astype(float)

                        st.session_state.data = ensure_schema(saved)

                        st.success("✅ Changes applied successfully.")
                        st.info(f"Total records: {len(st.session_state.data)}")

    # ---- Export ----
    st.markdown(
        """
        <div class="card">
          <h3>⬇️ Export</h3>
          <p>Download CSV regularly to avoid data loss.</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    csv = ensure_schema(st.session_state.data).to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", data=csv, file_name="ecmo_trend_data.csv", mime="text/csv")

# ======================================================
# PAGE 2: Charts & Analysis
# ======================================================
else:
    df = ensure_schema(st.session_state.data)
    if len(df) < 2:
        st.info("Not enough data yet. Add more records first.")
        st.stop()

    df["RecordedAt_dt"] = pd.to_datetime(df["RecordedAt"], errors="coerce")
    df = df.dropna(subset=["RecordedAt_dt"]).sort_values("RecordedAt_dt").reset_index(drop=True)

    if len(df) < 2:
        st.info("Not enough valid datetime records. Please fix RecordedAt on page 1.")
        st.stop()

    plt.close("all")

    st.markdown("<div class='card'><h3>View Mode</h3></div>", unsafe_allow_html=True)
    mode = st.radio(
        "Choose analysis view",
        ["All records (trend)", "Daily-first (last 7 days)"],
        horizontal=True
    )

    # Common helper
    def stats_text(series: pd.Series, fmt: str):
        s = pd.to_numeric(series, errors="coerce").dropna()
        if len(s) == 0:
            return "N=0"
        return f"Mean {fmt.format(s.mean())} | Max {fmt.format(s.max())} | Min {fmt.format(s.min())} | Median {fmt.format(s.median())} | N={len(s)}"

    # KPI baseline uses daily-first
    df["date"] = df["RecordedAt_dt"].dt.date
    daily_first = df.groupby("date", as_index=False).first().sort_values("date").reset_index(drop=True)
    last7_daily = daily_first.tail(7).copy()

    d0 = daily_first["date"].iloc[0]
    d1 = daily_first["date"].iloc[-1]
    day_no = (d1 - d0).days + 1

    def pct(prev, cur):
        if prev == 0:
            return None
        return (cur - prev) / abs(prev) * 100.0

    dp_tr = None
    r_tr = None
    rhb_tr = None
    if len(last7_daily) >= 2:
        dp_tr = pct(float(last7_daily["DeltaP"].iloc[-2]), float(last7_daily["DeltaP"].iloc[-1]))
        r_tr = pct(float(last7_daily["r"].iloc[-2]), float(last7_daily["r"].iloc[-1]))
        rhb_tr = pct(float(last7_daily["r_hb"].iloc[-2]), float(last7_daily["r_hb"].iloc[-1]))

    dp_delta = "—" if dp_tr is None else f"{dp_tr:+.1f}%"
    r_delta = "—" if r_tr is None else f"{r_tr:+.1f}%"
    rhb_delta = "—" if rhb_tr is None else f"{rhb_tr:+.1f}%"

    cur_dp = int(last7_daily["DeltaP"].iloc[-1])
    cur_r = float(last7_daily["r"].iloc[-1])
    cur_rhb = float(last7_daily["r_hb"].iloc[-1])

    st.markdown("<div class='card'><h3>📌 Current Status (Daily-first baseline)</h3></div>", unsafe_allow_html=True)
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Current Delta P (mmHg)", f"{cur_dp}", dp_delta)
    k2.metric("Current r (ΔP / Flow)", f"{cur_r:.2f}", r_delta)
    k3.metric("Current r/Hb (ΔP/Flow/Hb)", f"{cur_rhb:.3f}", rhb_delta)
    k4.metric("Day # (Day 1 = earliest record)", f"{day_no}")

    # ----------------------------
    # Mode A: All records
    # ----------------------------
    if mode == "All records (trend)":
        st.markdown("<div class='card'><h3>All-record Trend</h3><p>Use last N days and smoothing window to make many points readable.</p></div>", unsafe_allow_html=True)

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

        df_view["dp_s"] = pd.to_numeric(df_view["DeltaP"], errors="coerce").rolling(window=win, min_periods=1).mean()
        df_view["r_s"] = pd.to_numeric(df_view["r"], errors="coerce").rolling(window=win, min_periods=1).mean()
        df_view["rhb_s"] = pd.to_numeric(df_view["r_hb"], errors="coerce").rolling(window=win, min_periods=1).mean()
        df_view["rpmflow_s"] = pd.to_numeric(df_view["RPM_per_Flow"], errors="coerce").rolling(window=win, min_periods=1).mean()

        # Clip warnings
        if df_view["DeltaP"].max() > 50:
            st.warning("Delta P has values > 50. Plot is clipped at 50 by design.")
        if df_view["r"].max() > 30:
            st.warning("r has values > 30. Plot is clipped at 30 by design.")
        if df_view["r_hb"].max() > 5:
            st.warning("r/Hb has values > 5. Plot is clipped at 5 by design.")

        # Delta P (0–50)
        fig, ax = plt.subplots()
        ax.plot(df_view["RecordedAt_dt"], df_view["DeltaP"], linestyle="--", alpha=0.25, label="Raw")
        ax.plot(df_view["RecordedAt_dt"], df_view["dp_s"], marker="o", label=f"Smoothed (window={win})")
        ax.set_ylim(0, 50)
        ax.set_xlabel("Time")
        ax.set_ylabel("Delta P (mmHg)")
        ax.set_title("Delta P Trend (All records)")
        ax.legend()
        fig.autofmt_xdate()
        st.pyplot(fig, clear_figure=True)
        st.caption(stats_text(df_view["DeltaP"], "{:.1f}"))

        # r (0–30)
        fig, ax = plt.subplots()
        ax.plot(df_view["RecordedAt_dt"], df_view["r"], linestyle="--", alpha=0.25, label="Raw")
        ax.plot(df_view["RecordedAt_dt"], df_view["r_s"], marker="o", label=f"Smoothed (window={win})")
        ax.set_ylim(0, 30)
        ax.set_xlabel("Time")
        ax.set_ylabel("r (ΔP / Flow)")
        ax.set_title("r Trend (All records)")
        ax.legend()
        fig.autofmt_xdate()
        st.pyplot(fig, clear_figure=True)
        st.caption(stats_text(df_view["r"], "{:.2f}"))

        # r/Hb (default 0–5)
        fig, ax = plt.subplots()
        ax.plot(df_view["RecordedAt_dt"], df_view["r_hb"], linestyle="--", alpha=0.25, label="Raw")
        ax.plot(df_view["RecordedAt_dt"], df_view["rhb_s"], marker="o", label=f"Smoothed (window={win})")
        ax.set_ylim(0, 5)
        ax.set_xlabel("Time")
        ax.set_ylabel("r/Hb (ΔP/Flow/Hb)")
        ax.set_title("r/Hb Trend (All records)")
        ax.legend()
        fig.autofmt_xdate()
        st.pyplot(fig, clear_figure=True)
        st.caption(stats_text(df_view["r_hb"], "{:.3f}"))

        # RPM/Flow (auto y-scale)
        fig, ax = plt.subplots()
        ax.plot(df_view["RecordedAt_dt"], df_view["RPM_per_Flow"], linestyle="--", alpha=0.25, label="Raw")
        ax.plot(df_view["RecordedAt_dt"], df_view["rpmflow_s"], marker="o", label=f"Smoothed (window={win})")
        ax.set_xlabel("Time")
        ax.set_ylabel("RPM / Flow")
        ax.set_title("RPM / Flow Trend (All records)")
        ax.legend()
        fig.autofmt_xdate()
        st.pyplot(fig, clear_figure=True)
        st.caption(stats_text(df_view["RPM_per_Flow"], "{:.2f}"))

    # ----------------------------
    # Mode B: Daily-first last 7
    # ----------------------------
    else:
        st.markdown("<div class='card'><h3>Daily-first (Last 7 Days)</h3><p>Each day uses the first record of that day.</p></div>", unsafe_allow_html=True)

        show7 = last7_daily[["date", "DeltaP", "r", "r_hb", "RPM_per_Flow"]].copy()
        st.dataframe(show7, use_container_width=True, hide_index=True)

        n = len(last7_daily)
        win = 1 if n <= 5 else 2 if n <= 10 else 3
        last7_daily["dp_s"] = pd.to_numeric(last7_daily["DeltaP"], errors="coerce").rolling(window=win, min_periods=1).mean()
        last7_daily["r_s"] = pd.to_numeric(last7_daily["r"], errors="coerce").rolling(window=win, min_periods=1).mean()
        last7_daily["rhb_s"] = pd.to_numeric(last7_daily["r_hb"], errors="coerce").rolling(window=win, min_periods=1).mean()
        last7_daily["rpmflow_s"] = pd.to_numeric(last7_daily["RPM_per_Flow"], errors="coerce").rolling(window=win, min_periods=1).mean()

        # Delta P (0–50)
        fig, ax = plt.subplots()
        ax.plot(last7_daily["date"], last7_daily["DeltaP"], linestyle="--", alpha=0.35, label="Raw (daily first)")
        ax.plot(last7_daily["date"], last7_daily["dp_s"], marker="o", label=f"Smoothed (window={win})")
        ax.set_ylim(0, 50)
        ax.set_xlabel("Date")
        ax.set_ylabel("Delta P (mmHg)")
        ax.set_title("Delta P Trend (Daily-first)")
        ax.legend()
        st.pyplot(fig, clear_figure=True)
        st.caption(stats_text(last7_daily["DeltaP"], "{:.1f}"))

        # r (0–30)
        fig, ax = plt.subplots()
        ax.plot(last7_daily["date"], last7_daily["r"], linestyle="--", alpha=0.35, label="Raw (daily first)")
        ax.plot(last7_daily["date"], last7_daily["r_s"], marker="o", label=f"Smoothed (window={win})")
        ax.set_ylim(0, 30)
        ax.set_xlabel("Date")
        ax.set_ylabel("r (ΔP / Flow)")
        ax.set_title("r Trend (Daily-first)")
        ax.legend()
        st.pyplot(fig, clear_figure=True)
        st.caption(stats_text(last7_daily["r"], "{:.2f}"))

        # r/Hb (0–5 default)
        fig, ax = plt.subplots()
        ax.plot(last7_daily["date"], last7_daily["r_hb"], linestyle="--", alpha=0.35, label="Raw (daily first)")
        ax.plot(last7_daily["date"], last7_daily["rhb_s"], marker="o", label=f"Smoothed (window={win})")
        ax.set_ylim(0, 5)
        ax.set_xlabel("Date")
        ax.set_ylabel("r/Hb (ΔP/Flow/Hb)")
        ax.set_title("r/Hb Trend (Daily-first)")
        ax.legend()
        st.pyplot(fig, clear_figure=True)
        st.caption(stats_text(last7_daily["r_hb"], "{:.3f}"))

        # RPM/Flow (auto)
        fig, ax = plt.subplots()
        ax.plot(last7_daily["date"], last7_daily["RPM_per_Flow"], linestyle="--", alpha=0.35, label="Raw (daily first)")
        ax.plot(last7_daily["date"], last7_daily["rpmflow_s"], marker="o", label=f"Smoothed (window={win})")
        ax.set_xlabel("Date")
        ax.set_ylabel("RPM / Flow")
        ax.set_title("RPM / Flow Trend (Daily-first)")
        ax.legend()
        st.pyplot(fig, clear_figure=True)
        st.caption(stats_text(last7_daily["RPM_per_Flow"], "{:.2f}"))

    # ----------------------------
    # RPM vs Flow (color=r fixed)
    # ----------------------------
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
