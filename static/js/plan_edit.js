const planBody = document.getElementById("planBody");
const planBar = document.getElementById("planBar");

// switch edit mode on and off without reloading or losing your place on the page
function setEditing(on) {
    planBody.classList.toggle("editing", on);
    planBar.classList.toggle("editing", on);
    document.querySelectorAll(".plan-heading .edit-only").forEach(el => el.hidden = !on);
    const url = new URL(location.href);
    on ? url.searchParams.set("edit", "1") : url.searchParams.delete("edit");
    history.replaceState(null, "", url.pathname + url.search + url.hash);
}
document.getElementById("editOn").addEventListener("click", event => {
    event.preventDefault();
    setEditing(true);
});
document.getElementById("editOff").addEventListener("click", event => {
    event.preventDefault();
    setEditing(false);
});
setEditing(planBody.classList.contains("editing"));

// "+ Add a stop" opens the list, sorted by distance to that gap
const sheet = document.getElementById("addSheet");
const gaps = JSON.parse(sheet.dataset.gaps);
const addSearch = document.getElementById("addSearch");
const stopNames = [...document.querySelectorAll(".plan-stop .plan-card strong")].map(el => el.textContent);

function km(a, b) {
    // straight line distance, close enough for sorting
    const rad = Math.PI / 180;
    const x = (b[1] - a[1]) * rad * Math.cos((a[0] + b[0]) / 2 * rad);
    const y = (b[0] - a[0]) * rad;
    return Math.sqrt(x * x + y * y) * 6371;
}

function openSheet(position) {
    const before = gaps[position];
    const after = gaps[position + 1];
    const items = [...sheet.querySelectorAll("li[data-name]")];
    items.forEach(item => {
        const point = [+item.dataset.lat, +item.dataset.lng];
        const away = Math.min(km(before, point), after ? km(point, after) : Infinity);
        item.dataset.away = away;
        item.querySelector(".add-km").textContent = `${away.toFixed(1)} km away`;
        item.querySelector(".add-position").value = position;
    });
    items.sort((a, b) => a.dataset.away - b.dataset.away).forEach(item => item.parentElement.appendChild(item));

    const from = position === 0 ? "your start" : stopNames[position - 1];
    document.getElementById("addWhere").textContent = position < stopNames.length
        ? `Between ${from} and ${stopNames[position]}` : `After ${from}`;
    addSearch.value = "";
    items.forEach(item => item.hidden = false);
    sheet.hidden = false;
    document.body.classList.add("sheet-open");
}

function closeSheet() {
    sheet.hidden = true;
    document.body.classList.remove("sheet-open");
}

document.querySelectorAll(".add-here").forEach(button => {
    button.addEventListener("click", () => openSheet(+button.dataset.position));
});
document.getElementById("addClose").addEventListener("click", closeSheet);
sheet.addEventListener("click", event => {
    if (event.target === sheet) closeSheet();
});
document.addEventListener("keydown", event => {
    if (event.key === "Escape" && !sheet.hidden) closeSheet();
});

addSearch.addEventListener("input", () => {
    const q = addSearch.value.trim().toLowerCase();
    sheet.querySelectorAll("li[data-name]").forEach(item => {
        item.hidden = q && !item.dataset.name.includes(q);
    });
});

// show the button is working while the plan is worked out again
document.querySelectorAll(".plan-page form").forEach(form => {
    form.addEventListener("submit", event => {
        const button = event.submitter || form.querySelector("button");
        if (button) button.classList.add("busy");
        document.body.classList.add("plan-busy");
    });
});
