from datetime import datetime, timedelta

from db import query_all
from planner import plan_trip

categories = {c["name"]: c["category_id"] for c in query_all("SELECT category_id, name FROM categories")}

# Dambulla, tomorrow 6 AM to 6 PM, by van, with lunch
tomorrow = datetime.now() + timedelta(days=1)
depart = tomorrow.replace(hour=6, minute=0, second=0, microsecond=0)
end = tomorrow.replace(hour=18, minute=0, second=0, microsecond=0)

plan = plan_trip(
    start_point=(7.8742, 80.6511),
    depart=depart,
    end=end,
    interest_ids=[categories["Religious"], categories["Cultural"], categories["Nature"]],
    vehicle="van",
    lunch=True,
    dining_id=categories["Dining"],
)

print(f"{plan['depart']:%I:%M %p}  Leave Dambulla")
for i, stop in enumerate(plan["stops"], 1):
    print(f"   | drive {stop['km']} km, {stop['drive_min']} min")
    lunch = " (lunch)" if stop["is_lunch"] else ""
    wait = f", wait until {stop['start']:%I:%M %p}" if stop["start"] > stop["arrive"] else ""
    print(f"{stop['arrive']:%I:%M %p}  {i}. {stop['place']['name']}{lunch}{wait}")
    print(f"           stay {stop['place']['stay_min']} min ({stop['place']['stay_label']}), leave {stop['leave']:%I:%M %p}")
print(f"{plan['finish']:%I:%M %p}  Trip ends (planned end {plan['end']:%I:%M %p})")
