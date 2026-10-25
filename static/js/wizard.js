const wizard = document.getElementById("wizard");
const allSteps = [...wizard.querySelectorAll(".wizard-step")];
let steps = allSteps;
const nextBtn = document.getElementById("wizardNext");
const backBtn = document.getElementById("wizardBack");
let current = 0;
const ICONS = JSON.parse(wizard.dataset.icons);

const startLat = document.getElementById("startLat");
const startLng = document.getElementById("startLng");
const startLabel = document.getElementById("startLabel");

const isManual = () => wizard.querySelector("[name='mode']:checked")?.value === "manual";
function updateSteps() {
    steps = allSteps.filter(step => !(isManual() && "autoOnly" in step.dataset));
}
wizard.querySelectorAll("[name='mode']").forEach(input => input.addEventListener("change", () => {
    const step = steps[current];
    updateSteps();
    let index = steps.indexOf(step);
    if (index === -1) {
        const before = allSteps.slice(0, allSteps.indexOf(step)).filter(s => steps.includes(s));
        index = Math.max(0, before.length - 1);
        step.hidden = true;
    }
    current = index;
    showStep(index);
}));
updateSteps();

const isDone = {
    start: () => startLat.value && startLng.value,
    when: () => wizard.querySelector("[name='day']:checked")?.value && document.getElementById("startTime").value,
    end: () => endMinutes() - startMinutes() >= 120,
    finish: () => wizard.querySelector("[name='finish']:checked"),
    interests: () => wizard.querySelector("[name='interests']:checked"),
    vehicle: () => wizard.querySelector("[name='vehicle']:checked"),
    meals: () => true,
    review: () => true
};

function minutes(value) {
    const [h, m] = value.split(":").map(Number);
    return h * 60 + m;
}
const startMinutes = () => minutes(document.getElementById("startTime").value);
const endMinutes = () => minutes(document.getElementById("endTime").value);

function showStep(index, back = false) {
    TimePicker.close();
    steps[current].hidden = true;
    current = index;
    const step = steps[current];
    step.hidden = false;
    step.classList.remove("slide-in", "slide-back");
    void step.offsetWidth;
    step.classList.add(back ? "slide-back" : "slide-in");

    updateProgress();
    backBtn.style.visibility = current === 0 ? "hidden" : "visible";

    const last = current === steps.length - 1;
    nextBtn.textContent = !last ? "Continue" : isManual() ? "Pick my places" : "Plan my trip";
    nextBtn.classList.toggle("plan-btn", last);
    if (step.dataset.step === "review") fillReview();
    if (step.dataset.step === "meals") updateBreakfast();
    updateNext();
    window.scrollTo({ top: 0, behavior: "smooth" });
}

function updateProgress() {
    document.getElementById("wizardBar").style.width = `${(current + 1) / steps.length * 100}%`;
    document.getElementById("wizardCount").textContent = `${current + 1} / ${steps.length}`;
}

function updateNext() {
    nextBtn.disabled = !isDone[steps[current].dataset.step]();
}

nextBtn.addEventListener("click", () => {
    if (current < steps.length - 1) {
        showStep(current + 1);
    } else {
        if (isManual()) {
            document.querySelector(".planning-box strong").textContent = "Loading places...";
        }
        document.getElementById("planningOverlay").hidden = false;
        wizard.submit();
    }
});
backBtn.addEventListener("click", () => {
    if (current > 0) showStep(current - 1, true);
});
wizard.addEventListener("change", updateNext);
wizard.addEventListener("input", updateNext);

let startMap = null;
let startPin = null;
let geocoder = null;
let placesLib = null;
let searchToken = null;
const mapBox = document.getElementById("startMap");
const KANDY = { lat: 7.2906, lng: 80.6337 };

function setStart(lat, lng, label, zoom = true) {
    startLat.value = lat.toFixed(6);
    startLng.value = lng.toFixed(6);
    startLabel.value = label;
    const picked = document.getElementById("pickedStart");
    picked.hidden = false;
    picked.textContent = `Starting from: ${label}`;

    if (startMap) {
        if (!startPin) startPin = new google.maps.Marker({ map: startMap });
        startPin.setPosition({ lat, lng });
        if (zoom) {
            startMap.setCenter({ lat, lng });
            startMap.setZoom(12);
        }
    }
    updateNext();
}

function shortName(result) {
    return result.formatted_address.split(",").slice(0, 2).join(",").trim();
}

async function initStartMap() {
    startMap = new google.maps.Map(mapBox, {
        center: KANDY,
        zoom: 9,
        disableDefaultUI: true,
        zoomControl: true,
        clickableIcons: false,
        styles: [{ featureType: "poi", stylers: [{ visibility: "off" }] }]
    });
    geocoder = new google.maps.Geocoder();
    startMap.addListener("click", event => {
        const lat = event.latLng.lat();
        const lng = event.latLng.lng();
        setStart(lat, lng, "Pinned on the map", false);
        geocoder.geocode({ location: { lat, lng } }).then(({ results }) => {
            if (results[0] && startLat.value === lat.toFixed(6)) setStart(lat, lng, shortName(results[0]), false);
        }).catch(() => {});
    });
    if (startLat.value) setStart(+startLat.value, +startLng.value, startLabel.value);
    placesLib = await google.maps.importLibrary("places");
    searchToken = new placesLib.AutocompleteSessionToken();
}

function mapFailed() {
    mapBox.innerHTML = "<p class='map-fallback'>Map unavailable</p>";
}
window.gm_authFailure = mapFailed;

document.getElementById("locateBtn").addEventListener("click", () => {
    const note = document.getElementById("locateNote");
    if (!navigator.geolocation) {
        note.textContent = "Location not available";
        return;
    }
    note.textContent = "Locating...";
    navigator.geolocation.getCurrentPosition(
        pos => {
            note.textContent = "Location found";
            setStart(pos.coords.latitude, pos.coords.longitude, "My current location");
        },
        () => note.textContent = "Location blocked"
    );
});

const searchInput = document.getElementById("startSearch");
const results = document.getElementById("startResults");
let searchTimer = null;

function addResult(main, extra, pick) {
    const item = document.createElement("li");
    item.innerHTML = "<strong></strong><small></small>";
    item.querySelector("strong").textContent = main;
    item.querySelector("small").textContent = extra || "";
    item.addEventListener("click", async () => {
        results.hidden = true;
        searchInput.value = main;
        try {
            await pick();
        } catch {
            document.getElementById("pickedStart").hidden = false;
            document.getElementById("pickedStart").textContent = "Place not found";
        }
    });
    results.appendChild(item);
}

async function googleSuggestions(q) {
    const { suggestions } = await placesLib.AutocompleteSuggestion.fetchAutocompleteSuggestions({
        input: q,
        includedRegionCodes: ["lk"],
        locationBias: { center: KANDY, radius: 50000 },
        sessionToken: searchToken
    });
    suggestions.forEach(({ placePrediction: place }) => {
        const main = place.mainText.text;
        addResult(main, place.secondaryText?.text, async () => {
            const spot = await findPoint(place, place.text.text);
            setStart(spot.lat(), spot.lng(), main);
            searchToken = new placesLib.AutocompleteSessionToken();
        });
    });
}

async function findPoint(prediction, fullText) {
    const tries = [
        async () => (await prediction.toPlace().fetchFields({ fields: ["location"] })).place.location,
        async () => (await placesLib.Place.searchByText({
            textQuery: fullText, fields: ["location"], maxResultCount: 1
        })).places[0].location,
        async () => (await geocoder.geocode({ address: fullText })).results[0].geometry.location
    ];
    for (const attempt of tries) {
        try {
            const spot = await attempt();
            if (spot) return spot;
        } catch (error) {
            console.warn("Google lookup failed, trying the next one", error);
        }
    }
    throw new Error("No point found");
}

async function geocoderResults(q) {
    const found = (await geocoder.geocode({ address: q, componentRestrictions: { country: "LK" } })).results;
    found.slice(0, 5).forEach(place => {
        const [main, ...rest] = place.formatted_address.split(",");
        addResult(main.trim(), rest.join(",").trim(),
            async () => setStart(place.geometry.location.lat(), place.geometry.location.lng(), main.trim()));
    });
}

searchInput.addEventListener("input", () => {
    clearTimeout(searchTimer);
    const q = searchInput.value.trim();
    if (q.length < 2) {
        results.hidden = true;
        return;
    }
    searchTimer = setTimeout(async () => {
        results.innerHTML = "";
        try {
            await googleSuggestions(q);
        } catch (error) {
            console.warn("Google suggestions failed, trying the geocoder", error);
            try {
                await geocoderResults(q);
            } catch (error2) {
                console.warn("Google geocoder failed", error2);
            }
        }
        if (searchInput.value.trim() !== q) return;
        if (!results.children.length) results.innerHTML = "<li class='empty'>No places found</li>";
        results.hidden = false;
    }, 300);
});
document.addEventListener("click", event => {
    if (!event.target.closest(".place-search")) results.hidden = true;
});

setupDatePicker(wizard.querySelector(".day-pick"), updateNext);

const endNote = document.getElementById("endNote");
function updateEnd() {
    const hours = (endMinutes() - startMinutes()) / 60;
    endNote.textContent = hours >= 2
        ? `${Math.floor(hours)} hr${hours % 1 ? " " + Math.round(hours % 1 * 60) + " min" : ""} trip`
        : "Minimum 2 hours";
    endNote.classList.toggle("warn", hours < 2);
}

const presetRows = wizard.querySelectorAll(".time-presets-row");
function markPresets() {
    presetRows.forEach(row => row.querySelectorAll("button").forEach(b =>
        b.classList.toggle("active", b.dataset.time === document.getElementById(row.dataset.for).value)));
}
presetRows.forEach(row => row.querySelectorAll("button").forEach(button => {
    button.addEventListener("click", () => TimePicker.set(document.getElementById(row.dataset.for), button.dataset.time));
}));
document.getElementById("startTime").addEventListener("change", markPresets);
document.getElementById("endTime").addEventListener("change", markPresets);
markPresets();
document.getElementById("endTime").addEventListener("change", updateEnd);
document.getElementById("startTime").addEventListener("change", updateEnd);
updateEnd();

function updateSubPicks() {
    let any = false;
    wizard.querySelectorAll(".sub-group").forEach(group => {
        const on = wizard.querySelector(`[name='interests'][value='${group.dataset.category}']`).checked;
        group.hidden = !on;
        if (!on) group.querySelectorAll("input").forEach(box => box.checked = false);
        any = any || on;
    });
    document.getElementById("subPicks").hidden = !any;
}
wizard.querySelectorAll("[name='interests']").forEach(box => box.addEventListener("change", updateSubPicks));

function updateBreakfast() {
    const early = startMinutes() < 10 * 60 + 30;
    const box = wizard.querySelector("[name='breakfast']");
    box.disabled = !early;
    if (!early) box.checked = false;
    document.getElementById("breakfastCard").classList.toggle("off", !early);
}

function fillReview() {
    const checkedText = name => [...wizard.querySelectorAll(`[name='${name}']:checked`)]
        .map(input => input.closest("label").querySelector("strong").textContent.trim()).join(", ");
    const day = new Date(wizard.querySelector("[name='day']:checked").value + "T00:00")
        .toLocaleDateString("en-GB", { weekday: "short", day: "numeric", month: "short" });
    const icon = name => ICONS[name];
    const meals = checkedText("breakfast") ? [checkedText("breakfast")] : [];
    if (checkedText("lunch")) meals.push(checkedText("lunch"));
    let rows = [
        ["start", icon("location"), "Start", startLabel.value],
        ["when", icon("calendar"), "Leaving", `${day}, ${TimePicker.niceTime(document.getElementById("startTime").value)}`],
        ["end", icon("finish"), "Finish by", TimePicker.niceTime(document.getElementById("endTime").value)],
        ["finish", icon("map"), "Day ends", checkedText("finish")],
        ["interests", icon("heart"), "Interests", checkedText("interests") +
            (wizard.querySelector("[name='sub_types']:checked") ? ` (${[...wizard.querySelectorAll("[name='sub_types']:checked")].map(b => b.nextElementSibling.textContent).join(", ")})` : "")],
        ["vehicle", icon(wizard.querySelector("[name='vehicle']:checked").value), "Travel by", checkedText("vehicle")],
        ["meals", icon(meals.length ? "lunch" : "skip"), "Meal stops", meals.join(" and ") || "No meal stops"]
    ];
    rows = rows.filter(([step]) => steps.some(s => s.dataset.step === step));
    const list = document.getElementById("reviewList");
    list.innerHTML = "";
    rows.forEach(([step, icon, title, value]) => {
        const item = document.createElement("li");
        item.innerHTML = `<span class="review-icon"><img src="${icon}" alt=""></span><span><small>${title}</small><strong></strong></span><em>Change</em>`;
        item.querySelector("strong").textContent = value;
        item.addEventListener("click", () => showStep(steps.findIndex(s => s.dataset.step === step), true));
        list.appendChild(item);
    });
}

window.addEventListener("pageshow", () => document.getElementById("planningOverlay").hidden = true);

showStep(0);
