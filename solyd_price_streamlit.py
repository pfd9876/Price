import streamlit as st
import pandas as pd
from pathlib import Path
import io
import sys
import glob

# ------------- Config (same as your original) -------------
CSV_PATH = Path("solyd_ids_products.csv")          # Local CSV file in same folder
EXCEL_GLOB = "output_data/price_comparison_*.xlsx"  # Not used online, kept for compatibility
ID_COL_INDEX_CSV = 0
PRICE_COL_INDEX_CSV = 1
ID_COL_NAME_EXCEL = 0
NEW_PRICE_COL_NAME = "solyd-price"
CASE_SENSITIVE = True
STRIP_SPACES = True
FORCE_SEP = None
PLACEHOLDER_VALUE = "N.A"
# ----------------------------------------------------------

# =========================
# Page Meta & Global Styles (UI ONLY)
# =========================
st.set_page_config(
    page_title="Solyd Price Inserter",
    page_icon="💾",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .block-container{padding-top:2rem;padding-bottom:3rem}
    .spi-title{font-size:2rem;font-weight:800;letter-spacing:.2px}
    .spi-subtle{color:var(--text-color-secondary,#7a7f87)}
    .spi-card{background:rgba(127,127,127,.04);border:1px solid rgba(127,127,127,.18);border-radius:14px;padding:1.1rem}
    .spi-section{font-weight:700;font-size:1.05rem;margin:.1rem 0 .6rem}
    .stButton>button{border-radius:12px !important;padding:.6rem 1rem;font-weight:600}
    .stDownloadButton{margin-top:.35rem}
    .stDataFrame{border-radius:12px;overflow:hidden}
    section[data-testid='stSidebar']{border-right:1px solid rgba(127,127,127,.15)}
    .spi-badge{display:inline-block;padding:.2rem .55rem;border-radius:999px;font-size:.75rem;font-weight:700;border:1px solid rgba(127,127,127,.25);margin-left:.35rem}
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================
# Header (UI ONLY)
# =========================
left, right = st.columns([0.8, 0.2])
with left:
    st.markdown("<div class='spi-title'>📊 Solyd Price Inserter</div>", unsafe_allow_html=True)
    st.caption("Read local CSV of IDs/prices, insert matches into your uploaded Excel, and download the updated file.")
with right:
    st.markdown("<div style='text-align:right;'><span class='spi-badge'>v1</span><span class='spi-badge'>Modern UI</span></div>", unsafe_allow_html=True)

# =========================
# Sidebar guide (UI ONLY)
# =========================
with st.sidebar:
    st.header("How it works ✨")
    st.markdown(
        """
        1) **Upload** the Excel file to update.  
        2) App reads the local **solyd_ids_products.csv**.  
        3) It inserts prices where IDs match.  
        4) **Download** the updated Excel.
        """
    )
    st.divider()
    st.subheader("Notes")
    st.markdown(
        """
        - Matching respects the current **case sensitivity** and **space stripping** flags.
        - New prices are written to **`solyd-price`** column; unmatched stay **N.A**.
        - No processing logic was changed—this is a visual refresh only.
        """
    )

# =========================
# ORIGINAL FUNCTIONS (UNTOUCHED LOGIC)
# =========================

def norm(x: str) -> str:
    if x is None:
        return ""
    s = str(x)
    if STRIP_SPACES:
        s = s.strip()
    if not CASE_SENSITIVE:
        s = s.lower()
    return s

def die(msg: str):
    st.error(f"[ERROR] {msg}")
    st.stop()

def find_latest_excel(pattern: str):
    """Kept for backward compatibility."""
    files = glob.glob(pattern)
    if not files:
        return None
    latest_file = max(files, key=Path)
    return Path(latest_file)

# =========================
# MAIN — same processing flow, presented with nicer sections
# =========================

def main():
    # Title area (kept to mirror original st.title usage)
    st.write("")
    st.markdown("<div class='spi-section'>1) Upload Excel</div>", unsafe_allow_html=True)
    with st.container():
        st.markdown("<div class='spi-card'>", unsafe_allow_html=True)
        uploaded_excel = st.file_uploader("Upload Excel file to process", type=["xlsx"], key="excel")
        st.markdown("</div>", unsafe_allow_html=True)

    if not uploaded_excel:
        st.info("Please upload an Excel file to start.")
        st.stop()

    # Validate CSV (unchanged)
    st.markdown("<div class='spi-section' style='margin-top:1rem;'>2) Read Local CSV</div>", unsafe_allow_html=True)
    if not CSV_PATH.exists():
        die(f"CSV not found: {CSV_PATH}")

    try:
        if FORCE_SEP is None:
            df_csv = pd.read_csv(CSV_PATH, dtype=str, encoding="utf-8-sig", sep=None, engine="python")
        else:
            df_csv = pd.read_csv(CSV_PATH, dtype=str, encoding="utf-8-sig", sep=FORCE_SEP)
    except Exception as e:
        try:
            df_csv = pd.read_csv(CSV_PATH, dtype=str, encoding="utf-8-sig")
        except Exception:
            die(f"Failed to read CSV: {e}")

    if ID_COL_INDEX_CSV >= len(df_csv.columns) or PRICE_COL_INDEX_CSV >= len(df_csv.columns):
        die("ID or Price column index in CSV is out of range.")

    id_col_csv = df_csv.columns[ID_COL_INDEX_CSV]
    price_col_csv = df_csv.columns[PRICE_COL_INDEX_CSV]

    price_lookup = {}
    for _, row in df_csv.iterrows():
        normalized_id = norm(row[id_col_csv])
        if normalized_id not in price_lookup:
            price_lookup[normalized_id] = row[price_col_csv]

    st.success(f"✅ Loaded {len(price_lookup)} unique IDs and prices from {CSV_PATH.name}.")

    # Read uploaded Excel (unchanged)
    st.markdown("<div class='spi-section' style='margin-top:1rem;'>3) Process Excel</div>", unsafe_allow_html=True)
    try:
        df_excel = pd.read_excel(uploaded_excel, dtype=str)
    except Exception as e:
        die(f"Failed to read uploaded Excel file: {e}")

    if ID_COL_NAME_EXCEL >= len(df_excel.columns):
        die("ID column index in Excel is out of range.")

    id_col_excel = df_excel.columns[ID_COL_NAME_EXCEL]
    df_excel[NEW_PRICE_COL_NAME] = PLACEHOLDER_VALUE

    rows_matched = 0
    rows_total = len(df_excel)

    for index, row in df_excel.iterrows():
        wanted_id_norm = norm(row[id_col_excel])
        if wanted_id_norm in price_lookup:
            price = price_lookup[wanted_id_norm]
            df_excel.at[index, NEW_PRICE_COL_NAME] = price
            rows_matched += 1

    # Quick metrics (UI only)
    m1, m2, m3 = st.columns(3)
    m1.metric("Total rows processed", f"{rows_total:,}")
    m2.metric("IDs matched", f"{rows_matched:,}")
    m3.metric("Not matched", f"{rows_total - rows_matched:,}")

    with st.expander("Preview first 15 rows (after insertion)", expanded=False):
        st.dataframe(df_excel.head(15), use_container_width=True)

    # Prepare Excel for download (unchanged)
    st.markdown("<div class='spi-section' style='margin-top:1rem;'>4) Download</div>", unsafe_allow_html=True)
    buffer = io.BytesIO()
    df_excel.to_excel(buffer, index=False)
    buffer.seek(0)

    st.download_button(
        label="⬇️ Download Updated Excel File",
        data=buffer,
        file_name="updated_price_comparison.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

    st.caption("Logic unchanged. This is a UI refresh only.")

if __name__ == "__main__":
    main()
