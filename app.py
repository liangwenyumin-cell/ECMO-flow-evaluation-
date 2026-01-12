import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from scipy.stats import pearsonr, spearmanr
import uuid

# -------------------------
# Page config + simple UI CSS
# -------------------------
st.set_page_config(page_title="ECMO Trend Analyzer", layout="wide")

st.markdown(
    """
    <style>
      .big-title {font-size: 28px; font-weight: 700; margin-bottom: 6px;}
      .big-caption {font-size: 14px; color: #666; margin-bottom: 14px;}
      label, .stTextInput label, .stNumberInput label, .stDateInput label, .stTimeInput label {
        font-size: 16px !important;
      }
      .stNumberInput input, .stTextInput input {
        font-size: 18px !important;
      }
      .stButton button {
        font-size: 16px !important;
        padding: 10px 14px !important;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="big-title">ECMO Trend Analyzer</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="big-caption">Backfillable date/time • r = Delta P / Flow • Trends • RPM–Flow coupling (colored by r) • Correlations • CSV restore</div>',
    unsafe_allow_html=True
)

# -------------------------
# Data schema
# -------------------------
COLUMNS = [
    "ID",
    "RecordedAt",
    "Flow", "RPM", "DeltaP", "Hb",
    "Glucose_mmol", "Glucose_mg_dL",
    "r",
    "RPM_per_Flow",
]

def ensure_schema(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure all expected columns exist; create ID if missing."""
    if df is None or len(df) == 0:
        return pd.DataFrame(columns=COLUMNS)

    for col in COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA

    # Create IDs if missing
    if df["ID"].isna().any() or (df["ID"].astype(str).str.len() == 0).any():
        df["ID"] = df["ID"].apply(lambda x: x if pd.notna(x) and str(x).strip() else str(uuid.uuid4())[:8])

    # Keep only columns we need, in order
    return df[COLUMNS].copy()

# -------------------------
# Session state
# -------------------------
if "data" not in st.session_state:
    st.session_state.data = pd.DataFrame(columns=COLUMNS)

st.session_state.data = ensure_schema(st.session_state.data)

# -------------------------
# Page selector (2nd page for charts)
# -------------------------
page = st.radio("Page", ["Data Entry & Records", "Charts & Analysis"], horizontal=True)

# =========================
# PAGE 1: Data entry + records
# =========================
if page == "Data Entry & Records":

    # ---- CSV Restore (Option A) ----
    st.subheader("Data Persistence (CSV Restore)")
    st.caption("To prevent data loss after refresh/closing the tab: download CSV regularly and restore via CSV upload.")
    uploaded = st.file_uploader("Restore from CSV", type=["csv"])
    if uploaded is not None:
        try:
            loaded = pd.read_csv(uploaded)
            loaded = ensure_schema(loaded)

            # Basic sanity: must have key columns
            required_cols = {"RecordedAt", "Flow", "RPM", "DeltaP", "Hb", "Glucose_mmol", "r"}
            if not required_cols.issubset(set(loaded.columns)):
                st.error("CSV format mismatch. Please upload a CSV exported from this app.")
            else:
                st.session_state.data = loaded
                st.success(f"Restored {len(loaded)} records from CSV. You can continue adding records now.")
        except Exception as e:
            st.error(f"Failed to load CSV: {e}")

    st.divider()

    # ---- Data Entry (Vertical, bigger) ----
    st.subheader("Add Record (Backfillable)")

    with st.form("input_form", clear_on_submit=False):
        rec_date = st.date_input("Date", value=datetime.now().date())
        rec_time = st.time_input("Time", value=datetime.now().time().replace(second=0, microsecond=0))
        recorded_at = datetime.combine(rec_date, rec_time)

        flow = st.number_input("ECMO Flow (L/min)", min_value=0.1, value=4.5, step=0.1)
        rpm = st.number_input("Pump RPM", min_value=0, value=3200, step=10)

        # Delta P integer
        delta_p = st.number_input("Delta P (mmHg)", min_value=0, value=55, step=1, format="%d")

        # Hb 1 decimal
        hb = st.number_input("Hemoglobin (g/dL)", min_value=0.0, value=10.8, step=0.1, format="%.1f")

        # Glucose 1 decimal mmol/L
        glucose_mmol = st.number_input("Glucose (mmol/L)", min_value=0.0, value=8.0, step=0.1, format="%.1f")

        add = st.form_submit_button("Add record")

    def compute_r(dp: float, fl: float) -> float:
        return dp / fl

    if add:
        glucose_mg_dl = float(glucose_mmol) * 18.0
        r_val = compute_r(float(delta_p), float(flow))
        rpm_per_flow = float(rpm) / float(flow)

        new_row = {
            "ID": str(uuid.uuid4())[:8],
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

        try:
            st.toast("Record added. Tip: Download CSV to avoid losing data on refresh/close.", icon="💾")
        except Exception:
            st.info("Record added. Tip: Download CSV to avoid losing data on refresh/close.")

    st.divider()

    # ---- Editable records table ----
    st.subheader("Records (Editable)")
    st.caption("Edit values directly below, then click **Save changes**. IDs are hidden but used for safe delete/restore.")

    df = ensure_schema(st.session_state.data)

    # Show friendly time for display (but keep original in data)
    df_display = df.copy()
    df_display["RecordedAt"] = pd.to_datetime(df_display["RecordedAt"], errors="coerce").dt.strftime("%Y-%m-%d %H:%M")

    edited = st.data_editor(
        df_display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "ID": st.column_config.TextColumn("ID", disabled=True, help="Internal record key"),
            "RecordedAt": st.column_config.TextColumn("RecordedAt (YYYY-MM-DD HH:MM)", help="Backfilled time of record"),
            "DeltaP": st.column_config.NumberColumn("DeltaP (mmHg)", step=1, format="%d"),
            "Hb": st.column_config.NumberColumn("Hb (g/dL)", step=0.1, format="%.1f"),
            "Glucose_mmol": st.column_config.NumberColumn("Glucose (mmol/L)", step=0.1, format="%.1f"),
        }
    )

    # Save changes button (explicit, avoids accidental edits)
    if st.button("Save changes"):
        try:
            # Convert back: RecordedAt text -> ISO string
            saved = edited.copy()

            # Attempt to parse displayed RecordedAt into ISO minutes
            parsed = pd.to_datetime(saved["RecordedAt"], errors="coerce")
            if parsed.isna().any():
                st.error("Some RecordedAt values could not be parsed. Use format YYYY-MM-DD HH:MM.")
            else:
                saved["RecordedAt"] = parsed.dt.strftime("%Y-%m-%dT%H:%M")

                # Enforce types / recompute derived fields (r, glucose_mg_dL, rpm_per_flow)
                saved["Flow"] = pd.to_numeric(saved["Flow"], errors="coerce")
                saved["RPM"] = pd.to_numeric(saved["RPM"], errors="coerce")
                saved["DeltaP"] = pd.to_numeric(saved["DeltaP"], errors="coerce").round(0).astype("Int64")
                saved["Hb"] = pd.to_numeric(saved["Hb"], errors="coerce")
                saved["Glucose_mmol"] = pd.to_numeric(saved["Glucose_mmol"], errors="coerce")

                # Recompute derived columns safely
                saved["Glucose_mg_dL"] = saved["Glucose_mmol"] * 18.0
                saved["r"] = saved["DeltaP"].astype(float) / saved["Flow"].astype(float)
                saved["RPM_per_Flow"] = saved["RPM"].astype(float) / saved["Flow"].astype(float)

                # Keep schema + drop rows with missing essentials
                saved = ensure_schema(saved)
                essentials = ["RecordedAt", "Flow", "RPM", "DeltaP"]
                if saved[essentials].isna().any().any():
                    st.error("Some required fields are missing after edit (RecordedAt/Flow/RPM/DeltaP). Please fix and save again.")
                else:
                    st.session_state.data = saved
                    st.success("Changes saved.")
        except Exception as e:
            st.error(f"Failed to save changes: {e}")

    st.divider()

    # ---- Delete with confirmation ----
    st.subheader("Delete Record (with confirmation)")
    df_now = ensure_schema(st.session_state.data).copy()
    df_now["RecordedAt_disp"] = pd.to_datetime(df_now["RecordedAt"], errors="coerce").dt.strftime("%Y-%m-%d %H:%M")

    # A readable selector: time + ID + key values
    options = df_now.apply(
        lambda r: f'{r["RecordedAt_disp"]} | ID={r["ID"]} | Flow={r["Flow"]} | RPM={r["RPM"]} | ΔP={r["DeltaP"]}',
        axis=1
    ).tolist()

    if len(options) == 0:
        st.info("No records to delete.")
    else:
        sel = st.selectbox("Select a record to delete", options)
        sel_idx = options.index(sel)
        sel_id = df_now.iloc[sel_idx]["ID"]

        confirm = st.checkbox("Yes, I want to delete this record", value=False)
        if st.button("Delete selected record"):
            if not confirm:
                st.warning("Please confirm deletion by ticking the checkbox.")
            else:
                st.session_state.data = df_now[df_now["ID"] != sel_id].drop(columns=["RecordedAt_disp"], errors="ignore").reset_index(drop=True)
                st.success("Record deleted.")

    st.divider()

    # ---- Export ----
    st.subheader("Export")
    csv = ensure_schema(st.session_state.data).to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", data=csv, file_name="ecmo_trend_data.csv", mime="text/csv")


# =========================
# PAGE 2: Charts + analysis (bigger)
# =========================
else:
    df = ensure_schema(st.session_state.data).copy()

    if len(df) == 0:
        st.info("No data yet. Go to 'Data Entry & Records' to add records.")
        st.stop()

    # Prep time ordering
    df["RecordedAt_dt"] = pd.to_datetime(df["RecordedAt"], errors="coerce")
    plot_df = df.dropna(subset=["RecordedAt_dt"]).sort_values("RecordedAt_dt")

    st.subheader("Trends (X-axis: Time)")

    # One large chart per row (bigger)
    fig, ax = plt.subplots()
    ax.plot(plot_df["RecordedAt_dt"], plot_df["DeltaP"], marker="o")
    ax.set_xlabel("Time")
    ax.set_ylabel("Delta P (mmHg)")
    ax.set_title("Delta P Trend Over Time")
    fig.autofmt_xdate()
    st.pyplot(fig, clear_figure=True)

    fig, ax = plt.subplots()
    ax.plot(plot_df["RecordedAt_dt"], plot_df["r"], marker="o")
    ax.set_xlabel("Time")
    ax.set_ylabel("r (Delta P / Flow)")
    ax.set_title("r Trend Over Time")
    fig.autofmt_xdate()
    st.pyplot(fig, clear_figure=True)

    fig, ax = plt.subplots()
    ax.plot(plot_df["RecordedAt_dt"], plot_df["RPM_per_Flow"], marker="o")
    ax.set_xlabel("Time")
    ax.set_ylabel("RPM / Flow")
    ax.set_title("RPM / Flow Trend Over Time")
    fig.autofmt_xdate()
    st.pyplot(fig, clear_figure=True)

    st.divider()

    st.subheader("RPM–Flow Coupling (Color-coded by r)")

    fig, ax = plt.subplots()
    sc = ax.scatter(plot_df["RPM"], plot_df["Flow"], c=plot_df["r"], cmap="viridis")
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

    st.divider()

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

    corr_block(df["Hb"], df["r"], "Hemoglobin (g/dL)", "r (Delta P / Flow)")
    corr_block(df["Glucose_mmol"], df["r"], "Glucose (mmol/L)", "r (Delta P / Flow)")
