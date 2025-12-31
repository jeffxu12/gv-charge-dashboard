import sys
import os

# 1. 基础环境修复
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
# 🎨 页面配置 (Admin 风格)
# ==========================================
st.set_page_config(
    page_title="GV-Charge Admin Pro", 
    page_icon="🛡️", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# 初始化数据库连接
@st.cache_resource
def init_connection():
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        return None

supabase = init_connection()

# ==========================================
# 🔐 1. 登录系统 (修复版 - 更加稳健)
# ==========================================
def check_password():
    """Returns `True` if the user had a correct password."""
    
    # 初始化登录状态
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    # 如果已经登录成功，直接返回 True
    if st.session_state["password_correct"]:
        return True

    # 显示登录框
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown("### 🛡️ GV-Charge 管理后台")
        st.info("请输入管理员密码以继续")
        password = st.text_input("Password:", type="password")
        
        if password:
            if password == "admin123":
                st.session_state["password_correct"] = True
                st.rerun()  # 登录成功立刻刷新
            else:
                st.error("❌ 密码错误")
    
    return False

# 🛑 如果密码不对，直接停止运行下面的代码
if not check_password():
    st.stop()

# ==========================================
# 🧠 数据获取与处理
# ==========================================
def get_transactions():
    if not supabase: return pd.DataFrame()
    try:
        response = supabase.table("transactions").select("*").order("created_at", desc=True).execute()
        if not response.data: return pd.DataFrame()
        df = pd.DataFrame(response.data)
        # 清洗
        df['created_at'] = pd.to_datetime(df['created_at'])
        if df['created_at'].dt.tz is None:
            df['created_at'] = df['created_at'].dt.tz_localize('UTC')
        df['local_time'] = df['created_at'].dt.tz_convert('America/Vancouver')
        
        # 确保数值类型正确
        df['total_fee'] = df['total_fee'].astype(float)
        df['kwh'] = df['kwh'].astype(float)
        return df
    except Exception:
        return pd.DataFrame()

# ==========================================
# 🖥️ 侧边栏：全局控制
# ==========================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/900/900834.png", width=50)
    st.title("Admin Pro")
    st.success(f"🟢 Online: SuperAdmin")
    st.caption(f"Region: Metro Vancouver")
    
    st.divider()
    
    # 导航模式
    page_mode = st.radio("系统模块 (Modules)", ["📊 监控大屏 (Dashboard)", "🛠️ 设备运维 (Device Ops)", "💰 财务报表 (Finance)"])
    
    st.divider()
    if st.button("🚪 退出登录 (Logout)"):
        st.session_state["password_correct"] = False
        st.rerun()

# ==========================================
# 📊 模块 1：监控大屏 (Dashboard)
# ==========================================
if page_mode == "📊 监控大屏 (Dashboard)":
    st.title("📊 运营监控中心")
    
    # 自动刷新逻辑
    if st.toggle('🔴 实时自动刷新 (Live Refresh)', value=True):
        time.sleep(3)
        st.rerun()

    df = get_transactions()
    
    if not df.empty:
        # KPI Row
        col1, col2, col3, col4 = st.columns(4)
        total_rev = df['total_fee'].sum()
        # 计算今日营收
        today = datetime.now().date()
        today_rev = df[df['local_time'].dt.date == today]['total_fee'].sum()
        
        col1.metric("💰 总营收 (Lifetime)", f"${total_rev:,.2f}")
        col2.metric("📅 今日营收 (Today)", f"${today_rev:,.2f}")
        col3.metric("🔌 活跃站点", df['unit_id'].nunique())
        col4.metric("🚨 系统状态", "Normal")

        st.divider()

        # Charts Row
        c1, c2 = st.columns([2, 1])
        with c1:
            st.subheader("📈 营收趋势 (Revenue Trend)")
            chart = alt.Chart(df.tail(100)).mark_area(
                line={'color':'darkblue'},
                color=alt.Gradient(
                    gradient='linear',
                    stops=[alt.GradientStop(color='white', offset=0),
                           alt.GradientStop(color='darkblue', offset=1)],
                    x1=1, x2=1, y1=1, y2=0
                )
            ).encode(
                x=alt.X('local_time', format='%H:%M', title="Time"),
                y='total_fee',
                tooltip=['local_time', 'total_fee']
            ).properties(height=350)
            st.altair_chart(chart, use_container_width=True)
            
        with c2:
            st.subheader("📍 站点分布 (Station Share)")
            pie = alt.Chart(df).mark_arc(innerRadius=60).encode(
                theta='sum(total_fee)',
                color='unit_id',
                tooltip=['unit_id', 'sum(total_fee)']
            ).properties(height=350)
            st.altair_chart(pie, use_container_width=True)

# ==========================================
# 🛠️ 模块 2：设备运维 (Device Ops)
# ==========================================
elif page_mode == "🛠️ 设备运维 (Device Ops)":
    st.title("🛠️ 设备全生命周期管理")
    st.info("💡 提示：管理员可在此手动修改设备状态，或下发远程指令。")

    # 1. 模拟设备数据 (用 Session State 保持修改)
    if "device_status" not in st.session_state:
        st.session_state["device_status"] = pd.DataFrame([
            {"Unit ID": "VAN-001", "Location": "Burnaby, Metrotown", "Status": "Online", "Health": 98, "Version": "v1.2.0"},
            {"Unit ID": "RIC-002", "Location": "Richmond, Aberdeen", "Status": "Online", "Health": 95, "Version": "v1.2.0"},
            {"Unit ID": "SUR-003", "Location": "Surrey, Central", "Status": "Maintenance", "Health": 45, "Version": "v1.0.1"},
        ])

    # 2. 交互式编辑器
    st.subheader("🔌 充电桩状态控制台")
    
    edited_df = st.data_editor(
        st.session_state["device_status"],
        column_config={
            "Health": st.column_config.ProgressColumn(
                "Health Score", format="%d%%", min_value=0, max_value=100
            ),
            "Status": st.column_config.SelectboxColumn(
                "System Status",
                options=["Online", "Offline", "Maintenance", "Faulted"],
                required=True
            )
        },
        num_rows="dynamic",
        use_container_width=True
    )

    if st.button("💾 保存状态变更 (Save to Cloud)"):
        st.session_state["device_status"] = edited_df
        st.toast("✅ 设备状态已同步成功！", icon="☁️")
        
    st.divider()
    
    # 3. 远程命令下发
    st.subheader("📡 远程指令中心 (Command Center)")
    col1, col2 = st.columns(2)
    with col1:
        target_unit = st.selectbox("选择目标设备", ["VAN-001", "RIC-002", "SUR-003"])
    with col2:
        action = st.selectbox("选择操作指令", ["Remote Reset (软重启)", "Unlock Connector (解锁枪头)", "Firmware Update (固件升级)"])
        
    if st.button("🚀 发送指令 (Execute)"):
        with st.spinner(f"正在连接 {target_unit}..."):
            time.sleep(1.5)
            st.success(f"✅ 指令 [{action}] 已发送至 {target_unit}。设备响应正常。")

# ==========================================
# 💰 模块 3：财务报表 (Finance)
# ==========================================
elif page_mode == "💰 财务报表 (Finance)":
    st.title("💰 财务对账系统")
    
    df = get_transactions()
    
    if not df.empty:
        st.subheader("📊 月度营收详情")
        
        # 简单的数据处理
        df['Date'] = df['local_time'].dt.date
        daily_report = df.groupby('Date')[['total_fee', 'kwh']].sum().sort_index(ascending=False)
        
        # 展示表格
        st.dataframe(
            daily_report,
            use_container_width=True,
            column_config={
                "total_fee": st.column_config.NumberColumn("Revenue (CAD)", format="$%.2f"),
                "kwh": st.column_config.NumberColumn("Energy (kWh)", format="%.2f kWh"),
            }
        )
        
        # 下载按钮
        st.download_button(
            label="📥 导出 Excel 报表 (CSV)",
            data=daily_report.to_csv().encode('utf-8'),
            file_name='financial_report.csv',
            mime='text/csv',
        )
    else:
        st.warning("暂无交易数据，请先进行模拟充电。")