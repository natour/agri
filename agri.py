import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import pvlib
from pvlib.tools import cosd

st.set_page_config(layout="wide")
st.title("🌾 Agrivoltaic System Modeling using pvlib")

# Sidebar Inputs
st.sidebar.header("Simulation Parameters")

latitude = st.sidebar.number_input("Latitude", value=55.0)
longitude = st.sidebar.number_input("Longitude", value=10.0)
date_input = st.sidebar.date_input("Date", value=pd.to_datetime("2020-06-28"))

height = st.sidebar.number_input("Tracker Height (m)", value=2.6)
pitch = st.sidebar.number_input("Row Spacing (Pitch) (m)", value=12.0)
row_width = st.sidebar.number_input("Row Width (m)", value=2 * 2.384)
axis_azimuth = st.sidebar.slider("Tracker Axis Azimuth (°)", 0, 360, 0)
max_angle = st.sidebar.slider("Max Tracker Angle (°)", 0, 90, 55)

albedo = st.sidebar.slider("Ground Albedo", 0.0, 1.0, 0.2)
temp_air = st.sidebar.slider("Ambient Temperature (°C)", -10, 50, 18)
bifaciality = st.sidebar.slider("Bifaciality Coefficient", 0.0, 1.0, 0.7)

N_modules = st.sidebar.number_input("Number of Modules", value=1512)
pdc0_per_module = st.sidebar.number_input("Module Rating (W)", value=660)
gamma_pdc = st.sidebar.number_input("Gamma PDC (1/°C)", value=-0.004)

# Calculations
location = pvlib.location.Location(latitude, longitude)
times = pd.date_range(date_input, periods=1440, freq="1min", tz="UTC")
solpos = location.get_solarposition(times)
clearsky = location.get_clearsky(times, model='ineichen')

gcr = row_width / pitch
tracking = pvlib.tracking.singleaxis(
    apparent_zenith=solpos['apparent_zenith'],
    apparent_azimuth=solpos['azimuth'],
    axis_azimuth=axis_azimuth,
    max_angle=max_angle,
    backtrack=True,
    gcr=gcr,
)

dni_extra = pvlib.irradiance.get_extra_radiation(times)

irradiance = pvlib.bifacial.infinite_sheds.get_irradiance(
    surface_tilt=tracking['surface_tilt'],
    surface_azimuth=tracking['surface_azimuth'],
    solar_zenith=solpos['apparent_zenith'],
    solar_azimuth=solpos['azimuth'],
    gcr=gcr,
    height=height,
    pitch=pitch,
    ghi=clearsky['ghi'],
    dhi=clearsky['dhi'],
    dni=clearsky['dni'],
    albedo=albedo,
    model='haydavies',
    dni_extra=dni_extra,
    bifaciality=bifaciality,
)

# DC Power Estimation
pdc0 = pdc0_per_module * N_modules
temp_cell = pvlib.temperature.faiman(irradiance['poa_global'], temp_air)
power_dc = pvlib.pvsystem.pvwatts_dc(
    effective_irradiance=irradiance['poa_global'],
    temp_cell=temp_cell,
    pdc0=pdc0,
    gamma_pdc=gamma_pdc,
)

# Crop irradiance estimate
vf_ground_sky = pvlib.bifacial.utils.vf_ground_sky_2d_integ(
    surface_tilt=tracking['surface_tilt'],
    gcr=gcr,
    height=height,
    pitch=pitch,
)
unshaded_ground_fraction = pvlib.bifacial.utils._unshaded_ground_fraction(
    surface_tilt=tracking['surface_tilt'],
    surface_azimuth=tracking['surface_azimuth'],
    solar_zenith=solpos['apparent_zenith'],
    solar_azimuth=solpos['azimuth'],
    gcr=gcr,
)

crop_irradiance = (
    unshaded_ground_fraction * clearsky['dni'] * cosd(solpos['apparent_zenith']) +
    vf_ground_sky * clearsky['dhi']
)

# --- Plot 1: DC Power ---
st.subheader("📈 DC Power Output")
fig1, ax1 = plt.subplots()
power_dc.divide(1000).plot(ax=ax1)
ax1.set_title("DC Power (kW)")
ax1.set_ylabel("kW")
st.pyplot(fig1)

# --- Plot 2: Crop vs Panel Irradiance ---
st.subheader("🌤️ Irradiance Comparison")
fig2, ax2 = plt.subplots()
clearsky['ghi'].plot(ax=ax2, label='Above-panel GHI')
crop_irradiance.plot(ax=ax2, label='Crop-level Irradiance')
ax2.legend()
ax2.set_ylabel("Irradiance [W/m²]")
ax2.set_title("Irradiance at Panel vs Crop Level")
st.pyplot(fig2)
