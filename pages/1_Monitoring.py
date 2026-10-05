import streamlit as st

from monitoring.dashboard import render

st.set_page_config(page_title="ATLAS Monitoring", page_icon="📊", layout="wide")
render()
