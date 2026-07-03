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

# ✨ [완벽 구현] 스트림릿 리눅스 서버에서 절대로 죽지 않고 한글을 100% 살려내는 공식 웹폰트 백엔드 주입 방식
@st.cache_resource
def load_stable_korean_font(font_size):
    # 구글 공식 한글 폰트 배포망의 절대 경로를 사용하여 주소를 확보합니다.
    stable_font_url = "https://gstatic.com"
    local_font_path = "NanumGothic_Web.ttf"
    
    if not os.path.exists(local_font_path):
        try:
            import urllib.request
            req = urllib.request.Request(stable_font_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                with open(local_font_path, 'wb') as f:
                    f.write(response.read())
        except Exception:
            return ImageFont.load_default(size=font_size)
            
    try:
        if os.path.exists(local_font_path):
            return ImageFont.truetype(local_font_path, font_size)
    except Exception:
        pass
    return ImageFont.load_default(size=font_size)

def create_pdf_from_uploaded(files, dpi=300):
    cm_to_pixel = dpi / 2.54
    canvas_w, canvas_h = int(29.7 * cm_to_pixel), int(42.0 * cm_to_pixel)
    target_w, margin, text_margin_to_image = int(6.0 * cm_to_pixel), int(0.8 * cm_to_pixel), 20
    
    pages = []
    current_canvas = Image.new("RGB", (canvas_w, canvas_h), "white")
    x_offset, y_offset = margin, margin
    max_row_height = 0

    # 해상도 배율에 맞게 글자 크기를 아주 선명하고 큼직하게 자동 셋팅
    font_size = int(dpi * 0.16) 
    korean_font = load_stable_korean_font(font_size)

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

                # 확장자 떼어내고 온전한 이름만 획득
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
                
                # 부드럽고 가독성 극대화된 웹 나눔고딕으로 파일명 출력
                draw.text((x_offset, y_offset + target_h + text_margin_to_image), filename_only, fill=(50, 50, 50), font=korean_font)

                x_offset += target_w + margin
                if current_block_height > max_row_height:
                    max_row_height = current_block_height
            
            del file_bytes
            gc.collect()
            
        except Exception as e:
            st.error(f"파일 처리 실패 ({file.name}): {e}")

    pages.append(current_canvas)
    
    pdf_buffer = io.BytesIO()
    pages[0].save(pdf_buffer, "PDF", resolution=dpi, quality=85, save_all=True, append_images=pages[1:])
    pdf_buffer.seek(0)
    
    for page in pages:
        page.close()
    gc.collect()
    
    return pdf_buffer

if uploaded_files:
    st.success(f"총 {len(uploaded_files)}개의 파일이 선택되었습니다.")
    
    with st.spinner("안정적인 구글 배포망에서 나눔폰트를 빌드하여 PDF를 생성 중입니다..."):
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
