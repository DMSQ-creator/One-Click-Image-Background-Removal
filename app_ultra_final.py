import streamlit as st
from transparent_background import Remover
from PIL import Image
import io
import zipfile
import time
import torch
import os
import datetime  # 新增：用于获取时间戳

# ==========================================
# 1. 页面配置
# ==========================================
st.set_page_config(
    page_title="AI 旗舰级抠图 (智能分文件夹版)",
    page_icon="💎",
    layout="wide"
)

st.title("💎 AI 旗舰级抠图 Pro")
st.markdown("""
**当前模式：智能归档模式**。
每次点击运行，系统会自动创建一个**以当前时间命名**的文件夹，防止图片混淆。
""")

# ==========================================
# 2. 初始化核心引擎
# ==========================================
@st.cache_resource
def load_remover(mode_type):
    is_fast = True if mode_type == 'fast' else False
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"🔄 正在加载模型... 设备: {device}, 模式: {mode_type}")
    remover = Remover(mode=mode_type, device=device, jit=False) 
    return remover

# ==========================================
# 3. 辅助工具函数
# ==========================================
def create_checkerboard(w, h, cell_size=20):
    img = Image.new("RGB", (w, h), (240, 240, 240))
    pixels = img.load()
    for y in range(h):
        for x in range(w):
            if ((x // cell_size) + (y // cell_size)) % 2 == 0:
                pixels[x, y] = (200, 200, 200)
    return img

def apply_checkerboard_background(rgba_img):
    w, h = rgba_img.size
    preview_max = 1024
    if max(w, h) > preview_max:
        scale = preview_max / max(w, h)
        new_w, new_h = int(w * scale), int(h * scale)
        bg = create_checkerboard(new_w, new_h)
        fg = rgba_img.resize((new_w, new_h), Image.Resampling.BILINEAR)
        bg.paste(fg, (0, 0), fg)
        return bg
    else:
        bg = create_checkerboard(w, h)
        bg.paste(rgba_img, (0, 0), rgba_img)
        return bg

# ==========================================
# 4. 侧边栏配置
# ==========================================
st.sidebar.header("🛠️ 参数设置")

model_mode = st.sidebar.radio(
    "1. 选择精度等级：",
    ("💎 旗舰画质 (Base)", "⚡ 快速画质 (Fast)"),
    index=0
)
mode_param = 'base' if "旗舰" in model_mode else 'fast'

max_resolution = st.sidebar.selectbox(
    "2. 图片最大边长限制：",
    (2048, 4096, "不限制 (慎选)"),
    index=0
)

uploaded_files = st.sidebar.file_uploader(
    "3. 上传图片 (支持多选)", 
    type=["jpg", "png", "jpeg", "webp"], 
    accept_multiple_files=True
)

# ==========================================
# 5. 主处理逻辑
# ==========================================

# 定义总目录
BASE_OUTPUT_DIR = "抠图任务归档"

# 初始化 Session State
if "processed_images_final" not in st.session_state:
    st.session_state.processed_images_final = []
if "current_task_dir" not in st.session_state:
    st.session_state.current_task_dir = "" # 记录当前任务的文件夹路径

if uploaded_files:
    start_btn = st.sidebar.button("▶️ 启动新任务", type="primary")
    
    if start_btn:
        # 1. 每次点击都生成一个新的文件夹名称 (例如: 抠图任务归档/20231027_143055)
        time_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        task_folder_name = f"{time_str}_任务({len(uploaded_files)}张)"
        current_output_path = os.path.join(BASE_OUTPUT_DIR, task_folder_name)
        
        # 创建这个新文件夹
        if not os.path.exists(current_output_path):
            os.makedirs(current_output_path)
        
        # 更新 Session State
        st.session_state.current_task_dir = current_output_path
        st.session_state.processed_images_final = []
        
        # 2. 加载模型
        with st.spinner(f"正在唤醒 AI ({mode_param})..."):
            remover = load_remover(mode_param)
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        start_time = time.time()
        
        # 3. 循环处理
        for i, uploaded_file in enumerate(uploaded_files):
            status_text.markdown(f"**处理中 {i+1}/{len(uploaded_files)}:** `{uploaded_file.name}`")
            
            try:
                img = Image.open(uploaded_file).convert("RGB")
                
                # 缩放限制
                if isinstance(max_resolution, int):
                    if max(img.size) > max_resolution:
                        img.thumbnail((max_resolution, max_resolution), Image.Resampling.LANCZOS)
                
                # === 核心处理 ===
                out = remover.process(img) 
                
                # === 保存到新创建的独立文件夹 ===
                file_name_no_ext = uploaded_file.name.rsplit('.', 1)[0]
                save_name = f"{file_name_no_ext}_nobg.png"
                save_path = os.path.join(current_output_path, save_name)
                
                out.save(save_path)
                
                # 生成预览图 (用于网页显示)
                preview_img = apply_checkerboard_background(out)
                
                # 存入列表用于回显
                st.session_state.processed_images_final.append({
                    "name": save_name,
                    "path": save_path,
                    "original": img,
                    "result_preview": preview_img
                })
                
            except Exception as e:
                st.error(f"❌ {uploaded_file.name} 失败: {e}")
            
            progress_bar.progress((i + 1) / len(uploaded_files))
        
        duration = time.time() - start_time
        status_text.success(f"✅ 任务完成！耗时 {duration:.1f} 秒")
        progress_bar.progress(100)
        
        # 尝试自动打开文件夹 (Windows)
        try:
            os.startfile(current_output_path)
        except:
            pass

# ==========================================
# 6. 结果展示
# ==========================================
if st.session_state.processed_images_final:
    st.divider()
    
    current_dir = st.session_state.current_task_dir
    
    # 顶部信息栏
    st.info(f"📂 **本次结果已保存至新文件夹：** `{os.path.abspath(current_dir)}`")
    
    # 图库展示
    for index, item in enumerate(st.session_state.processed_images_final):
        with st.container(border=True):
            c1, c2, c3 = st.columns([1, 1, 1])
            with c1: st.image(item['original'], caption="原图", use_container_width=True)
            with c2: st.image(item['result_preview'], caption="结果预览", use_container_width=True)
            with c3:
                st.write(f"**文件名:** `{item['name']}`")
                st.success(f"✅ 已保存")
                st.caption(f"路径: .../{os.path.basename(current_dir)}/{item['name']}")

else:
    if not uploaded_files:
        st.info("👈 点击“启动新任务”后，系统会自动创建一个带时间戳的文件夹来保存结果。")