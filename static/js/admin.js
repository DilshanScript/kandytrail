// confirm popup, returns true when the user clicks the main button
const modal = document.getElementById("confirmModal");

function confirmBox({ title, text, yes = "OK", no = "Cancel", danger = false }) {
    document.getElementById("modalTitle").textContent = title;
    document.getElementById("modalText").textContent = text;
    const yesBtn = document.getElementById("modalYes");
    yesBtn.textContent = yes;
    yesBtn.className = danger ? "btn btn-danger-solid" : "btn btn-primary";
    document.getElementById("modalNo").textContent = no;
    modal.classList.toggle("danger", danger);
    modal.hidden = false;
    yesBtn.focus();

    return new Promise(resolve => {
        function answer(event) {
            const choice = event.target.closest("[data-answer]");
            if (!choice && event.key !== "Escape") return;
            modal.hidden = true;
            modal.removeEventListener("click", answer);
            document.removeEventListener("keydown", onKey);
            resolve(choice ? choice.dataset.answer === "yes" : false);
        }
        function onKey(event) {
            if (event.key === "Escape") answer(event);
        }
        modal.addEventListener("click", answer);
        document.addEventListener("keydown", onKey);
    });
}

// ask before deleting
document.querySelectorAll(".delete-form").forEach(form => {
    form.addEventListener("submit", async event => {
        event.preventDefault();
        const ok = await confirmBox({
            title: "Delete this place?",
            text: `"${form.dataset.name}" and its reviews will be removed. This can't be undone.`,
            yes: "Delete",
            danger: true
        });
        if (ok) form.submit();
    });
});

// dashboard search and category filter
const placeSearch = document.getElementById("placeSearch");
if (placeSearch) {
    const filterBtn = document.getElementById("adminFilterBtn");
    const filterMenu = document.getElementById("adminFilterMenu");
    const filterCount = document.getElementById("filterCount");
    const checks = document.querySelectorAll(".filter-check");

    function filterRows() {
        const text = placeSearch.value.trim().toLowerCase();
        const picked = [...checks].filter(c => c.checked).map(c => c.value);
        let shown = 0;

        document.querySelectorAll(".admin-row").forEach(row => {
            const cats = row.dataset.categories.split(" ");
            const matchText = row.dataset.search.includes(text);
            const matchCat = !picked.length || picked.some(id => cats.includes(id));
            row.hidden = !(matchText && matchCat);
            if (!row.hidden) shown++;
        });

        filterCount.hidden = !picked.length;
        filterCount.textContent = picked.length;
        const noMatch = document.getElementById("noMatch");
        if (noMatch) noMatch.hidden = shown > 0;
    }

    placeSearch.addEventListener("input", filterRows);
    checks.forEach(c => c.addEventListener("change", filterRows));
    document.getElementById("clearFilter").addEventListener("click", () => {
        checks.forEach(c => c.checked = false);
        filterRows();
    });

    filterBtn.addEventListener("click", () => {
        filterMenu.hidden = !filterMenu.hidden;
        filterBtn.setAttribute("aria-expanded", !filterMenu.hidden);
    });
    document.addEventListener("click", event => {
        if (!event.target.closest(".admin-search-wrap")) filterMenu.hidden = true;
    });
}

// category and type chips on the place form
const categoryPicks = document.getElementById("categoryPicks");
if (categoryPicks) {
    const mainInput = document.getElementById("mainCategory");
    const categoryChecks = [...categoryPicks.querySelectorAll("input")];
    const typeOptions = document.querySelectorAll("#typePicks .option");
    const typeHint = document.getElementById("typeHint");

    // the first ticked category stays the main one
    let order = categoryChecks.filter(c => c.checked).map(c => c.value);
    if (mainInput.value && order.includes(mainInput.value)) {
        order = [mainInput.value, ...order.filter(id => id !== mainInput.value)];
    }

    function updateCategories() {
        mainInput.value = order[0] || "";
        categoryChecks.forEach(c => c.closest(".option").classList.toggle("is-main", c.value === order[0]));

        let visible = 0;
        typeOptions.forEach(option => {
            option.hidden = !order.includes(option.dataset.category);
            if (option.hidden) option.querySelector("input").checked = false;
            else visible++;
        });
        typeHint.hidden = visible > 0;
    }

    categoryChecks.forEach(check => check.addEventListener("change", () => {
        order = order.filter(id => id !== check.value);
        if (check.checked) order.push(check.value);
        updateCategories();
        updateKeywordPicks();
    }));
    updateCategories();
}

// quick picks: click to fill a field
const keywordIdeas = {
    1: ["temple", "buddhist", "worship", "dress code", "history"],
    2: ["nature", "hiking", "views", "photos", "waterfall", "bathing", "picnic"],
    3: ["history", "museum", "ancient", "architecture", "kings"],
    4: ["culture", "dance", "show", "traditional", "evening"],
    5: ["lunch", "sri lankan food", "rice and curry", "cheap", "tea", "vegetarian"]
};

function listValues(input) {
    return input.value.split(",").map(v => v.trim()).filter(Boolean);
}

function updateKeywordPicks() {
    const box = document.getElementById("keywordPicks");
    if (!box) return;
    const picked = [...document.querySelectorAll("#categoryPicks input:checked")].map(c => c.value);
    const words = new Set();
    picked.forEach(id => (keywordIdeas[id] || []).forEach(w => words.add(w)));
    box.dataset.saved.split(",").filter(Boolean).forEach(w => words.add(w));

    box.innerHTML = "";
    [...words].slice(0, 18).forEach(word => {
        const button = document.createElement("button");
        button.type = "button";
        button.dataset.value = word;
        button.textContent = word;
        box.appendChild(button);
    });
    markPicks();
}

function markPicks() {
    document.querySelectorAll(".quick-picks").forEach(box => {
        const input = document.querySelector(`[name="${box.dataset.target}"]`);
        const values = box.dataset.mode === "list" ? listValues(input).map(v => v.toLowerCase()) : [input.value];
        box.querySelectorAll("button").forEach(button => {
            button.classList.toggle("active", values.includes(button.dataset.value.toLowerCase()) || values.includes(button.dataset.value));
        });
    });
}

document.addEventListener("click", event => {
    const button = event.target.closest(".quick-picks button");
    if (!button) return;
    const box = button.closest(".quick-picks");
    const input = document.querySelector(`[name="${box.dataset.target}"]`);

    if (box.dataset.mode === "list") {
        let values = listValues(input);
        const word = button.dataset.value;
        const exists = values.some(v => v.toLowerCase() === word.toLowerCase());
        values = exists ? values.filter(v => v.toLowerCase() !== word.toLowerCase()) : [...values, word];
        input.value = values.join(", ");
    } else {
        input.value = button.dataset.value;
    }
    input.dispatchEvent(new Event("input", { bubbles: true }));
    markPicks();
});

document.querySelectorAll("[name='keywords'], [name='opening_hours'], [name='visit_duration_min'], [name='entry_fee']")
    .forEach(input => input.addEventListener("input", markPicks));
updateKeywordPicks();
markPicks();

// character counter for the short description
document.querySelectorAll(".counter").forEach(counter => {
    const field = document.querySelector(`[name="${counter.dataset.for}"]`);
    const update = () => counter.textContent = `${field.value.length} / ${field.maxLength}`;
    field.addEventListener("input", update);
    update();
});

// map to pick the location
const pickMap = document.getElementById("pickMap");
if (pickMap && window.L) {
    const kandy = [7.2906, 80.6337];
    const latInput = document.getElementById("latInput");
    const lngInput = document.getElementById("lngInput");
    const distanceOut = document.getElementById("distanceOut");

    const map = L.map(pickMap).setView(kandy, 11);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: "&copy; OpenStreetMap contributors"
    }).addTo(map);
    L.circle(kandy, { radius: 25000, color: "#009AFF", weight: 1.5, fillOpacity: 0.05 }).addTo(map);

    const pin = L.divIcon({ className: "map-pin", iconSize: [26, 26], iconAnchor: [13, 26] });
    let marker = null;

    function setPin(lat, lng, moveMap) {
        if (!marker) {
            marker = L.marker([lat, lng], { icon: pin, draggable: true }).addTo(map);
            marker.on("dragend", () => {
                const p = marker.getLatLng();
                setPin(p.lat, p.lng, false);
                latInput.dispatchEvent(new Event("input", { bubbles: true }));
            });
        }
        marker.setLatLng([lat, lng]);
        latInput.value = lat.toFixed(6);
        lngInput.value = lng.toFixed(6);

        const km = map.distance(kandy, [lat, lng]) / 1000;
        distanceOut.textContent = `${km.toFixed(1)} km`;
        distanceOut.classList.toggle("too-far", km > 25);
        if (moveMap) map.setView([lat, lng], 14);
    }

    map.on("click", event => {
        setPin(event.latlng.lat, event.latlng.lng, false);
        latInput.dispatchEvent(new Event("input", { bubbles: true }));
    });

    // typing the numbers also moves the pin
    [latInput, lngInput].forEach(input => input.addEventListener("change", () => {
        const lat = parseFloat(latInput.value);
        const lng = parseFloat(lngInput.value);
        if (!isNaN(lat) && !isNaN(lng)) setPin(lat, lng, true);
    }));

    if (latInput.value && lngInput.value) {
        setPin(parseFloat(latInput.value), parseFloat(lngInput.value), true);
    }
}

// preview the chosen photo
const photoInput = document.getElementById("photoInput");
if (photoInput) {
    photoInput.addEventListener("change", () => {
        const file = photoInput.files[0];
        if (!file) return;
        const img = document.createElement("img");
        img.src = URL.createObjectURL(file);
        const preview = document.getElementById("photoPreview");
        preview.innerHTML = "";
        preview.appendChild(img);
        photoInput.closest(".photo-drop").querySelector("strong").textContent = file.name;
    });
}

// warn before leaving the form with unsaved changes
const placeForm = document.getElementById("placeForm");
if (placeForm) {
    let changed = false;
    placeForm.addEventListener("input", () => changed = true);
    placeForm.addEventListener("change", () => changed = true);
    placeForm.addEventListener("submit", () => changed = false);

    document.querySelectorAll("a[href]").forEach(link => {
        link.addEventListener("click", async event => {
            if (!changed || link.target === "_blank") return;
            event.preventDefault();
            const leave = await confirmBox({
                title: "Discard changes?",
                text: "You have changes that are not saved. If you leave now they will be lost.",
                yes: "Discard",
                no: "Keep editing",
                danger: true
            });
            if (leave) {
                changed = false;
                window.location = link.href;
            }
        });
    });

    // browser back button, reload or closing the tab
    window.addEventListener("beforeunload", event => {
        if (changed) {
            event.preventDefault();
            event.returnValue = "";
        }
    });
}
