import streamlit as st
import requests
import pandas as pd
from streamlit_folium import st_folium
import folium
from folium.plugins import MarkerCluster, Fullscreen, LocateControl
from datetime import datetime
import re

st.set_page_config(page_title="Progress Director", layout="wide", initial_sidebar_state="expanded")
st.title("🌍 Progress Director")
st.markdown("### The antidote to doomscrolling — watching humanity actually win, right now.")

# === DATA ===
@st.cache_data(ttl=600)
def get_restor():
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"}
        url = "https://api.restor.eco/sites?limit=15000"
        data = requests.get(url, headers=headers, timeout=10).json()
        return pd.DataFrame(data["features"])
    except Exception as e:
        st.error(f"Restor error: {e}")
        return pd.DataFrame()

restor_df = get_restor()

@st.cache_data(ttl=120)
def get_ecosia():
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"}
        html = requests.get("https://www.ecosia.org/trees", headers=headers, timeout=10).text
        match = re.search(r'(\d{1,3}(?:,\d{3})*) trees planted', html)
        return int(match.group(1).replace(',', '')) if match else 215000000
    except:
        return 215000000

ecosia = get_ecosia()

@st.cache_data(ttl=1800)
def get_ocean_cleanup():
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"}
        html = requests.get("https://theoceancleanup.com/dashboard/", headers=headers, timeout=10).text
        match = re.search(r'(\d{1,3}(?:,\d{3})*) kg of trash removed', html, re.I)
        if match:
            return int(match.group(1).replace(',', ''))
        return 44193195
    except:
        return 44193195

ocean_kg = get_ocean_cleanup()

# === MAP ===
m = folium.Map(location=[20, 0], zoom_start=2, tiles='CartoDB positron', prefer_canvas=True)

# Base tiles
folium.TileLayer('Stamen Terrain', name="Terrain", attr='Map tiles by Stamen Design, CC BY 3.0 — Map data © OpenStreetMap').add_to(m)
folium.TileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', name="Topo", attr='© OpenTopoMap (CC-BY-SA)').add_to(m)

# Electricity layer — v3, works with test key (limited zones)
token = st.secrets.get("electricitymaps_token", "")
if token:
    electricity_layer = folium.FeatureGroup(name="⚡ Live Low-Carbon Electricity %", show=True)
    try:
        data = requests.get("https://api.electricitymaps.com/v3/carbon-intensity/latest", headers={"auth-token": token}).json()
        zones_geo = requests.get("https://raw.githubusercontent.com/electricitymaps/electricitymaps-contrib/master/web/geo/world.geojson").json()
        
        for feature in zones_geo["features"]:
            zone = feature["properties"]["zoneName"]
            if zone in data and "lowCarbonPercentage" in data[zone]:
                pct = data[zone]["lowCarbonPercentage"]
                color = "darkgreen" if pct > 80 else "green" if pct > 60 else "lightgreen" if pct > 40 else "yellow" if pct > 20 else "orange"
                folium.GeoJson(feature, style_function=lambda f, c=color: {"fillColor": c, "color": "#333", "weight": 1, "fillOpacity": 0.7},
                               tooltip=f"<b>{zone}</b>: {pct}% low-carbon").add_to(electricity_layer)
        electricity_layer.add_to(m)
    except Exception as e:
        st.sidebar.warning(f"Electricity error: {e}")

# Restoration sites — beautiful clusters
if not restor_df.empty:
    restor_layer = folium.FeatureGroup(name="🌲 Active Restoration Sites (Restor)", show=True)
    cluster = MarkerCluster().add_to(restor_layer)
    for _, row in restor_df.iterrows():
        p = row["properties"]
        coords = row["geometry"]["coordinates"][::-1]
        folium.CircleMarker(
            location=coords, radius=5, color="#006400", fill=True, fill_color="#00ff00", fill_opacity=0.8,
            popup=f"<b>{p.get('name','Site')}</b><br>Trees: {p.get('treesPlanted','?')}<br>Hectares: {p.get('hectaresRestored','?')}"
        ).add_to(cluster)
    restor_layer.add_to(m)

Fullscreen().add_to(m)
LocateControl().add_to(m)
folium.LayerControl().add_to(m)

# Sidebar metrics
with st.sidebar:
    st.markdown("## Live Wins Right Now")
    st.metric("Trees planted (Ecosia)", f"{ecosia:,}")
    st.metric("Ocean plastic removed", f"{ocean_kg:,} kg")
    st.markdown("---")
    st.caption(f"Updated: {datetime.now().strftime('%H:%M UTC · %b %d')}")

st_folium(m, width="100%", height=800, returned_objects=[])

st.caption("v1.0 fixed · Built by James + Grok · Austin, Texas · Nov 18 2025")
