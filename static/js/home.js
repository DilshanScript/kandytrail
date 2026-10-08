const row = document.getElementById("placeRow");
const prevBtn = document.getElementById("prevBtn");
const nextBtn = document.getElementById("nextBtn");
const slideCount = document.getElementById("slideCount");
const noPlaces = document.getElementById("noPlaces");
const categoryButtons = document.querySelectorAll(".category");

function visibleCards() {
    return [...row.querySelectorAll(".place-card")].filter(card => !card.hidden);
}

function cardStep() {
    const card = visibleCards()[0];
    if (!card) return 0;
    const gap = parseFloat(getComputedStyle(row).columnGap) || 0;
    return card.offsetWidth + gap;
}

function updateCount() {
    const total = visibleCards().length;
    const step = cardStep();
    const current = step ? Math.round(row.scrollLeft / step) + 1 : 0;
    slideCount.textContent = total ? `${Math.min(current, total)} / ${total}` : "0 / 0";
    prevBtn.disabled = row.scrollLeft <= 0;
    nextBtn.disabled = row.scrollLeft + row.clientWidth >= row.scrollWidth - 1;
}

if (row) {
    prevBtn.addEventListener("click", () => row.scrollBy({ left: -cardStep(), behavior: "smooth" }));
    nextBtn.addEventListener("click", () => row.scrollBy({ left: cardStep(), behavior: "smooth" }));
    row.addEventListener("scroll", updateCount);

    // keep the same card in view when the window size changes
    let resizeTimer;
    window.addEventListener("resize", () => {
        const step = cardStep();
        const index = step ? Math.round(row.scrollLeft / step) : 0;
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(() => {
            row.scrollTo({ left: index * cardStep() });
            updateCount();
        }, 150);
    });

    updateCount();
}

// show only places from the selected category, click again to show all
categoryButtons.forEach(button => {
    button.addEventListener("click", () => {
        const isActive = button.classList.contains("active");
        categoryButtons.forEach(b => b.classList.remove("active"));
        if (!isActive) button.classList.add("active");

        const selected = isActive ? null : button.dataset.category;
        row.querySelectorAll(".place-card").forEach(card => {
            card.hidden = selected !== null && card.dataset.category !== selected;
        });

        noPlaces.hidden = visibleCards().length > 0;
        row.scrollLeft = 0;
        updateCount();
    });
});

// saved places are kept in the browser until user accounts are added
const saved = new Set(JSON.parse(localStorage.getItem("savedPlaces") || "[]"));

document.querySelectorAll(".save-btn").forEach(button => {
    if (saved.has(button.dataset.place)) button.classList.add("saved");

    button.addEventListener("click", () => {
        const id = button.dataset.place;
        if (saved.has(id)) {
            saved.delete(id);
        } else {
            saved.add(id);
        }
        button.classList.toggle("saved");
        localStorage.setItem("savedPlaces", JSON.stringify([...saved]));
    });
});
