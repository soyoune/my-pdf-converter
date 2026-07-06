import os
import sys
import re
import gc
import zipfile
from PIL import Image, ImageEnhance, ImageDraw, ImageFont
import io

try:
    import streamlit as st
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "streamlit"])
    import streamlit as st

# 1. 페이지 기본 설정 및 레이아웃
st.set_page_config(page_title="이미지 -> 다중 포맷 변환기", layout="centered")
st.title("📄 이미지 다중 규격 & 투명도 유지 변환 프로그램")
st.write("원하는 규격을 선택한 후, PDF 결합본 또는 투명도가 100% 유지되는 PNG 압축파일로 다운로드하세요.")

# 2. UI 구성 요소
size_option = st.selectbox(
    "출력하실 용지 크기를 선택하세요:",
    ["A3 (29.7cm x 42.0cm)", "A4 (21.0cm x 29.7cm)", "사용자 정의 (55.0cm x 100.0cm)"]
)

download_format = st.radio(
    "저장 방식을 선택하세요:",
    ["인쇄용 PDF 결합본 (투명 영역이 흰색으로 채워짐)", "투명도 100% 유지 PNG 압축파일 (.zip)"]
)

uploaded_files = st.file_uploader(
    "변환할 이미지 파일들을 선택하세요 (다중 선택 가능)", 
    type=["png", "jpg", "jpeg", "bmp"], 
    accept_multiple_files=True
)

def natural_sort_key(file_obj):
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', file_obj.name)]

def load_safe_font(font_size):
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

def process_images(files, size_mode, out_format, dpi=300):
    cm_to_pixel = dpi / 2.54
    
    if "A4" in size_mode:
        width_cm, height_cm = 21.0, 29.7
        target_w = int(4.5 * cm_to_pixel)       
        margin = int(0.6 * cm_to_pixel)
        font_size = 24       
        text_padding = 15    
    elif "A3" in size_mode:
        width_cm, height_cm = 29.7, 42.0
        target_w = int(6.0 * cm_to_pixel)       
        margin = int(0.8 * cm_to_pixel)
        font_size = 36       
        text_padding = 20    
    else:
        width_cm, height_cm = 55.0, 100.0
        target_w = int(11.0 * cm_to_pixel)      
        margin = int(1.5 * cm_to_pixel)
        font_size = 64       
        text_padding = 35    
        
    canvas_w, canvas_h = int(width_cm * cm_to_pixel), int(height_cm * cm_to_pixel)
    
    pages = []
    # 📌 투명도를 온전히 담기 위해 투명(RGBA) 도화지로 시작합니다.
    current_canvas = Image.new("RGBA", (canvas_w, canvas_h), (255, 255, 255, 0))
    x_offset, y_offset = margin, margin
    max_row_height = 0
    
    korean_font = load_safe_font(font_size)
    sorted_files = sorted(files, key=natural_sort_key)
    
    for file in sorted_files:
        try:
            file_bytes = file.read()
            with Image.open(io.BytesIO(file_bytes)) as img:
                img = img.convert("RGBA")
                
                orig_w, orig_h = img.size
                target_h = int(target_w * (orig_h / orig_w))
                img_resized = img.resize((target_w, target_h), Image.Resampling.BILINEAR)
                
                if x_offset + target_w + margin > canvas_w:
                    x_offset = margin
                    y_offset += max_row_height + margin
                    max_row_height = 0
                
                total_block_height = target_h + font_size + (text_padding * 2)
                
                if y_offset + total_block_height + margin > canvas_h:
                    pages.append(current_canvas)
                    current_canvas = Image.new("RGBA", (canvas_w, canvas_h), (255, 255, 255, 0))
                    x_offset, y_offset = margin, margin
                    max_row_height = 0
                
                draw = ImageDraw.Draw(current_canvas)
                filename_only = os.path.splitext(file.name)[0]
                
                text_y_position = y_offset + text_padding
                image_y_position = text_y_position + font_size + text_padding
                
                draw.text((x_offset, text_y_position), filename_only, fill=(40, 40, 40, 255), font=korean_font)
                current_canvas.paste(img_resized, (x_offset, image_y_position), img_resized)
                
                x_offset += target_w + margin
                if total_block_height > max_row_height:
                    max_row_height = total_block_height
            del file_bytes
            gc.collect()
        except Exception as e:
            st.error(f"파일 처리 실패 ({file.name}): {e}")
            
    pages.append(current_canvas)
    
    # 3. 사용자가 선택한 포맷에 따른 데이터 빌드 및 리턴
    if "PDF" in out_format:
        pdf_buffer = io.BytesIO()
        if pages:
            # PDF 저장을 위해 투명 배경을 순백색(RGB)으로 압축 변환
            final_pages = [p.convert("RGB") if p.mode == "RGBA" else p for p in pages]
            final_pages[0].save(pdf_buffer, "PDF", resolution=dpi, quality=100, save_all=True, append_images=final_pages[1:])
            pdf_buffer.seek(0)
        for page in pages:
            page.close()
        return pdf_buffer, "application/pdf", "pdf"
    else:
        # ✨ 핵심 추가: 투명 채널(RGBA)을 100% 유지한 채 PNG 파일들을 ZIP으로 압축
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for i, page in enumerate(pages):
                page_img_buffer = io.BytesIO()
                page.save(page_img_buffer, "PNG", resolution=dpi, quality=100)
                page_img_buffer.seek(0)
                zip_file.writestr(f"page_{i+1}.png", page_img_buffer.read())
                page.close()
        zip_buffer.seek(0)
        return zip_buffer, "application/zip", "zip"

# 4. 메인 로직 실행부
if uploaded_files:
    st.success(f"총 {len(uploaded_files)}개의 파일이 선택되었습니다.")
    with st.spinner("요청하신 형식에 맞춰 고품질 파일을 생성 중입니다..."):
        try:
            output_data, mime_type, ext = process_images(uploaded_files, size_option, download_format)
            short_size_name = "A3" if "A3" in size_option else "A4" if "A4" in size_option else "550x1000"
            
            st.download_button(
                label=f"📥 변환 완료 파일 다운로드 받기", 
                data=output_data, 
                file_name=f"변환완료_출력파일_{short_size_name}.{ext}", 
                mime=mime_type
            )
        except Exception as e:
            st.error(f"파일 변환 중 오류가 발생했습니다: {e}")
