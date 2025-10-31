# Price Comparison Tool — Streamlit App

This repo contains a ready-to-deploy Streamlit app for comparing supplier prices vs your store CSV.
The main entry point is `app.py` (copied from your uploaded script).

## 1) Quick Run Locally
```bash
# (optional) python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## 2) Deploy on Streamlit Community Cloud (free & fast)
1. Create a new GitHub repo and upload these files.
2. Go to https://share.streamlit.io, click **New app** and select your repo.
3. **Main file path:** `app.py`
4. It will auto-install from `requirements.txt`. Python version is specified by `runtime.txt`.
5. When it opens, upload your supplier Excel files and store CSV, select columns, and click **Run Price Comparison**.

## 3) Deploy on Hugging Face Spaces
1. Create a new Space → **Streamlit** template.
2. Upload all files (or link to your Git repo).
3. In **App file**, set `app.py`.
4. The Space will build with `requirements.txt` automatically.

## 4) Deploy on Render (web service)
1. Create a **Web Service** from your GitHub repo.
2. **Build Command:** `pip install -r requirements.txt`
3. **Start Command:** `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
4. Set environment variable `PORT` if Render doesn’t set it automatically.

## Notes / Gotchas
- `.xls` support: the app expects **xlrd==1.2.0** for old Excel files. This is pinned in `requirements.txt`.
- `solyd_price.py` button: your UI shows a button to run `solyd_price.py`. If that file isn’t present in the repo, clicking it will show an error. Either remove that button or add the script.
- Max upload size can be tuned via `.streamlit/config.toml` (currently 500 MB).
- If you see engine errors opening `.xls`, confirm the file is truly `.xls` and not a renamed `.xlsx`.

## Files
- `app.py` — Streamlit app
- `requirements.txt` — Python deps (incl. xlrd 1.2.0 + openpyxl)
- `runtime.txt` — Pin Python 3.11 (some hosts)
- `.streamlit/config.toml` — App config (larger upload limit, light theme)

---

### Troubleshooting
- **ModuleNotFoundError**: Make sure the dependency is in `requirements.txt` and redeploy.
- **App boots but file uploads fail**: Increase `maxUploadSize` in `.streamlit/config.toml`.
- **Subprocess error for `solyd_price.py`**: Ensure the file exists in the root and is callable with `python solyd_price.py`.
