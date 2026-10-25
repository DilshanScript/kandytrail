const planBox = document.getElementById("planMap");
const plan = JSON.parse(planBox.dataset.plan);
let planMap = null;
const markers = [];

function pinIcon(label, color) {
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="36" height="44" viewBox="0 0 36 44">
        <path d="M18 42s16-14 16-25A16 16 0 0 0 2 17c0 11 16 25 16 25z" fill="${color}" stroke="#fff" stroke-width="3"/>
        <text x="18" y="22" text-anchor="middle" font-family="Arial" font-size="14" font-weight="700" fill="#fff">${label}</text></svg>`;
    return {
        url: "data:image/svg+xml;charset=UTF-8," + encodeURIComponent(svg),
        scaledSize: new google.maps.Size(36, 44),
        anchor: new google.maps.Point(18, 42)
    };
}

function initPlanMap() {
    planMap = new google.maps.Map(planBox, {
        disableDefaultUI: true,
        zoomControl: true,
        fullscreenControl: true,
        clickableIcons: false,
        styles: [
            { featureType: "poi", stylers: [{ visibility: "off" }] },
            { featureType: "transit", stylers: [{ visibility: "off" }] }
        ]
    });
    const info = new google.maps.InfoWindow({ headerDisabled: true });
    const bounds = new google.maps.LatLngBounds();

    plan.pins.forEach((pin, i) => {
        const color = ["S", "E"].includes(pin.label) ? "#222B38" : plan.legs[i - 1].color;
        const marker = new google.maps.Marker({
            map: planMap,
            position: { lat: pin.lat, lng: pin.lng },
            icon: pinIcon(pin.label, color),
            title: pin.name,
            zIndex: 10 + i
        });
        marker.addListener("click", () => {
            const box = document.createElement("div");
            box.className = "map-info";
            box.innerHTML = `<button type="button" class="map-info-close" aria-label="Close">
                <svg viewBox="0 0 24 24"><path d="M6 6l12 12M18 6 6 18"/></svg></button>
                <span class="map-info-text"><strong></strong><small></small></span>`;
            if (pin.image) {
                const img = document.createElement("img");
                img.src = pin.image;
                img.alt = "";
                box.prepend(img);
            }
            box.querySelector("strong").textContent = `${pin.label === "S" ? "Start:" : pin.label + "."} ${pin.name}`;
            box.querySelector("small").textContent = pin.time || "";
            box.querySelector(".map-info-close").addEventListener("click", () => info.close());
            info.setContent(box);
            info.open(planMap, marker);
        });
        markers.push(marker);
        bounds.extend(marker.getPosition());
    });

    plan.legs.forEach((leg, i) => {
        const path = leg.line
            ? leg.line.map(([lat, lng]) => ({ lat, lng }))
            : [plan.pins[i], plan.pins[i + 1]].map(p => ({ lat: p.lat, lng: p.lng }));
        new google.maps.Polyline({
            map: planMap,
            path,
            strokeColor: leg.color,
            strokeOpacity: leg.line ? 0.9 : 0,
            strokeWeight: 5,
            icons: leg.line ? [] : [{ icon: { path: "M 0,-1 0,1", strokeOpacity: 1, scale: 3 }, offset: "0", repeat: "14px" }]
        });
        path.forEach(point => bounds.extend(point));
    });
    planMap.fitBounds(bounds, 40);
}

function planMapFailed() {
    planBox.innerHTML = "<p class='map-fallback'>Map unavailable</p>";
}
window.gm_authFailure = planMapFailed;

document.querySelectorAll(".plan-stop").forEach(item => {
    item.addEventListener("click", event => {
        if (!planMap || event.target.closest("a, form")) return;
        const marker = markers[+item.dataset.pin];
        planMap.panTo(marker.getPosition());
        planMap.setZoom(15);
        google.maps.event.trigger(marker, "click");
        planBox.scrollIntoView({ behavior: "smooth", block: "center" });
    });
});
