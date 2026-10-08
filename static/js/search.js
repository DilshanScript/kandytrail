// place suggestions while typing in a search box
document.querySelectorAll(".search-box input[name='q']").forEach(input => {
    const box = input.closest(".search-row");
    const list = document.createElement("ul");
    list.className = "suggest-list";
    list.hidden = true;
    box.appendChild(list);

    let timer;
    let current = -1;

    function close() {
        list.hidden = true;
        current = -1;
    }

    function choose(name) {
        window.location = `/places?q=${encodeURIComponent(name)}`;
    }

    function highlight(index) {
        const items = list.querySelectorAll("li");
        items.forEach(li => li.classList.remove("active"));
        current = index;
        if (items[current]) items[current].classList.add("active");
    }

    async function load() {
        const text = input.value.trim();
        if (text.length < 2) return close();

        const response = await fetch(`/api/suggest?q=${encodeURIComponent(text)}`);
        const places = await response.json();
        if (input.value.trim() !== text) return;

        list.innerHTML = "";
        places.forEach(place => {
            const li = document.createElement("li");
            const name = document.createElement("strong");
            const type = document.createElement("span");
            name.textContent = place.name;
            type.textContent = place.type;
            li.append(name, type);
            li.addEventListener("mousedown", () => choose(place.name));
            list.appendChild(li);
        });
        current = -1;
        list.hidden = places.length === 0;
    }

    input.addEventListener("input", () => {
        clearTimeout(timer);
        timer = setTimeout(load, 200);
    });

    input.addEventListener("keydown", event => {
        const items = list.querySelectorAll("li");
        if (list.hidden || !items.length) return;

        if (event.key === "ArrowDown") {
            event.preventDefault();
            highlight((current + 1) % items.length);
        } else if (event.key === "ArrowUp") {
            event.preventDefault();
            highlight(current <= 0 ? items.length - 1 : current - 1);
        } else if (event.key === "Enter" && current >= 0) {
            event.preventDefault();
            choose(items[current].querySelector("strong").textContent);
        } else if (event.key === "Escape") {
            close();
        }
    });

    input.addEventListener("blur", close);
});
