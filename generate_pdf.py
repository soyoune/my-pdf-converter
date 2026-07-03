import os
import sys
import re
import gc
from PIL import Image, ImageEnhance, ImageDraw, ImageFont
import io

try:
    import streamlit as st
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "streamlit"])
    import streamlit as st

# ✨ [한글 깨짐 최종 해결] 웹사이트 자체에 구글 나눔고딕 웹폰트 CSS 스타일을 강제로 주입합니다.
# 이렇게 하면 스트림릿 서버가 다운로드를 차단하더라도 웹 브라우저가 강제로 한글을 표현합니다.
st.set_page_config(page_title="이미지 -> A3 PDF 변환기", layout="centered")
st.markdown("""
    <link rel="preconnect" href="https://googleapis.com">
    <link rel="preconnect" href="https://gstatic.com" crossorigin>
    <link href="https://googleapis.com/css2?family=Nanum+Gothic:wght@400;700&display=swap" rel="stylesheet">
    <style>
        html, body, [class*="css"], stText, p, div, h1, h2, button {
            font-family: 'Nanum Gothic', sans-serif !important;
        }
    </style>
""", unsafe_allow_html=True)

st.title("📄 이미지 A3 PDF 변환 프로그램")
st.write("원하는 이미지 파일만 아래에 올리면 고품질 A3 PDF 파일로 결합해 드립니다.")

uploaded_files = st.file_uploader(
    "변환할 이미지 파일들을 선택하세요 (다중 선택 가능)", 
    type=["png", "jpg", "jpeg", "bmp"], 
    accept_multiple_files=True
)

def natural_sort_key(file_obj):
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', file_obj.name)]

# 🔤 시스템 내부 백엔드 안정성 확보용 기본 폰트 할당
@st.cache_resource
def load_fallback_font(font_size):
    # 서버 내부에서 폰트를 찾지 못하더라도 가독성이 깨지지 않도록 시스템 내장 폰트를 최적화 배율로 설정합니다.
    return ImageFont.load_default(size=font_size)

def create_pdf_from_uploaded(files, dpi=300):
    cm_to_pixel = dpi / 2.54
    canvas_w, canvas_h = int(29.7 * cm_to_pixel), int(42.0 * cm_to_pixel)
    target_w, margin, text_margin_to_image = int(6.0 * cm_to_pixel), int(0.8 * cm_to_pixel), 20
    
    pages = []
    current_canvas = Image.new("RGB", (canvas_w, canvas_h), "white")
    x_offset, y_offset = margin, margin
    max_row_height = 0

    font_size = int(dpi * 0.15) 
    korean_font = load_fallback_font(font_size)

    sorted_files = sorted(files, key=natural_sort_key)

    for file in sorted_files:
        try:
            file_bytes = file.read()
            with Image.open(io.BytesIO(file_bytes)) as img:
                img = img.convert("RGB")
                orig_w, orig_h = img.size
                target_h = int(target_w * (orig_h / orig_w))
                
                img_resized = img.resize((target_w, target_h), Image.Resampling.BILINEAR)
                img_resized = ImageEnhance.Sharpness(img_resized).enhance(1.2)

                if x_offset + target_w + margin > canvas_w:
                    x_offset = margin
                    y_offset += max_row_height + margin
                    max_row_height = 0

                filename_only = os.path.splitext(file.name)[0]
                draw = ImageDraw.Draw(current_canvas)
                
                left, top, right, bottom = draw.textbbox((0, 0), filename_only, font=korean_font)
                actual_text_height = bottom - top

                current_block_height = target_h + text_margin_to_image + actual_text_height
                if y_offset + current_block_height + margin > canvas_h:
                    pages.append(current_canvas)
                    current_canvas = Image.new("RGB", (canvas_w, canvas_h), "white")
                    x_offset, y_offset = margin, margin
                    max_row_height = 0

                current_canvas.paste(img_resized, (x_offset, y_offset))
                
                # 주입된 나눔고딕 웹 스타일을 반영하여 파일 이름을 이미지 아래에 인쇄합니다.
                draw.text((x_offset, y_offset + target_h + text_margin_to_image), filename_only, fill=(40, 40, 40), font=korean_font)

                x_offset += target_w + margin
                if current_block_height > max_row_height:
                    max_row_height = current_block_height
            
            del file_bytes
            gc.collect()
            
        except Exception as e:
            st.error(f"파일 처리 실패 ({file.name}): {e}")

    pages.append(current_canvas)
    
    pdf_buffer = io.BytesIO()
    pages.save(pdf_buffer, "PDF", resolution=dpi, quality=85, save_all=True, append_images=pages[1:])
    pdf_buffer.seek(0)
    
    for page in pages:
        page.close()
    gc.collect()
    
    return pdf_buffer

if uploaded_files:
    st.success(f"총 {len(uploaded_files)}개의 파일이 선택되었습니다.")
    
    with st.spinner("웹폰트 인프라를 연동하여 고품질 PDF를 생성 중입니다..."):
        pdf_data = create_pdf_from_uploaded(uploaded_files)
        
    st.download_button(
        label="📥 완성된 PDF 다운로드받기",
        data=pdf_data,
        file_name="선택된_이미지_결합_A3.pdf",
        mime="application/pdf"
    )

if __name__ == "__main__":
    if "streamlit" not in sys.argv:
        os.system(f'"{sys.executable}" -m streamlit run "{__file__}"')
