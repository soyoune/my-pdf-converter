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

# 1. 페이지 기본 설정 및 레이아웃
st.set_page_config(page_title="이미지 -> PDF 변환기", layout="centered")
st.title("📄 이미지 다중 규격 PDF 변환 프로그램")
st.write("원하는 이미지 파일과 출력 사이즈를 선택하면 고품질 PDF 파일로 결합해 드립니다.")

# 2. UI 구성 요소
size_option = st.selectbox(
    "출력하실 PDF 용지 크기를 선택하세요:",
    ["A3 (29.7cm x 42.0cm)", "A4 (21.0cm x 29.7cm)", "사용자 정의 (55.0cm x 100.0cm)"]
)

uploaded_files = st.file_uploader(
    "변환할 이미지 파일들을 선택하세요 (다중 선택 가능)", 
    type=["png", "jpg", "jpeg", "bmp"], 
    accept_multiple_files=True
)

def natural_sort_key(file_obj):
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', file_obj.name)]

def load_safe_font(font_size):
    """버전 충돌 없는 안전한 맞춤형 크기 폰트 로드"""
    font_path = "NanumGothic.ttf"
    if os.path.exists(font_path):
        try:
            return ImageFont.truetype(font_path, font_size)
        except Exception:
            pass
    try:
        return ImageFont.load_default(size=font_size)
    except TypeError:
        return ImageFont.load_default()

def create_pdf_from_uploaded(files, size_mode, dpi=300):
    cm_to_pixel = dpi / 2.54
    
    # ✨ 제안: 용지 규격별 '이미지 크기', '여백', '폰트 크기' 황금 비율 세팅
    if "A4" in size_mode:
        width_cm, height_cm = 21.0, 29.7
        target_w = int(4.5 * cm_to_pixel)       
        margin = int(0.6 * cm_to_pixel)
        font_size = 24       # A4용 가독성 크기
        text_padding = 15    # 글자와 이미지 사이 간격
    elif "A3" in size_mode:
        width_cm, height_cm = 29.7, 42.0
        target_w = int(6.0 * cm_to_pixel)       
        margin = int(0.8 * cm_to_pixel)
        font_size = 36       # A3용 가독성 크기
        text_padding = 20    
    else:  # 550mm x 1m (55cm x 100cm)
        width_cm, height_cm = 55.0, 100.0
        target_w = int(11.0 * cm_to_pixel)      
        margin = int(1.5 * cm_to_pixel)
        font_size = 64       # 대형 출력물용 시원한 크기
        text_padding = 35    
        
    canvas_w, canvas_h = int(width_cm * cm_to_pixel), int(height_cm * cm_to_pixel)
    
    pages = []
    current_canvas = Image.new("RGB", (canvas_w, canvas_h), "white")
    x_offset, y_offset = margin, margin
    max_row_height = 0
    
    korean_font = load_safe_font(font_size)
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
                
                # 행 바꿈 계산 (우측 여백 초과 시)
                if x_offset + target_w + margin > canvas_w:
                    x_offset = margin
                    y_offset += max_row_height + margin
                    max_row_height = 0
                
                # ✨ 제안: 글자가 들어갈 총 높이(폰트크기 + 이미지높이 + 여백)를 계산하여 다음 페이지 전환 결정
                total_block_height = target_h + font_size + text_padding
                
                if y_offset + total_block_height + margin > canvas_h:
                    pages.append(current_canvas)
                    current_canvas = Image.new("RGB", (canvas_w, canvas_h), "white")
                    x_offset, y_offset = margin, margin
                    max_row_height = 0
                
                # 텍스트가 들어갈 도화지 준비
                draw = ImageDraw.Draw(current_canvas)
                filename_only = os.path.splitext(file.name)[0]
                
                # ✨ 제안: 파일명을 이미지 '위쪽'에 자연스러운 여백을 두고 배치
                text_y_position = y_offset + text_padding
                image_y_position = text_y_position + font_size
                
                # 파일명 먼저 쓰기
                draw.text((x_offset, text_y_position), filename_only, fill=(40, 40, 40), font=korean_font)
                
                # 파일명 아래에 이미지 배치
                current_canvas.paste(img_resized, (x_offset, image_y_position))
                
                x_offset += target_w + margin
                if total_block_height > max_row_height:
                    max_row_height = total_block_height
            del file_bytes
            gc.collect()
        except Exception as e:
            st.error(f"파일 처리 실패 ({file.name}): {e}")
            
    pages.append(current_canvas)
    
    pdf_buffer = io.BytesIO()
    if pages:
        pages[0].save(pdf_buffer, "PDF", resolution=dpi, quality=85, save_all=True, append_images=pages[1:])
        pdf_buffer.seek(0)
    
    for page in pages:
        page.close()
    gc.collect()
    
    return pdf_buffer

# 3. 메인 로직 실행부
if uploaded_files:
    st.success(f"총 {len(uploaded_files)}개의 파일이 선택되었습니다.")
    with st.spinner("선택하신 크기에 맞춰 고품질 PDF를 생성 중입니다..."):
        try:
            pdf_data = create_pdf_from_uploaded(uploaded_files, size_option)
            short_size_name = "A3" if "A3" in size_option else "A4" if "A4" in size_option else "550x1000"
            st.download_button(
                label=f"📥 완성된 {short_size_name} PDF 다운로드받기", 
                data=pdf_data, 
                file_name=f"선택된_이미지_결합_{short_size_name}.pdf", 
                mime="application/pdf"
            )
        except Exception as e:
            st.error(f"PDF 생성 중 오류가 발생했습니다: {e}")
