from datetime import datetime

from models.calendar_models import CalendarEvent, ConflictPair
from tools.calendar_tools import fetch_today_events


def detect_conflicts(events: list[CalendarEvent]) -> list[ConflictPair]:
    sorted_events = sorted(events, key=lambda e: e.start_time)
    conflicts: list[ConflictPair] = []
    for i in range(len(sorted_events)):
        for j in range(i + 1, len(sorted_events)):
            a = sorted_events[i]
            b = sorted_events[j]
            if a.start_time < b.end_time and a.end_time > b.start_time:
                conflicts.append(ConflictPair(event_a=a, event_b=b))
    return conflicts


async def fetch_calendar_data() -> tuple[list[CalendarEvent], list[ConflictPair], str]:
    events = await fetch_today_events()
    conflicts = detect_conflicts(events)
    date_str = datetime.now().strftime("%Y-%m-%d")
    return events, conflicts, date_str
