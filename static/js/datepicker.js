// "More dates" chip opens a month calendar for days after the first week
function setupDatePicker(pick, onPick) {
    const moreDays = pick.querySelector(".day-chip.more");
    const moreInput = moreDays.querySelector("input");
    const lastDay = new Date(moreDays.dataset.max + "T00:00");
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const shownMonth = new Date(today.getFullYear(), today.getMonth(), 1);
    const empty = moreDays.querySelector("span").innerHTML;

    const calendar = document.createElement("div");
    calendar.className = "time-menu date-menu";
    calendar.hidden = true;
    pick.appendChild(calendar);

    const isoDate = d => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

    function draw() {
        const year = shownMonth.getFullYear();
        const month = shownMonth.getMonth();
        const title = shownMonth.toLocaleDateString("en-GB", { month: "long", year: "numeric" });
        let cells = "";
        const blanks = (new Date(year, month, 1).getDay() + 6) % 7;  // weeks start on Monday
        for (let i = 0; i < blanks; i++) cells += "<span></span>";
        for (let d = 1; d <= new Date(year, month + 1, 0).getDate(); d++) {
            const day = new Date(year, month, d);
            const off = day < today || day > lastDay;
            const picked = pick.querySelector("[name='day']:checked")?.value === isoDate(day);
            cells += `<button type="button" data-date="${isoDate(day)}" ${off ? "disabled" : ""} class="${picked ? "active" : ""}">${d}</button>`;
        }
        calendar.innerHTML = `
            <div class="date-head">
                <button type="button" data-move="-1" ${shownMonth <= today ? "disabled" : ""} aria-label="Previous month">&lsaquo;</button>
                <strong>${title}</strong>
                <button type="button" data-move="1" ${new Date(year, month + 1, 1) > lastDay ? "disabled" : ""} aria-label="Next month">&rsaquo;</button>
            </div>
            <div class="date-grid">
                <small>Mo</small><small>Tu</small><small>We</small><small>Th</small><small>Fr</small><small>Sa</small><small>Su</small>
                ${cells}
            </div>
            <button type="button" class="btn btn-primary time-done">Done</button>`;
    }

    moreDays.addEventListener("click", event => {
        event.preventDefault();
        if (window.TimePicker) TimePicker.close();
        calendar.hidden = !calendar.hidden;
        if (!calendar.hidden) draw();
    });

    calendar.addEventListener("click", event => {
        event.stopPropagation();  // the calendar redraws, so the outside-click check below can't see the button
        const button = event.target.closest("button");
        if (!button) return;
        if (button.dataset.move) {
            shownMonth.setMonth(shownMonth.getMonth() + +button.dataset.move);
            return draw();
        }
        if (button.classList.contains("time-done")) return calendar.hidden = true;

        // a date in the first week ticks its own chip, later dates go on the "More dates" chip
        const chip = pick.querySelector(`.day-chip:not(.more) input[value='${button.dataset.date}']`);
        const day = new Date(button.dataset.date + "T00:00");
        if (chip) {
            chip.checked = true;
            moreDays.querySelector("span").innerHTML = empty;
        } else {
            moreInput.value = button.dataset.date;
            moreInput.checked = true;
            moreDays.querySelector("span").innerHTML = `<small>${day.toLocaleDateString("en-GB", { weekday: "short" })}</small>
                <strong>${day.getDate()}</strong><small>${day.toLocaleDateString("en-GB", { month: "short" })}</small>`;
        }
        if (onPick) onPick();
        draw();
    });

    // picking a first-week chip clears a date shown on "More dates"
    pick.querySelectorAll(".day-chip:not(.more) input").forEach(input => {
        input.addEventListener("change", () => moreDays.querySelector("span").innerHTML = empty);
    });

    document.addEventListener("click", event => {
        if (!calendar.hidden && !pick.contains(event.target)) calendar.hidden = true;
    });
}
