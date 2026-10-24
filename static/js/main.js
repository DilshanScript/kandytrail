const header = document.querySelector(".site-header");

// add a shadow to the top bar once the page is scrolled
function updateHeader() {
    header.classList.toggle("scrolled", window.scrollY > 8);
}

window.addEventListener("scroll", updateHeader);
updateHeader();

// hide "welcome" messages after a few seconds
document.querySelectorAll(".flash:not(.error)").forEach(message => {
    setTimeout(() => message.classList.add("hide"), 4000);
    message.addEventListener("transitionend", () => message.remove());
});

// save or unsave a place in the traveller's account
const csrfToken = document.querySelector("meta[name='csrf-token']").content;

document.querySelectorAll(".save-btn, .save-toggle").forEach(button => {
    button.addEventListener("click", async () => {
        const form = new FormData();
        form.append("csrf_token", csrfToken);
        form.append("next", location.pathname + location.search);
        const response = await fetch(`/places/${button.dataset.place}/save`, { method: "POST", body: form });
        const result = await response.json();
        if (response.status === 401) {
            location.href = result.login;  // sign in first
            return;
        }
        button.classList.toggle("saved", result.saved);
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
