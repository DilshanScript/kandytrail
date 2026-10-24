// manual planning: map with the nearest places, search, and a sheet to pick the visit time
const places = new Map(BUILD.places.map(place => [place.id, place]));
const mapBox = document.getElementById("buildMap");
const mapData = JSON.parse(mapBox.dataset.map);

// minutes from midnight -> "9:05 AM"
function clockText(minutes) {
    const hour = Math.floor(minutes / 60) % 24;
    const min = String(minutes % 60).padStart(2, "0");
    return `${hour % 12 || 12}:${min} ${hour < 12 ? "AM" : "PM"}`;
}

// 75 -> "1 hr 15 min"
function durationText(minutes) {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    if (!hours) return `${mins} min`;
    return mins ? `${hours} hr ${mins} min` : `${hours} hr`;
}

function driveText(place) {
    return (place.road ? "" : "about ") + durationText(place.drive);
}

// sheet to choose how long to stay
const sheet = document.getElementById("stopSheet");
const sheetOptions = document.getElementById("sheetOptions");
let sheetPlace = null;

function updateSheetTimes() {
    const chosen = sheetOptions.querySelector("input:checked");
    const stay = +chosen.dataset.min;
    const leave = sheetPlace.start + stay;
    document.getElementById("sheetTimes").textContent =
        `Arrive ${clockText(sheetPlace.arrive)}${sheetPlace.start > sheetPlace.arrive ? `, opens ${clockText(sheetPlace.start)}` : ""} · leave ${clockText(leave)}`;
    let warning = sheetPlace.problem || "";
    if (!warning && sheetPlace.closes !== null && leave > sheetPlace.closes) {
        warning = `Closes at ${clockText(sheetPlace.closes)}, before your visit ends`;
    }
    document.getElementById("sheetWarn").textContent = warning;
}

function openSheet(id) {
    sheetPlace = places.get(id);
    if (!sheetPlace) return;
    document.getElementById("sheetName").textContent = sheetPlace.name;
    document.getElementById("sheetType").textContent = sheetPlace.types;
    document.getElementById("sheetHours").textContent = sheetPlace.hours;
    document.getElementById("sheetPlace").value = sheetPlace.id;
    document.getElementById("sheetFacts").innerHTML = `
        <span>${sheetPlace.km} km</span>
        <span><img src="${BUILD.vehicleIcon}" alt="">${driveText(sheetPlace)}</span>`;

    sheetOptions.innerHTML = "";
    sheetPlace.options.forEach(option => {
        const label = document.createElement("label");
        label.className = "visit-option";
        label.innerHTML = `<input type="radio" name="option"><span><strong></strong><small></small></span>`;
        const input = label.querySelector("input");
        input.value = option.id ?? "";
        input.dataset.min = option.min;
        input.checked = option.default;
        label.querySelector("strong").textContent = option.label;
        label.querySelector("small").textContent = durationText(option.min);
        input.addEventListener("change", updateSheetTimes);
        sheetOptions.appendChild(label);
    });
    if (!sheetOptions.querySelector("input:checked")) sheetOptions.querySelector("input").checked = true;
    updateSheetTimes();

    sheet.hidden = false;
    document.body.classList.add("sheet-open");
}

function closeSheet() {
    sheet.hidden = true;
    document.body.classList.remove("sheet-open");
}

document.getElementById("sheetClose").addEventListener("click", closeSheet);
sheet.addEventListener("click", event => {
    if (event.target === sheet) closeSheet();
});
document.addEventListener("keydown", event => {
    if (event.key === "Escape" && !sheet.hidden) closeSheet();
});

document.querySelectorAll(".next-card[data-place]").forEach(card => {
    card.addEventListener("click", () => openSheet(+card.dataset.place));
});

// search every place with category and type filters, nearest first
const searchSheet = document.getElementById("searchSheet");
const search = document.getElementById("placeSearch");
const results = document.getElementById("placeResults");

function showResults() {
    const text = search.value.trim().toLowerCase();
    const category = searchSheet.querySelector("[name='findCategory']:checked").value;
    searchSheet.querySelectorAll(".find-types").forEach(group => group.hidden = group.dataset.category !== category);
    const type = category ? searchSheet.querySelector(`[name='findType${category}']:checked`)?.value || "" : "";

    const found = BUILD.places.filter(place =>
        (!text || place.name.toLowerCase().includes(text) || place.types.toLowerCase().includes(text))
        && (!category || place.categories.includes(+category))
        && (!type || place.subTypes.includes(+type)));

    document.getElementById("findCount").textContent = `${found.length} place${found.length === 1 ? "" : "s"}, nearest first`;
    results.innerHTML = "";
    found.forEach(place => {
        const item = document.createElement("li");
        item.innerHTML = `<span class="find-photo"></span><span class="find-text"><strong></strong><small></small><em></em></span>`;
        if (place.image) item.querySelector(".find-photo").innerHTML = `<img src="${place.image}" alt="">`;
        item.querySelector("strong").textContent = place.name;
        item.querySelector("small").textContent = place.types;
        item.querySelector("em").textContent = `${place.km} km · ${driveText(place)} · arrive ${clockText(place.arrive)}`;
        item.addEventListener("click", () => {
            closeSearch();
            openSheet(place.id);
        });
        results.appendChild(item);
    });
    if (!found.length) results.innerHTML = "<li class='empty'>No places match. Try another name or filter.</li>";
}

function openSearch() {
    searchSheet.hidden = false;
    document.body.classList.add("sheet-open");
    showResults();
    search.focus();
}

function closeSearch() {
    searchSheet.hidden = true;
    document.body.classList.remove("sheet-open");
}

document.getElementById("openSearch").addEventListener("click", openSearch);
document.getElementById("searchClose").addEventListener("click", closeSearch);
searchSheet.addEventListener("click", event => {
    if (event.target === searchSheet) closeSearch();
});
search.addEventListener("input", showResults);
searchSheet.querySelectorAll(".find-chips input").forEach(input => input.addEventListener("change", showResults));
document.addEventListener("keydown", event => {
    if (event.key === "Escape" && !searchSheet.hidden) closeSearch();
});

// map: the trip so far, and lettered pins for the places to pick next
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

// called by the Google Maps script when it has loaded
function initBuildMap() {
    const map = new google.maps.Map(mapBox, {
        disableDefaultUI: true,
        zoomControl: true,
        fullscreenControl: true,
        clickableIcons: false,
        styles: [
            { featureType: "poi", stylers: [{ visibility: "off" }] },
            { featureType: "transit", stylers: [{ visibility: "off" }] }
        ]
    });
    const bounds = new google.maps.LatLngBounds();
    const here = mapData.pins[mapData.pins.length - 1];

    mapData.pins.forEach((pin, i) => {
        new google.maps.Marker({
            map,
            position: pin,
            icon: pinIcon(pin.label, i === 0 ? "#222B38" : "#009AFF"),
            title: pin.name,
            zIndex: 10 + i
        });
        bounds.extend(pin);
    });

    // road lines for the trip so far, straight dashed lines when Google gave none
    mapData.lines.forEach((line, i) => {
        const path = line ? line.map(([lat, lng]) => ({ lat, lng })) : [mapData.pins[i], mapData.pins[i + 1]];
        new google.maps.Polyline({
            map,
            path,
            strokeColor: "#009AFF",
            strokeOpacity: line ? 0.8 : 0,
            strokeWeight: 4,
            icons: line ? [] : [{ icon: { path: "M 0,-1 0,1", strokeOpacity: 1, scale: 3 }, offset: "0", repeat: "14px" }]
        });
    });

    // places to pick next, with a light dashed line from where you are
    mapData.next.forEach(next => {
        const place = places.get(next.id);
        const position = { lat: place.lat, lng: place.lng };
        const marker = new google.maps.Marker({
            map,
            position,
            icon: pinIcon(next.label, "#FF8A00"),
            title: `${place.name}, ${driveText(place)}`,
            zIndex: 50
        });
        marker.addListener("click", () => openSheet(place.id));
        new google.maps.Polyline({
            map,
            path: [here, position],
            strokeOpacity: 0,
            icons: [{ icon: { path: "M 0,-1 0,1", strokeOpacity: 0.5, strokeColor: "#FF8A00", scale: 2 }, offset: "0", repeat: "10px" }]
        });
        bounds.extend(position);
    });
    map.fitBounds(bounds, 50);
}

function buildMapFailed() {
    mapBox.innerHTML = "<p class='map-fallback'>The map couldn't load right now. Pick a place below.</p>";
}
window.gm_authFailure = buildMapFailed;  // Google calls this when the key is wrong
