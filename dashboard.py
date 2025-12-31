import sys
import os
import glob

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
import qrcode
from PIL import Image
import io

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
# 🎨 页面配置
# ==========================================
st.set_page_config(
    page_title="GV-Charge 总控平台", 
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

# ==========================================
# 🔐 登录逻辑
# ==========================================
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if st.session_state["password_correct"]:
        return True
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown("### ⚡️ GV-Charge 运营管理平台")
        st.info("系统升级中：请输入管理员密码 (admin123)")
        password = st.text_input("Password", type="password")
        if password:
            if password == "admin123":
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("❌ 密码错误")
    return False

if not check_password():
    st.stop()

# ==========================================
# 🧠 数据获取
# ==========================================
def get_transactions():
    if not supabase: return pd.DataFrame()
    try:
        response = supabase.table("transactions").select("*").order("created_at", desc=True).execute()
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

# ==========================================
# 🖥️ 侧边栏菜单
# ==========================================
with st.sidebar:
    st.title("Admin Pro 2.0")
    st.caption("Metro Vancouver Region")
    
    page = st.radio("功能导航", [
        "📊 运营大屏 (Dashboard)", 
        "📍 资产与二维码 (Assets & QR)", 
        "🧾 发票与财务 (Invoices)",
        "🛠️ 设备运维 (Ops)"
    ])
    
    st.divider()
    
    # 这里是一个关键设置：让用户输入 Ngrok 地址
    st.subheader("🌐 支付网关配置")
    ngrok_url = st.text_input("当前 Ngrok 网址 (不带/scan)", placeholder="https://xxxx.ngrok-free.app")
    st.caption("⚠️ 用于生成二维码，请复制终端里的网址")
    
    st.divider()
    if st.button("退出登录"):
        st.session_state["password_correct"] = False
        st.rerun()

# ==========================================
# 📍 模块：资产与二维码 (这是你要的！地址、型号、扫码)
# ==========================================
if page == "📍 资产与二维码 (Assets & QR)":
    st.title("📍 充电站资产管理")
    st.info("这里展示每台设备的详细物理信息，并可生成打印用的二维码物料。")
    
    # 1. 定义详细的资产数据
    asset_data = [
        {
            "Unit ID": "VAN-001", 
            "Model": "Tesla V3 Supercharger", 
            "Power": "250 kW",
            "Address": "4700 Kingsway, Burnaby, BC (Metrotown P1)", 
            "Connector": "CCS2 / NACS",
            "Install Date": "2024-01-15"
        },
        {
            "Unit ID": "RIC-002", 
            "Model": "ChargePoint CP6000", 
            "Power": "150 kW",
            "Address": "4151 Hazelbridge Way, Richmond, BC (Aberdeen)", 
            "Connector": "CCS2",
            "Install Date": "2024-02-20"
        },
        {
            "Unit ID": "SUR-003", 
            "Model": "Flo CoRe+ Max", 
            "Power": "50 kW",
            "Address": "10153 King George Blvd, Surrey, BC", 
            "Connector": "CHAdeMO / CCS",
            "Install Date": "2024-03-10"
        }
    ]
    df_assets = pd.DataFrame(asset_data)
    
    # 2. 展示资产表格
    st.dataframe(
        df_assets, 
        use_container_width=True,
        column_config={
            "Install Date": st.column_config.DateColumn("安装日期")
        }
    )
    
    st.divider()
    
    # 3. 二维码生成工厂
    st.subheader("🖨️ 物料生成中心 (QR Code Generator)")
    
    if not ngrok_url:
        st.warning("⚠️ 请在侧边栏输入当前的 Ngrok 网址，否则无法生成有效二维码！")
    else:
        # 清洗 URL，防止用户多输了 /scan
        clean_url = ngrok_url.rstrip("/")
        if "/scan" in clean_url:
            clean_url = clean_url.split("/scan")[0]
            
        cols = st.columns(3)
        for index, row in enumerate(asset_data):
            unit_id = row["Unit ID"]
            full_link = f"{clean_url}/scan/{unit_id}"
            
            with cols[index % 3]:
                st.markdown(f"**{unit_id}**")
                
                # 生成二维码
                qr = qrcode.QRCode(box_size=10, border=4)
                qr.add_data(full_link)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                
                # 转换成 streamlit 能显示的格式
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='PNG')
                st.image(img_byte_arr, caption=f"扫码充电: {unit_id}", width=200)
                
                st.code(full_link, language="text")
                st.caption(f"📍 {row['Address']}")

# ==========================================
# 🧾 模块：发票与财务 (这里解决“发票在哪”的问题)
# ==========================================
elif page == "🧾 发票与财务 (Invoices)":
    st.title("🧾 财务与票据中心")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📂 本地发票归档 (Local Archive)")
        st.markdown("系统生成的 PDF 发票默认存储在服务器的 `invoices/` 目录下。")
        
        # 扫描 invoices 文件夹
        if os.path.exists("invoices"):
            files = glob.glob("invoices/*.pdf")
            # 按时间倒序
            files.sort(key=os.path.getmtime, reverse=True)
            
            if files:
                invoice_list = []
                for f in files:
                    file_name = os.path.basename(f)
                    file_time = datetime.fromtimestamp(os.path.getmtime(f)).strftime('%Y-%m-%d %H:%M:%S')
                    file_size = f"{os.path.getsize(f) / 1024:.1f} KB"
                    invoice_list.append({"File Name": file_name, "Generated Time": file_time, "Size": file_size, "Path": f})
                
                df_inv = pd.DataFrame(invoice_list)
                st.dataframe(df_inv, use_container_width=True)
                
                st.info(f"💡 共找到 {len(files)} 张发票。请在您的电脑文件夹 `/charging platform/invoices` 中打开它们。")
            else:
                st.warning("📭 文件夹存在，但没有发现 PDF 文件。请先尝试支付一笔订单。")
        else:
            st.error("❌ 未找到 `invoices` 文件夹。请确保您已经运行过 qr_server.py 并完成了至少一笔支付。")

    with col2:
        st.subheader("📊 实时流水")
        df_trans = get_transactions()
        if not df_trans.empty:
            st.dataframe(
                df_trans[['local_time', 'unit_id', 'total_fee']], 
                use_container_width=True,
                hide_index=True
            )

# ==========================================
# 📊 模块：运营大屏 (保留之前的)
# ==========================================
elif page == "📊 运营大屏 (Dashboard)":
    st.title("📊 运营监控中心")
    if st.toggle('🔴 自动刷新', value=True):
        time.sleep(3)
        st.rerun()
        
    df = get_transactions()
    if not df.empty:
        k1, k2, k3 = st.columns(3)
        k1.metric("💰 总营收", f"${df['total_fee'].sum():,.2f}")
        k2.metric("⚡️ 总电量", f"{df['kwh'].sum():,.1f} kWh")
        k3.metric("🧾 订单数", len(df))
        
        c1, c2 = st.columns([2,1])
        with c1:
            st.altair_chart(alt.Chart(df.tail(50)).mark_area(color='darkblue', opacity=0.5).encode(
                x='local_time', y='total_fee'
            ).properties(height=300), use_container_width=True)
        with c2:
            st.altair_chart(alt.Chart(df).mark_arc().encode(
                theta='sum(total_fee)', color='unit_id'
            ), use_container_width=True)

# ==========================================
# 🛠️ 模块：设备运维 (保留之前的)
# ==========================================
elif page == "🛠️ 设备运维 (Ops)":
    st.title("🛠️ 远程运维")
    st.info("模拟远程控制设备状态。")
    
    # 模拟状态
    if "device_table" not in st.session_state:
        st.session_state["device_table"] = pd.DataFrame([
             {"Unit ID": "VAN-001", "Status": "Online", "Health": 98},
             {"Unit ID": "RIC-002", "Status": "Online", "Health": 95},
             {"Unit ID": "SUR-003", "Status": "Offline", "Health": 0},
        ])
    
    edited_df = st.data_editor(
        st.session_state["device_table"],
        column_config={
             "Status": st.column_config.SelectboxColumn(options=["Online", "Offline", "Maintenance"])
        },
        use_container_width=True
    )
    if st.button("保存状态"):
        st.session_state["device_table"] = edited_df
        st.success("状态已更新")