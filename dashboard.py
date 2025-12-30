import sys
import os

# 1. 强制修复中文和 Emoji 报错
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["LANG"] = "en_US.UTF-8"

import streamlit as st
import pandas as pd
import altair as alt
from supabase import create_client
import time
from datetime import datetime

# ==========================================
# ⚡️ Supabase 配置
# ==========================================
LOCAL_URL = "https://fohuvfuhrtdurmnqvrty.supabase.co"
LOCAL_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZvaHV2ZnVocnRkdXJtbnF2cnR5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjY5ODEwNjksImV4cCI6MjA4MjU1NzA2OX0.FkkJGaI4yt6YnkqINMgtHYnRhJBObRysYbVZh-HuUPQ"

try:
    if "supabase" in st.secrets:
        SUPABASE_URL = st.secrets["supabase"]["url"]
        SUPABASE_KEY = st.secrets["supabase"]["key"]
    else:
        SUPABASE_URL = LOCAL_URL
        SUPABASE_KEY = LOCAL_KEY
except Exception:
    SUPABASE_URL = LOCAL_URL
    SUPABASE_KEY = LOCAL_KEY

# ==========================================
# 🎨 页面设置
# ==========================================
st.set_page_config(
    page_title="GV-Charge 运营中心", 
    page_icon="⚡️", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# 初始化连接
@st.cache_resource
def init_connection():
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        return None

supabase = init_connection()

# 获取数据
def get_data():
    if not supabase: return pd.DataFrame()
    try:
        response = supabase.table("transactions").select("*").order("created_at", desc=True).execute()
        if not response.data: return pd.DataFrame()
        return pd.DataFrame(response.data)
    except Exception:
        return pd.DataFrame()

# ==========================================
# 🖥️ 侧边栏
# ==========================================
with st.sidebar:
    st.header("🎛️ 运营控制台")
    st.caption("Control Panel")
    
    # 自动刷新开关
    auto_refresh = st.toggle('自动刷新 (Auto Refresh)', value=True)
    
    # 场站筛选
    station_filter = st.selectbox(
        "选择场站 (Select Station)",
        ["All Stations", "VAN-001 (Vancouver)", "RIC-002 (Richmond)"]
    )
    
    st.divider()
    st.info(f"System: 🟢 Online")
    st.caption(f"Update: {datetime.now().strftime('%H:%M:%S')}")

# ==========================================
# 📊 主界面 (已移除 while True 循环)
# ==========================================
st.title("⚡️ GV-Charge 大温地区运营监控")
st.markdown("### 🇨🇦 Real-time Charging Network")

# A. 获取数据
df = get_data()

if not df.empty:
    # --- 数据清洗 ---
    df['created_at'] = pd.to_datetime(df['created_at'])
    if df['created_at'].dt.tz is None:
        df['created_at'] = df['created_at'].dt.tz_localize('UTC')
    df['local_time'] = df['created_at'].dt.tz_convert('America/Vancouver')
    
    df['total_fee'] = df['total_fee'].astype(float)
    df['kwh'] = df['kwh'].astype(float)

    # --- 筛选 ---
    if "VAN-001" in station_filter:
        df = df[df['unit_id'] == "VAN-001"]
    elif "RIC-002" in station_filter:
        df = df[df['unit_id'] == "RIC-002"]

    # B. KPI
    k1, k2, k3, k4 = st.columns(4)
    total_rev = df['total_fee'].sum()
    total_kwh = df['kwh'].sum()
    avg_price = total_rev / total_kwh if total_kwh > 0 else 0
    
    k1.metric("💰 总营收", f"${total_rev:,.2f}")
    k2.metric("⚡️ 总电量", f"{total_kwh:,.1f} kWh")
    k3.metric("🧾 订单数", len(df))
    k4.metric("📊 均价", f"${avg_price:.2f} /kWh")

    st.divider()

    # C. 图表
    c1, c2 = st.columns([2, 1])

    with c1:
        st.subheader("📈 营收趋势")
        chart = alt.Chart(df.tail(100)).mark_area(
            line={'color':'darkorange'},
            color=alt.Gradient(
                gradient='linear',
                stops=[alt.GradientStop(color='white', offset=0),
                       alt.GradientStop(color='darkorange', offset=1)],
                x1=1, x2=1, y1=1, y2=0
            )
        ).encode(
            x=alt.X('local_time', title='Time', axis=alt.Axis(format='%H:%M')),
            y=alt.Y('total_fee', title='Fee ($)'),
            tooltip=['local_time', 'total_fee', 'unit_id']
        ).properties(height=350)
        st.altair_chart(chart, use_container_width=True)

    with c2:
        st.subheader("📍 站点占比")
        pie = alt.Chart(df).mark_arc(innerRadius=50).encode(
            theta=alt.Theta(field="total_fee", aggregate="sum"),
            color=alt.Color(field="unit_id", title="Station ID"),
            tooltip=['unit_id', 'sum(total_fee)']
        ).properties(height=350)
        st.altair_chart(pie, use_container_width=True)

    # D. 表格
    st.subheader("📝 交易明细")
    view_df = df[['local_time', 'unit_id', 'location', 'total_fee', 'kwh', 'status']].copy()
    view_df = view_df.sort_values('local_time', ascending=False).head(8)
    view_df['local_time'] = view_df['local_time'].dt.strftime('%Y-%m-%d %H:%M:%S')
    view_df['total_fee'] = view_df['total_fee'].apply(lambda x: f"${x:.2f}")
    view_df['kwh'] = view_df['kwh'].apply(lambda x: f"{x:.2f} kWh")
    
    st.dataframe(view_df, use_container_width=True, hide_index=True)

else:
    st.warning("📡 等待数据接入... 请确保本地 python3 charge_point.py 正在运行")

# ==========================================
# 🔄 关键修改：用 st.rerun() 替代 while 循环
# ==========================================
if auto_refresh:
    time.sleep(2) # 等待2秒
    st.rerun()    # 重新运行整个脚本 (告诉服务器：我跑完了，再来一次！)