from datetime import datetime, timedelta

from db import query_all
from planner import build_timeline, plan_trip

categories = {c["name"]: c["category_id"] for c in query_all("SELECT category_id, name FROM categories")}

start = (7.8742, 80.6511)
tomorrow = datetime.now() + timedelta(days=1)
depart = tomorrow.replace(hour=6, minute=0, second=0, microsecond=0)
end = tomorrow.replace(hour=18, minute=0, second=0, microsecond=0)

plan = plan_trip(
    start_point=start,
    depart=depart,
    end=end,
    interest_ids=[categories["Religious"], categories["Cultural"], categories["Nature"]],
    vehicle="van",
    lunch=True,
    breakfast=True,
    dining_id=categories["Dining"],
    end_point=start,
)
day = build_timeline(start, depart, "van", [{"place": s["place"], "meal": s["meal"]} for s in plan["stops"]], start)


def hours(place):
    if place["open_time"] is None:
        text = "open all day"
    else:
        text = f"open {str(place['open_time'])[:-3]} - {str(place['close_time'])[:-3]}"
    return text + (f", closed {place['closed_days']}" if place["closed_days"] else "")


print(f"{depart:%A %d %B}")
print(f"{depart:%I:%M %p}  Leave Dambulla")
for i, stop in enumerate(day["stops"], 1):
    print(f"   | drive {stop['km']} km, {stop['drive_min']} min")
    meal = f" ({stop['meal']})" if stop["meal"] else ""
    print(f"{stop['arrive']:%I:%M %p}  {i}. {stop['place']['name']}{meal}")
    print(f"           visit {stop['start']:%I:%M %p} - {stop['leave']:%I:%M %p}  [{hours(stop['place'])}]")
    print(f"           {'PROBLEM: ' + stop['problem'] if stop['problem'] else 'hours OK'}")
print(f"   | back to start {day['back']['km']} km, {day['back']['drive_min']} min")
print(f"{day['finish']:%I:%M %p}  Day ends (planned end {end:%I:%M %p})")
