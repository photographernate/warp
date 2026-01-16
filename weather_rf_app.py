
"""
Weather-Induced RF Attenuation Tool
==================================

Developer Notes
---------------
This application requires the following Python dependencies:

Required:
- streamlit
- requests
- numpy
- pandas
- python-metar  (imported as `metar`)

Install Dependencies:
    python -m pip install streamlit requests numpy pandas python-metar matplotlib

Run with:
    python -m streamlit run weather_rf_app.py

Models:
- Rain: ITU-R P.838-inspired (k/alpha frequency trend)
- Gas: ITU-R P.676 qualitative (O2 + H2O resonance behavior)
- Clouds/Fog: ITU-R P.840 order-of-magnitude

Modes:
- Terrestrial LOS
- Space (LEO / MEO / GEO) using elevation-angle slant paths


Notes:
- The METAR data source is NOAA TGFTP (plain-text METARs).
- Rain, gaseous absorption, and cloud attenuation are modeled using
  ITU-R-inspired formulations (P.838, P.676, P.840).
- Python 3.10+ recommended. Tested on Python 3.13 (Windows).

Author: Nathan Jones/Phase Shift Labs
"""

import streamlit as st
import requests
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

try:
    from metar.Metar import Metar
except ImportError:
    raise ImportError(
        "Missing dependency: python-metar\n"
        "Install with: python -m pip install python-metar"
    )

# =========================
# METAR HANDLING
# =========================
def fetch_metar(station):
    url = f"https://tgftp.nws.noaa.gov/data/observations/metar/stations/{station.upper()}.TXT"
    r = requests.get(url, timeout=10)
    if r.status_code != 200:
        raise RuntimeError("METAR fetch failed")
    return r.text.strip().splitlines()[-1]


def parse_metar(metar_raw):
    obs = Metar(metar_raw)
    return {
        "temp_c": obs.temp.value("C") if obs.temp else 15,
        "pressure_hpa": obs.press.value("HPA") if obs.press else 1013,
        "rain_rate": rain_rate_from_metar(metar_raw),
    }

def decode_metar(obs):
    """Return a plain-English, engineer-friendly METAR decode."""
    decoded = {}

    decoded["Station"] = obs.station_id
    decoded["Observation Time (UTC)"] = obs.time.strftime("%Y-%m-%d %H:%M")

    if obs.temp:
        decoded["Temperature (°C)"] = float(obs.temp.value())
    if obs.dewpt:
        decoded["Dew Point (°C)"] = float(obs.dewpt.value())
    if obs.temp and obs.dewpt:
        T = obs.temp.value("C")
        Td = obs.dewpt.value("C")

        rh = 100 * np.exp((17.625 * Td) / (243.04 + Td)) / \
                np.exp((17.625 * T)  / (243.04 + T))

        decoded["Relative Humidity (%)"] = round(rh, 1)
    if obs.wind_speed:
        decoded["Wind Speed (kt)"] = float(obs.wind_speed.value())
    if obs.wind_dir:
        decoded["Wind Direction (deg)"] = int(obs.wind_dir.value())

    if obs.vis:
        decoded["Visibility (SM)"] = obs.vis.value()

    if obs.press:
        decoded["Pressure (hPa)"] = round(obs.press.value(), 1)

    # Clouds
    cloud_desc = []
    for layer in obs.sky:
        cover = layer[0]
        height_ft = layer[1]
        if height_ft:
            cloud_desc.append(f"{cover} at {height_ft * 100} ft")
        else:
            cloud_desc.append(f"{cover}")

    decoded["Cloud Layers"] = cloud_desc if cloud_desc else ["Clear"]

    # Weather phenomena
    if obs.weather:
        decoded["Weather"] = ", ".join(str(w) for w in obs.weather)
    else:
        decoded["Weather"] = "None reported"

    return decoded


def rain_rate_from_metar(metar):
    if "+RA" in metar:
        return 25
    elif "RA" in metar:
        return 5
    elif "-RA" in metar:
        return 1
    return 0


# =========================
# ITU-R MODELS (ENGINEER-SANE)
# =========================
def rain_specific_attenuation(freq_ghz, rain_rate):
    if rain_rate == 0:
        return 0
    k = 0.000038 * freq_ghz ** 2.42
    alpha = 1.0
    return k * rain_rate ** alpha  # dB/km


def gaseous_attenuation(freq_ghz):
    oxygen = 0.007 * freq_ghz**2 / (freq_ghz**2 + 60**2)
    water = 0.02 * freq_ghz**2 / (freq_ghz**2 + 22.3**2)
    return oxygen + water  # dB/km


def cloud_attenuation(freq_ghz):
    return 0.08 * (freq_ghz / 10) ** 2  # dB/km


# =========================
# ATTENUATION COMPUTATION
# =========================
def compute_attenuation(freqs, wx, mode, path_km=None, elevation_deg=None):
    rows = []

    if mode == "Space":
        el_rad = np.deg2rad(elevation_deg)
        slant_factor = 1 / np.sin(el_rad)
        eff_path = 3 * slant_factor  # rain height ~3 km
    else:
        eff_path = path_km

    for f in freqs:
        g_r = rain_specific_attenuation(f, wx["rain_rate"])
        g_g = gaseous_attenuation(f)
        g_c = cloud_attenuation(f)

        A_r = g_r * eff_path
        A_g = g_g * eff_path
        A_c = g_c * eff_path

        rows.append([
            f, A_r, A_g, A_c, A_r + A_g + A_c
        ])

    return pd.DataFrame(
        rows,
        columns=["Freq (GHz)", "Rain (dB)", "Gas (dB)", "Cloud (dB)", "Total (dB)"]
    )


# =========================
# STREAMLIT UI
# =========================
st.set_page_config(layout="wide")
st.title("Weather-Induced RF Attenuation")

station = st.text_input("METAR Station", "KVPS")

freqs = st.multiselect(
    "Frequencies (GHz)",
    [5, 10, 15, 20, 23, 30, 40],
    default=[10, 23, 30]
)

mode = st.radio("Propagation Mode", ["Terrestrial LOS", "Space"])

# --- Session State Init ---
if "elevation_deg" not in st.session_state:
    st.session_state.elevation_deg = 30
if "orbit" not in st.session_state:
    st.session_state.orbit = "MEO"

if mode == "Terrestrial LOS":
    path_km = st.slider("Path Length (km)", 1, 100, 20)
else:
    orbit = st.selectbox("Orbit Type", ["LEO", "MEO", "GEO"], index=1)
    orbit_defaults = {"LEO": 60, "MEO": 30, "GEO": 15}

    if orbit != st.session_state.orbit:
        st.session_state.elevation_deg = orbit_defaults[orbit]
        st.session_state.orbit = orbit

    elevation = st.slider(
        "Elevation Angle (deg)",
        5,
        90,
        st.session_state.elevation_deg
    )
    st.session_state.elevation_deg = elevation


if st.button("Fetch METAR & Compute"):
    metar_raw = fetch_metar(station)
    st.code(metar_raw)

    obs = Metar(metar_raw)
    decoded = decode_metar(obs)

    st.subheader("Decoded Weather Summary")

    left, right = st.columns(2)
    items = list(decoded.items())

    half = (len(items) + 1) // 2

    for col, subset in zip([left, right], [items[:half], items[half:]]):
        with col:
            for key, value in subset:
                if isinstance(value, list):
                    st.markdown(f"**{key}:**<br>" + "<br>".join(value), unsafe_allow_html=True)
                else:
                    st.markdown(f"**{key}:** {value}")

    wx = parse_metar(metar_raw)

    df = compute_attenuation(
        freqs,
        wx,
        mode="Space" if mode == "Space" else "LOS",
        path_km=path_km if mode == "Terrestrial LOS" else None,
        elevation_deg=st.session_state.elevation_deg if mode == "Space" else None
    )

    st.dataframe(df, use_container_width=True)

    # ===== Plot =====
    fig, ax = plt.subplots()
    ax.plot(df["Freq (GHz)"], df["Rain (dB)"], label="Rain")
    ax.plot(df["Freq (GHz)"], df["Gas (dB)"], label="Gas")
    ax.plot(df["Freq (GHz)"], df["Cloud (dB)"], label="Cloud")
    ax.plot(df["Freq (GHz)"], df["Total (dB)"], label="Total", linewidth=2)

    ax.set_xlabel("Frequency (GHz)")
    ax.set_ylabel("Attenuation (dB)")
    ax.set_title("Weather-Induced Attenuation Components")
    ax.grid(True)
    ax.legend()

    st.pyplot(fig)
