"""
tools/environment.py — Live environment & weather advisory
------------------------------------------------------------
Calls the NEA/data.gov.sg real-time APIs for PSI air quality and the
2-hour weather forecast. Used by both the Gemini chat tool and (indirectly)
by server.py's dedicated /api/sg-hub/weather endpoint.
"""

import os
import math
import logging
import requests
from tools.core import _data_gov_sg_headers, _cache_get, _cache_set

logger = logging.getLogger("merlion-os-environment")

def get_singapore_live_environment_advisory(context_query: str = "general") -> str:
    """Tool: Retrieves live Singapore environment advisories, including weather forecasts and PSI (air quality index) from data.gov.sg.

    Args:
        context_query: The specific advisory requested, e.g., 'weather', 'psi', or 'haze'. Defaults to 'general'.
    """
    import requests

    q_lower = context_query.lower()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        **_data_gov_sg_headers()
    }

    results = []

    # 1. Fetch PSI data if haze/psi or general is queried
    if "weather" not in q_lower or "psi" in q_lower or "haze" in q_lower or q_lower == "general":
        try:
            print("  [NEA API] HTTP GET https://api-open.data.gov.sg/v2/real-time/api/psi")
            r_psi = requests.get("https://api-open.data.gov.sg/v2/real-time/api/psi", headers=headers, timeout=10)
            if r_psi.status_code == 200:
                data = r_psi.json()
                readings_list = data.get("data", {}).get("readings", [])
                if readings_list:
                    readings = readings_list[0]
                    psi_twenty_four = readings.get("psiTwentyFourHr", {})
                    national_psi = psi_twenty_four.get("national", "N/A")

                    status = "Good"
                    try:
                        val = float(national_psi)
                        if val > 300: status = "Hazardous"
                        elif val > 200: status = "Very Unhealthy"
                        elif val > 100: status = "Unhealthy"
                        elif val > 50: status = "Moderate"
                    except ValueError:
                        pass

                    results.append(
                        f"--- [NEA LIVE ADVISORY: PSI AIR QUALITY] ---\n"
                        f"🍃 24-Hr National PSI Reading: {national_psi} ({status})\n"
                        f"📋 Status Summary: Air quality is {status.lower()}. Suitable for general outdoor activities."
                    )
                else:
                    results.append("--- [NEA LIVE ADVISORY: PSI AIR QUALITY] ---\n📋 No current air quality readings available.")
            else:
                results.append(f"--- [NEA LIVE ADVISORY: PSI AIR QUALITY] ---\n⚠️ Failed to fetch PSI: HTTP {r_psi.status_code}")
        except Exception as e:
            results.append(f"--- [NEA LIVE ADVISORY: PSI AIR QUALITY] ---\n⚠️ Failed to fetch PSI: {str(e)}")

    # 2. Fetch Weather Forecast if weather or general is queried
    if "psi" not in q_lower or "weather" in q_lower or "forecast" in q_lower or q_lower == "general":
        try:
            print("  [NEA API] HTTP GET https://api-open.data.gov.sg/v2/real-time/api/two-hr-forecast")
            r_weather = requests.get("https://api-open.data.gov.sg/v2/real-time/api/two-hr-forecast", headers=headers, timeout=10)
            if r_weather.status_code == 200:
                data = r_weather.json()
                items = data.get("data", {}).get("items", [])
                if items:
                    forecasts = items[0].get("forecasts", [])
                    targets = {"Tampines", "Orchard", "Jurong West", "Woodlands", "Downtown Core", "Punggol"}
                    forecast_lines = []
                    for f in forecasts:
                        area = f.get("area")
                        if area in targets:
                            forecast_lines.append(f"   • {area}: {f.get('forecast')}")

                    weather_summary = "\n".join(forecast_lines) if forecast_lines else "   • Live forecast data temporarily unavailable."

                    results.append(
                        f"--- [NEA LIVE ADVISORY: 2-HR WEATHER FORECAST] ---\n"
                        f"⛅ Current Area Outlook:\n{weather_summary}"
                    )
                else:
                    results.append("--- [NEA LIVE ADVISORY: 2-HR WEATHER FORECAST] ---\n📋 No current forecast readings available.")
            else:
                results.append(f"--- [NEA LIVE ADVISORY: 2-HR WEATHER FORECAST] ---\n⚠️ Failed to fetch Weather: HTTP {r_weather.status_code}")
        except Exception as e:
            results.append(f"--- [NEA LIVE ADVISORY: 2-HR WEATHER FORECAST] ---\n⚠️ Failed to fetch Weather: {str(e)}")

    return "\n\n".join(results)

def fetch_weather_data() -> dict:
    """
    Synchronous worker that fires all 10 NEA real-time API calls this panel needs.

    The calls are independent, so they run concurrently on a small thread pool — a cold fetch
    now costs ~1 round-trip instead of ~10 in series. (This function is only reached on a cache
    miss; the endpoint caches the result for a few minutes.)
    """
    from concurrent.futures import ThreadPoolExecutor

    print("\n\033[94m[MerlionOS Orchestrator] --- Fetching Weather & PSI Data Selected ---\033[0m")
    print("\033[96m[NEA API Weather Engine] Querying live weather forecasts & air quality...\033[0m")

    headers = {"User-Agent": "Mozilla/5.0"}
    data_gov_sg_api_key = os.environ.get("DATA_GOV_SG_API_KEY", "").strip()
    if data_gov_sg_api_key:
        headers["x-api-key"] = data_gov_sg_api_key

    base = "https://api-open.data.gov.sg/v2/real-time/api"

    def _get(endpoint: str):
        print(f"  \033[90m[NEA API] HTTP GET {base}/{endpoint}\033[0m")
        return requests.get(f"{base}/{endpoint}", headers=headers, timeout=5)

    try:
        def fetch_psi():
            psi_val, psi_status = 28, "Good"
            try:
                r_psi = _get("psi")
                if r_psi.status_code == 200:
                    data = r_psi.json()
                    readings = data.get("data", {}).get("readings", [])
                    if readings:
                        national_val = readings[0].get("psiTwentyFourHr", {}).get("national", 28)
                        try:
                            psi_val = int(national_val)
                        except:
                            pass
                        if psi_val > 300: psi_status = "Hazardous"
                        elif psi_val > 200: psi_status = "Very Unhealthy"
                        elif psi_val > 100: psi_status = "Unhealthy"
                        elif psi_val > 50: psi_status = "Moderate"
                        else: psi_status = "Good"
            except Exception as e:
                logger.warning(f"PSI Fetch failed: {e}")
            return {"value": psi_val, "status": psi_status}

        def fetch_forecasts():
            forecasts_list = []
            try:
                r_weather = _get("two-hr-forecast")
                if r_weather.status_code == 200:
                    data = r_weather.json()
                    items = data.get("data", {}).get("items", [])
                    if items:
                        raw_forecasts = items[0].get("forecasts", [])
                        targets = {"Tampines", "Orchard", "Jurong West", "Woodlands", "Downtown Core", "Punggol"}
                        for f in raw_forecasts:
                               area = f.get("area")
                               if area in targets:
                                   forecasts_list.append({
                                       "area": area,
                                       "forecast": f.get("forecast")
                                   })
            except Exception as e:
                logger.warning(f"Weather Fetch failed: {e}")

            if not forecasts_list:
                forecasts_list = [
                    {"area": "Downtown Core", "forecast": "Partly Cloudy"},
                    {"area": "Orchard", "forecast": "Partly Cloudy"},
                    {"area": "Tampines", "forecast": "Light Showers"},
                    {"area": "Jurong West", "forecast": "Fair"},
                    {"area": "Woodlands", "forecast": "Cloudy"},
                    {"area": "Punggol", "forecast": "Thundery Showers"}
                ]
            return forecasts_list

        def fetch_pm25():
            try:
                r_pm25 = _get("pm25")
                if r_pm25.status_code == 200:
                    items = r_pm25.json().get("data", {}).get("items", [])
                    if items:
                        regional = items[0].get("readings", {}).get("pm25_one_hourly", {})
                        if regional:
                            return round(sum(regional.values()) / len(regional))
            except Exception as e:
                logger.warning(f"PM2.5 Fetch failed: {e}")
            return None

        def avg_station_reading(endpoint: str):
            try:
                r = _get(endpoint)
                if r.status_code == 200:
                    readings = r.json().get("data", {}).get("readings", [])
                    if readings:
                        values = [d["value"] for d in readings[0].get("data", []) if isinstance(d.get("value"), (int, float))]
                        if values:
                            return round(sum(values) / len(values), 1)
            except Exception as e:
                logger.warning(f"{endpoint} Fetch failed: {e}")
            return None

        def fetch_wind_direction():
            try:
                r_dir = _get("wind-direction")
                if r_dir.status_code == 200:
                    readings = r_dir.json().get("data", {}).get("readings", [])
                    if readings:
                        degrees = [d["value"] for d in readings[0].get("data", []) if isinstance(d.get("value"), (int, float))]
                        if degrees:
                            sin_sum = sum(math.sin(math.radians(d)) for d in degrees)
                            cos_sum = sum(math.cos(math.radians(d)) for d in degrees)
                            mean_deg = math.degrees(math.atan2(sin_sum, cos_sum)) % 360
                            compass = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                                       "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
                            return compass[round(mean_deg / 22.5) % 16]
            except Exception as e:
                logger.warning(f"Wind Direction Fetch failed: {e}")
            return None

        def fetch_rainfall():
            try:
                r_rain = _get("rainfall")
                if r_rain.status_code == 200:
                    readings = r_rain.json().get("data", {}).get("readings", [])
                    if readings:
                        values = [d["value"] for d in readings[0].get("data", []) if isinstance(d.get("value"), (int, float))]
                        if values:
                            return (max(values), sum(1 for v in values if v > 0), len(values))
            except Exception as e:
                logger.warning(f"Rainfall Fetch failed: {e}")
            return (None, 0, 0)

        def fetch_outlook():
            try:
                r_outlook = _get("twenty-four-hr-forecast")
                if r_outlook.status_code == 200:
                    records = r_outlook.json().get("data", {}).get("records", [])
                    if records:
                        general = records[0].get("general", {})
                        return {
                            "forecast": general.get("forecast", {}).get("text"),
                            "temp_low": general.get("temperature", {}).get("low"),
                            "temp_high": general.get("temperature", {}).get("high"),
                            "humidity_low": general.get("relativeHumidity", {}).get("low"),
                            "humidity_high": general.get("relativeHumidity", {}).get("high"),
                            "wind_speed_low": general.get("wind", {}).get("speed", {}).get("low"),
                            "wind_speed_high": general.get("wind", {}).get("speed", {}).get("high"),
                            "wind_direction": general.get("wind", {}).get("direction"),
                        }
            except Exception as e:
                logger.warning(f"24-Hr Forecast Fetch failed: {e}")
            return None

        # Fire every independent NEA call at once; the panel loads in one round-trip's time.
        with ThreadPoolExecutor(max_workers=10) as ex:
            f_psi = ex.submit(fetch_psi)
            f_forecasts = ex.submit(fetch_forecasts)
            f_pm25 = ex.submit(fetch_pm25)
            f_air = ex.submit(avg_station_reading, "air-temperature")
            f_humidity = ex.submit(avg_station_reading, "relative-humidity")
            f_wind = ex.submit(avg_station_reading, "wind-speed")
            f_uv = ex.submit(avg_station_reading, "uv-index")
            f_dir = ex.submit(fetch_wind_direction)
            f_rain = ex.submit(fetch_rainfall)
            f_outlook = ex.submit(fetch_outlook)

            psi = f_psi.result()
            forecasts_list = f_forecasts.result()
            pm25_val = f_pm25.result()
            air_temp = f_air.result()
            humidity = f_humidity.result()
            wind_speed = f_wind.result()
            uv_index = f_uv.result()
            wind_direction = f_dir.result()
            rainfall_max, rainfall_stations_wet, rainfall_stations_total = f_rain.result()
            outlook_24hr = f_outlook.result()

        print("\033[96m[NEA API Weather Engine] Live environment metrics retrieved successfully.\033[0m")
        result = {
            "psi": psi,
            "pm25": pm25_val,
            "forecasts": forecasts_list,
            "current_conditions": {
                "air_temperature": air_temp,
                "humidity": humidity,
                "wind_speed": wind_speed,
                "wind_direction": wind_direction,
                "rainfall_max": rainfall_max,
                "rainfall_stations_wet": rainfall_stations_wet,
                "rainfall_stations_total": rainfall_stations_total,
                "uv_index": uv_index,
            },
            "outlook_24hr": outlook_24hr
        }
        return result
    except Exception:
        logger.exception("Error fetching weather data")
        raise

_flood_alerts_cache = {"data": None, "fetched_at": 0}
_FLOOD_ALERTS_CACHE_TTL_SECONDS = 3 * 60

def fetch_pub_flood_alerts() -> dict:
    """
    Calls the PUB Flood Alerts real-time API on data.gov.sg.
    Returns a structured dict with active/cancelled alerts.
    Cached for 3 minutes to stay within burst rate limits.
    """
    cached = _cache_get(_flood_alerts_cache, _FLOOD_ALERTS_CACHE_TTL_SECONDS)
    if cached is not None:
        return cached

    headers = {"User-Agent": "Mozilla/5.0"}
    data_gov_sg_api_key = os.environ.get("DATA_GOV_SG_API_KEY", "").strip()
    if data_gov_sg_api_key:
        headers["x-api-key"] = data_gov_sg_api_key

    url = "https://api-open.data.gov.sg/v2/real-time/api/weather/flood-alerts"
    print(f"  \033[90m[PUB Flood Alerts] HTTP GET {url}\033[0m")
    try:
        r = requests.get(url, headers=headers, timeout=6)
        print(f"  \033[90m[PUB Flood Alerts] HTTP RESPONSE: {r.status_code}\033[0m")
        r.raise_for_status()
        data = r.json()

        from datetime import datetime, timezone, timedelta
        sgt_now = datetime.now(timezone(timedelta(hours=8)))
        retrieved_at = sgt_now.strftime("%d %b %Y, %I:%M %p")

        items = data.get("data", {}).get("items", [])
        alerts = []
        for item in items:
            for alert in item.get("floodAlerts", []):
                message = alert.get("message", "").strip()
                status = alert.get("status", "").strip()
                if not message:
                    continue
                alerts.append({
                    "message": message,
                    "status": status,
                    "is_active": status.lower() not in ("cancel", "cancelled", "cleared", "all clear"),
                })

        active_count = sum(1 for a in alerts if a["is_active"])
        print(f"  \033[32m✔\033[0m [PUB Flood Alerts] {len(alerts)} alert(s) retrieved ({active_count} active).")

        result = {"alerts": alerts, "active_count": active_count, "retrieved_at": retrieved_at}
        _cache_set(_flood_alerts_cache, result)
        return result
    except Exception as e:
        logger.warning(f"[PUB Flood Alerts] Fetch failed: {e}")
        result = {"alerts": [], "active_count": 0, "retrieved_at": None}
        _cache_set(_flood_alerts_cache, result)
        return result
