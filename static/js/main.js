const header = document.querySelector(".site-header");

// add a shadow to the top bar once the page is scrolled
function updateHeader() {
    header.classList.toggle("scrolled", window.scrollY > 8);
}

window.addEventListener("scroll", updateHeader);
updateHeader();
