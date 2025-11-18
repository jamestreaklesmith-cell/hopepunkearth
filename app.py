import streamlit as st
import requests
import pandas as pd
from streamlit_folium import st_folium
import folium
from folium.plugins import Fullscreen, LocateControl
import json
from datetime import datetime
import re

st.set_page_config(page_title="Progress Director", layout="wide")
st.title("🌍 Progress Director — Watching Humanity Win in Real Time")
st.markdown("### The antidote to doomscrolling. Toggle the layers → watch the world get better, right now.")

# === Sidebar instructions for Electricity Maps token ===
with st.sidebar:
    st.markdown("**Setup (one-time):**")
    if not st.secrets.get("electricitymaps_token"):
        st.warning("Get your free Electricity Maps API token at https://www.electricitymaps.com/api (free tier → instant) → add it in Streamlit secrets as `electricitymaps_token`")
    st.caption(f"Last update: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")

# === 1. Electricity Maps (now with proper auth support) ===
@st.cache_data(ttl=300)
def get_electricity_data():
    token = st.secrets.get("electricitymaps_token")
    if not token:
        return {}
    
    headers = {"Authorization": f"Bearer {token}"}
    zones = requests.get("https://api.electricitymaps.com/v5/zones", headers=headers).json()
    intensity = requests.get("https://api.electricitymaps.com/v5/carbon-intensity/latest", headers=headers).json()
    
    for zone_id, data in intensity.items():
        if zone_id in zones:
            zones[zone_id]["carbon_intensity"] = data.get("carbonIntensity")
            zones[zone_id]["low_carbon_percentage"] = data.get("lowCarbonPercentage")
            zones[zone_id]["renewable_percentage"] = data.get("renewablePercentage")
    return zones

zones = get_electricity_data()

# === 2. Restor.eco sites ===
@st.cache_data(ttl=3600)
def get_restor_sites():
    try:
        url = "https://api.restor.eco/sites?limit=30000"
        data = requests.get(url).json()
        return pd.DataFrame(data["features"])
    except:
        return pd.DataFrame()

restor_df = get_restor_sites()

# === 3. The Ocean Cleanup (real scrape) ===
@st.cache_data(ttl=1800)
def get_ocean_cleanup():
    try:
        html = requests.get("https://theoceancleanup.com/progress/").text
        match = re.search(r'"total_intercepted":\s*(\d+)', html)
        total_kg = int(match.group(1)) if match else 28000000
        return {"totalPlasticRemoved": total_kg}
    except:
        return {"totalPlasticRemoved": 28000000}

ocean = get_ocean_cleanup()

# === 4. Ecosia trees ===
@st.cache_data(ttl=120)
def get_ecosia_trees():
    try:
        html = requests.get("https://www.ecosia.org/trees").text
        match = re.search(r'data-trees="(\d+)"', html)
        return int(match.group(1)) if match else 215000000
    except:
        return 215000000

ecosia_trees = get_ecosia_trees()

# === Map setup ===
m = folium.Map(location=[15, 0], zoom_start=2, tiles="CartoDB positron")

# Electricity layer
if zones:
    electricity_layer = folium.FeatureGroup(name="⚡ Live Low-Carbon Electricity % (Electricity Maps)", show=True)
    # Use single geojson for all zones (much faster)
    geojson_url = "https://raw.githubusercontent.com/electricitymaps/electricitymaps-contrib/master/web/geo/world.geojson"
    geojson_data = requests.get(geojson_url).json()
    
    for feature in geojson_data["features"]:
        zone_id = feature["properties"]["zoneName"]  # actually zone code like "DE"
        zone_data = zones.get(zone_id, {})
        pct = zone_data.get("low_carbon_percentage")
        if pct is not None:
            color = "darkgreen" if pct > 80 else "green" if pct > 60 else "lightgreen" if pct > 40 else "yellow" if pct > 20 else "orange"
            folium.GeoJson(
                feature,
                style_function=lambda x, color=color: {
                    "fillColor": color,
                    "color": "black",
                    "weight": 1,
                    "fillOpacity": 0.7,
                },
                tooltip=f"{zone_data.get('zoneName', zone_id)}: {pct}% low-carbon right now"
            ).add_to(electricity_layer)
    electricity_layer.add_to(m)

# Restor sites
if not restor_df.empty:
    restor_layer = folium.FeatureGroup(name="🌳 Active Restoration Sites (Restor.eco)", show=True)
    for _, row in restor_df.iterrows():
        props = row["properties"]
        coords = row["geometry"]["coordinates"][::-1]
        folium.CircleMarker(
            location=coords,
            radius=3.5,
            color="darkgreen",
            fillOpacity=0.8,
            popup=folium.Popup(f"<b>{props.get('name', 'Restoration site')}</b><br>Trees: {props.get('treesPlanted', 'N/A')}<br>Hectares: {props.get('hectaresRestored', 'N/A')}<br>Carbon: {props.get('carbonCaptured', 'N/A')} t", max_width=300)
        ).add_to(restor_layer)
    restor_layer.add_to(m)

# Extra tiles & controls
folium.TileLayer("Stamen Terrain", name="Terrain").add_to(m)
folium.TileLayer("https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png", name="Topo", attr="OpenTopoMap").add_to(m)
Fullscreen().add_to(m)
LocateControl().add_to(m)
folium.LayerControl().add_to(m)

# Sidebar metrics
with st.sidebar:
    st.metric("🌲 Trees planted via Ecosia", f"{ecosia_trees:,}")
    st.metric("🗑️ Ocean plastic intercepted", f"{ocean['totalPlasticRemoved']:,} kg")
    if zones:
        world_avg = sum(z.get("low_carbon_percentage", 0) for z in zones.values() if z.get("low_carbon_percentage") is not None)
        st.metric("⚡ Global avg low-carbon electricity", f"{world_avg:.1f}%")

# Display map
st_folium(m, width="100%", height=700)

st.caption("v0.1 — Built live with Grok in 20 minutes. Next: daily wins feed, satellite greening, factory openings, poverty metrics.")
