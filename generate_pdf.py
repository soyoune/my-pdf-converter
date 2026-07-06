import os
import sys
import re
import gc
import zipfile
import io

try:
    import streamlit as st
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "streamlit"])
    import streamlit as st

# 일러스트 방식 투명 PDF를 위한 reportlab 라이브러리
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "reportlab"])
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader

from PIL import Image

# 1. 페이지 기본 설정 및 레이아웃
st.set_page_config(page_title="완벽 투명 다중 변환기", layout="centered")
st.title("🎨 이미지 다중 규격 & 완벽 투명 변환 프로그램")
st.write("원하는 규격을 선택한 후, 일러스트 방식의 투명 PDF 또는 투명 PNG 압축파일로 다운로드하세요.")

# 2. UI 구성 요소
size_option = st.selectbox(
    "출력하실 용지 크기를 선택하세요:",
    ["A3 (29.7cm x 42.0cm)", "A4 (21.0cm x 29.7cm)", "사용자 정의 (55.0cm x 100.0cm)"]
)

download_format = st.radio(
    "저장 방식을 선택하세요:",
    ["일러스트 방식 투명 PDF (뷰어에서도 격자 유지)", "투명도 100% 유지 PNG 압축파일 (.zip)"]
)

uploaded_files = st.file_uploader(
    "변환할 이미지 파일들을 선택하세요 (다중 선택 가능)", 
    type=["png"], 
    accept_multiple_files=True
)

def natural_sort_key(file_obj):
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', file_obj.name)]

# --- 내부 처리 함수 ---
def build_outputs(files, size_mode, out_format):
    scale = 72 / 2.54  # cm to point (reportlab 단위 기준)
    
    if "A4" in size_mode:
        canvas_w, canvas_h = 21.0 * scale, 29.7 * scale
        target_w = 4.5 * scale
        margin = 0.6 * scale
        font_size = 8  
        text_padding = 4
    elif "A3" in size_mode:
        canvas_w, canvas_h = 29.7 * scale, 42.0 * scale
        target_w = 6.0 * scale
        margin = 0.8 * scale
        font_size = 12
        text_padding = 6
    else:
        canvas_w, canvas_h = 55.0 * scale, 100.0 * scale
        target_w = 11.0 * scale
        margin = 1.5 * scale
        font_size = 18
        text_padding = 10

    sorted_files = sorted(files, key=natural_sort_key)

    # 1) 사용자가 [일러스트 방식 투명 PDF]를 선택한 경우
    if "PDF" in out_format:
        pdf_buffer = io.BytesIO()
        pdf_canvas = canvas.Canvas(pdf_buffer, pagesize=(canvas_w, canvas_h))
        
        x_offset, y_offset = margin, canvas_h - margin
        max_row_height = 0
        
        for file in sorted_files:
            file_bytes = file.read()
            with Image.open(io.BytesIO(file_bytes)) as pil_img:
                orig_w, orig_h = pil_img.size
                target_h = target_w * (orig_h / orig_w)
            
            total_block_height = target_h + font_size + (text_padding * 2)
            
            if x_offset + target_w > canvas_w - margin:
                x_offset = margin
                y_offset -= (max_row_height + margin)
                max_row_height = 0
                
            if y_offset - total_block_height < margin:
                pdf_canvas.showPage()
                x_offset, y_offset = margin, canvas_h - margin
                max_row_height = 0
                
            filename_only = os.path.splitext(file.name)[0]
            text_y = y_offset - text_padding - font_size
            image_y = text_y - text_padding - target_h
            
            pdf_canvas.setFont("Helvetica", font_size)
            pdf_canvas.setFillColorRGB(0.15, 0.15, 0.15)
            pdf_canvas.drawString(x_offset, text_y, filename_only)
            
            img_reader = ImageReader(io.BytesIO(file_bytes))
            pdf_canvas.drawImage(img_reader, x_offset, image_y, width=target_w, height=target_h, mask='auto')
            
            x_offset += target_w + margin
            if total_block_height > max_row_height:
                max_row_height = total_block_height
            gc.collect()
            
        pdf_canvas.save()
        pdf_buffer.seek(0)
        return pdf_buffer, "application/pdf", "pdf"

    # 2) 사용자가 [투명 PNG 압축파일]을 선택한 경우
    else:
        from PIL import ImageDraw, ImageFont
        # Pillow 전용 픽셀 스케일 재생산
        dpi = 300
        px_scale = dpi / 2.54
        px_w, px_h = int((canvas_w/scale)*px_scale), int((canvas_h/scale)*px_scale)
        p_target_w = int((target_w/scale)*px_scale)
        p_margin = int((margin/scale)*px_scale)
        p_font_size = int(font_size * 2.5) # 가독성을 위한 폰트 스케일 보정
        p_padding = int(text_padding * 2.5)
        
        try:
            korean_font = ImageFont.truetype("NanumGothic.ttf", p_font_size)
        except:
            korean_font = ImageFont.load_default()

        pages = []
        current_canvas = Image.new("RGBA", (px_w, px_h), (255, 255, 255, 0))
        x_off, y_off = p_margin, p_margin
        max_h = 0
        
        for file in sorted_files:
            file_bytes = file.read()
            with Image.open(io.BytesIO(file_bytes)) as img:
                img = img.convert("RGBA")
                orig_w, orig_h = img.size
                p_target_h = int(p_target_w * (orig_h / orig_w))
                img_resized = img.resize((p_target_w, p_target_h), Image.Resampling.BILINEAR)
                
                if x_off + p_target_w + p_margin > px_w:
                    x_off = p_margin
                    y_off += max_h + p_margin
                    max_h = 0
                    
                total_h = p_target_h + p_font_size + (p_padding * 2)
                
                if y_off + total_h + p_margin > px_h:
                    pages.append(current_canvas)
                    current_canvas = Image.new("RGBA", (px_w, px_h), (255, 255, 255, 0))
                    x_off, y_off = p_margin, p_margin
                    max_h = 0
                    
                draw = ImageDraw.Draw(current_canvas)
                filename_only = os.path.splitext(file.name)[0]
                
                t_y = y_off + p_padding
                i_y = t_y + p_font_size + p_padding
                
                draw.text((x_off, t_y), filename_only, fill=(40, 40, 40, 255), font=korean_font)
                current_canvas.paste(img_resized, (x_off, i_y), img_resized)
                
                x_off += p_target_w + p_margin
                if total_h > max_h:
                    max_h = total_h
            gc.collect()
            
        pages.append(current_canvas)
        
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

# 3. 메인 로직 실행부
if uploaded_files:
    st.success(f"총 {len(uploaded_files)}개의 파일이 선택되었습니다.")
    with st.spinner("선택하신 포맷으로 완벽 투명 빌드를 진행 중입니다..."):
        try:
            output_data, mime_type, ext = build_outputs(uploaded_files, size_option, download_format)
            short_size_name = "A3" if "A3" in size_option else "A4" if "A4" in size_option else "550x1000"
            
            st.download_button(
                label=f"📥 변환 완료 파일 다운로드", 
                data=output_data, 
                file_name=f"완벽투명_변환결과_{short_size_name}.{ext}", 
                mime=mime_type
            )
        except Exception as e:
            st.error(f"파일 변환 중 오류가 발생했습니다: {e}")
