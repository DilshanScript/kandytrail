"""Fill open_time / close_time from the old opening_hours text.
Run: python database/fix_hours.py          (shows what will change)
     python database/fix_hours.py --save   (saves it)"""
import re
import sys

sys.path.insert(0, ".")
from db import execute, query_all  # noqa: E402

TIME = r"(\d{1,2})(?:[:.](\d{2}))?\s*(am|pm)"
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def to_24h(hour, minute, half):
    hour = int(hour) % 12 + (12 if half.lower() == "pm" else 0)
    return f"{hour:02d}:{int(minute or 0):02d}"


places = query_all("SELECT place_id, name, opening_hours FROM places WHERE open_time IS NULL")
changes = []
for place in places:
    text = place["opening_hours"] or ""
    match = re.search(TIME + r"\s*(?:-|to)\s*" + TIME, text, re.IGNORECASE)
    if re.search(r"all day|24 ?hours", text, re.IGNORECASE):
        print(f"ok    {place['name']}: open all day")
        continue
    if not match:
        print(f"skip  {place['name']}: '{text}' (no times found, set it in admin)")
        continue
    opens, closes = to_24h(*match.groups()[:3]), to_24h(*match.groups()[3:])
    closed = [d for d in DAYS if re.search(r"closed[^.]*\b" + d, text, re.IGNORECASE)]
    changes.append((opens, closes, ",".join(closed) or None, place["place_id"]))
    print(f"fix   {place['name']}: '{text}' -> {opens} - {closes}" + (f", closed {closed}" if closed else ""))

if "--save" in sys.argv and changes:
    for change in changes:
        execute("UPDATE places SET open_time = %s, close_time = %s, closed_days = %s WHERE place_id = %s", change)
    print(f"saved {len(changes)} places")
elif changes:
    print("run again with --save to save these")
