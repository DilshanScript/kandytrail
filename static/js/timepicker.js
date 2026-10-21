// time picker popup for every .time-button, the value goes into the hidden input named in data-for
const TimePicker = (() => {
    const buttons = document.querySelectorAll(".time-button[data-for]");

    function niceTime(value) {
        const [hour, minute] = value.split(":").map(Number);
        return `${hour % 12 || 12}:${String(minute).padStart(2, "0")} ${hour < 12 ? "AM" : "PM"}`;
    }

    function refresh() {
        buttons.forEach(button => {
            const input = document.getElementById(button.dataset.for);
            button.querySelector(".time-text").textContent = input.value ? niceTime(input.value) : "Pick a time";
            button.classList.toggle("empty", !input.value);
        });
    }

    function set(input, value) {
        input.value = value;
        input.dispatchEvent(new Event("input", { bubbles: true }));
        input.dispatchEvent(new Event("change", { bubbles: true }));
        refresh();
    }

    const menu = document.createElement("div");
    menu.className = "time-menu";
    menu.hidden = true;
    menu.innerHTML = `
        <div class="period-switch">
            <button type="button" data-period="am">AM</button>
            <button type="button" data-period="pm">PM</button>
        </div>
        <div class="time-columns">
            <div><small>Hour</small><div class="time-grid" data-part="hour"></div></div>
            <div><small>Minutes</small><div class="time-grid" data-part="minute"></div></div>
        </div>
        <button type="button" class="btn btn-primary time-done">Done</button>`;
    for (let h = 1; h <= 12; h++) {
        menu.querySelector("[data-part='hour']").insertAdjacentHTML("beforeend",
            `<button type="button" data-value="${h}">${h}</button>`);
    }
    for (let m = 0; m < 60; m += 5) {
        menu.querySelector("[data-part='minute']").insertAdjacentHTML("beforeend",
            `<button type="button" data-value="${m}">${String(m).padStart(2, "0")}</button>`);
    }
    let activeInput = null;

    function currentValue() {
        return (activeInput.value || activeInput.dataset.default || "08:00").split(":").map(Number);
    }

    function showChoice() {
        const [hour, minute] = currentValue();
        menu.querySelectorAll("[data-part='hour'] button").forEach(b => b.classList.toggle("active", +b.dataset.value === (hour % 12 || 12)));
        menu.querySelectorAll("[data-part='minute'] button").forEach(b => b.classList.toggle("active", +b.dataset.value === minute));
        menu.querySelectorAll("[data-period]").forEach(b => b.classList.toggle("active", b.dataset.period === (hour < 12 ? "am" : "pm")));
    }

    function close() {
        menu.hidden = true;
        buttons.forEach(b => b.classList.remove("open"));
        activeInput = null;
    }

    buttons.forEach(button => {
        button.addEventListener("click", () => {
            const input = document.getElementById(button.dataset.for);
            if (activeInput === input) return close();
            close();
            activeInput = input;
            button.parentElement.appendChild(menu);
            button.classList.add("open");
            menu.hidden = false;
            showChoice();

            // keep the popup inside the screen, phones show it as a bottom sheet
            menu.style.left = "";
            if (window.matchMedia("(min-width: 900px)").matches) {
                const overflow = menu.getBoundingClientRect().right - (window.innerWidth - 16);
                if (overflow > 0) menu.style.left = `${-overflow}px`;
            }
        });
    });

    menu.addEventListener("click", event => {
        const choice = event.target.closest("button");
        if (!choice || !activeInput) return;
        if (choice.classList.contains("time-done")) return close();

        let [hour, minute] = currentValue();
        const pm = hour >= 12;
        const part = choice.closest("[data-part]")?.dataset.part;
        if (part === "hour") hour = (+choice.dataset.value % 12) + (pm ? 12 : 0);
        if (part === "minute") minute = +choice.dataset.value;
        if (choice.dataset.period) hour = (hour % 12) + (choice.dataset.period === "pm" ? 12 : 0);

        set(activeInput, `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`);
        showChoice();
    });

    document.addEventListener("click", event => {
        if (activeInput && !event.target.closest(".time-pick")) close();
    });
    document.addEventListener("keydown", event => {
        if (event.key === "Escape" && activeInput) close();
    });

    refresh();
    return { set, close, refresh, niceTime };
})();
