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
            card.hidden = selected !== null && !card.dataset.categories.split(" ").includes(selected);
        });

        // open the places page with the same category
        document.querySelectorAll(".explore-link").forEach(link => {
            link.href = selected ? `/places?category=${selected}` : "/places";
        });

        noPlaces.hidden = visibleCards().length > 0;
        row.scrollLeft = 0;
        updateCount();
    });
});

// filter panel
const filterBtn = document.getElementById("filterBtn");
const filterPanel = document.getElementById("filterPanel");
const panelForm = filterPanel.querySelector("form");
const panelTypes = document.getElementById("panelTypes");
const panelSubmit = document.getElementById("panelSubmit");
const allCards = document.querySelectorAll(".place-card");

function openPanel(open) {
    filterPanel.hidden = !open;
    filterBtn.setAttribute("aria-expanded", open);
}

// show the types of the picked category and count matching places
function updatePanel() {
    const category = panelForm.category.value;
    const typeInput = panelForm.querySelector("input[name='sub_type']:checked");

    panelTypes.querySelectorAll(".option").forEach(option => {
        option.hidden = option.dataset.category !== category;
        if (option.hidden) option.querySelector("input").checked = false;
    });
    panelTypes.hidden = !category || !panelTypes.querySelector(".option:not([hidden])");

    const type = typeInput && !typeInput.closest(".option").hidden ? typeInput.value : "";
    const count = [...allCards].filter(card =>
        (!category || card.dataset.categories.split(" ").includes(category)) &&
        (!type || card.dataset.subTypes.split(" ").includes(type))
    ).length;
    panelSubmit.textContent = `Show ${count} place${count === 1 ? "" : "s"}`;
}

filterBtn.addEventListener("click", () => openPanel(filterPanel.hidden));
filterPanel.querySelectorAll("[data-close]").forEach(el => el.addEventListener("click", () => openPanel(false)));
document.addEventListener("keydown", event => {
    if (event.key === "Escape") openPanel(false);
});

panelForm.addEventListener("change", updatePanel);
panelForm.addEventListener("reset", () => setTimeout(updatePanel));
updatePanel();
