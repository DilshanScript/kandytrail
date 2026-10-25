const backLink = document.getElementById("backLink");
backLink.addEventListener("click", event => {
    if (document.referrer.startsWith(window.location.origin) && history.length > 1) {
        event.preventDefault();
        history.back();
    }
});

const mapBox = document.getElementById("map");

function pinIcon() {
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="36" height="44" viewBox="0 0 36 44">
        <path d="M18 42s16-14 16-25A16 16 0 0 0 2 17c0 11 16 25 16 25z" fill="#009AFF" stroke="#fff" stroke-width="3"/>
        <circle cx="18" cy="17" r="6" fill="#fff"/></svg>`;
    return {
        url: "data:image/svg+xml;charset=UTF-8," + encodeURIComponent(svg),
        scaledSize: new google.maps.Size(36, 44),
        anchor: new google.maps.Point(18, 42)
    };
}

function initPlaceMap() {
    if (!mapBox) return;
    const position = { lat: parseFloat(mapBox.dataset.lat), lng: parseFloat(mapBox.dataset.lng) };
    const map = new google.maps.Map(mapBox, {
        center: position,
        zoom: 15,
        disableDefaultUI: true,
        zoomControl: true,
        fullscreenControl: true,
        clickableIcons: false,
        gestureHandling: "cooperative"
    });
    new google.maps.Marker({ map, position, icon: pinIcon(), title: mapBox.dataset.name });
}

function placeMapFailed() {
    if (mapBox) mapBox.innerHTML = "<p class='map-fallback'>Map unavailable</p>";
}
window.gm_authFailure = placeMapFailed;

const tripBtn = document.querySelector(".trip-btn");
const trip = new Set(JSON.parse(localStorage.getItem("tripPlaces") || "[]"));

if (trip.has(tripBtn.dataset.place)) tripBtn.classList.add("saved");

tripBtn.addEventListener("click", () => {
    const id = tripBtn.dataset.place;
    if (trip.has(id)) {
        trip.delete(id);
    } else {
        trip.add(id);
    }
    tripBtn.classList.toggle("saved");
    localStorage.setItem("tripPlaces", JSON.stringify([...trip]));
});

const viewer = document.getElementById("viewer");
if (viewer) {
    const photos = JSON.parse(document.getElementById("photoList").textContent);
    const image = document.getElementById("viewerImage");
    const count = document.getElementById("viewerCount");
    let current = 0;
    let touchX = null;

    const show = index => {
        current = (index + photos.length) % photos.length;
        image.src = photos[current];
        count.textContent = `${current + 1} / ${photos.length}`;
    };

    const open = index => {
        show(index);
        viewer.hidden = false;
        document.body.style.overflow = "hidden";
    };

    const close = () => {
        viewer.hidden = true;
        document.body.style.overflow = "";
    };

    document.querySelectorAll(".collage-photo").forEach(button => {
        button.addEventListener("click", () => open(parseInt(button.dataset.index)));
    });

    document.getElementById("viewerClose").addEventListener("click", close);
    document.getElementById("viewerPrev").addEventListener("click", () => show(current - 1));
    document.getElementById("viewerNext").addEventListener("click", () => show(current + 1));
    document.getElementById("viewerPrev").hidden = photos.length < 2;
    document.getElementById("viewerNext").hidden = photos.length < 2;

    viewer.addEventListener("click", event => {
        if (event.target === viewer) close();
    });

    document.addEventListener("keydown", event => {
        if (viewer.hidden) return;
        if (event.key === "Escape") close();
        if (event.key === "ArrowLeft") show(current - 1);
        if (event.key === "ArrowRight") show(current + 1);
    });

    viewer.addEventListener("touchstart", event => touchX = event.touches[0].clientX, { passive: true });
    viewer.addEventListener("touchend", event => {
        if (touchX === null) return;
        const moved = event.changedTouches[0].clientX - touchX;
        if (Math.abs(moved) > 50) show(current + (moved < 0 ? 1 : -1));
        touchX = null;
    });
}
