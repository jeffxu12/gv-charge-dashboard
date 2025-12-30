import sys
import os

# ==========================================
# 1. 强制修复中文和 Emoji 报错 (必须放在最前面)
# ==========================================
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
# ⚡️ Supabase 配置 (混合模式：支持云端 & 本地)
# ==========================================

# 你的 Key (本地运行时使用，作为备用)
LOCAL_URL = "https://fohuvfuhrtdurmnqvrty.supabase.co"
LOCAL_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZvaHV2ZnVocnRkdXJtbnF2cnR5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjY5ODEwNjksImV4cCI6MjA4MjU1NzA2OX0.FkkJGaI4yt6YnkqINMgtHYnRhJBObRysYbVZh-HuUPQ"

# 👇👇👇 【智能切换逻辑】 👇👇👇
try:
    # 尝试从 Streamlit Cloud 的加密柜里拿钥匙
    # 如果本地没有 secrets.toml 文件，这里会直接报错，跳转到 except
    if "supabase" in st.secrets:
        SUPABASE_URL = st.secrets["supabase"]["url"]
        SUPABASE_KEY = st.secrets["supabase"]["key"]
    else:
        # 如果有文件但没配 supabase，也用本地的
        SUPABASE_URL = LOCAL_URL
        SUPABASE_KEY = LOCAL_KEY
except Exception:
    # ⚠️ 只要找不到 secrets 文件（比如在你的 MacBook 上），就自动使用这里的本地钥匙
    # 这样就不会报错了！
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

# 初始化连接 (带缓存)
@st.cache_resource
def init_connection():
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        return None

supabase = init_connection()

# --- 核心数据获取 ---
def get_data():
    if not supabase: return pd.DataFrame()
    try:
        # 抓取数据 (按时间倒序)
        response = supabase.table("transactions").select("*").order("created_at", desc=True).execute()
        if not response.data: return pd.DataFrame()
        return pd.DataFrame(response.data)
    except Exception:
        return pd.DataFrame()

# ==========================================
# 🖥️ 侧边栏：控制台
# ==========================================
with st.sidebar:
    st.header("🎛️ 运营控制台")
    st.caption("Control Panel")
    
    # 1. 自动刷新开关
    auto_refresh = st.toggle('自动刷新 (Auto Refresh)', value=True)
    
    # 2. 场站筛选器
    station_filter = st.selectbox(
        "选择场站 (Select Station)",
        ["All Stations", "VAN-001 (Vancouver)", "RIC-002 (Richmond)"]
    )
    
    st.divider()
    
    # 系统状态展示
    st.info(f"System: 🟢 Online")
    st.caption(f"Last Update: {datetime.now().strftime('%H:%M:%S')}")
    st.caption("📍 Server: Burnaby, BC")

# ==========================================
# 📊 主界面逻辑
# ==========================================
st.title("⚡️ GV-Charge 大温地区运营监控")
st.markdown("### 🇨🇦 Real-time Charging Network")

# 1. 先定义主容器 (这就是之前报错的地方，现在修好了)
placeholder = st.empty()

# 2. 进入循环
while True:
    with placeholder.container():
        # A. 获取数据
        df = get_data()
        
        if not df.empty:
            # --- 数据清洗 ---
            df['created_at'] = pd.to_datetime(df['created_at'])
            
            # 时区转换：UTC -> Vancouver (GMT-7/8)
            if df['created_at'].dt.tz is None:
                df['created_at'] = df['created_at'].dt.tz_localize('UTC')
            df['local_time'] = df['created_at'].dt.tz_convert('America/Vancouver')
            
            df['total_fee'] = df['total_fee'].astype(float)
            df['kwh'] = df['kwh'].astype(float)

            # --- 筛选逻辑 ---
            # 如果侧边栏选了特定场站，这里就进行过滤
            if "VAN-001" in station_filter:
                df = df[df['unit_id'] == "VAN-001"]
            elif "RIC-002" in station_filter:
                df = df[df['unit_id'] == "RIC-002"]

            # B. 顶部 KPI 卡片
            k1, k2, k3, k4 = st.columns(4)
            
            # 计算总额
            total_rev = df['total_fee'].sum()
            total_kwh = df['kwh'].sum()
            avg_price = total_rev / total_kwh if total_kwh > 0 else 0
            
            k1.metric("💰 总营收 (Revenue)", f"${total_rev:,.2f}", delta="实时")
            k2.metric("⚡️ 总电量 (Energy)", f"{total_kwh:,.1f} kWh")
            k3.metric("🧾 订单数 (Orders)", len(df))
            k4.metric("📊 均价 (Avg Price)", f"${avg_price:.2f} /kWh")

            st.divider() # 分割线

            # C. 高级图表区
            c1, c2 = st.columns([2, 1]) # 左边宽，右边窄

            with c1:
                st.subheader("📈 营收增长趋势 (Revenue Trend)")
                # 升级为：面积图 (Area Chart) + 渐变色
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
                st.subheader("📍 站点贡献占比")
                # 升级为：环形图 (Donut Chart)
                pie = alt.Chart(df).mark_arc(innerRadius=50).encode(
                    theta=alt.Theta(field="total_fee", aggregate="sum"),
                    color=alt.Color(field="unit_id", title="Station ID"),
                    tooltip=['unit_id', 'sum(total_fee)', 'count()']
                ).properties(height=350)
                st.altair_chart(pie, use_container_width=True)

            # D. 详细数据表 (美化版)
            st.subheader("📝 最新交易明细 (Latest Transactions)")
            
            # 选取展示列
            view_df = df[['local_time', 'unit_id', 'location', 'total_fee', 'kwh', 'status']].copy()
            view_df = view_df.sort_values('local_time', ascending=False).head(8)
            
            # 格式化
            view_df['local_time'] = view_df['local_time'].dt.strftime('%Y-%m-%d %H:%M:%S')
            view_df['total_fee'] = view_df['total_fee'].apply(lambda x: f"${x:.2f}")
            view_df['kwh'] = view_df['kwh'].apply(lambda x: f"{x:.2f} kWh")
            
            st.dataframe(
                view_df, 
                use_container_width=True,
                hide_index=True,
                column_config={
                    "status": st.column_config.TextColumn(
                        "Status",
                        help="订单状态",
                        validate="^finished$", # 高亮 finished 状态
                    )
                }
            )

        else:
            # 空数据状态
            st.warning("📡 系统在线，等待数据接入...")
            st.info("💡 请确保 `python3 charge_point.py` 正在运行并产生数据。")

    # 控制刷新频率
    if auto_refresh:
        time.sleep(2)
    else:
        # 如果关闭了自动刷新，就停止循环，显示一个按钮
        st.button("🔄 手动刷新 (Click to Refresh)")
        break