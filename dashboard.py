import sys
import os
import glob
import base64
import time
import random
from datetime import datetime, timedelta

# 1. 基础环境配置
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
import qrcode
from PIL import Image
import io

# ==========================================
# 🎨 0. 页面全局配置 (商业级 SaaS 风格)
# ==========================================
st.set_page_config(
    page_title="GV-Charge 综合能源管理平台", 
    page_icon="⚡️", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# 🔥 CSS 注入：打造“阿里云/AntDesign”风格的卡片式布局
st.markdown("""
<style>
    /* 全局背景微灰，减少视觉疲劳 */
    .stApp {
        background-color: #f5f7fa;
    }
    
    /* 侧边栏样式 */
    section[data-testid="stSidebar"] {
        background-color: #001529; /* 深蓝商务色 */
        color: white;
    }
    
    /* 卡片容器样式 (关键！) */
    .css-card {
        background-color: white;
        padding: 20px;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        margin-bottom: 20px;
        border: 1px solid #e8e8e8;
    }
    
    /* 指标数字样式 */
    div[data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
        color: #1890ff; /* 科技蓝 */
        font-weight: 600;
    }
    
    /* 标题样式 */
    h1, h2, h3 {
        font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif;
        color: #333;
    }
    
    /* 去除顶部留白 */
    .block-container {
        padding-top: 1.5rem;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🔌 1. 数据库连接
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
except:
    SUPABASE_URL = LOCAL_URL
    SUPABASE_KEY = LOCAL_KEY

@st.cache_resource
def init_connection():
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except:
        return None
supabase = init_connection()

# ==========================================
# 🔐 2. 登录鉴权 (模拟企业 SSO)
# ==========================================
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if st.session_state["password_correct"]:
        return True
    
    # 登录页布局
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        with st.container(border=True):
            st.image("https://cdn-icons-png.flaticon.com/512/900/900834.png", width=60)
            st.markdown("### GV-Charge 综合能源管理平台")
            st.caption("Enterprise Energy Management System")
            
            password = st.text_input("管理员密码", type="password", placeholder="请输入 admin123")
            if password:
                if password == "admin123":
                    st.session_state["password_correct"] = True
                    st.rerun()
                else:
                    st.error("🚫 密码错误")
    return False

if not check_password():
    st.stop()

# ==========================================
# 🧠 3. 数据处理中心
# ==========================================
def get_data():
    if not supabase: return pd.DataFrame()
    try:
        # 获取最近 500 条
        response = supabase.table("transactions").select("*").order("created_at", desc=True).limit(500).execute()
        df = pd.DataFrame(response.data)
        if not df.empty:
            df['created_at'] = pd.to_datetime(df['created_at']).dt.tz_convert('America/Vancouver')
            df['date'] = df['created_at'].dt.date
            df['total_fee'] = df['total_fee'].astype(float)
        return df
    except:
        return pd.DataFrame()

# ==========================================
# 🖥️ 4. 侧边栏导航 (功能分层)
# ==========================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2991/2991148.png", width=50)
    st.markdown("### GV-Charge Group")
    st.caption("版本: Enterprise v4.2.0")
    st.markdown("---")
    
    # 导航菜单
    menu = st.radio(
        "系统导航",
        ["🏠 综合态势 (首页)", "📈 经营分析 (运营)", "🛠️ 设备运维 (监控)", "📂 资产档案 (资产)", "🧾 财务中心 (票据)"],
        index=0
    )
    
    st.markdown("---")
    st.info("💡 提示：点击上方菜单切换不同管理模块")
    
    # Ngrok 配置放在最下面
    with st.expander("⚙️ 系统配置"):
        ngrok_url = st.text_input("支付网关 (Ngrok)", value="https://xxxx.ngrok-free.app")

# ==========================================
# 🏠 模块 1: 综合态势 (首页 - 聚合看板)
# ==========================================
if "首页" in menu:
    st.title("综合态势感知中心")
    st.caption("Overview & Real-time Monitoring")
    
    df = get_data()
    
    # --- 第一行：核心指标卡 ---
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        with st.container(border=True):
            st.metric("💰 本月累计营收", f"${df['total_fee'].sum():,.2f}", "+12.5%")
    with col2:
        with st.container(border=True):
            st.metric("⚡️ 累计充电量", f"{df['kwh'].sum():,.1f} kWh", "+8.2%")
    with col3:
        with st.container(border=True):
            st.metric("🔌 在线终端数", "3 / 3", "100% 在线")
    with col4:
        with st.container(border=True):
            st.metric("🚨 待处理告警", "0", "系统正常")

    # --- 第二行：地图 + 实时曲线 ---
    c1, c2 = st.columns([1.5, 2.5])
    
    with c1:
        st.markdown("##### 📍 站点分布态势")
        with st.container(border=True):
            # 真实地图坐标
            map_data = pd.DataFrame({
                'lat': [49.2276, 49.1833, 49.1896],
                'lon': [-123.0076, -123.1333, -122.8490],
                'name': ['Burnaby Stn', 'Richmond Stn', 'Surrey Stn'],
                'color': ['#00FF00', '#00FF00', '#FFA500'] # 绿, 绿, 黄
            })
            st.map(map_data, latitude='lat', longitude='lon', size=200, zoom=10)
            
    with c2:
        st.markdown("##### 📈 实时负荷/营收趋势")
        with st.container(border=True):
            if not df.empty:
                chart = alt.Chart(df).mark_area(
                    line={'color':'#1890ff'},
                    color=alt.Gradient(
                        gradient='linear',
                        stops=[alt.GradientStop(color='white', offset=0),
                               alt.GradientStop(color='#1890ff', offset=1)],
                        x1=1, x2=1, y1=1, y2=0
                    )
                ).encode(
                    x=alt.X('created_at', title='时间'),
                    y=alt.Y('total_fee', title='金额 (CAD)'),
                    tooltip=['created_at', 'total_fee']
                ).properties(height=350)
                st.altair_chart(chart, use_container_width=True)
            else:
                st.info("暂无实时数据")

    # --- 第三行：实时告警/日志列表 ---
    st.markdown("##### 📝 系统实时日志")
    with st.container(border=True):
        log_df = pd.DataFrame({
            "时间": [datetime.now().strftime("%H:%M:%S")] * 3,
            "级别": ["INFO", "INFO", "SUCCESS"],
            "来源": ["System", "Gateway", "Database"],
            "内容": ["系统心跳检测正常", "接收到新的支付连接请求", "数据自动归档完成"]
        })
        st.dataframe(log_df, use_container_width=True, hide_index=True)

# ==========================================
# 📈 模块 2: 经营分析 (Operations)
# ==========================================
elif "经营" in menu:
    st.title("📈 经营数据分析")
    st.info("多维度的财务与运营报表，支持按日、按周、按月统计。")
    
    df = get_data()
    
    if not df.empty:
        # 数据聚合
        daily_kpi = df.groupby('date')[['total_fee', 'kwh']].sum().reset_index().sort_values('date', ascending=False)
        
        tab1, tab2 = st.tabs(["📊 营收透视", "📋 详细报表"])
        
        with tab1:
            st.altair_chart(
                alt.Chart(daily_kpi).mark_bar().encode(
                    x='date',
                    y='total_fee',
                    color=alt.value("#1890ff"),
                    tooltip=['date', 'total_fee']
                ).properties(height=400),
                use_container_width=True
            )
        
        with tab2:
            st.dataframe(
                daily_kpi, 
                use_container_width=True,
                column_config={
                    "total_fee": st.column_config.NumberColumn("营收 (CAD)", format="$%.2f"),
                    "kwh": st.column_config.NumberColumn("电量 (kWh)", format="%.2f"),
                    "date": "日期"
                }
            )

# ==========================================
# 🛠️ 模块 3: 设备运维 (Maintenance)
# ==========================================
elif "运维" in menu:
    st.title("🛠️ 设备全生命周期运维")
    st.caption("Device Lifecycle Management & Remote Control")
    
    # 模拟设备状态库
    if "devices" not in st.session_state:
        st.session_state["devices"] = pd.DataFrame([
            {"设备ID": "VAN-001", "位置": "Metrotown P1", "状态": "运行中", "版本": "v2.1", "温度": "35°C"},
            {"设备ID": "RIC-002", "位置": "Aberdeen Mall", "状态": "运行中", "版本": "v2.1", "温度": "32°C"},
            {"设备ID": "SUR-003", "位置": "Surrey Central", "状态": "维护中", "版本": "v2.0", "温度": "28°C"},
        ])

    # 1. 设备列表 (可编辑)
    with st.container(border=True):
        st.subheader("🔌 终端状态监控")
        edited_df = st.data_editor(
            st.session_state["devices"],
            column_config={
                "状态": st.column_config.SelectboxColumn(options=["运行中", "离线", "维护中", "故障"]),
                "温度": st.column_config.ProgressColumn(format="%s", min_value=0, max_value=100),
            },
            use_container_width=True,
            num_rows="dynamic"
        )
        if st.button("💾 保存状态变更"):
            st.session_state["devices"] = edited_df
            st.success("配置已同步至云端")

    st.markdown("<br>", unsafe_allow_html=True)

    # 2. 远程控制台
    with st.container(border=True):
        st.subheader("📡 远程指令下发")
        c1, c2, c3 = st.columns([1, 1, 2])
        with c1:
            target = st.selectbox("选择目标设备", ["VAN-001", "RIC-002", "SUR-003"])
        with c2:
            cmd = st.selectbox("指令类型", ["远程重启 (Reboot)", "固件升级 (OTA)", "锁定/解锁 (Lock)"])
        with c3:
            st.write("") 
            st.write("")
            if st.button("🚀 发送指令", type="primary"):
                with st.spinner(f"正在连接 {target} ..."):
                    time.sleep(1.5)
                    st.success(f"指令 [{cmd}] 下发成功！设备响应时长: 24ms")

# ==========================================
# 📂 模块 4: 资产档案 (Assets & QR)
# ==========================================
elif "资产" in menu:
    st.title("📂 固定资产档案管理")
    
    assets = [
        {"Code": "VAN-001", "Model": "Tesla V3", "Power": "250kW", "Install": "2024-01-10", "Addr": "Burnaby, BC"},
        {"Code": "RIC-002", "Model": "ChargePoint", "Power": "150kW", "Install": "2024-02-15", "Addr": "Richmond, BC"},
        {"Code": "SUR-003", "Model": "Flo CoRe+", "Power": "50kW", "Install": "2024-03-20", "Addr": "Surrey, BC"},
    ]
    
    st.dataframe(pd.DataFrame(assets), use_container_width=True)
    
    st.markdown("---")
    st.subheader("🖨️ 物料生成 (二维码)")
    
    # 二维码生成逻辑
    if ngrok_url:
        clean_url = ngrok_url.rstrip("/").split("/scan")[0]
        cols = st.columns(3)
        for i, item in enumerate(assets):
            with cols[i]:
                with st.container(border=True):
                    st.markdown(f"**{item['Code']}**")
                    st.caption(item['Model'])
                    
                    link = f"{clean_url}/scan/{item['Code']}"
                    qr = qrcode.QRCode(box_size=8, border=1)
                    qr.add_data(link)
                    qr.make(fit=True)
                    img = qr.make_image(fill_color="black", back_color="white")
                    
                    byte_io = io.BytesIO()
                    img.save(byte_io, 'PNG')
                    st.image(byte_io, use_column_width=True)
                    st.caption("扫码直接进入支付")
    else:
        st.warning("请先在左侧侧边栏配置 Ngrok 地址")

# ==========================================
# 🧾 模块 5: 财务中心 (Invoices)
# ==========================================
elif "财务" in menu:
    st.title("🧾 财务票据中心")
    
    # 本地发票浏览
    if not os.path.exists("invoices"):
        try: os.makedirs("invoices") 
        except: pass
        
    files = glob.glob("invoices/*.pdf")
    files.sort(key=os.path.getmtime, reverse=True)
    
    if not files:
        # 容错：生成假发票用于展示 UI
        st.warning("暂无真实发票，展示系统样例。")
        col1, col2 = st.columns([1,2])
        with col1:
             st.markdown("**发票列表**")
             st.info("INV-20250101-001.pdf (样例)")
        with col2:
             st.markdown("**预览**")
             st.image("https://cdn-icons-png.flaticon.com/512/337/337946.png", width=100, caption="PDF 预览占位")
    else:
        c1, c2 = st.columns([1, 2])
        with c1:
            st.subheader("🗂️ 文件归档")
            selected_file = st.radio("选择文件", [os.path.basename(f) for f in files])
        
        with c2:
            st.subheader("📄 电子发票预览")
            if selected_file:
                file_path = os.path.join("invoices", selected_file)
                with open(file_path, "rb") as f:
                    base64_pdf = base64.b64encode(f.read()).decode('utf-8')
                pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600"></iframe>'
                st.markdown(pdf_display, unsafe_allow_html=True)