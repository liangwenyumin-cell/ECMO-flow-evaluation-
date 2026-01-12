import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

st.set_page_config(page_title="ECMO Trend Analyzer", layout="wide")
st.title("ECMO Trend Analyzer (Test)")
st.caption("手動輸入日期時間（可回填）＋計算 r=ΔP/Flow ＋ 趨勢圖（時間 vs ΔP、r）")

# -------------------------
# Session state: data store
# -------------------------
COLUMNS = [
    "RecordedAt",          # user-entered datetime (for backfilling)
    "Flow", "RPM", "DeltaP", "Hb",
    "Sugar_mmol", "Sugar_mg_dL",
    "r"                    # r = DeltaP / Flow
]

if "data" not in st.session_state:
    st.session_state.data = pd.DataFrame(columns=COLUMNS)

# -------------------------
# Input form
# -------------------------
with st.form("input_form", clear_on_submit=False):
    # Date/time input (stable on iPad)
    t1, t2 = st.columns(2)
    rec_date = t1.date_input("日期", value=datetime.now().date())
    rec_time = t2.time_input("時間", value=datetime.now().time().replace(second=0, microsecond=0))
    recorded_at = datetime.combine(rec_date, rec_time)

    c1, c2, c3, c4, c5 = st.columns(5)
    flow = c1.number_input("ECMO Flow (L/min)", min_value=0.1, value=4.5, step=0.1)
    rpm = c2.number_input("RPM", min_value=0, value=3200, step=10)
    delta_p = c3.number_input("Delta P (mmHg)", min_value=0.1, value=55.0, step=0.5)
    hb = c4.number_input("Hb (g/dL)", min_value=0.1, value=10.8, step=0.1)
    sugar_mmol = c5.number_input("Sugar (mmol/L)", min_value=0.1, value=8.0, step=0.1)

    add = st.form_submit_button("新增一筆資料")

# -------------------------
# Add row
# -------------------------
def compute_r(delta_p_val: float, flow_val: float) -> float:
    return delta_p_val / flow_val

if add:
    sugar_mg_dl = sugar_mmol * 18.0
    r_val = compute_r(delta_p, flow)

    new_row = {
        "RecordedAt": recorded_at.isoformat(timespec="minutes"),
        "Flow": float(flow),
        "RPM": int(rpm),
        "DeltaP": float(delta_p),
        "Hb": float(hb),
        "Sugar_mmol": float(sugar_mmol),
        "Sugar_mg_dL": float(sugar_mg_dl),
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
    if st.button("刪除最後一筆") and len(st.session_state.data) > 0:
        st.session_state.data = st.session_state.data.iloc[:-1].reset_index(drop=True)
with ctrl2:
    if st.button("清空全部資料"):
        st.session_state.data = st.session_state.data.iloc[0:0]

# -------------------------
# Table
# -------------------------
st.subheader("資料表（每列一筆）")
df = st.session_state.data.copy()

if len(df) == 0:
    st.info("目前沒有資料。請先新增一筆。")
    st.stop()

# Format for display
show_df = df.copy()
show_df["RecordedAt"] = pd.to_datetime(show_df["RecordedAt"], errors="coerce").dt.strftime("%Y-%m-%d %H:%M")
show_df["r"] = show_df["r"].map(lambda x: f"{x:.4f}")
show_df["Sugar_mg_dL"] = show_df["Sugar_mg_dL"].map(lambda x: f"{x:.1f}")
st.dataframe(show_df, use_container_width=True)

# -------------------------
# Trend plots: X = time
# -------------------------
st.subheader("趨勢圖（X 軸：時間）")

plot_df = df.copy()
plot_df["RecordedAt_dt"] = pd.to_datetime(plot_df["RecordedAt"], errors="coerce")
plot_df = plot_df.dropna(subset=["RecordedAt_dt"]).sort_values("RecordedAt_dt")

if len(plot_df) < 2:
    st.warning("目前可用的時間點少於 2 筆，趨勢圖會比較不明顯。建議多新增幾筆資料。")

p1, p2 = st.columns(2)

with p1:
    fig, ax = plt.subplots()
    ax.plot(plot_df["RecordedAt_dt"], plot_df["DeltaP"], marker="o")
    ax.set_xlabel("Time")
    ax.set_ylabel("Delta P (mmHg)")
    ax.set_title("Delta P Trend")
    fig.autofmt_xdate()
    st.pyplot(fig, clear_figure=True)

with p2:
    fig, ax = plt.subplots()
    ax.plot(plot_df["RecordedAt_dt"], plot_df["r"], marker="o")
    ax.set_xlabel("Time")
    ax.set_ylabel("r = DeltaP / Flow")
    ax.set_title("r Trend")
    fig.autofmt_xdate()
    st.pyplot(fig, clear_figure=True)

# -------------------------
# Export
# -------------------------
st.divider()
st.subheader("匯出")
csv = df.to_csv(index=False).encode("utf-8")
st.download_button("下載 CSV", data=csv, file_name="ecmo_trend_data.csv", mime="text/csv")
