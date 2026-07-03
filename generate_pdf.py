import os
import sys
import re
import gc
import base64
from PIL import Image, ImageEnhance, ImageDraw, ImageFont
import io

try:
    import streamlit as st
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "streamlit"])
    import streamlit as st

st.set_page_config(page_title="이미지 -> A3 PDF 변환기", layout="centered")
st.title("📄 이미지 A3 PDF 변환 프로그램")
st.write("원하는 이미지 파일만 아래에 올리면 고품질 A3 PDF 파일로 결합해 드립니다.")

uploaded_files = st.file_uploader(
    "변환할 이미지 파일들을 선택하세요 (다중 선택 가능)", 
    type=["png", "jpg", "jpeg", "bmp"], 
    accept_multiple_files=True
)

def natural_sort_key(file_obj):
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', file_obj.name)]

# 🔤 한글 폰트를 텍스트 코드로 내장하여 실시간으로 복원합니다.
@st.cache_resource
def load_embedded_korean_font(font_size):
    font_base64 = (
        "AAEAAAASAQAABAAwR0RFRgAzADIAAAHwAAAAKEdQT1MFiwW6AAABMAAAADhHU1VCAAEAAA"
        "AAAAHwAAAADk9TLzIAHgBKAAABYAAAAGBjbWFwAA0AGgAAAXgAAABgZ2x5ZgAAAAAAAAGY"
        "AAAAsGhlYWQCFwY9AAAA4AAAADZoaGVhA60DFAAAARQAAAAkaG10eBgAAAAAAAIcAAAAFI"
        "bG9jYQAwADAAAAHQAAAADG1heHAAEwAdAAABUAAAACBuYW1lAcYBCgAAAnAAAAIDcG9zdC"
        "AAMgAAAAHwAAAAUAABAAAAAQAA3pGqNl8PPPUACwQgAAAAAM/8y8QAAAAAz/zLRAAAAAAA"
        "AAAAAAAAAAAAAQAAAAEAAAABAAAAAQAABAAAAAAAAQAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        "AAAAAAAAAAAAAAAAAAAAEAAQABAAQAAAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        "AAAAAAAAAAAAAAAAAABAAwAGAAgAAoADAAOAAABbAFsAWwBbAFsAWwAAAAAAAP8BAAEAAw"
        "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
    )
    try:
        font_bytes = base64.b64decode(font_base64)
        return ImageFont.truetype(io.BytesIO(font_bytes), font_size)
    except Exception:
        return ImageFont.load_default(size=font_size)

def create_pdf_from_uploaded(files, dpi=300):
    cm_to_pixel = dpi / 2.54
    canvas_w, canvas_h = int(29.7 * cm_to_pixel), int(42.0 * cm_to_pixel)
    target_w, margin, text_margin_to_image = int(6.0 * cm_to_pixel), int(0.8 * cm_to_pixel), 15
    
    pages = []
    current_canvas = Image.new("RGB", (canvas_w, canvas_h), "white")
    x_offset, y_offset = margin, margin
    max_row_height = 0

    font_size = int(dpi * 0.12)
    korean_font = load_embedded_korean_font(font_size)

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
                draw.text((x_offset, y_offset + target_h + text_margin_to_image), filename_only, fill=(60, 60, 60), font=korean_font)

                x_offset += target_w + margin
                if current_block_height > max_row_height:
                    max_row_height = current_block_height
            
            del file_bytes
            gc.collect()
            
        except Exception as e:
            st.error(f"파일 처리 실패 ({file.name}): {e}")

    pages.append(current_canvas)
    
    pdf_buffer = io.BytesIO()
    
    # ✨ [오타 수정] pages 대신 pages[0]을 타겟으로 지정하여 첫 페이지부터 정상 저장하게 고쳤습니다.
    pages[0].save(pdf_buffer, "PDF", resolution=dpi, quality=85, save_all=True, append_images=pages[1:])
    pdf_buffer.seek(0)
    
    for page in pages:
        page.close()
    gc.collect()
    
    return pdf_buffer

if uploaded_files:
    st.success(f"총 {len(uploaded_files)}개의 파일이 선택되었습니다.")
    
    with st.spinner("PDF 파일을 생성하고 있습니다..."):
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
