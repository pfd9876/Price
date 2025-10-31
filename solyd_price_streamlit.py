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

def main():
    st.title("📊 Solyd Price Inserter (Online Version)")
    st.write("Upload your Excel file below. The app will read the local `solyd_ids_products.csv` and insert matching prices.")

    # --- 1. Upload Excel file ---
    uploaded_excel = st.file_uploader("Upload Excel file to process", type=["xlsx"])

    if not uploaded_excel:
        st.info("Please upload an Excel file to start.")
        st.stop()

    # --- 2. Validate CSV file exists ---
    if not CSV_PATH.exists():
        die(f"CSV not found: {CSV_PATH}")

    # --- 3. Read CSV data ---
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

    # --- 4. Read uploaded Excel ---
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

    st.write(f"🔍 Total rows processed: {rows_total}")
    st.write(f"✅ IDs matched and prices inserted: {rows_matched}")
    st.write(f"⚠️ IDs not matched: {rows_total - rows_matched}")

    # --- 5. Prepare Excel for download ---
    buffer = io.BytesIO()
    df_excel.to_excel(buffer, index=False)
    buffer.seek(0)

    st.download_button(
        label="⬇️ Download Updated Excel File",
        data=buffer,
        file_name="updated_price_comparison.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

if __name__ == "__main__":
    main()
