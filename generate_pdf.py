import os
import sys
import re
import urllib.request
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

# 🔢 [정렬 기능] 숫자 크기를 먼저 비교하고, 같다면 글자순 정렬
def natural_sort_key(file_obj):
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', file_obj.name)]

# 🌐 [한글 깨짐 해결] 인터넷에서 무료 한글 폰트를 실시간으로 가져오는 함수
@st.cache_resource
def load_online_korean_font(font_size):
    font_url = "https://github.com"
    local_font_path = "NanumGothic.ttf"
    
    # 서버에 폰트가 없다면 구글 폰트 저장소에서 직접 다운로드합니다.
    if not os.path.exists(local_font_path):
        try:
            urllib.request.urlretrieve(font_url, local_font_path)
        except Exception:
            return ImageFont.load_default(size=font_size)
            
    try:
        return ImageFont.truetype(local_font_path, font_size)
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

    # 폰트 크기 및 세팅
    font_size = int(dpi * 0.12)
    korean_font = load_online_korean_font(font_size)

    # 🔄 파일 이름 규칙에 맞게 자동 정렬 적용
    sorted_files = sorted(files, key=natural_sort_key)

    for file in sorted_files:
        try:
            img = Image.open(file).convert("RGB")
            orig_w, orig_h = img.size
            target_h = int(target_w * (orig_h / orig_w))
            img_resized = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
            img_resized = ImageEnhance.Sharpness(img_resized).enhance(1.3)

            if x_offset + target_w + margin > canvas_w:
                x_offset = margin
                y_offset += max_row_height + margin
                max_row_height = 0

            # 확장자를 제외한 파일 이름 추출
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
        except Exception as e:
            st.error(f"파일 처리 실패 ({file.name}): {e}")

    pages.append(current_canvas)
    
    pdf_buffer = io.BytesIO()
    pages[0].save(pdf_buffer, "PDF", resolution=dpi, quality=100, save_all=True, append_images=pages[1:])
    pdf_buffer.seek(0)
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
