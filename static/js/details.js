// go back to the previous page if it was on this site
const backLink = document.getElementById("backLink");
backLink.addEventListener("click", event => {
    if (document.referrer.startsWith(window.location.origin) && history.length > 1) {
        event.preventDefault();
        history.back();
    }
});

// map with a pin on the place
const mapBox = document.getElementById("map");
if (mapBox && window.L) {
    const position = [parseFloat(mapBox.dataset.lat), parseFloat(mapBox.dataset.lng)];
    const map = L.map(mapBox, { scrollWheelZoom: false }).setView(position, 14);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: "&copy; OpenStreetMap contributors"
    }).addTo(map);

    const pin = L.divIcon({ className: "map-pin", iconSize: [26, 26], iconAnchor: [13, 26] });
    L.marker(position, { icon: pin }).addTo(map).bindTooltip(mapBox.dataset.name);
}

// places added to the trip are kept in the browser until the planner is built
const tripBtn = document.querySelector(".trip-btn");
const trip = new Set(JSON.parse(localStorage.getItem("tripPlaces") || "[]"));

if (trip.has(tripBtn.dataset.place)) tripBtn.classList.add("saved");

tripBtn.addEventListener("click", () => {
    const id = tripBtn.dataset.place;
    if (trip.has(id)) {
        trip.delete(id);
    } else {
        trip.add(id);
    }
    tripBtn.classList.toggle("saved");
    localStorage.setItem("tripPlaces", JSON.stringify([...trip]));
});
