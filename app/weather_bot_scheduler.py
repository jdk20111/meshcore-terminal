"""Weather bot scheduler for automatic 7am Mountain Time posts."""

import asyncio
import datetime
import logging
from pathlib import Path

from app.fanout.bot_exec import execute_bot_code, process_bot_response
from app.models import SendChannelMessageRequest
from app.routers.messages import send_channel_message

logger = logging.getLogger(__name__)

# Path to weather bot code
WEATHER_BOT_PATH = Path(__file__).parent.parent / "weather-bot" / "weather-bot.py"

# Target channel for weather posts
WEATHER_CHANNEL_KEY = None  # Will be set to CDC-BOTS channel key


async def load_weather_bot_code() -> str:
    """Load the weather bot Python code from file."""
    try:
        with open(WEATHER_BOT_PATH, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Failed to load weather bot code: {e}")
        return ""


def is_mdst(dt: datetime.datetime) -> bool:
    """Check if given datetime is during Mountain Daylight Time."""
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


def is_12_40_mountain_time() -> bool:
    """Check if current time is within the 12:40pm Mountain Time window."""
    now = datetime.datetime.now()
    
    # Apply correct Mountain Time offset
    mt_offset = -6 if is_mdst(now) else -7
    mt_time = now + datetime.timedelta(hours=mt_offset)
    
    # 5-minute window around 12:40pm MT
    return mt_time.hour == 12 and mt_time.minute >= 40 and mt_time.minute < 45


async def get_cdc_bots_channel_key() -> str | None:
    """Get the channel key for CDC-BOTS channel."""
    try:
        from app.repository import ChannelRepository
        
        # Search for CDC-BOTS channel
        channels = await ChannelRepository.get_all()
        for channel in channels:
            if channel.name and "CDC-BOTS" in channel.name.upper():
                return channel.key
        
        logger.warning("CDC-BOTS channel not found")
        return None
    except Exception as e:
        logger.error(f"Failed to get CDC-BOTS channel key: {e}")
        return None


async def trigger_weather_bot() -> None:
    """Trigger the weather bot with a simulated message."""
    global WEATHER_CHANNEL_KEY
    
    # Get channel key if not already cached
    if WEATHER_CHANNEL_KEY is None:
        WEATHER_CHANNEL_KEY = await get_cdc_bots_channel_key()
        if WEATHER_CHANNEL_KEY is None:
            logger.error("Cannot trigger weather bot: CDC-BOTS channel not found")
            return
    
    # Load weather bot code
    bot_code = await load_weather_bot_code()
    if not bot_code:
        logger.error("Cannot trigger weather bot: failed to load code")
        return
    
    try:
        # Execute bot code with simulated 7am trigger
        # We pass empty message text since this is a time-based trigger
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            execute_bot_code,
            bot_code,
            None,  # sender_name
            None,  # sender_key  
            "",    # message_text (empty for time trigger)
            False, # is_dm
            WEATHER_CHANNEL_KEY,  # channel_key
            "CDC-BOTS",  # channel_name
            None,  # sender_timestamp
            None,  # path
            False, # is_outgoing
        )
        
        if response:
            logger.info(f"Weather bot responded: {response}")
            await process_bot_response(response, False, "", WEATHER_CHANNEL_KEY)
        else:
            logger.info("Weather bot did not respond to time trigger")
            
    except Exception as e:
        logger.error(f"Error triggering weather bot: {e}")


async def weather_bot_scheduler() -> None:
    """Background task that checks for 12:40pm MT and triggers weather bot."""
    logger.info("Weather bot scheduler started (12:40pm MT)")
    
    while True:
        try:
            # Check if it's 12:40pm Mountain Time
            if is_12_40_mountain_time():
                logger.info("Triggering weather bot for 12:40pm MT post")
                await trigger_weather_bot()
                
                # Wait 10 minutes to avoid multiple triggers
                await asyncio.sleep(600)
            else:
                # Check every minute
                await asyncio.sleep(60)
                
        except asyncio.CancelledError:
            logger.info("Weather bot scheduler cancelled")
            break
        except Exception as e:
            logger.error(f"Error in weather bot scheduler: {e}")
            await asyncio.sleep(60)  # Wait before retrying


async def start_weather_bot_scheduler() -> asyncio.Task:
    """Start the weather bot scheduler as a background task."""
    return asyncio.create_task(weather_bot_scheduler())
