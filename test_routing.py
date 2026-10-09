from datetime import datetime, timedelta

from routing import route_line, travel_from

dambulla = (7.8742, 80.6511)
places = {
    "Temple of the Tooth": (7.2936, 80.6413),
    "Bahirawakanda": (7.2965, 80.6290),
    "Kandy Lake": (7.2925, 80.6415),
}

# tomorrow 6 AM
leave = (datetime.now() + timedelta(days=1)).replace(hour=6, minute=0, second=0, microsecond=0)
results = travel_from(dambulla, list(places.values()), leave, "van")

print(f"From Dambulla, leaving {leave:%I:%M %p} by van:")
for name, r in zip(places, results):
    print(f"  {name}: {r['km']} km, {r['min']} min")

path = route_line([dambulla, places["Temple of the Tooth"], places["Bahirawakanda"]], leave, "van")
print(f"Route has {len(path['line'])} map points, legs: {path['legs']}")
