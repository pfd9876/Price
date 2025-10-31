import streamlit as st
import pandas as pd
import re
from pathlib import Path
from datetime import datetime
import zipfile
import io
import os
import subprocess


# --- Header Markup (no logic changes) ---
st.markdown("""
<div class="pp-brand">
  <div class="pp-logo">PAULPROMO</div>
  <div class="pp-pill">Livraison 72h • Prix imbattables</div>
</div>
""", unsafe_allow_html=True)

# --- Header config (no logic changes) ---
HERO_URL = "https://your.cdn.com/path/to/hero.jpg"  # put your image URL here; leave "" for gradient only
palette = {
    "accent": "#ff7a00",   # pill + logo color
    "text":   "#ffffff"    # hero text color
}

# =========================
# Page Meta & Global Styles
# =========================
st.set_page_config(
    page_title="Price Comparison Tool",
    page_icon="🧮",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---- Modern theming tweaks (purely visual) ----
st.markdown(
    """
    <style>
    /* App container */
    .block-container {padding-top: 2rem; padding-bottom: 3rem;}

    /* Big title styling */
    .pct-title {font-size: 2.1rem; font-weight: 800; letter-spacing: .2px;}
    .pct-subtle {color: var(--text-color-secondary, #7a7f87);}

    /* Card-like boxes */
    .pct-card {background: rgba(127,127,127,.04); border: 1px solid rgba(127,127,127,.18);
               border-radius: 14px; padding: 1rem 1.1rem;}

    /* Section headers */
    .pct-section {font-weight: 700; font-size: 1.1rem; margin: .25rem 0 .75rem;}

    /* Make dataframe corners rounded */
    .stDataFrame {border-radius: 12px; overflow: hidden;}

    /* Buttons a bit larger & rounded */
    .stButton>button {border-radius: 12px !important; padding: .6rem 1rem; font-weight: 600;}

    /* Download buttons spacing */
    .stDownloadButton {margin-bottom: .35rem;}

    /* Tabs weight */
    .stTabs [data-baseweb="tab"] {font-weight: 700;}

    /* Progress text size */
    .stProgress .progress-bar {height: 10px;}

    /* Small badges */
    .pct-badge {display:inline-block; padding:.2rem .55rem; border-radius:999px; font-size:.75rem;
                font-weight:700; border:1px solid rgba(127,127,127,.25); margin-right:.35rem;}

    /* Sidebar polish */
    section[data-testid='stSidebar'] {border-right: 1px solid rgba(127,127,127,.15);}    
    </style>
    """,
    unsafe_allow_html=True,
)
# --- Header CSS (no logic changes) ---
hero_bg = f'url("{HERO_URL}")' if HERO_URL else "linear-gradient(180deg, #111 0%, #333 100%)"

st.markdown(f"""
<style>
.main .block-container {{
  padding-top: 0.6rem; padding-left: 0; padding-right: 0; max-width: 100%;
}}
.pp-brand {{
  width: 100%;
  display:flex; align-items:center; justify-content:space-between;
  padding: 0 24px;
  padding-top: 30px;
}}
.pp-logo {{ font-weight: 900; letter-spacing: .5px; font-size: 28px; color: {palette["accent"]}; }}
.pp-pill {{
  background: {palette["accent"]}; color: white; font-weight: 800;
  padding: 6px 12px; border-radius: 999px; font-size: 12px; margin-right: 4px;
}}

/* keep your modern UI vibes consistent */
.pp-card {{ background: white; border-top: 1px solid #eee; padding: 18px 24px; }}
.stButton>button {{
  background: {palette["accent"]} !important; color: white !important; border: 0 !important;
  border-radius: 10px !important; font-weight: 700 !important;
}}
.stTextInput>div>div>input, .stSelectbox>div>div>div>div, .stToggle {{ border-radius: 10px !important; }}
[data-testid="stDataFrame"] > div {{ padding-left: 0 !important; padding-right: 0 !important; }}
</style>
""", unsafe_allow_html=True)

# =========================
# Header
# =========================
left, right = st.columns([0.8, 0.2])
with left:
    st.markdown("<div class='pct-title'>🧮 Price Comparison Tool</div>", unsafe_allow_html=True)
    st.caption("Match store references with supplier price lists, compute VAT-inclusive nets, and export clean reports.")
with right:
    st.markdown("""
        <div style='text-align:right;'>
            <span class='pct-badge'>v1</span>
            <span class='pct-badge'>By Yassir</span>
        </div>
    """, unsafe_allow_html=True)

# =========================
# Sidebar (guide & tips)
# =========================
with st.sidebar:
    st.header("How it works ✨")
    st.markdown(
        """
        1. **Upload** the 3 supplier workbooks and your **Store CSV**.
        2. **Map** the right columns from your store file.
        3. Click **Run Price Comparison** to process.
        4. Review the **table**, then **download** the exports.
        """
    )
    st.divider()
    st.subheader("Tips")
    st.markdown(
        """
        - Use the **column preview** to double-check selections.
        - The tool computes **Net = Brut × 1.21** for each supplier.
        - Exports include: main comparison, **unmatched references**, and **exact first-pass matches**.
        """
    )

# =========================
# ORIGINAL LOGIC — unchanged
# (Only the layout and text around it were improved)
# =========================

# --- File Uploads (grouped nicely) ---
upload_tab, run_tab, results_tab, help_tab, solyd_tab = st.tabs([
    "1) 1.Upload Files", "2) 2.Map & Run", "3) 3.Results & Exports", "Help", "4.Solyd Price ↗"
])
with upload_tab:
    st.markdown("<div class='pct-section'>Supplier Workbooks</div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        van_file   = st.file_uploader("Vanoirschot Excel (.xlsx)", type=["xlsx"], key="van")
    with c2:
        facq_file  = st.file_uploader("Facq Excel (.xlsx)", type=["xlsx"], key="facq")
    with c3:
        desco_file = st.file_uploader("Desco Excel (.xlsx)", type=["xlsx"], key="desco")

    st.markdown("<div class='pct-section' style='margin-top:1rem;'>Store CSV</div>", unsafe_allow_html=True)
    store_file = st.file_uploader("Store CSV file", type=["csv"], key="store")

# ---------------
# Helper functions (UNCHANGED PROCESSING LOGIC)
# ---------------

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

# =========================
# Column Mapping & RUN (UI polish only)
# =========================
with run_tab:
    if van_file and facq_file and desco_file and store_file:
        st.markdown("<div class='pct-section'>Map Store Columns</div>", unsafe_allow_html=True)
        df_store = read_csv_smart(store_file)

        with st.expander("Preview first 10 rows of your Store CSV", expanded=False):
            st.dataframe(df_store.head(10), use_container_width=True)

        cols = list(df_store.columns)
        def col_selector(label, default_idx):
            idx = default_idx if 0 <= default_idx < len(cols) else 0
            return st.selectbox(f"Select column for {label}", cols, index=idx)

        c1, c2, c3, c4, c5 = st.columns([1,1,1,1,1])
        with c1:
            col_handle = col_selector("Handle", 0)
        with c2:
            col_ref    = col_selector("Reference", 1)
        with c3:
            col_brut   = col_selector("P.Brut (raw price)", 2)
        with c4:
            col_ttc    = col_selector("P.Vente (sale price)", 3)
        with c5:
            col_name   = col_selector("Product Name", 8 if len(cols)>8 else 0)

        st.markdown("<div class='pct-section' style='margin-top:.5rem;'>Run</div>", unsafe_allow_html=True)
        run_script = st.button("▶️ Run Price Comparison", use_container_width=True)
        progress_placeholder = st.empty()

        if run_script:
            progress_bar = progress_placeholder.progress(0, text="Loading supplier files…")
            # --- Load supplier data ---
            df_van   = read_excel_smart(van_file, van_file.name)
            df_facq  = read_excel_smart(facq_file, facq_file.name)
            df_desco = read_excel_smart(desco_file, desco_file.name)
            if df_van is None or df_facq is None or df_desco is None:
                st.stop()

            # --- Vanoirschot Processing (A + B refs, B priority) ---
            progress_bar.progress(10, text="Processing Vanoirschot data…")

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
            progress_bar.progress(20, text="Processing Facq and Desco data…")
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
            progress_bar.progress(40, text="Processing store data…")
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
            progress_bar.progress(50, text="Matching supplier prices…")
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
            progress_bar.progress(80, text="Generating outputs and downloads…")

            st.markdown("<div class='pct-section' style='margin-top: .5rem;'>Comparison Table</div>", unsafe_allow_html=True)
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

    else:
        st.info("Upload all supplier and store files in the **Upload Files** tab to continue.")

# =========================
# Results & Downloads (unchanged logic, nicer presentation)
# =========================
with results_tab:
    if "comparison_file" in st.session_state:
        st.markdown("<div class='pct-section'>Exports</div>", unsafe_allow_html=True)
        dl1, dl2, dl3 = st.columns([1,1,1])
        with dl1:
            st.download_button(
                "⬇️ Main Comparison (XLSX)",
                st.session_state["comparison_file"],
                file_name=st.session_state["comparison_name"],
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        with dl2:
            st.download_button(
                "⬇️ Unmatched / Missing (XLSX)",
                st.session_state["no_ref_file"],
                file_name=st.session_state["no_ref_name"],
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        with dl3:
            st.download_button(
                "⬇️ Exact First-Pass Matches (XLSX)",
                st.session_state["exact_file"],
                file_name=st.session_state["exact_name"],
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

        st.markdown("<div class='pct-section' style='margin-top:1rem;'>Bundle</div>", unsafe_allow_html=True)
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zipf:
            zipf.writestr(st.session_state["comparison_name"], st.session_state["comparison_file"])
            zipf.writestr(st.session_state["no_ref_name"], st.session_state["no_ref_file"])
            zipf.writestr(st.session_state["exact_name"], st.session_state["exact_file"])
        zip_buffer.seek(0)
        st.download_button(
            label="📦 Download All Exports (ZIP)",
            data=zip_buffer,
            file_name=f"price_comparison_outputs_{st.session_state['timestamp']}.zip",
            mime="application/zip",
            use_container_width=True,
        )

        st.divider()
        st.markdown("<div class='pct-section'>Quick Metrics</div>", unsafe_allow_html=True)
        # Lightweight summary cards
        try:
            out_df = pd.read_excel(io.BytesIO(st.session_state["comparison_file"]))
            total_rows = int(out_df.shape[0])
            matched_rows = int(out_df[["VANOIRSCHOT Brut", "FACQ Brut", "DESCO Brut"]].notna().any(axis=1).sum())
            unmatched_rows = total_rows - matched_rows
        except Exception:
            total_rows = matched_rows = unmatched_rows = 0

        m1, m2, m3 = st.columns(3)
        m1.metric("Total Products", f"{total_rows:,}")
        m2.metric("Matched (any supplier)", f"{matched_rows:,}")
        m3.metric("Unmatched", f"{unmatched_rows:,}")

    else:
        st.info("No results yet. Run the comparison in the **Map & Run** tab.")

# =========================
# Help & Notes
# =========================
with help_tab:
    st.markdown(
        """
        **About this app**  
        This UI refresh focuses purely on **layout and design**. All **processing logic and data handling** remain unchanged: file parsing, mapping, price computation, matching, and exports.

        **File requirements**
        - Supplier files must be **.xlsx**
        - Store file must be **.csv**

        **Exports**
        - Main Comparison (VAT-inclusive nets)
        - Unmatched / Missing references
        - Exact First‑pass matches
        """
    )
# =========================
# Solyd Price (external link)
# =========================
with solyd_tab:
    st.markdown("[Open Solyd Price ↗](https://price-compare-2.streamlit.app/)"
)

# =========================
# Fallback message (mirrors original behavior)
# =========================
if "comparison_file" not in st.session_state:
    st.caption("Need a hand? Go to **Upload Files** → add all four files → **Map & Run**.")
