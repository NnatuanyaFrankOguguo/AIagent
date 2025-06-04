from datetime import datetime
from zoneinfo import ZoneInfo


def local_to_utc(local_dt: datetime, tz_str: str) -> datetime:
    """
    Convert a local datetime to UTC based on the provided timezone string.

    Args:
        local_dt (datetime): The local datetime to convert.
        tz_str (str): The timezone string (e.g., 'America/New_York').

    Returns:
        datetime: The converted UTC datetime.
    """
    local_tz = ZoneInfo(tz_str)
    return local_dt.astimezone(local_tz).astimezone(ZoneInfo("UTC"))

def utc_to_local(utc_dt: datetime, tz_str: str) -> datetime:
    """
    Convert a UTC datetime to local time based on the provided timezone string.

    Args:
        utc_dt (datetime): The UTC datetime to convert.
        tz_str (str): The timezone string (e.g., 'America/New_York').

    Returns:
        datetime: The converted local datetime.
    """

    local_tz = ZoneInfo(tz_str)
    return utc_dt.astimezone(ZoneInfo("UTC")).astimezone(local_tz)