"""Redirect configurable runtime storage before plotting/Streamlit imports."""
import os
from pathlib import Path
import tempfile
ROOT=Path(__file__).resolve().parents[1]
for key,folder in {'MPLCONFIGDIR':'.runtime/matplotlib','TEMP':'.runtime/tmp','TMP':'.runtime/tmp','XDG_CACHE_HOME':'.cache','STREAMLIT_CONFIG_DIR':'.runtime/streamlit'}.items():
    path=ROOT/folder; path.mkdir(parents=True,exist_ok=True); os.environ[key]=str(path)
tempfile.tempdir=str(ROOT/'.runtime/tmp')
