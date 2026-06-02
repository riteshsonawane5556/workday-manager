from datetime import datetime

from models.calendar_models import CalendarEvent, ConflictPair


def build_calendar_prompt(
    events: list[CalendarEvent],
    conflicts: list[ConflictPair],
    date_str: str,
) -> str:
    lines = [f"Date: {date_str}", f"Total events: {len(events)}", "", "Events:"]
    for e in events:
        start = datetime.fromtimestamp(e.start_time).strftime("%I:%M %p")
        end = datetime.fromtimestamp(e.end_time).strftime("%I:%M %p")
        pax = ", ".join(e.participants) if e.participants else "none"
        lines.append(f"  - [{e.id}] {e.title} | {start} – {end} | participants: {pax}")

    lines += ["", f"Conflicts detected: {len(conflicts)}"]
    for c in conflicts:
        lines.append(f"  - '{c.event_a.title}' overlaps with '{c.event_b.title}'")

    return "\n".join(lines)
