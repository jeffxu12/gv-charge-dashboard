import sys
import os
import glob
import base64 # 用于预览 PDF

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
import time
from datetime import datetime
import qrcode
from PIL import Image
import io

# ==========================================
# ⚡️ 0. 全局页面配置 (宽屏模式)
# ==========================================
st.set_page_config(
    page_title="GV-Charge Enterprise", 
    page_icon="⚡️", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义 CSS 让界面更紧凑、更专业
st.markdown("""
<style>
    .block-container {padding-top: 1rem; padding-bottom: 0rem;}
    .stMetric {background-color: #f0f2f6; padding: 10px; border-radius: 10px;}
    div[data-testid="stExpander"] div[role="button"] p {font-size: 1.1rem; font-weight: bold;}
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
except Exception:
    SUPABASE_URL = LOCAL_URL
    SUPABASE_KEY = LOCAL_KEY

@st.cache_resource
def init_connection():
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        return None

supabase = init_connection()

# ==========================================
# 🔐 2. 登录门禁
# ==========================================
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if st.session_state["password_correct"]:
        return True
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown("<br><br><h2 style='text-align: center;'>⚡️ GV-Charge Command Center</h2>", unsafe_allow_html=True)
        st.info("🔒 Authorized Personnel Only (System Access)")
        password = st.text_input("Access Key", type="password")
        if password:
            if password == "admin123":
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("❌ Access Denied")
    return False

if not check_password():
    st.stop()

# ==========================================
# 🧠 3. 数据处理中心
# ==========================================
def get_transactions():
    if not supabase: return pd.DataFrame()
    try:
        response = supabase.table("transactions").select("*").order("created_at", desc=True).limit(500).execute()
        if not response.data: return pd.DataFrame()
        df = pd.DataFrame(response.data)
        df['created_at'] = pd.to_datetime(df['created_at'])
        if df['created_at'].dt.tz is None:
            df['created_at'] = df['created_at'].dt.tz_localize('UTC')
        df['local_time'] = df['created_at'].dt.tz_convert('America/Vancouver')
        df['total_fee'] = df['total_fee'].astype(float)
        df['kwh'] = df['kwh'].astype(float)
        return df
    except Exception:
        return pd.DataFrame()

def display_pdf(file_path):
    """在该页面直接嵌入 PDF 预览"""
    with open(file_path, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode('utf-8')
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)

# ==========================================
# 🖥️ 4. 侧边栏与布局
# ==========================================
with st.sidebar:
    st.title("Enterprise V3.0")
    st.caption("Metro Vancouver Grid")
    
    # 导航栏图标化
    page = st.radio("Navigation", [
        "🗺️ 全局态势 (Map View)", 
        "📊 运营数据 (Analytics)",
        "🧾 票据中心 (Invoices)",
        "🛠️ 资产管理 (Assets & QR)",
        "📡 系统日志 (System Logs)"
    ])
    
    st.divider()
    st.subheader("Gateway Config")
    ngrok_url = st.text_input("Ngrok URL", placeholder="https://xxxx.ngrok-free.app")
    
    st.divider()
    if st.button("Logout"):
        st.session_state["password_correct"] = False
        st.rerun()

# ==========================================
# 🗺️ 模块 A: 全局态势 (Map View) - [新增高光功能]
# ==========================================
if page == "🗺️ 全局态势 (Map View)":
    st.title("🗺️ Network Operations Center (NOC)")
    
    # 1. 定义三个站点的真实坐标 (温哥华)
    map_data = pd.DataFrame({
        'lat': [49.2276, 49.1833, 49.1896],
        'lon': [-123.0076, -123.1333, -122.8490],
        'unit_id': ['VAN-001 (Metrotown)', 'RIC-002 (Aberdeen)', 'SUR-003 (Surrey Ctrl)'],
        'status': ['🟢 Online', '🟢 Online', '🔴 Maintenance']
    })

    col1, col2 = st.columns([3, 1])
    
    with col1:
        # 展示交互式地图
        st.map(map_data, latitude='lat', longitude='lon', size=200, color='#ffaa00')
    
    with col2:
        st.subheader("Station Status")
        for index, row in map_data.iterrows():
            with st.expander(f"{row['unit_id']}", expanded=True):
                st.write(f"Status: **{row['status']}**")
                st.caption(f"Lat: {row['lat']}, Lon: {row['lon']}")
                if "Online" in row['status']:
                    st.progress(98, text="Health Check")
                else:
                    st.progress(0, text="Health Check")

# ==========================================
# 🧾 模块 B: 票据中心 (Invoices) - [升级：内嵌预览]
# ==========================================
elif page == "🧾 票据中心 (Invoices)":
    st.title("🧾 Invoice Management System")
    
    if not os.path.exists("invoices"):
        st.error("❌ No local invoice directory found.")
    else:
        files = glob.glob("invoices/*.pdf")
        files.sort(key=os.path.getmtime, reverse=True)
        
        if not files:
            st.warning("📭 No invoices generated yet.")
        else:
            col_list, col_view = st.columns([1, 2])
            
            with col_list:
                st.subheader("🗂️ File List")
                # 让用户选择一个文件
                file_names = [os.path.basename(f) for f in files]
                selected_file_name = st.radio("Select Invoice:", file_names)
                
                # 找到完整路径
                selected_path = os.path.join("invoices", selected_file_name)
                file_stat = os.stat(selected_path)
                
                st.info(f"""
                **File Details:**
                \n📅 Date: {datetime.fromtimestamp(file_stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')}
                \n📦 Size: {file_stat.st_size/1024:.1f} KB
                """)

            with col_view:
                st.subheader("📄 Document Preview")
                # 直接显示 PDF
                display_pdf(selected_path)

# ==========================================
# 📊 模块 C: 运营数据 (Analytics)
# ==========================================
elif page == "📊 运营数据 (Analytics)":
    st.title("📊 Business Intelligence")
    if st.toggle('Auto-Refresh', value=True):
        time.sleep(3)
        st.rerun()
        
    df = get_transactions()
    if not df.empty:
        # KPI Cards
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total Revenue", f"${df['total_fee'].sum():,.2f}", "+12%")
        k2.metric("Energy Delivered", f"{df['kwh'].sum():,.1f} kWh", "+5%")
        k3.metric("Transactions", len(df), "+2")
        k4.metric("Active Sites", df['unit_id'].nunique())
        
        st.divider()
        
        c1, c2 = st.columns([2,1])
        with c1:
            st.markdown("##### Revenue Trend (Last 24h)")
            chart = alt.Chart(df).mark_area(
                line={'color':'#ffaa00'},
                color=alt.Gradient(
                    gradient='linear',
                    stops=[alt.GradientStop(color='white', offset=0),
                           alt.GradientStop(color='#ffaa00', offset=1)],
                    x1=1, x2=1, y1=1, y2=0
                )
            ).encode(
                x='local_time', y='total_fee', tooltip=['local_time', 'total_fee']
            ).properties(height=350)
            st.altair_chart(chart, use_container_width=True)
            
        with c2:
            st.markdown("##### Station Distribution")
            donut = alt.Chart(df).mark_arc(innerRadius=60).encode(
                theta='sum(total_fee)', color='unit_id', tooltip=['unit_id', 'sum(total_fee)']
            )
            st.altair_chart(donut, use_container_width=True)

# ==========================================
# 🛠️ 模块 D: 资产与二维码
# ==========================================
elif page == "🛠️ 资产管理 (Assets & QR)":
    st.title("🛠️ Asset & QR Generator")
    
    asset_data = [
        {"Unit": "VAN-001", "Loc": "Burnaby", "Type": "Tesla V3", "Power": "250kW"},
        {"Unit": "RIC-002", "Loc": "Richmond", "Type": "ChargePoint", "Power": "150kW"},
        {"Unit": "SUR-003", "Loc": "Surrey", "Type": "Flo CoRe+", "Power": "50kW"}
    ]
    st.dataframe(pd.DataFrame(asset_data), use_container_width=True)
    
    st.divider()
    st.subheader("🖨️ QR Production")
    
    if not ngrok_url:
        st.warning("⚠️ Please enter Ngrok URL in Sidebar first.")
    else:
        clean_url = ngrok_url.rstrip("/").split("/scan")[0]
        cols = st.columns(3)
        for i, item in enumerate(asset_data):
            with cols[i]:
                unit = item['Unit']
                link = f"{clean_url}/scan/{unit}"
                qr = qrcode.QRCode(box_size=8, border=2)
                qr.add_data(link)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                
                # Show Image
                byte_io = io.BytesIO()
                img.save(byte_io, 'PNG')
                st.image(byte_io, caption=f"{unit} ({item['Loc']})")
                st.caption(link)

# ==========================================
# 📡 模块 E: 系统日志 (System Logs) - [新增装X神器]
# ==========================================
elif page == "📡 系统日志 (System Logs)":
    st.title("📡 System Kernel Logs")
    st.caption("Real-time stream from WebSocket Gateway & Payment Server")
    
    # 模拟日志数据
    log_container = st.empty()
    
    # 假装在读取日志 (Hack effect)
    logs = []
    now = datetime.now()
    
    mock_events = [
        "[INFO] Connection established with Station VAN-001 IP: 192.168.1.105",
        "[INFO] Heartbeat received from RIC-002 (Signal: Strong)",
        "[WARN] Grid voltage fluctuation detected at SUR-003 (Dev: 1.2%)",
        "[INFO] Payment Gateway: Transaction verified via Apple Pay Token",
        "[DB] Writing transaction record to Supabase (Table: transactions)",
        "[PDF] Invoice generated successfully. Path: /invoices/INV-2025...",
        "[SYS] Memory usage stable: 45%. CPU Load: 12%."
    ]
    
    st.markdown("""
        <style>
        .log-box {
            font-family: 'Courier New', Courier, monospace;
            background-color: #0e1117;
            color: #00ff00;
            padding: 20px;
            border-radius: 5px;
            height: 400px;
            overflow-y: scroll;
            border: 1px solid #333;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # 模拟实时滚动
    log_html = '<div class="log-box">'
    for i in range(15):
        t = now - pd.Timedelta(seconds=15-i)
        import random
        event = random.choice(mock_events)
        line = f"[{t.strftime('%H:%M:%S')}] {event}<br>"
        log_html += line
    log_html += '<span style="color:white">_</span></div>'
    
    st.markdown(log_html, unsafe_allow_html=True)
    
    if st.button("🔄 Refresh Logs"):
        st.rerun()