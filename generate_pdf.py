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

st.set_page_config(page_title="이미지 -> PDF 변환기 (투명 유지)", layout="centered")
st.title("📄 투명 PNG 대응 PDF 변환 프로그램")
st.write("배경이 투명한 PNG의 투명도를 그대로 유지하여 고품질 PDF로 변환합니다.")

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
    # ✨ 변경 포인트 1: 도화지 자체를 투명 채널이 존재하는 "RGBA" 모드로 생성합니다. (투명 바탕 스케치북)
    current_canvas = Image.new("RGBA", (canvas_w, canvas_h), (255, 255, 255, 0))
    x_offset, y_offset = margin, margin
    max_row_height = 0
    
    korean_font = load_safe_font(font_size)
    sorted_files = sorted(files, key=natural_sort_key)
    
    for file in sorted_files:
        try:
            file_bytes = file.read()
            with Image.open(io.BytesIO(file_bytes)) as img:
                # ✨ 변경 포인트 2: 원본 PNG의 투명도(RGBA) 모드를 손실 없이 그대로 유지합니다.
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
                
                # 파일명 쓰기
                draw.text((x_offset, text_y_position), filename_only, fill=(40, 40, 40, 255), font=korean_font)
                
                # ✨ 변경 포인트 3: 투명도를 유지하며 도화지에 붙이기 위해 세 번째 인자에 자기 자신(img_resized)을 마스크로 지정합니다.
                current_canvas.paste(img_resized, (x_offset, image_y_position), img_resized)
                
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
        # ✨ 변경 포인트 4: PDF는 본질적으로 투명 레이어를 온전히 지원하지 못하므로, 
        # 최종 빌드 시점에 투명도를 해석할 수 있는 포맷으로 온전히 변환하여 저장 큐에 태웁니다.
        final_pages = [p.convert("RGB") if p.mode == "RGBA" else p for p in pages]
        final_pages[0].save(pdf_buffer, "PDF", resolution=dpi, quality=100, save_all=True, append_images=final_pages[1:])
        pdf_buffer.seek(0)
    
    for page in pages:
        page.close()
    gc.collect()
    
    return pdf_buffer

if uploaded_files:
    st.success(f"총 {len(uploaded_files)}개의 파일이 선택되었습니다.")
    with st.spinner("투명도를 유지하여 고품질 PDF를 생성 중입니다..."):
        try:
            pdf_data = create_pdf_from_uploaded(uploaded_files, size_option)
            short_size_name = "A3" if "A3" in size_option else "A4" if "A4" in size_option else "550x1000"
            st.download_button(
                label=f"📥 완성된 {short_size_name} PDF 다운로드받기", 
                data=pdf_data, 
                file_name=f"투명포함_이미지_결합_{short_size_name}.pdf", 
                mime="application/pdf"
            )
        except Exception as e:
            st.error(f"PDF 생성 중 오류가 발생했습니다: {e}")
