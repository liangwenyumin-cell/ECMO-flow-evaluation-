import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, time
from scipy.stats import pearsonr, spearmanr

# -------------------------
# Page config + selector first (for theme)
# -------------------------
st.set_page_config(page_title="ECMO Trend Analyzer", layout="wide")

page = st.radio(
    "Page",
    ["Data Entry & Records Page", "Charts & Anysia Page"],
    horizontal=True
)

# -------------------------
# Background color by page
# -------------------------
page_bg = "#FFF9E6" if page == "Data Entry & Records Page" else "#EAF4FF"  # light yellow / light blue

# -------------------------
# UI Theme (same palette per page)
# -------------------------
st.markdown(
    f"""
    <style>
      .stApp {{
        background-color: {page_bg};
      }}

      :root {{
        --entry-card: rgba(255, 245, 210, 0.95);
        --entry-soft: rgba(255, 250, 230, 0.95);

        --analysis-card: rgba(225, 240, 255, 0.95);
        --analysis-soft: rgba(235, 245, 255, 0.95);

        --border-soft: rgba(0,0,0,0.08);
        --muted: rgba(0,0,0,0.55);
      }}

      body {{
        --card-bg: {"var(--entry-card)" if page == "Data Entry & Records Page" else "var(--analysis-card)"};
        --soft-bg: {"var(--entry-soft)" if page == "Data Entry & Records Page" else "var(--analysis-soft)"};
      }}

      .block-container {{
        padding-top: 1.1rem;
        padding-bottom: 2rem;
      }}

      /* Hero */
      .hero {{
        border: 1px solid var(--border-soft);
        background: var(--soft-bg);
        border-radius: 18px;
        padding: 16px 18px;
        margin-bottom: 14px;
      }}
      .hero-title {{
        font-size: 28px;
        font-weight: 800;
        margin: 0;
      }}
      .hero-sub {{
        margin-top: 6px;
        color: var(--muted);
        font-size: 14px;
      }}

      /* Cards */
      .card {{
        border: 1px solid var(--border-soft);
        background: var(--card-bg);
        border-radius: 16px;
        padding: 14px;
        margin: 10px 0 14px 0;
      }}
      .card h3 {{
        margin: 0 0 6px 0;
        font-size: 18px;
      }}
      .card p {{
        margin: 0;
        color: var(--muted);
        font-size: 13px;
      }}

      /* Alerts */
      .stAlert {{
        background-color: var(--soft-bg) !important;
        border: 1px solid var(--border-soft) !important;
        border-radius: 14px !important;
      }}

      /* Inputs (bigger for iPad) */
      label {{
        font-size: 16px !important;
      }}
      .stNumberInput input,
      .stDateInput input,
      .stTimeInput input {{
        font-size: 18px !important;
        background-color: #ffffff !important;
      }}

      /* Buttons */
      .stButton button,
      .stDownloadButton button {{
        font-size: 16px !important;
        padding: 10px 14px !important;
        border-radius: 12px !important;
        background-color: var(--soft-bg) !important;
        border: 1px solid var(--border-soft) !important;
      }}

      /* Table header */
      thead tr th {{
        font-size: 13px !important;
        background-color: var(--soft-bg) !important;
      }}
      tbody tr:nth-child(even) {{
        background-color: rgba(0,0,0,0.02);
      }}
    </style>
    """,
    unsafe_allow_html=True
)

# -------------------------
# Header
# -------------------------
st.markdown(
    """
    <div class="hero">
      <div class="hero-title">ECMO Trend Analyzer</div>
      <div class="hero-sub">
        Backfillable date/time • r = Delta P / Flow • Trends • RPM–Flow coupling • Correlations • CSV restore
      </div>
    </div>
    """,
    unsafe_allow_html=True
)

# -------------------------
# Data schema
# -------------------------
COLUMNS = [
    "No",
    "RecordedAt",
    "Flow", "RPM", "DeltaP", "Hb",
    "Glucose_mmol", "Glucose_mg_dL",
    "r",
    "RPM_per_Flow",
]

def ensure_schema(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or len(df) == 0:
        return pd.DataFrame(columns=COLUMNS)
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA
    df["No"] = pd.to_numeric(df["No"], errors="coerce")
    return df[COLUMNS].copy()

def next_no(df: pd.DataFrame) -> int:
    if len(df) == 0 or df["No"].dropna().empty:
        return 1
    return int(df["No"].dropna().max()) + 1

# -------------------------
# Session state
# -------------------------
if "data" not in st.session_state:
    st.session_state.data = pd.DataFrame(columns=COLUMNS)
st.session_state.data = ensure_schema(st.session_state.data)

# Guard flag to prevent infinite rerun on restore
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
          <p>Inputs default to the last saved record (for faster entry). On iPad, number inputs will open the numeric keypad.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Defaults from last record if available
    df_now = ensure_schema(st.session_state.data)
    if len(df_now) > 0 and df_now["No"].dropna().any():
        last = df_now.sort_values("No").iloc[-1]

        def pick(val, fallback):
            return fallback if pd.isna(val) else val

        d_flow = float(pick(last.get("Flow"), 4.5))
        d_rpm = int(pick(last.get("RPM"), 3200))
        d_dp = int(pick(last.get("DeltaP"), 55))
        d_hb = float(pick(last.get("Hb"), 10.8))
        d_glu = float(pick(last.get("Glucose_mmol"), 8.0))
    else:
        d_flow, d_rpm, d_dp, d_hb, d_glu = 4.5, 3200, 55, 10.8, 8.0

    with st.form("input_form", clear_on_submit=False):
        rec_date = st.date_input("Date", value=datetime.now().date())
        rec_time = st.time_input("Time", value=time(8, 0))  # default 08:00 (SG/TPE UTC+8)

        flow = st.number_input("ECMO Flow (L/min)", min_value=0.0, value=float(d_flow), step=0.1)
        rpm = st.number_input("Pump RPM", min_value=0, value=int(d_rpm), step=10)
        delta_p = st.number_input("Delta P (mmHg)", min_value=0, value=int(d_dp), step=1, format="%d")
        hb = st.number_input("Hemoglobin (g/dL)", min_value=0.0, value=float(d_hb), step=0.1, format="%.1f")
        glucose_mmol = st.number_input("Glucose (mmol/L)", min_value=0.0, value=float(d_glu), step=0.1, format="%.1f")

        add = st.form_submit_button("Add record")

    # ---- Add record with spinner + success ----
    if add:
        if flow <= 0:
            st.error("Flow must be > 0.")
        else:
            with st.spinner("Saving..."):
                df_now = ensure_schema(st.session_state.data)
                rec_no = next_no(df_now)
                recorded_at = datetime.combine(rec_date, rec_time)

                glucose_mg_dl = float(glucose_mmol) * 18.0
                r_val = float(delta_p) / float(flow)
                rpm_per_flow = float(rpm) / float(flow)

                new_row = {
                    "No": rec_no,
                    "RecordedAt": recorded_at.isoformat(timespec="minutes"),
                    "Flow": float(flow),
                    "RPM": int(rpm),
                    "DeltaP": int(delta_p),
                    "Hb": round(float(hb), 1),
                    "Glucose_mmol": round(float(glucose_mmol), 1),
                    "Glucose_mg_dL": float(glucose_mg_dl),
                    "r": float(r_val),
                    "RPM_per_Flow": float(rpm_per_flow),
                }

                st.session_state.data = pd.concat([df_now, pd.DataFrame([new_row])], ignore_index=True)

            st.success("✅ Saved successfully.")
            try:
                st.toast("Saved successfully.", icon="✅")
            except Exception:
                pass

            st.info(f"Total records: {len(st.session_state.data)} | Latest No: {rec_no}")

    # ---- Restore from CSV (under Add Record) ----
    st.markdown(
        """
        <div class="card">
          <h3>💾 Restore from CSV</h3>
          <p>Upload a CSV previously exported from this app to restore your session.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    uploaded = st.file_uploader("Upload CSV", type=["csv"], key="restore_csv")

    # IMPORTANT: only restore once per selected file to avoid infinite rerun
    if uploaded is not None and not st.session_state.restore_done:
        with st.spinner("Restoring..."):
            try:
                loaded = pd.read_csv(uploaded)
                st.session_state.data = ensure_schema(loaded)

                st.session_state.restore_done = True  # prevents rerun loop

                st.success(f"✅ Restored {len(st.session_state.data)} records.")
                try:
                    st.toast("Restored from CSV.", icon="✅")
                except Exception:
                    pass

                st.rerun()

            except Exception as e:
                st.error(f"Failed to load CSV: {e}")

    # Optional: allow restoring another CSV explicitly
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
          <p>Edit cells and click <b>Apply changes</b>. Derived metrics are recalculated.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    df = ensure_schema(st.session_state.data)
    if len(df) == 0:
        st.info("No data yet. Add a record above, or restore from CSV.")
    else:
        df_disp = df.copy()
        df_disp["RecordedAt"] = pd.to_datetime(df_disp["RecordedAt"], errors="coerce").dt.strftime("%Y-%m-%d %H:%M")

        edited = st.data_editor(df_disp, use_container_width=True, hide_index=True)

        st.info("Edits are not saved until you click **Apply changes**.")

        # ---- Apply changes with spinner + success ----
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
                    saved["Glucose_mmol"] = pd.to_numeric(saved["Glucose_mmol"], errors="coerce")

                    if (saved["Flow"] <= 0).any():
                        st.error("Flow must be > 0 for all rows.")
                    else:
                        saved["Glucose_mg_dL"] = saved["Glucose_mmol"] * 18.0
                        saved["r"] = saved["DeltaP"].astype(float) / saved["Flow"].astype(float)
                        saved["RPM_per_Flow"] = saved["RPM"].astype(float) / saved["Flow"].astype(float)

                        st.session_state.data = ensure_schema(saved)

                        st.success("✅ Changes applied successfully.")
                        try:
                            st.toast("Changes applied.", icon="✅")
                        except Exception:
                            pass

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
# PAGE 2: Charts & Anysia
# ======================================================
else:
    df = ensure_schema(st.session_state.data)
    if len(df) == 0:
        st.info("No data yet.")
        st.stop()

    df["RecordedAt_dt"] = pd.to_datetime(df["RecordedAt"], errors="coerce")
    plot_df = df.dropna(subset=["RecordedAt_dt"]).sort_values("RecordedAt_dt")

    st.markdown(
        """
        <div class="card">
          <h3>📈 Trends</h3>
          <p>Large charts for analysis view.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    for title, y, ylabel in [
        ("Delta P Trend Over Time", "DeltaP", "Delta P (mmHg)"),
        ("r Trend Over Time", "r", "r (Delta P / Flow)"),
        ("RPM / Flow Trend Over Time", "RPM_per_Flow", "RPM / Flow"),
    ]:
        fig, ax = plt.subplots()
        ax.plot(plot_df["RecordedAt_dt"], plot_df[y], marker="o")
        ax.set_xlabel("Time")
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        fig.autofmt_xdate()
        st.pyplot(fig, clear_figure=True)

    st.markdown(
        """
        <div class="card">
          <h3>🔎 RPM–Flow Coupling</h3>
          <p>Scatter plot colored by r.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    fig, ax = plt.subplots()
    sc = ax.scatter(plot_df["RPM"], plot_df["Flow"], c=plot_df["r"], cmap="viridis")
    ax.set_xlabel("Pump RPM")
    ax.set_ylabel("ECMO Flow (L/min)")
    ax.set_title("RPM vs Flow (Color = r)")
    cbar = plt.colorbar(sc, ax=ax)
    cbar.set_label("r (Delta P / Flow)")
    st.pyplot(fig, clear_figure=True)

    st.info(
        "Interpretation: When RPM increases without proportional Flow increase, elevated r suggests increased circuit resistance."
    )

    st.markdown(
        """
        <div class="card">
          <h3>🧪 Correlation Analysis</h3>
          <p>Pearson (linear) and Spearman (rank) correlation between r and Hb / Glucose.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    def corr_block(x, y, x_name, y_name):
        d = pd.DataFrame({"x": x, "y": y}).dropna()
        if len(d) < 3:
            st.warning(f"Not enough data for {y_name} vs {x_name} (n={len(d)}).")
            return
        pr, pp = pearsonr(d["x"], d["y"])
        sr, sp = spearmanr(d["x"], d["y"])
        st.write(f"**{y_name} vs {x_name}** (n={len(d)})")
        st.write(f"- Pearson r = {pr:.3f}, p = {pp:.4g}")
        st.write(f"- Spearman ρ = {sr:.3f}, p = {sp:.4g}")

    corr_block(df["Hb"], df["r"], "Hemoglobin (g/dL)", "r")
    corr_block(df["Glucose_mmol"], df["r"], "Glucose (mmol/L)", "r")
