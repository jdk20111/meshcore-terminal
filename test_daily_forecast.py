#!/usr/bin/env python3
"""
Test OpenWeatherMap Daily Forecast API
"""

import json
import urllib.request

def test_daily_forecast_api():
    """Test OpenWeatherMap Daily Forecast API"""
    
    api_key = "c6894f088d4d4f462c99cfc5a03581ef"  # Your actual API key
    
    lat = 39.7392
    lon = -104.9903
    
    # Use daily forecast API
    url = f"https://api.openweathermap.org/data/2.5/forecast/daily?lat={lat}&lon={lon}&appid={api_key}&units=imperial&cnt=1"
    
    print(f"Testing OpenWeatherMap Daily Forecast API: {url}")
    
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = response.read()
            print(f"SUCCESS - Status: {response.status}")
            
            json_data = json.loads(data.decode("utf-8"))
            
            # Extract daily forecast data
            forecasts = json_data.get("list", [])
            
            if forecasts:
                daily_forecast = forecasts[0]
                main = daily_forecast.get("temp", {})
                weather = daily_forecast.get("weather", [{}])[0]
                
                temp_day = main.get("day", "N/A")
                temp_min = main.get("min", "N/A")
                temp_max = main.get("max", "N/A")
                humidity = daily_forecast.get("humidity", "N/A")
                
                weather_desc = weather.get("description", "Unknown")
                precip_prob = daily_forecast.get("pop", 0) * 100
                
                wind_speed = daily_forecast.get("speed", 0)
                
                # Get forecast date
                forecast_date = daily_forecast.get("dt", 0)
                import datetime
                forecast_datetime = datetime.datetime.fromtimestamp(forecast_date)
                
                print(f"Forecast date: {forecast_datetime.strftime('%Y-%m-%d')}")
                print(f"Weather: {weather_desc}")
                print(f"Daytime temp: {temp_day}°F")
                print(f"High/Low: {temp_max}°F / {temp_min}°F")
                print(f"Humidity: {humidity}%")
                print(f"Precipitation: {precip_prob}%")
                print(f"Wind: {wind_speed} MPH")
                
                # Show expected bot output
                user_mention = "@Bob"
                city_abbr = "DEN"
                forecast_output = f"GM! {user_mention} {city_abbr} Forecast: {weather_desc} H{int(temp_max)} L{int(temp_min)} Precip: {int(precip_prob)}% Hum: {humidity}% Wind: {wind_speed} MPH"
                print(f"\nExpected bot output: {forecast_output}")
            else:
                print("No daily forecast data received")
                    
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    test_daily_forecast_api()
