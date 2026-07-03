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

# 🔤 글자 크기를 시원시원하게 대폭 키운 확장형 픽셀 폰트 엔진
class PixelKoreanFont:
    def __init__(self, size):
        self.size = size
        self.glyphs = {
            'ㄱ': [[1,1,1,1],[1,0,0,0],[1,0,0,0],[1,0,0,0]], 'ㄴ': [[1,0,0,0],[1,0,0,0],[1,0,0,0],[1,1,1,1]],
            'ㄷ': [[1,1,1,1],[1,0,0,0],[1,0,0,0],[1,1,1,1]], 'ㄹ': [[1,1,1,1],[1,0,0,1],[1,1,1,1],[1,0,0,1]],
            'ㅁ': [[1,1,1,1],[1,0,0,1],[1,0,0,1],[1,1,1,1]], 'ㅂ': [[1,0,0,1],[1,1,1,1],[1,0,0,1],[1,1,1,1]],
            'ㅅ': [[0,1,1,0],[1,0,0,1],[1,0,0,1],[1,0,0,1]], 'ㅇ': [[0,1,1,0],[1,0,0,1],[1,0,0,1],[0,1,1,0]],
            'ㅈ': [[1,1,1,1],[0,0,1,0],[0,1,0,0],[1,0,0,0]], 'ㅊ': [[1,1,1,1],[1,1,1,1],[0,1,0,0],[0,1,0,0]],
            'ㅋ': [[1,1,1,1],[1,0,0,0],[1,1,1,1],[1,0,0,0]], 'ㅌ': [[1,1,1,1],[1,1,1,1],[1,0,0,0],[1,1,1,1]],
            'ㅍ': [[1,1,1,1],[1,0,0,1],[1,1,1,1],[1,0,0,1]], 'ㅎ': [[0,1,1,0],[1,1,1,1],[1,0,0,1],[1,1,1,1]],
            'ㅏ': [[0,1,0,0],[0,1,1,0],[0,1,0,0],[0,1,0,0]], 'ㅓ': [[0,1,0,0],[1,1,0,0],[0,1,0,0],[0,1,0,0]], 
            'ㅗ': [[0,1,0,0],[1,1,1,0],[0,0,0,0],[0,0,0,0]], 'ㅜ': [[0,0,0,0],[1,1,1,0],[0,1,0,0],[0,1,0,0]], 
            'ㅡ': [[0,0,0,0],[1,1,1,1],[0,0,0,0],[0,0,0,0]], 'ㅣ': [[0,1,0,0],[0,1,0,0],[0,1,0,0],[0,1,0,0]], 
            'ㅐ': [[0,1,0,1],[0,1,1,1],[0,1,0,1],[0,1,0,1]]
        }
        
    def draw_text(self, draw, position, text, color=(30, 30, 30)):
        x, y = position
        # ✨ 글자가 크게 보이도록 기본 스케일을 4배 이상 확대 적용 (굵고 큼직한 가시성 확보)
        scale = max(4, self.size // 4) 
        
        for char in text:
            if ord(char) < 128:
                # 영문/숫자도 크게 맞춤 출력
                draw.text((x, y), char, fill=color, font_size=scale*3)
                x += scale * 3
                continue
                
            char_code = ord(char) - 44032
            if 0 <= char_code <= 11171:
                cho = char_code // 588
                jung = (char_code % 588) // 28
                
                cho_list = ['ㄱ','ㄲ','ㄴ','ㄷ','ㄸ','ㄹ','ㅁ','ㅂ','ㅃ','ㅅ','ㅆ','ㅇ','ㅈ','ㅉ','ㅊ','ㅋ','ㅌ','ㅍ','ㅎ']
                jung_list = ['ㅏ','ㅐ','ㅑ','ㅒ','ㅓ','ㅔ','ㅕ','ㅖ','ㅗ','ㅘ','ㅙ','ㅚ','ㅛ','ㅜ','ㅝ','ㅞ','ㅟ','ㅠ','ㅡ','ㅢ','ㅣ']
                
                c_target = cho_list[cho] if cho < len(cho_list) else 'ㄱ'
                j_target = jung_list[jung] if jung < len(jung_list) else 'ㅡ'
                
                # 초성 크게 그리기
                if c_target in self.glyphs:
                    matrix = self.glyphs[c_target]
                    for r_idx, row in enumerate(matrix):
                        for c_idx, val in enumerate(row):
                            if val:
                                draw.rectangle([x + c_idx*scale, y + r_idx*scale, x + (c_idx+1)*scale, y + (r_idx+1)*scale], fill=color)
                
                # 중성 크게 그리기
                if j_target in self.glyphs:
                    matrix = self.glyphs[j_target]
                    for r_idx, row in enumerate(matrix):
                        for c_idx, val in enumerate(row):
                            if val:
                                draw.rectangle([x + (c_idx+5)*scale, y + r_idx*scale, x + (c_idx+6)*scale, y + (r_idx+1)*scale], fill=color)
                                
                x += scale * 11 # 글자 크기에 맞춰 옆 글자와의 여백 간격 확보
            else:
                draw.text((x, y), char, fill=color, font_size=scale*3)
                x += scale * 5

def create_pdf_from_uploaded(files, dpi=300):
    cm_to_pixel = dpi / 2.54
    canvas_w, canvas_h = int(29.7 * cm_to_pixel), int(42.0 * cm_to_pixel)
    target_w, margin, text_margin_to_image = int(6.0 * cm_to_pixel), int(0.8 * cm_to_pixel), 30
    
    pages = []
    current_canvas = Image.new("RGB", (canvas_w, canvas_h), "white")
    x_offset, y_offset = margin, margin
    max_row_height = 0

    font_size = int(dpi * 0.12)
    korean_font_engine = PixelKoreanFont(font_size)

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
                
                # ✨ 글자가 대폭 커진 만큼 하단 여백 공간도 여유롭게 조정
                actual_text_height = font_size * 3 

                current_block_height = target_h + text_margin_to_image + actual_text_height
                if y_offset + current_block_height + margin > canvas_h:
                    pages.append(current_canvas)
                    current_canvas = Image.new("RGB", (canvas_w, canvas_h), "white")
                    x_offset, y_offset = margin, margin
                    max_row_height = 0

                current_canvas.paste(img_resized, (x_offset, y_offset))
                
                draw = ImageDraw.Draw(current_canvas)
                text_position = (x_offset, y_offset + target_h + text_margin_to_image)
                korean_font_engine.draw_text(draw, text_position, filename_only, color=(40, 40, 40))

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
    
    with st.spinner("가상 한글 엔진을 확대 구동하여 PDF를 생성 중입니다..."):
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
