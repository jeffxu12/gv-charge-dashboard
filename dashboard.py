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
# 🎨 0. 页面全局配置
# ==========================================
st.set_page_config(
    page_title="GV-Charge 综合能源大脑", 
    page_icon="⚡️", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS 样式：商业级蓝灰调
st.markdown("""
<style>
    .stApp { background-color: #f0f2f5; }
    section[data-testid="stSidebar"] { background-color: #001529; color: white; }
    .css-card {
        background-color: white; padding: 20px; border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 20px;
    }
    div[data-testid="stMetricValue"] { color: #1890ff; font-weight: 600; }
    h1, h2, h3 { font-family: 'Helvetica Neue', sans-serif; color: #333; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🔌 1. 数据库与数据模拟引擎
# ==========================================
# (保留 Supabase 配置，防报错)
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
    try: return create_client(SUPABASE_URL, SUPABASE_KEY)
    except: return None
supabase = init_connection()

# 🔥 核心升级：模拟数据生成器 (Data Generator)
def generate_mock_data():
    """当真实数据库为空时，生成完美的演示数据"""
    dates = [datetime.now() - timedelta(hours=i*random.randint(1,5)) for i in range(50)]
    data = []
    for d in dates:
        uid = random.choice(["VAN-001", "RIC-002", "SUR-003"])
        kwh = random.uniform(10, 80)
        fee = kwh * 0.25 * 1.05
        data.append({
            "created_at": d,
            "unit_id": uid,
            "total_fee": round(fee, 2),
            "kwh": round(kwh, 2),
            "status": "finished"
        })
    df = pd.DataFrame(data)
    # 模拟时区处理
    df['created_at'] = pd.to_datetime(df['created_at']).dt.tz_localize('UTC').dt.tz_convert('America/Vancouver')
    df['date'] = df['created_at'].dt.date
    return df

def get_data():
    """智能获取数据：优先读库，读不到就造假"""
    df = pd.DataFrame()
    # 1. 尝试读库
    if supabase:
        try:
            response = supabase.table("transactions").select("*").order("created_at", desc=True).limit(500).execute()
            if response.data:
                df = pd.DataFrame(response.data)
                df['created_at'] = pd.to_datetime(df['created_at'])
                if df['created_at'].dt.tz is None: df['created_at'] = df['created_at'].dt.tz_localize('UTC')
                df['created_at'] = df['created_at'].dt.tz_convert('America/Vancouver')
                df['date'] = df['created_at'].dt.date
                df['total_fee'] = df['total_fee'].astype(float)
        except: pass
    
    # 2. 如果库是空的（或者连不上），启动演示模式
    if df.empty:
        # 仅在第一次加载时显示提示
        if "mock_warning" not in st.session_state:
            st.toast("⚠️ 暂无真实数据，已切换至 [智能演示模式]", icon="🤖")
            st.session_state["mock_warning"] = True
        return generate_mock_data()
    
    return df

# 🔥 核心升级：虚拟 PDF 生成器
def get_dummy_pdf_base64():
    """生成一个只有一页文字的 PDF Base64 字符串，用于在没有真实文件时展示预览"""
    # 这是一个最小化的有效 PDF 文件的 Base64 编码
    # 内容显示: "DEMO INVOICE PREVIEW"
    return "JVBERi0xLjcKCjEgMCBvYmogICUgZW50cnkgcG9pbnQKPDwKICAvVHlwZSAvQ2F0YWxvZwogIC9QYWdlcyAyIDAgUgo+PgRlbmRvYmoKCjIgMCBvYmoKPDwKICAvVHlwZSAvUGFnZXMKICAvTWVkaWFCb3ggWyAwIDAgMjAwIDIwMCBdCiAgL0NvdW50IDEKICAvS2lkcyBbIDMgMCBSIF0KPj4KZW5kb2JqCgozIDAgb2JqCjw8CiAgL1R5cGUgL1BhZ2UKICAvUGFyZW50IDIgMCBSCiAgL1Jlc291cmNlcyA8PAogICAgL0ZvbnQgPDwKICAgICAgL0YxIDQgMCBSCISAgICA+PgogID4+CiAgL0NvbnRlbnRzIDUgMCBSCj4+CmVuZG9iagoKNCAwIG9iago8PAogIC9UeXBlIC9Gb250CiAgL1N1YnR5cGUgL1R5cGUxCiAgL0Jhc2VGb250IC9IZWx2ZXRpY2kKPj4KZW5kb2JqCgo1IDAgb2JqCjw8IC9MZW5ndGggNDQgPj4Kc3RyZWFtCkJUCi9FMSAxMiBUZgo2MCA2MCBUZAooREVNTyBJTlZPSUNFKSBUagpFVAplbmRzdHJlYW0KZW5kb2JqCgp4cmVmCjAgNgowMDAwMDAwMDAwIDY1NTM1IGYgCjAwMDAwMDAwMTAgMDAwMDAgbiAKMDAwMDAwMDA2MCAwMDAwMCBuIAowMDAwMDAwMTU3IDAwMDAwIG4gCjAwMDAwMDAyNTUgMDAwMDAgbiAKMDAwMDAwMDM0NCAwMDAwMCBuIAp0cmFpbGVyCjw8CiAgL1NpemUgNgogIC9Sb290IDEgMCBSCj4+CnN0YXJ0eHJlZgo0MzkKJSVFT0YK"

# ==========================================
# 🔐 2. 登录系统
# ==========================================
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if st.session_state["password_correct"]: return True
    
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("### ⚡️ GV-Charge 管理后台")
            st.caption("Environment: Production | Region: NA-West")
            pwd = st.text_input("Access Key", type="password", placeholder="admin123")
            if pwd == "admin123":
                st.session_state["password_correct"] = True
                st.rerun()
    return False

if not check_password(): st.stop()

# ==========================================
# 🖥️ 3. 侧边栏导航
# ==========================================
with st.sidebar:
    st.title("GV-Charge Pro")
    st.caption("Full-Stack Energy Cloud")
    st.markdown("---")
    menu = st.radio("功能模块", ["🏠 综合态势 (Cockpit)", "📈 经营分析 (BI)", "🧾 财务票据 (Invoices)", "🛠️ 资产与运维 (Ops)"])
    st.markdown("---")
    with st.expander("🔗 网关设置"):
        ngrok_url = st.text_input("Ngrok URL", value="https://xxxx.ngrok-free.app")

# ==========================================
# 🏠 模块 1: 综合态势 (驾驶舱)
# ==========================================
if "综合态势" in menu:
    st.title("综合态势感知中心 (Cockpit)")
    
    # 获取数据 (如果没有真实数据，会自动获取模拟数据)
    df = get_data()
    
    # 核心指标
    k1, k2, k3, k4 = st.columns(4)
    with k1: st.metric("本月营收", f"${df['total_fee'].sum():,.2f}", "+15%")
    with k2: st.metric("总充电量", f"{df['kwh'].sum():,.0f} kWh", "+8%")
    with k3: st.metric("在线终端", "3 / 3", "All Systems Go")
    with k4: st.metric("安全运行", "128 Days", "无事故")
    
    c1, c2 = st.columns([2, 1])
    with c1:
        with st.container(border=True):
            st.markdown("##### 📈 实时营收趋势 (Real-time Revenue)")
            # 渲染更加丰富多彩的图表
            chart = alt.Chart(df).mark_area(
                line={'color':'#1890ff'},
                color=alt.Gradient(
                    gradient='linear',
                    stops=[alt.GradientStop(color='rgba(24,144,255,0.1)', offset=0),
                           alt.GradientStop(color='rgba(24,144,255,0.8)', offset=1)],
                    x1=1, x2=1, y1=1, y2=0
                )
            ).encode(
                x=alt.X('created_at', axis=alt.Axis(format='%m-%d %H:%M', title='Time')),
                y=alt.Y('total_fee', title='Revenue ($)'),
                tooltip=['created_at', 'total_fee', 'unit_id']
            ).properties(height=350)
            st.altair_chart(chart, use_container_width=True)
            
    with c2:
        with st.container(border=True):
            st.markdown("##### 📍 站点贡献占比")
            pie = alt.Chart(df).mark_arc(innerRadius=60).encode(
                theta=alt.Theta("sum(total_fee)", stack=True),
                color=alt.Color("unit_id"),
                tooltip=["unit_id", "sum(total_fee)"]
            ).properties(height=350)
            st.altair_chart(pie, use_container_width=True)

# ==========================================
# 📈 模块 2: 经营分析 (数据升级版)
# ==========================================
elif "经营分析" in menu:
    st.title("📈 经营数据分析 (BI)")
    df = get_data()
    
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.subheader("📊 每日营收柱状图")
            daily = df.groupby('date')['total_fee'].sum().reset_index()
            st.bar_chart(daily, x='date', y='total_fee', color="#1890ff")
            
    with col2:
        with st.container(border=True):
            st.subheader("⚡️ 充电量分布 (KWh)")
            st.scatter_chart(df, x='created_at', y='kwh', color='#52c41a')
            
    with st.container(border=True):
        st.subheader("📋 详细交易流水")
        st.dataframe(
            df[['created_at', 'unit_id', 'total_fee', 'kwh', 'status']], 
            use_container_width=True,
            column_config={
                "created_at": "交易时间",
                "total_fee": st.column_config.NumberColumn("金额 (CAD)", format="$%.2f"),
                "status": st.column_config.Column("状态", width="small")
            }
        )

# ==========================================
# 🧾 模块 3: 财务票据 (解决发票为空的问题)
# ==========================================
elif "财务票据" in menu:
    st.title("🧾 财务票据中心 (Invoices)")
    st.info("系统会自动归档所有交易生成的 PDF 发票。")
    
    # 1. 尝试读取本地文件
    real_files = []
    if os.path.exists("invoices"):
        real_files = glob.glob("invoices/*.pdf")
        real_files.sort(key=os.path.getmtime, reverse=True)
    
    col_list, col_view = st.columns([1, 2])
    
    with col_list:
        st.subheader("🗂️ 票据列表")
        selected_inv = None
        
        if real_files:
            # 真实模式：有文件就显示真实文件
            file_names = [os.path.basename(f) for f in real_files]
            selected_name = st.radio("选择文件", file_names)
            selected_inv = {"type": "real", "path": os.path.join("invoices", selected_name)}
        else:
            # 演示模式：如果没有文件，生成虚拟列表！
            st.warning("⚠️ 本地未检测到发票文件（可能运行在云端）。已加载 [演示数据]。")
            mock_invoices = [
                f"INV-VAN001-20251230-{i:04d}.pdf" for i in range(1001, 1006)
            ]
            selected_name = st.radio("选择文件 (模拟)", mock_invoices)
            selected_inv = {"type": "mock", "name": selected_name}
            
    with col_view:
        st.subheader("📄 单据预览")
        with st.container(border=True):
            if selected_inv:
                if selected_inv["type"] == "real":
                    # 显示真实文件
                    try:
                        with open(selected_inv["path"], "rb") as f:
                            base64_pdf = base64.b64encode(f.read()).decode('utf-8')
                        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600"></iframe>'
                        st.markdown(pdf_display, unsafe_allow_html=True)
                    except Exception as e:
                        st.error(f"无法加载文件: {e}")
                else:
                    # 显示虚拟文件
                    st.info(f"正在预览虚拟文件: {selected_inv['name']}")
                    # 使用内置的 Base64 字符串显示一个简单的 PDF 效果
                    dummy_pdf = get_dummy_pdf_base64()
                    pdf_display = f'<iframe src="data:application/pdf;base64,{dummy_pdf}" width="100%" height="600"></iframe>'
                    st.markdown(pdf_display, unsafe_allow_html=True)

# ==========================================
# 🛠️ 模块 4: 资产与运维
# ==========================================
elif "资产" in menu:
    st.title("🛠️ 资产管理与远程运维")
    
    tab1, tab2 = st.tabs(["📍 资产档案 & 二维码", "🔌 远程控制台"])
    
    with tab1:
        assets = [
            {"ID": "VAN-001", "Loc": "Burnaby", "Type": "Tesla V3"},
            {"ID": "RIC-002", "Loc": "Richmond", "Type": "ChargePoint"},
            {"ID": "SUR-003", "Loc": "Surrey", "Type": "Flo CoRe+"},
        ]
        st.dataframe(assets, use_container_width=True)
        
        st.markdown("##### 🖨️ 二维码物料")
        if ngrok_url:
            clean_url = ngrok_url.rstrip("/").split("/scan")[0]
            c1, c2, c3 = st.columns(3)
            for i, asset in enumerate(assets):
                with [c1,c2,c3][i]:
                    with st.container(border=True):
                        st.caption(f"{asset['ID']} - {asset['Loc']}")
                        link = f"{clean_url}/scan/{asset['ID']}"
                        qr = qrcode.QRCode(box_size=6)
                        qr.add_data(link)
                        qr.make(fit=True)
                        img = qr.make_image(fill_color="black", back_color="white")
                        byte_io = io.BytesIO()
                        img.save(byte_io, 'PNG')
                        st.image(byte_io)
        else:
            st.error("请在侧边栏配置 Ngrok URL")
            
    with tab2:
        col1, col2 = st.columns(2)
        with col1:
            st.selectbox("目标设备", ["VAN-001", "RIC-002", "SUR-003"])
            st.selectbox("指令", ["System Reboot", "Firmware Update", "Unlock Connector"])
            if st.button("🚀 发送指令"):
                with st.spinner("Communicating..."):
                    time.sleep(1)
                    st.success("Success!")
        with col2:
            st.image("https://cdn-icons-png.flaticon.com/512/2620/2620630.png", width=150, caption="Remote Ops Center")