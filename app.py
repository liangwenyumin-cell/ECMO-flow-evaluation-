import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, time
from scipy.stats import pearsonr, spearmanr

# -------------------------
# Page config + UI style
# -------------------------
st.set_page_config(page_title="ECMO Trend Analyzer", layout="wide")

st.markdown(
    """
    <style>
      :root{
        --card-bg: rgba(255,255,255,0.75);
        --card-border: rgba(0,0,0,0.08);
        --muted: rgba(0,0,0,0.55);
      }

      /* Slightly nicer base spacing */
      .block-container { padding-top: 1.1rem; padding-bottom: 2rem; }

      /* Header */
      .hero {
        border: 1px solid var(--card-border);
        background: linear-gradient(135deg, rgba(240,248,255,0.85), rgba(245,245,255,0.85));
        border-radius: 18px;
        padding: 16px 18px;
        margin-bottom: 14px;
      }
      .hero-title { font-size: 28px; font-weight: 800; margin: 0; }
      .hero-sub { margin: 6px 0 0 0; color: var(--muted); font-size: 14px; }

      /* Cards */
      .card {
        border: 1px solid var(--card-border);
        background: var(--card-bg);
        border-radius: 16px;
        padding: 14px 14px;
        margin: 10px 0 14px 0;
      }
      .card h3 { margin: 0 0 6px 0; font-size: 18px; }
      .card p { margin: 0; color: var(--muted); font-size: 13px; }

      /* Inputs bigger for iPad */
      label { font-size: 16px !important; }
      .stNumberInput input, .stTextInput input { font-size: 18px !important; }
      .stDateInput input, .stTimeInput input { font-size: 18px !important; }

      /* Buttons */
      .stButton button, .stDownloadButton button {
        font-size: 16px !important;
        padding: 10px 14px !important;
        border-radius: 12px !important;
      }

      /* Reduce table header clutter */
      thead tr th { font-size: 13px !important; }

      /* Make radio pills nicer */
      div[role="radiogroup"] > label { padding-right: 12px; }

      /* Remove extra blank space at top of subheaders */
      h2, h3 { margin-top: 0.2rem; }

    </style>
    """,
    unsafe_allow_html=True,
)

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

# -------------------------
# Page selector
# -------------------------
page = st.radio(
    "Page",
    ["Data Entry & Records Page", "Charts & Anysia Page"],
    horizontal=True
)

# ======================================================
# PAGE 1: Data Entry & Records
# ======================================================
if page == "Data Entry & Records Page":

    # ---- Add Record (Vertical layout) ----
    st.markdown(
        """
        <div class="card">
          <h3>➕ Add Record</h3>
          <p>Enter values in a vertical layout (iPad-friendly). You can backfill past timestamps.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    with st.form("input_form", clear_on_submit=False):
        # Singapore/Taipei = UTC+8, so default 08:00 is correct for both.
        rec_date = st.date_input("Date", value=datetime.now().date())
        rec_time = st.time_input("Time", value=time(8, 0))  # default 08:00
        recorded_at = datetime.combine(rec_date, rec_time)

        flow = st.number_input("ECMO Flow (L/min)", min_value=0.1, value=4.5, step=0.1)
        rpm = st.number_input("Pump RPM", min_value=0, value=3200, step=10)
        delta_p = st.number_input("Delta P (mmHg)", min_value=0, value=55, step=1, format="%d")
        hb = st.number_input("Hemoglobin (g/dL)", min_value=0.0, value=10.8, step=0.1, format="%.1f")
        glucose_mmol = st.number_input("Glucose (mmol/L)", min_value=0.0, value=8.0, step=0.1, format="%.1f")

        add = st.form_submit_button("Add record")

    if add:
        df_now = ensure_schema(st.session_state.data)
        rec_no = next_no(df_now)

        glucose_mg_dl = glucose_mmol * 18.0
        r_val = delta_p / flow
        rpm_per_flow = rpm / flow

        new_row = {
            "No": rec_no,
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

        st.session_state.data = pd.concat([df_now, pd.DataFrame([new_row])], ignore_index=True)
        st.success("✅ Record added. Tip: Download CSV regularly to avoid data loss on refresh/close.")

    # ---- Restore from CSV (moved under Add Record) ----
    st.markdown(
        """
        <div class="card">
          <h3>💾 Restore from CSV</h3>
          <p>If you refreshed/closed the tab, upload the last exported CSV to restore and continue.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    uploaded = st.file_uploader("Upload CSV exported from this app", type=["csv"])
    if uploaded is not None:
        try:
            loaded = pd.read_csv(uploaded)
            loaded = ensure_schema(loaded)
            st.session_state.data = loaded
            st.success(f"✅ Restored {len(loaded)} records from CSV.")
        except Exception as e:
            st.error(f"Failed to load CSV: {e}")

    st.divider()

    # ---- Editable table ----
    st.markdown(
        """
        <div class="card">
          <h3>🧾 Records (Editable)</h3>
          <p>Edit values directly and click <b>Save changes</b>. Derived fields (r, RPM/Flow) will be recomputed.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    df = ensure_schema(st.session_state.data)
    if len(df) == 0:
        st.info("No data yet. Add a record above, or restore from CSV.")
    else:
        df_display = df.copy()
        df_display["RecordedAt"] = pd.to_datetime(df_display["RecordedAt"], errors="coerce").dt.strftime("%Y-%m-%d %H:%M")

        edited = st.data_editor(
            df_display,
            use_container_width=True,
            hide_index=True,
            column_config={
                "No": st.column_config.NumberColumn("No", disabled=True),
                "RecordedAt": st.column_config.TextColumn("RecordedAt (YYYY-MM-DD HH:MM)"),
                "DeltaP": st.column_config.NumberColumn("DeltaP (mmHg)", step=1, format="%d"),
                "Hb": st.column_config.NumberColumn("Hb (g/dL)", step=0.1, format="%.1f"),
                "Glucose_mmol": st.column_config.NumberColumn("Glucose (mmol/L)", step=0.1, format="%.1f"),
            }
        )

        csave, cclear, csp = st.columns([1, 1, 3])
        with csave:
            if st.button("Save changes"):
                try:
                    saved = edited.copy()
                    parsed = pd.to_datetime(saved["RecordedAt"], errors="coerce")
                    if parsed.isna().any():
                        st.error("Invalid RecordedAt format. Use YYYY-MM-DD HH:MM.")
                    else:
                        saved["RecordedAt"] = parsed.dt.strftime("%Y-%m-%dT%H:%M")
                        saved["Flow"] = pd.to_numeric(saved["Flow"], errors="coerce")
                        saved["RPM"] = pd.to_numeric(saved["RPM"], errors="coerce")
                        saved["DeltaP"] = pd.to_numeric(saved["DeltaP"], errors="coerce").round(0).astype("Int64")
                        saved["Hb"] = pd.to_numeric(saved["Hb"], errors="coerce")
                        saved["Glucose_mmol"] = pd.to_numeric(saved["Glucose_mmol"], errors="coerce")

                        # Recompute derived fields
                        saved["Glucose_mg_dL"] = saved["Glucose_mmol"] * 18.0
                        saved["r"] = saved["DeltaP"].astype(float) / saved["Flow"].astype(float)
                        saved["RPM_per_Flow"] = saved["RPM"].astype(float) / saved["Flow"].astype(float)

                        st.session_state.data = ensure_schema(saved)
                        st.success("✅ Changes saved.")
                except Exception as e:
                    st.error(f"Save failed: {e}")

        with cclear:
            confirm_clear = st.checkbox("Confirm clear all", value=False)
            if st.button("Clear all records"):
                if confirm_clear:
                    st.session_state.data = pd.DataFrame(columns=COLUMNS)
                    st.success("Cleared.")
                else:
                    st.warning("Please confirm before clearing.")

    st.divider()

    # ---- Export ----
    st.markdown(
        """
        <div class="card">
          <h3>⬇️ Export</h3>
          <p>Download CSV for backup. This is the recommended way to prevent data loss.</p>
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
        st.info("No data yet. Add records on the Data Entry page or restore from CSV.")
        st.stop()

    df["RecordedAt_dt"] = pd.to_datetime(df["RecordedAt"], errors="coerce")
    plot_df = df.dropna(subset=["RecordedAt_dt"]).sort_values("RecordedAt_dt")

    st.markdown(
        """
        <div class="card">
          <h3>📈 Trends</h3>
          <p>Large charts for easier viewing on iPad. X-axis is the recorded timestamp.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    for title, y, ylabel in [
        ("Delta P Trend Over Time", "DeltaP", "Delta P (mmHg)"),
        ("r Trend Over Time (r = Delta P / Flow)", "r", "r (Delta P / Flow)"),
        ("Pump Inefficiency Trend (RPM / Flow)", "RPM_per_Flow", "RPM / Flow"),
    ]:
        fig, ax = plt.subplots()
        ax.plot(plot_df["RecordedAt_dt"], plot_df[y], marker="o")
        ax.set_xlabel("Time")
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        fig.autofmt_xdate()
        st.pyplot(fig, clear_figure=True)

    st.divider()

    st.markdown(
        """
        <div class="card">
          <h3>🔎 RPM–Flow Coupling</h3>
          <p>Scatter plot of RPM vs Flow, colored by r (Delta P / Flow). Helps visualize weakening coupling when r is high.</p>
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
        "Interpretation: Normally, increasing RPM increases Flow. "
        "If RPM rises but Flow does not, an elevated r (ΔP/Flow) suggests increased circuit resistance. "
        "RPM/Flow complements r from a pump-centered perspective."
    )

    st.divider()

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
