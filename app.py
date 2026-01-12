import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="ECMO Flow Analyzer", layout="wide")
st.title("ECMO Flow Analyzer (Test v1)")
st.caption("輸入 ECMO Flow / RPM / ΔP / Hb / Sugar → 自動計算指標 → 以 Flow 為 X 軸畫 3 張關係圖")

# ---------- Session state ----------
if "data" not in st.session_state:
    st.session_state.data = pd.DataFrame(
        columns=["Flow", "RPM", "DeltaP", "Hb", "Sugar",
                 "DP_Flow", "DP_Flow_Hb", "DP_Flow_Hb_Sugar"]
    )

# ---------- Input ----------
with st.form("input_form", clear_on_submit=False):
    c1, c2, c3, c4, c5 = st.columns(5)
    flow = c1.number_input("ECMO Flow (L/min)", min_value=0.1, value=4.5, step=0.1)
    rpm = c2.number_input("RPM", min_value=0, value=3200, step=10)
    delta_p = c3.number_input("Delta P (mmHg)", min_value=0.1, value=55.0, step=0.5)
    hb = c4.number_input("Hb (g/dL)", min_value=0.1, value=10.8, step=0.1)
    sugar = c5.number_input("Sugar (mg/dL)", min_value=1.0, value=145.0, step=1.0)

    add = st.form_submit_button("新增一筆資料")

def compute_metrics(flow, delta_p, hb, sugar):
    dp_flow = delta_p / flow
    dp_flow_hb = dp_flow / hb
    dp_flow_hb_sugar = dp_flow_hb / sugar
    return dp_flow, dp_flow_hb, dp_flow_hb_sugar

if add:
    dp_flow, dp_flow_hb, dp_flow_hb_sugar = compute_metrics(flow, delta_p, hb, sugar)
    new_row = {
        "Flow": float(flow),
        "RPM": int(rpm),
        "DeltaP": float(delta_p),
        "Hb": float(hb),
        "Sugar": float(sugar),
        "DP_Flow": float(dp_flow),
        "DP_Flow_Hb": float(dp_flow_hb),
        "DP_Flow_Hb_Sugar": float(dp_flow_hb_sugar),
    }
    st.session_state.data = pd.concat(
        [st.session_state.data, pd.DataFrame([new_row])],
        ignore_index=True
    )

# ---------- Controls ----------
ctrl1, ctrl2, ctrl3 = st.columns([1, 1, 3])
with ctrl1:
    if st.button("刪除最後一筆") and len(st.session_state.data) > 0:
        st.session_state.data = st.session_state.data.iloc[:-1].reset_index(drop=True)
with ctrl2:
    if st.button("清空全部資料"):
        st.session_state.data = st.session_state.data.iloc[0:0]

# ---------- Table ----------
st.subheader("資料表（每列一筆）")
df = st.session_state.data.copy()

if len(df) == 0:
    st.info("目前沒有資料。請先新增一筆。")
    st.stop()

# 顯示時做一點格式化
show_df = df.copy()
for col in ["DP_Flow", "DP_Flow_Hb", "DP_Flow_Hb_Sugar"]:
    show_df[col] = show_df[col].map(lambda x: f"{x:.5f}")
st.dataframe(show_df, use_container_width=True)

# ---------- Plots vs Flow ----------
st.subheader("關係圖（X 軸：Flow）")

df_sorted = df.sort_values("Flow")

def scatter_plot(x, y, xlabel, ylabel, title):
    fig, ax = plt.subplots()
    ax.scatter(x, y)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    st.pyplot(fig, clear_figure=True)

p1, p2, p3 = st.columns(3)

with p1:
    scatter_plot(
        df_sorted["Flow"], df_sorted["DP_Flow"],
        "Flow (L/min)", "ΔP / Flow",
        "Flow vs ΔP/Flow"
    )

with p2:
    scatter_plot(
        df_sorted["Flow"], df_sorted["DP_Flow_Hb"],
        "Flow (L/min)", "ΔP / Flow / Hb",
        "Flow vs ΔP/Flow/Hb"
    )

with p3:
    scatter_plot(
        df_sorted["Flow"], df_sorted["DP_Flow_Hb_Sugar"],
        "Flow (L/min)", "ΔP / Flow / Hb / Sugar",
        "Flow vs ΔP/Flow/Hb/Sugar"
    )

# ---------- Export ----------
st.divider()
st.subheader("匯出")
csv = df.to_csv(index=False).encode("utf-8")
st.download_button("下載 CSV", data=csv, file_name="ecmo_flow_data.csv", mime="text/csv")
