import sys
import subprocess
import os

# [최초 1회 실행] 필요한 웹 라이브러리가 없다면 자동으로 설치합니다.
try:
    import streamlit as st
except ImportError:
    py_path = sys.executable
    subprocess.check_call([py_path, "-m", "pip", "install", "streamlit"])
    import streamlit as st

from PIL import Image, ImageEnhance, ImageDraw, ImageFont
import io

st.set_page_config(page_title="이미지 -> A3 PDF 변환기", layout="centered")
st.title("📄 이미지 A3 PDF 변환 프로그램")
st.write("원하는 이미지 파일만 아래에 올리면 고품질 A3 PDF 파일로 결합해 드립니다.")

# ✨ 핵심 기능: 사용자가 직접 파일들을 올릴 수 있는 업로더 창
uploaded_files = st.file_uploader(
    "변환할 이미지 파일들을 선택하세요 (다중 선택 가능)", 
    type=["png", "jpg", "jpeg", "bmp"], 
    accept_multiple_files=True
)

def create_pdf_from_uploaded(files, dpi=300):
    cm_to_pixel = dpi / 2.54
    canvas_w, canvas_h = int(29.7 * cm_to_pixel), int(42.0 * cm_to_pixel)
    target_w, margin, text_margin_to_image = int(6.0 * cm_to_pixel), int(0.8 * cm_to_pixel), 15
    
    pages = []
    current_canvas = Image.new("RGB", (canvas_w, canvas_h), "white")
    x_offset, y_offset = margin, margin
    max_row_height = 0

    font_path = "C:\\Windows\\Fonts\\malgun.ttf"
    font_size = int(dpi * 0.12)
    try:
        korean_font = ImageFont.truetype(font_path, font_size)
    except IOError:
        korean_font = ImageFont.load_default(size=font_size)

    for file in files:
        try:
            # 업로드된 파일 데이터를 이미지로 읽기
            img = Image.open(file).convert("RGB")
            orig_w, orig_h = img.size
            target_h = int(target_w * (orig_h / orig_w))
            img_resized = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
            
            img_resized = ImageEnhance.Sharpness(img_resized).enhance(1.3)

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
        except Exception as e:
            st.error(f"파일 처리 실패 ({file.name}): {e}")

    pages.append(current_canvas)
    
    # PDF를 메모리 스트림에 저장하여 바로 다운로드할 수 있게 변환
    pdf_buffer = io.BytesIO()
    pages[0].save(pdf_buffer, "PDF", resolution=dpi, quality=100, save_all=True, append_images=pages[1:])
    pdf_buffer.seek(0)
    return pdf_buffer

if uploaded_files:
    st.success(f"총 {len(uploaded_files)}개의 파일이 선택되었습니다.")
    
    with st.spinner("PDF 파일을 생성하고 있습니다..."):
        pdf_data = create_pdf_from_uploaded(uploaded_files)
        
    # 다운로드 버튼 활성화
    st.download_button(
        label="📥 완성된 PDF 다운로드받기",
        data=pdf_data,
        file_name="선택된_이미지_결합_A3.pdf",
        mime="application/pdf"
    )

if __name__ == "__main__":
    # 처음 딱 한 번만 웹서버를 자동으로 실행해주는 코드입니다.
    if "streamlit" not in sys.argv[0]:
        print("\n🌐 웹브라우저 창을 여는 중입니다. 잠시만 기다려주세요...")
        os.system(f'"{sys.executable}" -m streamlit run "{__file__}"')
