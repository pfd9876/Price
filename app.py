import streamlit as st
import pandas as pd
import re
from pathlib import Path
from datetime import datetime
import zipfile
import io
import os
import subprocess

# =========================================================
# ✅ CUSTOM UI STYLING (does NOT affect your logic)
# =========================================================

st.set_page_config(page_title="Price Comparison Tool", layout="wide")

# Inject custom CSS
st.markdown("""
<style>

/* Import Poppins font */
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600&display=swap');

html, body, [class*="css"]  {
    font-family: 'Poppins', sans-serif;
}

/* Background gradient */
body {
    background: linear-gradient(180deg, #f7f7f7 0%, #ffffff 45%) !important;
}

/* Top contact bar */
.top-bar {
    background: #ffffff;
    padding: 6px 30px;
    font-size: 13px;
    color: #111;
    border-bottom: 1px solid #e5e5e5;
}

/* Header main bar */
.header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: #ffffff;
    padding: 12px 30px;
    border-bottom: 1px solid #eee;
}

/* Logo */
.header img {
    height: 55px;
}

/* Menu buttons */
.navbar {
    display: flex;
    gap: 18px;
}
.nav-btn {
    padding: 8px 16px;
    border-radius: 6px;
    font-weight: 500;
    color: #000;
    text-decoration: none;
    background: transparent;
    border: 1px solid transparent;
    transition: 0.2s;
}
.nav-btn:hover {
    border-bottom: 2px solid #ff7a00;
    color: #ff7a00;
}

/* Orange buttons for Streamlit */
.stButton>button {
    background-color: #ff7a00 !important;
    color: white !important;
    border-radius: 6px;
    padding: 8px 18px;
    font-weight: 600;
    border: none;
}
.stButton>button:hover {
    background-color: #e36a00 !important;
    transform: translateY(-1px);
}

/* Form container sections */
.block-container {
    padding-top: 1rem !important;
}

</style>
""", unsafe_allow_html=True)

# =========================================================
# ✅ HEADER HTML (matches PaulPromo style)
# =========================================================

st.markdown(f"""
<div class="top-bar">
    ✉️ info@paulpromo.be &nbsp;&nbsp;|&nbsp;&nbsp; Livraison 72h • Paiement sécurisé • TVA 6%
</div>

<div class="header">
    <img src="https://paulpromo.be/cdn/shop/files/dernier-logo-paul-promo_a4138806-02d7-40d9-9ca2-8393e28810ac_300x.png">

    <div class="navbar">
        <a class="nav-btn" href="#" target="_self">Accueil</a>
        <a class="nav-btn" href="https://price-compare-2.streamlit.app/" target="_blank">Solyd Prices</a>
        <a class="nav-btn" href="#" target="_self">Chaudières</a>
        <a class="nav-btn" href="#" target="_self">Chauffage</a>
        <a class="nav-btn" href="#" target="_self">Pompes à Chaleur</a>
    </div>
</div>
""", unsafe_allow_html=True)

# =========================================================
# ✅ --- ORIGINAL APP BELOW (UNTOUCHED) ---
# =========================================================

st.title("Price Comparison Tool")

# --- File Uploads ---
st.header("Upload Supplier Files")
van_file   = st.file_uploader("Vanoirschot Excel (.xlsx)", type=["xlsx"], key="van")
facq_file  = st.file_uploader("Facq Excel (.xlsx)", type=["xlsx"], key="facq")
desco_file = st.file_uploader("Desco Excel (.xlsx)", type=["xlsx"], key="desco")

st.header("Upload Store CSV")
store_file = st.file_uploader("Store CSV file", type=["csv"], key="store")

def read_excel_smart(file, name):
    if file is None: return None
    suffix = Path(name).suffix.lower()
    if suffix == ".xlsx":
        try:
            return pd.read_excel(file, header=0, engine="openpyxl", dtype=str)
        except ImportError:
            st.error("Reading xlsx requires xlrd==1.2.0. Install: pip install 'xlrd==1.2.0'")
            return None
    return pd.read_excel(file, header=0, dtype=str)

def read_csv_smart(file):
    encodings = ("utf-8", "utf-8-sig", "cp1252", "latin1")
    seps = (None, ",", ";", "\t", "|")
    for enc in encodings:
        for sep in seps:
            try:
                kwargs = dict(header=0, dtype=str, keep_default_na=False, encoding=enc)
                if sep is None:
                    kwargs.update(sep=None, engine="python")
                else:
                    kwargs.update(sep=sep, low_memory=False)
                df = pd.read_csv(file, **kwargs)
                if df.shape[1] == 1 and sep is not None:
                    continue
                return df
            except (UnicodeDecodeError, pd.errors.ParserError, ValueError):
                continue
    return pd.read_csv(file, header=0, dtype=str, keep_default_na=False, encoding="latin1", sep=None, engine="python")

def to_num(x):
    if isinstance(x, pd.Series):
        return pd.to_numeric(x.astype(str).str.replace(",", ".", regex=False), errors="coerce")
    return pd.to_numeric(str(x).replace(",", "."), errors="coerce")

def plus_21(p):
    try:
        if p is None or (isinstance(p, float) and pd.isna(p)):
            return None
        return round(float(p) * 1.21, 6)
    except Exception:
        return None

def normalize_sku(s: pd.Series) -> pd.Series:
    return (
        s.astype(str)
         .str.replace("\ufeff", "", regex=False)
         .str.replace("\u200b", "", regex=False)
         .str.replace(r"[\u200e\u200f\u202a\u202c\u2060]", "", regex=True)
         .str.strip()
         .str.lstrip("'’\"")
    )

def clean_code_series(s: pd.Series) -> pd.Series:
    return (
        s.astype(str)
         .str.strip()
         .str.replace(r"\.0$", "", regex=True)
    )

def clean_code_token(tok: str) -> str:
    tok = tok.strip()
    tok = re.sub(r"\.0$", "", tok)
    return tok


def ref_key_series(s: pd.Series) -> pd.Series:
    return s.astype(str).str.strip().str.lower()

# Store selection
if van_file and facq_file and desco_file and store_file:
    df_store = read_csv_smart(store_file)
    st.subheader("Select Store Columns")
    cols = list(df_store.columns)
    def col_selector(label, default_idx):
        # clamp default index
        idx = default_idx if 0 <= default_idx < len(cols) else 0
        return st.selectbox(f"Select column for {label}", cols, index=idx)
    col_handle = col_selector("Handle", 0)
    col_ref    = col_selector("Reference", 1)
    col_brut   = col_selector("P.Brut (raw price)", 2)
    col_ttc    = col_selector("P.Vente (sale price)", 3)
    col_name   = col_selector("Product Name", 8 if len(cols)>8 else 0)

    run_script = st.button("Run Price Comparison")
    progress_placeholder = st.empty()

    if run_script:
        progress_bar = progress_placeholder.progress(0, text="Loading supplier files...")
        # --- Load supplier data ---
        df_van   = read_excel_smart(van_file, van_file.name)
        df_facq  = read_excel_smart(facq_file, facq_file.name)
        df_desco = read_excel_smart(desco_file, desco_file.name)
        if df_van is None or df_facq is None or df_desco is None:
            st.stop()

        # --- Vanoirschot Processing (A + B refs, B priority) ---
        progress_bar.progress(10, text="Processing Vanoirschot data...")

        # Column B (priority)
        van_ref_B = clean_code_series(df_van.iloc[:, 1].fillna(""))
        van_prix_B = to_num(df_van.iloc[:, 7]) if df_van.shape[1] > 7 else pd.Series([pd.NA] * len(van_ref_B))
        van_titles_B = df_van.iloc[:, 9].fillna("").astype(str) if df_van.shape[1] > 9 else pd.Series([""] * len(van_ref_B))

        # Column A (secondary)
        van_ref_A = clean_code_series(df_van.iloc[:, 0].fillna(""))
        van_prix_A = to_num(df_van.iloc[:, 7]) if df_van.shape[1] > 7 else pd.Series([pd.NA] * len(van_ref_A))
        van_titles_A = df_van.iloc[:, 9].fillna("").astype(str) if df_van.shape[1] > 9 else pd.Series([""] * len(van_ref_A))

        # Normalize
        van_norm_B = ref_key_series(van_ref_B)
        van_norm_A = ref_key_series(van_ref_A)

        # Build price map (B first, A second if not already present)
        van_price_map = {n: p for n, p in zip(van_norm_B, van_prix_B) if n}
        for n, p in zip(van_norm_A, van_prix_A):
            if n and n not in van_price_map:
                van_price_map[n] = p

        # (These were used only by the removed title check; harmless to keep assigned)
        van_titles_lower = pd.concat([van_titles_B, van_titles_A], ignore_index=True).str.lower()
        van_ref_orig_for_row = pd.concat([van_ref_B, van_ref_A], ignore_index=True)
        van_price_for_row    = pd.concat([van_prix_B, van_prix_A], ignore_index=True)

        # --- Facq + Desco ---
        progress_bar.progress(20, text="Processing Facq and Desco data...")
        facq_ref_raw = clean_code_series(df_facq.iloc[:, 5].fillna("")) if df_facq.shape[1] > 5 else pd.Series([""] * len(df_facq))
        facq_brut    = to_num(df_facq.iloc[:, 6]) if df_facq.shape[1] > 6 else pd.Series([pd.NA] * len(df_facq))

        desco_ref  = clean_code_series(df_desco.iloc[:, 3].fillna("")) if df_desco.shape[1] > 3 else pd.Series([""] * len(df_desco))
        desco_brut = to_num(df_desco.iloc[:, 4]) if df_desco.shape[1] > 4 else pd.Series([pd.NA] * len(df_desco))

        facq_price_map = {}
        for cell, price in zip(facq_ref_raw, facq_brut):
            for tok in re.split(r"[\/,;|]+", cell):
                tok = clean_code_token(tok)
                if not tok:
                    continue
                n = tok.strip().lower()
                if n and n not in facq_price_map:
                    facq_price_map[n] = price
        desco_norm = ref_key_series(desco_ref)
        desco_price_map = {n: p for n, p in zip(desco_norm, desco_brut) if n}

        # --- Store Data ---
        progress_bar.progress(40, text="Processing store data...")
        store_col_handle    = df_store[col_handle]
        store_col_name      = df_store[col_name].astype(str)
        store_col_brut      = to_num(df_store[col_brut])
        store_col_ttc       = to_num(df_store[col_ttc])
        store_col_ref_clean = normalize_sku(df_store[col_ref])
        store_col_ref_norm  = ref_key_series(store_col_ref_clean)

        base = pd.DataFrame({
            "ref_norm": store_col_ref_norm,
            "Reference ID Fallback": store_col_ref_clean,
            "Handle": store_col_handle,
            "Product Name": store_col_name,
            "P.Brut": store_col_brut,
            "P.Vente": store_col_ttc,
        })

        # --- Matching ---
        progress_bar.progress(50, text="Matching supplier prices...")
        base["VANOIRSCHOT Brut"] = base["ref_norm"].map(van_price_map)
        base["FACQ Brut"]        = base["ref_norm"].map(facq_price_map)
        base["DESCO Brut"]       = base["ref_norm"].map(desco_price_map)

        base["VANOIRSCHOT Net"]  = base["VANOIRSCHOT Brut"].map(plus_21)
        base["FACQ Net"]         = base["FACQ Brut"].map(plus_21)
        base["DESCO Net"]        = base["DESCO Brut"].map(plus_21)

        base["_highest_ref_net"] = base[["VANOIRSCHOT Net", "FACQ Net", "DESCO Net"]].max(axis=1, skipna=True)
        base["Highest Supplier Net"] = base["_highest_ref_net"]


        base["__exact_first_pass"] = base[["VANOIRSCHOT Brut", "FACQ Brut", "DESCO Brut"]].notna().any(axis=1)

        # --- REMOVED: Additional title-based Vanoirschot check ---
        # (No changes to prices/columns based on VANOIRSCHOT titles)

        base["Reference ID"] = base["Reference ID Fallback"]

        out_cols = [
            "Reference ID",
            "Handle",
            "Product Name",
            "VANOIRSCHOT Brut", "VANOIRSCHOT Net",
            "FACQ Brut", "FACQ Net",
            "DESCO Brut", "DESCO Net",
            "P.Brut", "P.Vente",
            "Highest Supplier Net",
        ]
        out_df = base[out_cols].sort_values(by="Reference ID", kind="stable")
        progress_bar.progress(80, text="Generating outputs and downloads...")

        st.subheader("Comparison Table")
        st.dataframe(out_df, use_container_width=True)

        # --- Outputs ---
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_path        = f"price_comparison_{timestamp}.xlsx"
        no_ref_xlsx        = "NO-Referance_found.xlsx"
        exact_matches_xlsx = f"exact_reference_matches_{timestamp}.xlsx"

        # Main comparison output
        towrite = io.BytesIO()
        with pd.ExcelWriter(towrite, engine="openpyxl") as writer:
            out_df.to_excel(writer, index=False, sheet_name="comparison")
        towrite.seek(0)
        st.session_state["comparison_file"] = towrite.getvalue()
        st.session_state["comparison_name"] = output_path

        # No reference output
        store_ref_clean = normalize_sku(df_store[col_ref])
        store_ref_norm  = ref_key_series(store_ref_clean)
        saved_keys = set(k for k in base["ref_norm"].dropna().unique() if k)
        mask_no_ref       = store_ref_norm.eq("") | store_ref_norm.isna()
        mask_not_in_excel = ~store_ref_norm.isin(saved_keys)
        final_mask        = mask_no_ref | mask_not_in_excel

        no_ref_df = df_store.loc[final_mask].copy()
        no_ref_df["Highest Supplier Net"] = pd.NA
        towrite2 = io.BytesIO()
        with pd.ExcelWriter(towrite2, engine="openpyxl") as writer:
            no_ref_df.to_excel(writer, index=False, sheet_name="no_reference")
        towrite2.seek(0)
        st.session_state["no_ref_file"] = towrite2.getvalue()
        st.session_state["no_ref_name"] = no_ref_xlsx

        # Exact first-pass matches output
        exact_first_df = base.loc[base["__exact_first_pass"], [
            "Reference ID Fallback", "Handle", "Product Name",
            "VANOIRSCHOT Brut", "FACQ Brut", "DESCO Brut",
            "VANOIRSCHOT Net", "FACQ Net", "DESCO Net",
            "P.Brut", "P.Vente", "Highest Supplier Net"
        ]].copy()

        towrite4 = io.BytesIO()
        with pd.ExcelWriter(towrite4, engine="openpyxl") as writer:
            if not exact_first_df.empty:
                exact_first_df.to_excel(writer, index=False, sheet_name="exact_matches")
            else:
                pd.DataFrame(columns=list(exact_first_df.columns)).to_excel(writer, index=False, sheet_name="exact_matches")
        towrite4.seek(0)
        st.session_state["exact_file"] = towrite4.getvalue()
        st.session_state["exact_name"] = exact_matches_xlsx

        st.session_state["timestamp"] = timestamp

        progress_bar.progress(100, text="Done!")

# --- Downloads: show if present ---
if "comparison_file" in st.session_state:
    st.subheader("Download Outputs")
    st.download_button(
        "Download Main Comparison Excel",
        st.session_state["comparison_file"],
        file_name=st.session_state["comparison_name"],
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    st.download_button(
        "Download Unmatched/Missing References Excel",
        st.session_state["no_ref_file"],
        file_name=st.session_state["no_ref_name"],
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    st.download_button(
        "Download Exact First-Pass Matches Excel",
        st.session_state["exact_file"],
        file_name=st.session_state["exact_name"],
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # Download all files as ZIP
    st.subheader("Download ALL output files")
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zipf:
        zipf.writestr(st.session_state["comparison_name"], st.session_state["comparison_file"])
        zipf.writestr(st.session_state["no_ref_name"], st.session_state["no_ref_file"])
        zipf.writestr(st.session_state["exact_name"], st.session_state["exact_file"])
    zip_buffer.seek(0)
    st.download_button(
        label="Download All Output Files as ZIP",
        data=zip_buffer,
        file_name=f"price_comparison_outputs_{st.session_state['timestamp']}.zip",
        mime="application/zip"
    )

#    # --- Save all files into folder ---
#    if st.button("Save All Files to 'output_data' Folder"):
#        save_dir = Path("output_data")
#        save_dir.mkdir(exist_ok=True)
#
#        with open(save_dir / st.session_state["comparison_name"], "wb") as f:
#            f.write(st.session_state["comparison_file"])
#        with open(save_dir / st.session_state["no_ref_name"], "wb") as f:
#            f.write(st.session_state["no_ref_file"])
#        with open(save_dir / st.session_state["exact_name"], "wb") as f:
#            f.write(st.session_state["exact_file"])
#
#        st.success(f"All files saved in {save_dir.resolve()}")
#
#    # --- Run solyd_price.py script ---
#    if st.button("Run solyd_price.py"):
#        try:
#            result = subprocess.run(
#                ["python", "solyd_price.py"],
#                capture_output=True,
#                text=True,
#                check=True
#            )
#            st.success("solyd_price.py executed successfully!")
#            st.text(result.stdout)
#        except subprocess.CalledProcessError as e:
#            st.error(f"Error running solyd_price.py:\n{e.stderr}")
#
else:
    st.info("Please upload all supplier and store files and run the comparison to generate outputs.")
