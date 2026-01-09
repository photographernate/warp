# WARP
**Weather Attenuation RF Planner**

<img width="300" height="300" alt="warppatch" src="https://github.com/user-attachments/assets/ea10491a-339d-42cb-9053-0a8e4a8ccf12" />


WARP is a small Python project that models RF signal degradation due to weather. The goal is to take real METAR weather data and estimate how much attenuation you might see from rain, atmospheric gases, and humidity across a range of RF frequencies.

This started as a “how bad is this link really going to be today?” tool and turned into a Streamlit app because that was faster than writing a proper UI.

This is not meant to be a standards-certified propagation tool. It’s an engineering estimation and visualization project.

---

## What it does

- Pulls current weather conditions from METAR data
- Models RF attenuation due to:
  - Rain
  - Gaseous absorption (oxygen and water vapor)
  - Humidity effects
- Supports multiple link types:
  - Fixed terrestrial LOS microwave paths
  - LEO / MEO / GEO satellite links
- Allows multiple frequencies to be evaluated at once
- Plots individual loss components and total attenuation

---

## What it does *not* do

- This is not flight-critical or ops-approved software
- This is not a full ITU-R implementation (yet)
- This will not magically fix a bad link budget

Use it as a planning and intuition tool, not a final answer.

---

## Tech stack

- Python 3.10+
- Streamlit
- metar (for METAR parsing)
- numpy
- pandas
- matplotlib

---

## Installation

Clone the repo:

```
git clone https://github.com/photographernate/WARP.git
cd WARP
pip install -r requirements.txt
```
Important: this project depends on the metar package. If you forget to install it, the app will crash immediately.
```
pip install metar
```
Running the app:
```
python -m streamlit run .\weather_rf_app.py
```

## Notes on modeling

- Satellite modes use typical altitudes for LEO, MEO, and GEO
- Elevation angle directly affects slant path length and attenuation
- Rain fade effects become dominant above ~10 GHz and get ugly fast above ~20–30 GHz
- Results are approximate and intended for comparative analysis
- If you need traceable, standard-compliant results, use the ITU docs directly.

## Known issues / rough edges

- UI is functional but not pretty
- METAR availability depends on station coverage
- Some assumptions are hardcoded and should probably be configurable
- This was written by an engineer, not a UI designer
- PRs welcome if you feel like fixing any of that.

## License

MIT License.
Do whatever you want with it, just don’t blame me if it breaks something.

## Author

Nathan Jones
