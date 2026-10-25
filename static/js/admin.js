window.addEventListener("pageshow", event => {
    if (event.persisted) window.location.reload();
});

document.querySelectorAll(".delete-form").forEach(form => {
    form.addEventListener("submit", async event => {
        event.preventDefault();
        const ok = await confirmBox({
            title: form.dataset.title || "Delete this place?",
            text: form.dataset.text || `"${form.dataset.name}" and its reviews will be removed. This can't be undone.`,
            yes: "Delete",
            danger: true
        });
        if (ok) form.submit();
    });
});

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

const categoryPicks = document.getElementById("categoryPicks");
if (categoryPicks) {
    const mainInput = document.getElementById("mainCategory");
    const categoryChecks = [...categoryPicks.querySelectorAll("input")];
    const typeOptions = document.querySelectorAll("#typePicks .option");
    const typeHint = document.getElementById("typeHint");

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
    document.querySelectorAll(".quick-picks[data-target]").forEach(box => {
        const input = document.querySelector(`[name="${box.dataset.target}"]`);
        const values = box.dataset.mode === "list" ? listValues(input).map(v => v.toLowerCase()) : [input.value];
        box.querySelectorAll("button").forEach(button => {
            button.classList.toggle("active", values.includes(button.dataset.value.toLowerCase()) || values.includes(button.dataset.value));
        });
    });
}

document.addEventListener("click", event => {
    const button = event.target.closest(".quick-picks[data-target] button");
    if (!button) return;
    const box = button.closest(".quick-picks[data-target]");
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

document.querySelectorAll("[name='keywords'], [name='entry_fee']")
    .forEach(input => input.addEventListener("input", markPicks));
updateKeywordPicks();
markPicks();

document.querySelectorAll(".counter").forEach(counter => {
    const field = document.querySelector(`[name="${counter.dataset.for}"]`);
    const update = () => counter.textContent = `${field.value.length} / ${field.maxLength}`;
    field.addEventListener("input", update);
    update();
});

const openAllDay = document.getElementById("openAllDay");
if (openAllDay) {
    const openTime = document.getElementById("openTime");
    const closeTime = document.getElementById("closeTime");
    const preview = document.getElementById("hoursPreview");
    const dayChecks = document.querySelectorAll("[name='closed_days']");

    function shortTime(value) {
        return TimePicker.niceTime(value).replace(" ", "").toLowerCase();
    }

    function updateHours() {
        document.querySelectorAll(".time-button").forEach(button => button.disabled = openAllDay.checked);

        const closed = [...dayChecks].filter(c => c.checked).map(c => c.value);
        let text = "Open all day";
        if (!openAllDay.checked) {
            text = openTime.value && closeTime.value
                ? `${shortTime(openTime.value)} - ${shortTime(closeTime.value)}`
                : "--";
            if (!closed.length && text !== "--") text = `Daily ${text}`;
        }
        if (closed.length) text += `, closed on ${closed.join(", ")}`;
        preview.textContent = text;

        document.querySelectorAll(".time-presets button").forEach(button => {
            button.classList.toggle("active", !openAllDay.checked
                && button.dataset.open === openTime.value && button.dataset.close === closeTime.value);
        });
    }

    document.querySelectorAll(".time-presets button").forEach(button => {
        button.addEventListener("click", () => {
            openAllDay.checked = false;
            TimePicker.set(openTime, button.dataset.open);
            TimePicker.set(closeTime, button.dataset.close);
        });
    });
    openAllDay.addEventListener("change", () => {
        TimePicker.close();
        updateHours();
    });
    [openTime, closeTime, ...dayChecks].forEach(input => input.addEventListener("change", updateHours));
    updateHours();
}

const visitOptions = document.getElementById("visitOptions");
if (visitOptions) {
    const addOption = document.getElementById("addOption");
    const MAX_OPTIONS = 6;

    function updateOptions() {
        const rows = visitOptions.querySelectorAll(".visit-option");
        rows.forEach((row, i) => {
            row.querySelector("[name='default_option']").value = i;
            row.querySelector(".remove-option").hidden = rows.length === 1;
        });
        if (!visitOptions.querySelector("[name='default_option']:checked")) {
            rows[0].querySelector("[name='default_option']").checked = true;
        }
        addOption.hidden = rows.length >= MAX_OPTIONS;
    }

    addOption.addEventListener("click", () => {
        const row = visitOptions.querySelector(".visit-option").cloneNode(true);
        row.querySelectorAll("input[type='text'], input[type='number']").forEach(input => input.value = "");
        row.querySelector("[name='default_option']").checked = false;
        visitOptions.appendChild(row);
        updateOptions();
        row.querySelector("input[type='text']").focus();
        visitOptions.dispatchEvent(new Event("change", { bubbles: true }));
    });

    visitOptions.addEventListener("click", event => {
        const button = event.target.closest(".remove-option");
        if (!button) return;
        button.closest(".visit-option").remove();
        updateOptions();
        visitOptions.dispatchEvent(new Event("change", { bubbles: true }));
    });

    updateOptions();
}

const pickMap = document.getElementById("pickMap");
const KANDY = { lat: 7.2906, lng: 80.6337 };

function kmBetween(a, b) {
    const rad = Math.PI / 180;
    const dLat = (b.lat - a.lat) * rad;
    const dLng = (b.lng - a.lng) * rad;
    const h = Math.sin(dLat / 2) ** 2 + Math.cos(a.lat * rad) * Math.cos(b.lat * rad) * Math.sin(dLng / 2) ** 2;
    return 12742 * Math.asin(Math.sqrt(h));
}

function initPickMap() {
    if (!pickMap) return;
    const latInput = document.getElementById("latInput");
    const lngInput = document.getElementById("lngInput");
    const distanceOut = document.getElementById("distanceOut");

    const map = new google.maps.Map(pickMap, {
        center: KANDY,
        zoom: 10,
        disableDefaultUI: true,
        zoomControl: true,
        fullscreenControl: true,
        clickableIcons: false
    });
    new google.maps.Circle({
        map,
        center: KANDY,
        radius: 25000,
        strokeColor: "#009AFF",
        strokeWeight: 1.5,
        fillColor: "#009AFF",
        fillOpacity: 0.05,
        clickable: false
    });

    let marker = null;

    function setPin(lat, lng, moveMap) {
        const point = { lat, lng };
        if (!marker) {
            marker = new google.maps.Marker({ map, position: point, draggable: true });
            marker.addListener("dragend", () => {
                const p = marker.getPosition();
                setPin(p.lat(), p.lng(), false);
                latInput.dispatchEvent(new Event("input", { bubbles: true }));
            });
        }
        marker.setPosition(point);
        latInput.value = lat.toFixed(6);
        lngInput.value = lng.toFixed(6);

        const km = kmBetween(KANDY, point);
        distanceOut.textContent = `${km.toFixed(1)} km`;
        distanceOut.classList.toggle("too-far", km > 25);
        if (moveMap) {
            map.setCenter(point);
            map.setZoom(14);
        }
    }

    map.addListener("click", event => {
        setPin(event.latLng.lat(), event.latLng.lng(), false);
        latInput.dispatchEvent(new Event("input", { bubbles: true }));
    });

    [latInput, lngInput].forEach(input => input.addEventListener("change", () => {
        const lat = parseFloat(latInput.value);
        const lng = parseFloat(lngInput.value);
        if (!isNaN(lat) && !isNaN(lng)) setPin(lat, lng, true);
    }));

    if (latInput.value && lngInput.value) {
        setPin(parseFloat(latInput.value), parseFloat(lngInput.value), true);
    }
}

function pickMapFailed() {
    if (pickMap) pickMap.innerHTML = "<p class='map-fallback'>Map unavailable</p>";
}
window.gm_authFailure = pickMapFailed;

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

const photoCount = document.getElementById("photoCount");
const galleryInput = document.getElementById("galleryInput");
if (photoCount && galleryInput) {
    const galleryGrid = document.getElementById("galleryGrid");
    const addTile = galleryInput.closest(".gallery-add");

    const countPhotos = () => {
        const main = photoInput.files.length || parseInt(photoCount.dataset.main) ? 1 : 0;
        const kept = galleryGrid.querySelectorAll(".gallery-item:not(.new) input:not(:checked)").length;
        const total = main + kept + galleryInput.files.length;
        photoCount.textContent = total;
        photoCount.classList.toggle("low", total < 5);
    };

    galleryInput.addEventListener("change", () => {
        galleryGrid.querySelectorAll(".gallery-item.new").forEach(item => item.remove());
        [...galleryInput.files].forEach(file => {
            const item = document.createElement("div");
            item.className = "gallery-item new";
            const img = document.createElement("img");
            img.src = URL.createObjectURL(file);
            item.appendChild(img);
            galleryGrid.insertBefore(item, addTile);
        });
        countPhotos();
    });

    photoInput.addEventListener("change", countPhotos);
    galleryGrid.addEventListener("change", event => {
        if (event.target.name === "remove_photo") countPhotos();
    });
    countPhotos();
}

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

    window.addEventListener("beforeunload", event => {
        if (changed) {
            event.preventDefault();
            event.returnValue = "";
        }
    });
}
