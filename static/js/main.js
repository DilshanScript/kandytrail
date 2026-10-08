const header = document.querySelector(".site-header");

// add a shadow to the top bar once the page is scrolled
function updateHeader() {
    header.classList.toggle("scrolled", window.scrollY > 8);
}

window.addEventListener("scroll", updateHeader);
updateHeader();

// saved places are kept in the browser until user accounts are added
const saved = new Set(JSON.parse(localStorage.getItem("savedPlaces") || "[]"));

document.querySelectorAll(".save-btn, .save-toggle").forEach(button => {
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

// dropdown menus
document.querySelectorAll(".dropdown").forEach(dropdown => {
    const button = dropdown.querySelector(".dropdown-btn");

    button.addEventListener("click", () => {
        const open = dropdown.classList.toggle("open");
        button.setAttribute("aria-expanded", open);
    });

    document.addEventListener("click", event => {
        if (!dropdown.contains(event.target)) {
            dropdown.classList.remove("open");
            button.setAttribute("aria-expanded", false);
        }
    });

    document.addEventListener("keydown", event => {
        if (event.key === "Escape") dropdown.classList.remove("open");
    });
});
