from pathlib import Path
import io
import zipfile
import base64

import fitz
import streamlit as st
from PIL import Image

# ==================================================
# Config
# ==================================================
st.set_page_config(
    page_title="PDF Figure Extractor",
    page_icon="📄",
    layout="wide"
)

# ==================================================
# CSS (完全にコントロールされたカードデザイン)
# ==================================================
st.markdown("""
<style>
/* 全体レイアウト */
.block-container {
    max-width: 1400px;
    padding-top: 2rem;
}

/* カード全体のスタイル定義 */
.custom-card {
    border: 1px solid rgba(49, 51, 63, 0.2);
    border-radius: 12px;
    padding: 16px;
    background-color: #ffffff;
    box-shadow: 0 4px 12px rgba(0,0,0,0.03);
    height: 380px; /* カード全体の高さを一律固定 */
    display: flex;
    flex-direction: column;
}

/* 画像を表示するエリア（ここがバラバラにならない肝） */
.card-img-wrapper {
    width: 100%;
    height: 180px; /* 画像エリアの高さを固定 */
    border-radius: 6px;
    background-color: #f8f9fa;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
    margin-bottom: 14px;
}

/* 画像自体のトリミング・フィッティングルール */
.card-img-wrapper img {
    width: 100%;
    height: 100%;
    object-fit: contain; /* 縦横比を維持して枠内に収める（余白はグレー） */
    /* ※もし隙間なく埋めたい場合は 'cover' に変更してください */
}

/* テキスト情報エリア */
.card-info {
    flex-grow: 1; /* 余白を埋めて、ボタンを一番下に押し下げる */
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
}

.card-id {
    font-size: 1.1rem;
    font-weight: 700;
    color: #31333F;
    margin-bottom: 4px;
}

.card-meta {
    font-size: 0.85rem;
    color: #555555;
    line-height: 1.5;
}

/* タイトルヘッダー */
.paper-title {
    font-size: 1.2rem;
    font-weight: 600;
    padding: 12px 16px;
    background: #f0f2f6;
    border-radius: 8px;
    margin-bottom: 20px;
}
</style>
""", unsafe_allow_html=True)

# ==================================================
# Helper Function (画像をHTMLに埋め込む用)
# ==================================================
def get_image_base64(img_bytes):
    """画像バイナリをHTMLのsrc属性で使えるBase64文字列に変換"""
    return base64.b64encode(img_bytes).decode()

# ==================================================
# Header
# ==================================================
st.title("📄 PDF Figure Extractor")
st.caption("PDF内の埋め込み画像を抽出して保存します。")

# ==================================================
# Upload
# ==================================================
uploaded_file = st.file_uploader(
    "PDFファイルを選択してください",
    type=["pdf"]
)

# ==================================================
# Main
# ==================================================
if uploaded_file:
    paper_name = Path(uploaded_file.name).stem

    st.markdown(
        f'<div class="paper-title">📚 対象ファイル: {paper_name}.pdf</div>',
        unsafe_allow_html=True
    )

    # PDF処理
    pdf = fitz.open(
        stream=uploaded_file.read(),
        filetype="pdf"
    )

    images = []
    progress_bar = st.progress(0, text="PDFを解析中...")

    for page_idx in range(len(pdf)):
        page = pdf[page_idx]
        for img_idx, img in enumerate(page.get_images(full=True)):
            try:
                xref = img[0]
                pix = fitz.Pixmap(pdf, xref)

                if pix.n > 4:
                    pix = fitz.Pixmap(fitz.csRGB, pix)

                img_bytes = pix.tobytes("png")
                image = Image.open(io.BytesIO(img_bytes))
                width, height = image.size

                images.append({
                    "page": page_idx + 1,
                    "width": width,
                    "height": height,
                    "image": image,
                    "bytes": img_bytes
                })
            except Exception:
                pass

        progress_bar.progress((page_idx + 1) / len(pdf), text=f"ページをスキャン中... ({page_idx + 1}/{len(pdf)})")

    progress_bar.empty()

    if not images:
        st.warning("PDF内から画像が検出されませんでした。")
    else:
        # 上部サマリーと一括ダウンロード
        col_summary, col_download = st.columns([2, 1])
        with col_summary:
            st.success(f"🎉 成功: {len(images)} 枚の画像を検出しました。")
        
        with col_download:
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                for idx, img in enumerate(images):
                    filename = f"{paper_name}_{idx+1:03d}.png"
                    zf.writestr(filename, img["bytes"])
            
            st.download_button(
                label="📦 全ての画像をZipで保存",
                data=zip_buffer.getvalue(),
                file_name=f"{paper_name}_images.zip",
                mime="application/zip",
                use_container_width=True,
                type="primary"
            )

        st.divider()

        # ==============================================
        # Gallery (カード表示)
        # ==============================================
        COLS = 4
        for start in range(0, len(images), COLS):
            cols = st.columns(COLS)

            for col_idx in range(COLS):
                idx = start + col_idx
                if idx >= len(images):
                    continue

                img = images[idx]
                filename = f"{paper_name}_{idx+1:03d}.png"
                
                # 画像のBase64文字列を取得
                img_b64 = get_image_base64(img["bytes"])

                with cols[col_idx]:
                    # 1. HTMLでカードの外枠、画像、テキストの配置を完全に固定
                    st.markdown(
                        f"""
                        <div class="custom-card">
                            <div class="card-img-wrapper">
                                <img src="data:image/png;base64,{img_b64}" />
                            </div>
                            <div class="card-info">
                                <div class="card-id">#{idx+1:03d}</div>
                                <div class="card-meta">
                                    📄 <b>Page:</b> {img["page"]}<br>
                                    📐 <b>Size:</b> {img["width"]} × {img["height"]} px
                                </div>
                            </div>
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )

                    # 2. 保存ボタンのみStreamlit純正コンポーネントを直下に配置
                    # (CSSの `flex-grow` の効果で、カードのすぐ真下にピタッと配置されます)
                    st.download_button(
                        label="💾 保存",
                        data=img["bytes"],
                        file_name=filename,
                        mime="image/png",
                        use_container_width=True,
                        key=f"save_{idx}"
                    )
                    
                    # カラム間の微調整用スペース
                    st.write("")

else:
    st.info("👆 上部の「PDFファイルを選択」からファイルをアップロードしてください。")