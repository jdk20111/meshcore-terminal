def bot(
    sender_name: str | None,
    sender_key: str | None,
    message_text: str,
    is_dm: bool,
    channel_key: str | None,
    channel_name: str | None,
    sender_timestamp: int | None,
    path: str | None,
    is_outgoing: bool = False,
    # NOTE: These would need to be added by modifying the bot system
    sender_lat: float | None = None,
    sender_lon: float | None = None,
) -> str | list[str] | None:
    """
    Weather bot that provides daily weather forecasts for the #jktest channel.
    Runs automatically at 7am Mountain Time and can be triggered manually.
    """
    # ALWAYS log that we were called
    print(f"*** BOT FUNCTION CALLED *** channel={channel_name}, message='{message_text}', outgoing={is_outgoing}")
    
    # Don't reply to our own outgoing messages
    if is_outgoing: 
        print(f"*** BOT IGNORING OUTGOING MESSAGE ***")
        return None

    print(f"*** BOT PROCESSING INCOMING MESSAGE ***")
    
    # Only respond in CDC-BOTS channel OR in DMs
    if channel_name != "CDC-BOTS" and not is_dm:
        print(f"*** BOT NOT RESPONDING - NOT IN CDC-BOTS AND NOT DM ***")
        return None

    import datetime
    
    # Check if it's 12:40pm Mountain Time (MDT/MST) for daily forecast
    now = datetime.datetime.now()
    
    # Proper Mountain Time calculation with DST handling
    # Mountain Time is UTC-7 (MST) or UTC-6 (MDT)
    # DST in US: Second Sunday in March to first Sunday in November
    def is_mdst(dt):
        """Check if given datetime is during Mountain Daylight Time"""
        year = dt.year
        # DST starts: Second Sunday in March at 2am local time
        march_start = datetime.datetime(year, 3, 1)
        days_to_sunday = (6 - march_start.weekday()) % 7
        dst_start = march_start + datetime.timedelta(days=days_to_sunday + 7, hours=2)
        
        # DST ends: First Sunday in November at 2am local time  
        november_start = datetime.datetime(year, 11, 1)
        days_to_sunday_nov = (6 - november_start.weekday()) % 7
        dst_end = november_start + datetime.timedelta(days=days_to_sunday_nov, hours=2)
        
        return dst_start <= dt < dst_end
    
    # Apply correct Mountain Time offset
    mt_offset = -6 if is_mdst(now) else -7
    mt_time = now + datetime.timedelta(hours=mt_offset)
    
    is_1_15_mt = mt_time.hour == 13 and mt_time.minute >= 15 and mt_time.minute < 20  # 5-minute window
    
    # Manual trigger: exactly "weather" (case-insensitive)
    is_weather_trigger = message_text.strip().lower() == "weather"
    
    # Auto-trigger: any message at 1:15pm MT (to allow scheduled posts)
    is_time_trigger = is_1_15_mt and message_text.strip() != ""
    
    # Respond if it's time trigger OR manual weather trigger
    if is_time_trigger or is_weather_trigger:
        if is_time_trigger:
            print(f"*** BOT RESPONDING - TIME TRIGGER: 1:15pm MT ***")
        else:
            print(f"*** BOT RESPONDING TO WEATHER REQUEST - DUAL POST ***")
        
        # Use sender's location if available, otherwise default to Denver
        lat = sender_lat if sender_lat is not None else 39.7392
        lon = sender_lon if sender_lon is not None else -104.9903
        location_name = "your location" if (sender_lat is not None and sender_lon is not None) else "Denver, CO"
        
        try:
            # Get both current weather and daily forecast
            current_weather = get_current_weather(lat, lon, location_name)
            daily_forecast = get_weather_forecast(lat, lon, location_name, sender_name, is_daily=True)
            
            # Return both messages as a list
            return [current_weather, daily_forecast]
            
        except Exception as e:
            print(f"*** BOT WEATHER ERROR: {e} ***")
            return [f"Sorry, I couldn't get the weather data for {location_name} right now."]
    
    print(f"*** BOT NOT RESPONDING - NO TRIGGER (TIME: {mt_time.hour}:{mt_time.minute:02d} MT) ***")
    return None


def get_current_weather(lat: float, lon: float, location_name: str) -> str:
    """
    Get current weather conditions using OpenWeatherMap API.
    
    Args:
        lat: Latitude
        lon: Longitude  
        location_name: Human-readable location name
        
    Returns:
        Formatted current weather string
    """
    import json
    import time
    from urllib.error import URLError
    from urllib.request import urlopen
    
    # OpenWeatherMap API for current weather
    api_key = "c6894f088d4d4f462c99cfc5a03581ef"  # Your actual API key
    
    if api_key == "YOUR_API_KEY_HERE":
        return "DEN Current: API key required - get one from https://openweathermap.org/api"
    
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=imperial"
    
    print(f"*** DEBUG: OpenWeatherMap Current URL: {url} ***")
    
    # Retry logic - try up to 3 times
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with urlopen(url, timeout=10) as response:
                payload = response.read()
            break  # Success, exit retry loop
        except URLError as e:
            if attempt == max_retries - 1:  # Last attempt
                raise Exception(f"Failed to fetch current weather after {max_retries} attempts: {e}")
            print(f"*** CURRENT WEATHER API ATTEMPT {attempt + 1} FAILED, RETRYING... ***")
            time.sleep(1)  # Wait 1 second before retry
    
    try:
        data = json.loads(payload.decode("utf-8"))
    except json.JSONDecodeError as e:
        raise Exception(f"Failed to parse current weather data: {e}")
    
    # Extract current weather data
    main = data.get("main", {})
    weather = data.get("weather", [{}])[0]
    wind = data.get("wind", {})
    
    temp = main.get("temp", "N/A")
    feels_like = main.get("feels_like", "N/A")
    humidity = main.get("humidity", "N/A")
    
    wind_speed = wind.get("speed", "N/A")
    
    weather_desc = weather.get("description", "Unknown")
    
    # Convert city abbreviation
    if "denver" in location_name.lower():
        city_abbr = "DEN"
    else:
        city_abbr = "DEN"  # Default to DEN
    
    # Format: DEN Current: Sunny 55°F Feels: 52°F Hum: 27% Wind: 3 MPH
    current = f"{city_abbr} Current: {weather_desc} {int(temp)}°F Feels: {int(feels_like)}°F Hum: {humidity}% Wind: {wind_speed} MPH"
    
    return current


def get_weather_forecast(lat: float, lon: float, location_name: str, sender_name: str | None, is_daily: bool = False) -> str:
    """
    Get a weather forecast using Open-Meteo for most data and OpenWeatherMap for precipitation.
    
    Args:
        lat: Latitude
        lon: Longitude  
        location_name: Human-readable location name
        sender_name: Name of the user requesting weather
        is_daily: If True, get daily forecast; if False, get 3-hour forecast
        
    Returns:
        Formatted weather forecast string
    """
    import json
    import time
    from urllib.error import URLError
    from urllib.request import urlopen
    
    # Open-Meteo API for most weather data (no API key required)
    openmeteo_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max,temperature_2m_min,weathercode,windspeed_10m_max,uv_index_max&forecast_days=1&timezone=auto&temperature_unit=fahrenheit&windspeed_unit=mph"
    
    print(f"*** DEBUG: Open-Meteo URL: {openmeteo_url} ***")
    
    # Get Open-Meteo data
    try:
        with urlopen(openmeteo_url, timeout=10) as response:
            openmeteo_payload = response.read()
    except URLError as e:
        raise Exception(f"Failed to fetch Open-Meteo data: {e}")
    
    try:
        openmeteo_data = json.loads(openmeteo_payload.decode("utf-8"))
    except json.JSONDecodeError as e:
        raise Exception(f"Failed to parse Open-Meteo data: {e}")
    
    # Parse Open-Meteo data
    daily = openmeteo_data.get("daily", {})
    dates = daily.get("time", [])
    max_temps = daily.get("temperature_2m_max", [])
    min_temps = daily.get("temperature_2m_min", [])
    weather_codes = daily.get("weathercode", [])
    wind_speeds = daily.get("windspeed_10m_max", [])
    uv_indices = daily.get("uv_index_max", [])
    
    if not dates or len(dates) == 0:
        raise Exception("Insufficient Open-Meteo data received")
    
    # Get today's data from Open-Meteo
    max_temp = max_temps[0] if len(max_temps) > 0 else "N/A"
    min_temp = min_temps[0] if len(min_temps) > 0 else "N/A"
    weather_code = weather_codes[0] if len(weather_codes) > 0 else 0
    wind_speed = wind_speeds[0] if len(wind_speeds) > 0 else 0
    uv_index = uv_indices[0] if len(uv_indices) > 0 else 0
    
    # Weather code descriptions (Open-Meteo format)
    weather_desc = {
        0: "Clear", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
        45: "Fog", 48: "Fog", 51: "Drizzle", 53: "Drizzle", 55: "Drizzle",
        56: "Freezing Drizzle", 57: "Freezing Drizzle", 61: "Rain", 63: "Rain",
        65: "Heavy rain", 66: "Freezing Rain", 67: "Freezing Rain",
        71: "Snow", 73: "Snow", 75: "Heavy snow", 77: "Snow grains",
        80: "Showers", 81: "Showers", 82: "Heavy showers", 85: "Snow showers",
        86: "Snow showers", 95: "Thunderstorm", 96: "Thunderstorm",
        99: "Severe thunderstorm"
    }
    
    weather = weather_desc.get(weather_code, "Unknown")
    
    # OpenWeatherMap API just for precipitation probability
    api_key = "c6894f088d4d4f462c99cfc5a03581ef"  # Your actual API key
    
    if api_key == "YOUR_API_KEY_HERE":
        precip_prob = 0  # Default to 0 if no API key
        print(f"*** WARNING: No OpenWeatherMap API key for precipitation data ***")
    else:
        openweather_url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={api_key}&units=imperial"
        
        print(f"*** DEBUG: OpenWeatherMap URL (precip only): {openweather_url} ***")
        
        # Retry logic for OpenWeatherMap
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with urlopen(openweather_url, timeout=10) as response:
                    openweather_payload = response.read()
                break
            except URLError as e:
                if attempt == max_retries - 1:
                    print(f"*** WARNING: Failed to get precipitation data after {max_retries} attempts: {e} ***")
                    precip_prob = 0
                    break
                print(f"*** PRECIP API ATTEMPT {attempt + 1} FAILED, RETRYING... ***")
                time.sleep(1)
        
        if 'openweather_payload' in locals():
            try:
                openweather_data = json.loads(openweather_payload.decode("utf-8"))
                forecasts = openweather_data.get("list", [])
                
                if forecasts:
                    # Get max precipitation probability and average humidity from today's forecasts
                    import datetime
                    today = datetime.datetime.now().date()
                    today_precips = []
                    today_humidities = []
                    
                    for forecast in forecasts:
                        forecast_time = datetime.datetime.fromtimestamp(forecast.get("dt", 0))
                        if forecast_time.date() == today:
                            today_precips.append(forecast.get("pop", 0) * 100)
                            today_humidities.append(forecast.get("main", {}).get("humidity", 0))
                    
                    if today_precips:
                        precip_prob = max(today_precips)
                    else:
                        precip_prob = forecasts[0].get("pop", 0) * 100
                    
                    if today_humidities:
                        humidity = int(sum(today_humidities) / len(today_humidities))
                    else:
                        humidity = forecasts[0].get("main", {}).get("humidity", 0)
                else:
                    precip_prob = 0
                    humidity = 0
                    
            except json.JSONDecodeError:
                print(f"*** WARNING: Failed to parse OpenWeatherMap precipitation data ***")
                precip_prob = 0
                humidity = 0
    
    # Convert city abbreviation
    if "denver" in location_name.lower():
        city_abbr = "DEN"
    else:
        city_abbr = "DEN"  # Default to DEN
    
    # Format: {city abbreviation} Forecast: Sunny H68 L33 Precip: 10% Hum: 85% Wind: 13 MPH UV: 5
    forecast = f"{city_abbr} Forecast: {weather} H{int(max_temp)} L{int(min_temp)} Precip: {int(precip_prob)}% Hum: {humidity}% Wind: {wind_speed} MPH UV: {uv_index}"
    
    return forecast
