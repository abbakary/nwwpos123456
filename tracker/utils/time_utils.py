"""
Time utilities for calculating working hours, estimated duration, and overdue status.
Working hours are defined as 8:00 AM to 5:00 PM (9 hours per day).
"""

from datetime import datetime, timedelta, time
from django.utils import timezone


# Working hours constants
WORK_START_HOUR = 8  # 8:00 AM
WORK_END_HOUR = 17   # 5:00 PM
WORKING_HOURS_PER_DAY = 9  # 8 AM to 5 PM = 9 hours
OVERDUE_THRESHOLD_HOURS = 9  # Mark as overdue after 9 working hours


def get_work_start_time(dt: datetime) -> datetime:
    """Get the start of working day (8 AM) for a given date."""
    if not dt:
        return None
    work_start = dt.replace(hour=WORK_START_HOUR, minute=0, second=0, microsecond=0)
    return work_start


def get_work_end_time(dt: datetime) -> datetime:
    """Get the end of working day (5 PM) for a given date."""
    if not dt:
        return None
    work_end = dt.replace(hour=WORK_END_HOUR, minute=0, second=0, microsecond=0)
    return work_end


def is_during_working_hours(dt: datetime) -> bool:
    """Check if a datetime falls during working hours (8 AM - 5 PM)."""
    if not dt:
        return False
    hour = dt.hour
    return WORK_START_HOUR <= hour < WORK_END_HOUR


def calculate_working_hours_between(start_dt: datetime, end_dt: datetime) -> float:
    """
    Calculate the number of working hours between two datetimes.
    Working hours are 8 AM to 5 PM (9 hours per day).
    
    Args:
        start_dt: Start datetime
        end_dt: End datetime
        
    Returns:
        Number of working hours between start and end (float)
    """
    if not start_dt or not end_dt:
        return 0.0
    
    # Ensure both datetimes are timezone-aware
    if start_dt.tzinfo is None:
        start_dt = timezone.make_aware(start_dt)
    if end_dt.tzinfo is None:
        end_dt = timezone.make_aware(end_dt)
    
    # If end is before start, return 0
    if end_dt <= start_dt:
        return 0.0
    
    total_working_hours = 0.0
    current_date = start_dt.date()
    end_date = end_dt.date()
    
    while current_date <= end_date:
        # Get work start and end times for current date
        day_work_start = timezone.make_aware(
            datetime.combine(current_date, time(WORK_START_HOUR, 0, 0))
        )
        day_work_end = timezone.make_aware(
            datetime.combine(current_date, time(WORK_END_HOUR, 0, 0))
        )
        
        # Determine the effective start and end times for this day
        if current_date == start_dt.date():
            # First day: use actual start time if after work start, otherwise use work start
            effective_start = max(start_dt, day_work_start)
        else:
            # Subsequent days: use work start time
            effective_start = day_work_start
        
        if current_date == end_dt.date():
            # Last day: use actual end time if before work end, otherwise use work end
            effective_end = min(end_dt, day_work_end)
        else:
            # Previous days: use work end time
            effective_end = day_work_end
        
        # Only count time if it's within working hours
        if effective_start < effective_end:
            hours = (effective_end - effective_start).total_seconds() / 3600.0
            total_working_hours += hours
        
        # Move to next day
        current_date += timedelta(days=1)
    
    return total_working_hours


def calculate_estimated_duration(started_at: datetime, completed_at: datetime) -> int | None:
    """
    Calculate estimated duration in minutes from started_at to completed_at.
    Uses working hours calculation (8 AM - 5 PM).
    
    Args:
        started_at: Order start datetime
        completed_at: Order completion datetime
        
    Returns:
        Estimated duration in minutes (int), or None if dates are invalid
    """
    if not started_at or not completed_at:
        return None
    
    working_hours = calculate_working_hours_between(started_at, completed_at)
    if working_hours <= 0:
        return None
    
    # Convert hours to minutes
    minutes = int(working_hours * 60)
    return minutes


def is_order_overdue(started_at: datetime, now: datetime = None) -> bool:
    """
    Check if an in-progress order has exceeded the 9-hour working hour threshold.
    
    Args:
        started_at: Order start datetime
        now: Current datetime (defaults to timezone.now())
        
    Returns:
        True if order has been in progress for 9+ working hours, False otherwise
    """
    if not started_at:
        return False
    
    if now is None:
        now = timezone.now()
    
    # Calculate working hours elapsed
    working_hours_elapsed = calculate_working_hours_between(started_at, now)
    
    return working_hours_elapsed >= OVERDUE_THRESHOLD_HOURS


def get_order_overdue_status(order) -> dict:
    """
    Get the overdue status of an order.
    
    Args:
        order: Order instance
        
    Returns:
        Dictionary with:
        - is_overdue (bool): Whether the order is overdue
        - working_hours_elapsed (float): Working hours since start
        - overdue_hours (float): How many hours over the threshold (0 if not overdue)
    """
    result = {
        'is_overdue': False,
        'working_hours_elapsed': 0.0,
        'overdue_hours': 0.0,
    }
    
    if not order.started_at:
        return result
    
    now = timezone.now()
    working_hours = calculate_working_hours_between(order.started_at, now)
    result['working_hours_elapsed'] = round(working_hours, 2)
    
    if working_hours >= OVERDUE_THRESHOLD_HOURS:
        result['is_overdue'] = True
        result['overdue_hours'] = round(working_hours - OVERDUE_THRESHOLD_HOURS, 2)
    
    return result


def format_working_hours(hours: float) -> str:
    """
    Format working hours as a human-readable string.
    
    Args:
        hours: Number of working hours (float)
        
    Returns:
        Formatted string like "9h 30m" or "2h 15m"
    """
    if hours < 0:
        return "0h"
    
    total_minutes = int(hours * 60)
    hours_part = total_minutes // 60
    minutes_part = total_minutes % 60
    
    if hours_part == 0 and minutes_part == 0:
        return "0h"
    elif hours_part == 0:
        return f"{minutes_part}m"
    elif minutes_part == 0:
        return f"{hours_part}h"
    else:
        return f"{hours_part}h {minutes_part}m"


def estimate_completion_time(started_at: datetime, estimated_minutes: int = None) -> dict:
    """
    Estimate the completion time based on start time and estimated duration.
    
    Args:
        started_at: Order start datetime
        estimated_minutes: Estimated duration in minutes (defaults to 9 hours)
        
    Returns:
        Dictionary with:
        - estimated_end (datetime): Estimated completion datetime
        - estimated_hours (float): Estimated duration in hours
        - formatted (str): Human-readable format
    """
    if not started_at:
        return None
    
    if estimated_minutes is None:
        estimated_minutes = OVERDUE_THRESHOLD_HOURS * 60
    
    estimated_hours = estimated_minutes / 60.0
    
    # Simple approximation: add estimated hours to start time
    # In reality, we'd need to account for working hours cutoff
    estimated_end = started_at + timedelta(hours=estimated_hours)
    
    return {
        'estimated_end': estimated_end,
        'estimated_hours': estimated_hours,
        'formatted': format_working_hours(estimated_hours),
    }
