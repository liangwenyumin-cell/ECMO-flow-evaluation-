import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, time, timedelta

# ======================================================
# Page config
# ======================================================
st.set_page_config(page_title="ECMO Trend Analyzer", layout="wide")

# ======================================================
# Page + ICU mode state (card buttons)
# ======================================================
if "page" not in st.session_state:
    st.session_state.page = "Data Entry & Records Page"
if "icu_mode" not in st.session_state:
    st.session_state.icu_mode = False

def go(page_name: str):
    st.session_state.page = page_name

c1, c2, c3 = st.columns([2, 2, 2])
with c1:
    st.button("📝 Data Entry", use_container_width=True, on_click=go, args=("Data Entry & Records Page",))
with c2:
    st.button("📊 Analysis", use_container_width=True, on_click=go, args=("Charts & Analysis Page",))
with c3:
    st.session_state.icu_mode = st.toggle("🩺 ICU Mode", value=st.session_state.icu_mode)

page = st.session_state.page

# ======================================================
# Background + UI
# ======================================================
page_bg = "#FFF9E6" if page == "Data Entry & Records Page" else "#EAF4FF"

st.markdown(
    f"""
    <style>
      /* ---------- ICU MODE TUNING ---------- */
      :root {{
        --icu-font: 18px;
        --icu-title: 30px;
        --icu-card-pad: 18px;
        --icu-border: 2px;
      }}

      body[data-icu="1"] {{
        font-size: var(--icu-font) !important;
      }}

      body[data-icu="1"] .hero-title {{
        font-size: var(--icu-title) !important;
      }}

      body[data-icu="1"] .card {{
        padding: var(--icu-card-pad) !important;
        border-width: var(--icu-border) !important;
      }}

      body[data-icu="1"] label {{
        font-size: 18px !important;
      }}

      body[data-icu="1"] .stNumberInput input,
      body[data-icu="1"] .stDateInput input,
      body[data-icu="1"] .stTimeInput input {{
        font-size: 22px !important;
        padding: 10px 12px !important;
      }}

      body[data-icu="1"] .stButton button,
      body[data-icu="1"] .stDownloadButton button {{
        font-size: 20px !important;
        padding: 14px 16px !important;
      }}

      /* ---------- BASE UI ---------- */
      .stApp {{
        background-color: {page_bg};
      }}

      .hero {{
        border: 1px solid rgba(0,0,0,0.08);
        background: rgba(255,255,255,0.85);
        border-radius: 18px;
        padding: 16px 18px;
        margin: 10px 0 12px 0;
      }}
      .hero-title {{
        font-size: 28px;
        font-weight: 800;
        margin: 0;
      }}
      .hero-sub {{
        margin-top: 6px;
        color: rgba(0,0,0,0.55);
        font-size: 14px;
      }}

      .card {{
        border: 1px solid rgba(0,0,0,0.08);
        background: rgba(255,255,255,0.92);
        border-radius: 16px;
        padding: 14px;
        margin: 10px 0 12px 0;
      }}

      label {{
        font-size: 16px !important;
      }}

      .stNumberInput input, .stDateInput input, .stTimeInput input {{
        font-size: 18px !important;
        background-color: #fff !important;
      }}

      .stButton button, .stDownloadButton button {{
        font-size: 16px !important;
        padding: 10px 14px !important;
        border-radius: 12px !important;
      }}

      thead tr th {{
        font-size: 13px !important;
      }}
      tbody tr:nth-child(even) {{
        background-color: rgba(0,0,0,0.02);
      }}
    </style>
    """,
    unsafe_allow_html=True
)

# Make ICU mode toggle actually apply
st.markdown(
    f"""
    <script>
      document.body.setAttribute("data-icu", "{1 if st.session_state.icu_mode else 0}");
    </script>
    """,
    unsafe_allow_html=True
)

st.markdown(
    """
    <div class="hero">
      <div class="hero-title">ECMO Trend Analyzer</div>
      <div class="hero-sub">
        r = ΔP / Flow • r/Hb = (ΔP/Flow)/Hb • RPM/Flow • 7-day daily-first trend • Correlation matrices + scatter selector • CSV restore
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

def _to_num(x):
    return pd.to_numeric(x, errors="coerce")

def ensure_schema(df: pd.DataFrame) -> pd.DataFrame:
    """Make old CSV compatible & recompute derived columns."""
    if df is None or len(df) == 0:
        return pd.DataFrame(columns=COLUMNS)

    # add missing cols
    for c in COLUMNS:
        if c not in df.columns:
            df[c] = pd.NA

    # numeric base
    df["No"] = _to_num(df["No"])
    if df["No"].isna().all():
        df["No"] = range(1, len(df) + 1)

    df["Flow"] = _to_num(df["Flow"])
    df["RPM"] = _to_num(df["RPM"])
    df["DeltaP"] = _to_num(df["DeltaP"]).round(0)
    df["Hb"] = _to_num(df["Hb"])

    # recompute derived
    valid_flow = df["Flow"] > 0
    df.loc[valid_flow, "r"] = df.loc[valid_flow, "DeltaP"] / df.loc[valid_flow, "Flow"]
    df.loc[valid_flow, "RPM_per_Flow"] = df.loc[valid_flow, "RPM"] / df.loc[valid_flow, "Flow"]

    valid_hb = df["Hb"] > 0
    valid_rhb = valid_flow & valid_hb
    df.loc[valid_rhb, "r_hb"] = df.loc[valid_rhb, "r"] / df.loc[valid_rhb, "Hb"]

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
    if len(df_now) > 0:
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
          <h3>🧾 Records (Editable)</h3>
          <p>Edit cells and click <b>Apply changes</b>. Derived metrics will be recomputed.</p>
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
                    st.session_state.data = ensure_schema(saved)
                    st.success("✅ Changes applied successfully.")
                    st.info(f"Total records: {len(st.session_state.data)}")

    # ---- Export ----
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

    # Daily-first baseline & last 7 days
    df["date"] = df["RecordedAt_dt"].dt.date
    daily_first = df.groupby("date", as_index=False).first().sort_values("date").reset_index(drop=True)
    last7 = daily_first.tail(7).copy()

    # Day #
    day_no = (daily_first["date"].iloc[-1] - daily_first["date"].iloc[0]).days + 1

    # 7-day trend % (today daily-first vs yesterday daily-first)
    def pct(prev, cur):
        if prev == 0:
            return None
        return (cur - prev) / abs(prev) * 100.0

    dp_delta = r_delta = rhb_delta = rpmflow_delta = "—"
    if len(last7) >= 2:
        dp_d = pct(float(last7["DeltaP"].iloc[-2]), float(last7["DeltaP"].iloc[-1]))
        r_d = pct(float(last7["r"].iloc[-2]), float(last7["r"].iloc[-1]))
        rhb_d = pct(float(last7["r_hb"].iloc[-2]), float(last7["r_hb"].iloc[-1]))
        rpmf_d = pct(float(last7["RPM_per_Flow"].iloc[-2]), float(last7["RPM_per_Flow"].iloc[-1]))
        dp_delta = "—" if dp_d is None else f"{dp_d:+.1f}%"
        r_delta = "—" if r_d is None else f"{r_d:+.1f}%"
        rhb_delta = "—" if rhb_d is None else f"{rhb_d:+.1f}%"
        rpmflow_delta = "—" if rpmf_d is None else f"{rpmf_d:+.1f}%"

    cur_dp = int(last7["DeltaP"].iloc[-1])
    cur_r = float(last7["r"].iloc[-1])
    cur_rhb = float(last7["r_hb"].iloc[-1])
    cur_rpmflow = float(last7["RPM_per_Flow"].iloc[-1])

    st.markdown("<div class='card'><h3>📌 Current Status (Daily-first baseline)</h3></div>", unsafe_allow_html=True)
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Current ΔP", f"{cur_dp}", dp_delta)
    k2.metric("Current r", f"{cur_r:.2f}", r_delta)
    k3.metric("Current r/Hb", f"{cur_rhb:.3f}", rhb_delta)
    k4.metric("Current RPM/Flow", f"{cur_rpmflow:.2f}", rpmflow_delta)
    k5.metric("Day #", f"{day_no}")

    # 7-day table with day-to-day change %
    show7 = last7[["date", "DeltaP", "r", "r_hb", "RPM_per_Flow"]].copy()
    show7["ΔP_%"] = "—"
    show7["r_%"] = "—"
    show7["r/Hb_%"] = "—"
    show7["RPM/Flow_%"] = "—"
    for i in range(1, len(show7)):
        p_dp = pct(float(show7.loc[show7.index[i-1], "DeltaP"]), float(show7.loc[show7.index[i], "DeltaP"]))
        p_r = pct(float(show7.loc[show7.index[i-1], "r"]), float(show7.loc[show7.index[i], "r"]))
        p_rhb = pct(float(show7.loc[show7.index[i-1], "r_hb"]), float(show7.loc[show7.index[i], "r_hb"]))
        p_rpmf = pct(float(show7.loc[show7.index[i-1], "RPM_per_Flow"]), float(show7.loc[show7.index[i], "RPM_per_Flow"]))
        show7.loc[show7.index[i], "ΔP_%"] = "—" if p_dp is None else f"{p_dp:+.1f}%"
        show7.loc[show7.index[i], "r_%"] = "—" if p_r is None else f"{p_r:+.1f}%"
        show7.loc[show7.index[i], "r/Hb_%"] = "—" if p_rhb is None else f"{p_rhb:+.1f}%"
        show7.loc[show7.index[i], "RPM/Flow_%"] = "—" if p_rpmf is None else f"{p_rpmf:+.1f}%"

    st.markdown("<div class='card'><h3>🗓️ Last 7 Days (Daily-first)</h3></div>", unsafe_allow_html=True)
    st.dataframe(show7, use_container_width=True, hide_index=True)

    # ----------------------------
    # Trend plots (RAW only)
    # ----------------------------
    st.markdown("<div class='card'><h3>📈 Trend Plots (Raw)</h3><p>No smoothing.</p></div>", unsafe_allow_html=True)

    def stats_text(series: pd.Series, fmt: str):
        s = pd.to_numeric(series, errors="coerce").dropna()
        if len(s) == 0:
            return "N=0"
        return f"Mean {fmt.format(s.mean())} | Max {fmt.format(s.max())} | Min {fmt.format(s.min())} | Median {fmt.format(s.median())} | N={len(s)}"

    cA, cB = st.columns(2)
    with cA:
        last_n_days = st.slider("Show last N days (plots & correlation)", 1, 60, 14)
    with cB:
        use_daily_first_only = st.checkbox("Use Daily-first only (plots)", value=False)

    cutoff = df["RecordedAt_dt"].max() - timedelta(days=int(last_n_days))
    df_view = df[df["RecordedAt_dt"] >= cutoff].copy()

    if use_daily_first_only:
        tmp = df_view.copy()
        tmp["date"] = tmp["RecordedAt_dt"].dt.date
        tmp = tmp.groupby("date", as_index=False).first()
        tmp["RecordedAt_dt"] = pd.to_datetime(tmp["RecordedAt_dt"])
        df_view = tmp.sort_values("RecordedAt_dt")

    if len(df_view) < 2:
        st.warning("Not enough points in this range. Increase N days.")
        st.stop()

    # ΔP (0–50)
    fig, ax = plt.subplots()
    ax.plot(df_view["RecordedAt_dt"], df_view["DeltaP"], marker="o")
    ax.set_ylim(0, 50)
    ax.set_title("Delta P Trend")
    ax.set_xlabel("Time")
    ax.set_ylabel("Delta P (mmHg)")
    fig.autofmt_xdate()
    st.pyplot(fig, clear_figure=True)
    st.caption(stats_text(df_view["DeltaP"], "{:.1f}"))

    # r (0–30)
    fig, ax = plt.subplots()
    ax.plot(df_view["RecordedAt_dt"], df_view["r"], marker="o")
    ax.set_ylim(0, 30)
    ax.set_title("r Trend")
    ax.set_xlabel("Time")
    ax.set_ylabel("r (ΔP/Flow)")
    fig.autofmt_xdate()
    st.pyplot(fig, clear_figure=True)
    st.caption(stats_text(df_view["r"], "{:.2f}"))

    # r/Hb
    fig, ax = plt.subplots()
    ax.plot(df_view["RecordedAt_dt"], df_view["r_hb"], marker="o")
    ax.set_title("r/Hb Trend")
    ax.set_xlabel("Time")
    ax.set_ylabel("r/Hb (ΔP/Flow/Hb)")
    fig.autofmt_xdate()
    st.pyplot(fig, clear_figure=True)
    st.caption(stats_text(df_view["r_hb"], "{:.3f}"))

    # RPM/Flow
    fig, ax = plt.subplots()
    ax.plot(df_view["RecordedAt_dt"], df_view["RPM_per_Flow"], marker="o")
    ax.set_title("RPM / Flow Trend")
    ax.set_xlabel("Time")
    ax.set_ylabel("RPM / Flow")
    fig.autofmt_xdate()
    st.pyplot(fig, clear_figure=True)
    st.caption(stats_text(df_view["RPM_per_Flow"], "{:.2f}"))

    # ----------------------------
    # Correlation investigation (Pearson + Spearman)
    # ----------------------------
    st.markdown("<div class='card'><h3>🔎 Correlation Investigation</h3><p>Pearson & Spearman correlation matrices for ΔP, r, r/Hb, RPM/Flow.</p></div>", unsafe_allow_html=True)

    corr_df = df_view[["DeltaP", "r", "r_hb", "RPM_per_Flow"]].apply(pd.to_numeric, errors="coerce").dropna()
    if len(corr_df) < 3:
        st.warning("Not enough complete rows for correlation (need ≥ 3).")
    else:
        pear = corr_df.corr(method="pearson").round(3)
        spear = corr_df.corr(method="spearman").round(3)

        st.subheader("Pearson correlation")
        st.dataframe(pear, use_container_width=True)

        st.subheader("Spearman correlation")
        st.dataframe(spear, use_container_width=True)

    # ----------------------------
    # Scatter selector (X/Y) + Pearson/Spearman for the selected pair
    # ----------------------------
    st.markdown("<div class='card'><h3>🎯 Scatter Selector</h3><p>Select X and Y to visualize relationship + show Pearson/Spearman.</p></div>", unsafe_allow_html=True)

    var_map = {
        "Delta P (mmHg)": "DeltaP",
        "r (ΔP/Flow)": "r",
        "r/Hb (ΔP/Flow/Hb)": "r_hb",
        "RPM/Flow": "RPM_per_Flow"
    }

    s1, s2, s3 = st.columns([2, 2, 2])
    with s1:
        x_label = st.selectbox("X axis", list(var_map.keys()), index=1)
    with s2:
        y_label = st.selectbox("Y axis", list(var_map.keys()), index=3)
    with s3:
        show_line = st.checkbox("Show linear trend line", value=True)

    x_col = var_map[x_label]
    y_col = var_map[y_label]

    pair = df_view[[x_col, y_col]].apply(pd.to_numeric, errors="coerce").dropna()
    if len(pair) < 3:
        st.warning("Not enough points for scatter/correlation (need ≥ 3).")
    else:
        pear_xy = pair[x_col].corr(pair[y_col], method="pearson")
        spear_xy = pair[x_col].corr(pair[y_col], method="spearman")

        st.write(f"**Pearson:** {pear_xy:.3f}   |   **Spearman:** {spear_xy:.3f}   |   **N:** {len(pair)}")

        fig, ax = plt.subplots()
        ax.scatter(pair[x_col], pair[y_col])
        ax.set_xlabel(x_label)
        ax.set_ylabel(y_label)
        ax.set_title(f"{y_label} vs {x_label}")

        if show_line:
            x = pair[x_col].astype(float)
            y = pair[y_col].astype(float)
            x_mean = x.mean()
            y_mean = y.mean()
            var_x = ((x - x_mean) ** 2).mean()
            if var_x > 0:
                cov_xy = ((x - x_mean) * (y - y_mean)).mean()
                slope = cov_xy / var_x
                intercept = y_mean - slope * x_mean
                xs = pd.Series([x.min(), x.max()])
                ys = slope * xs + intercept
                ax.plot(xs, ys)

        st.pyplot(fig, clear_figure=True)
