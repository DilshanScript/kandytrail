const modal = document.getElementById("confirmModal");

function confirmBox({ title, text = "", yes = "OK", no = "Cancel", danger = false }) {
    document.getElementById("modalTitle").textContent = title;
    document.getElementById("modalText").textContent = text;
    const yesBtn = document.getElementById("modalYes");
    yesBtn.textContent = yes;
    yesBtn.className = danger ? "btn btn-danger-solid" : "btn btn-primary";
    document.getElementById("modalNo").textContent = no;
    modal.classList.toggle("danger", danger);
    modal.hidden = false;
    yesBtn.focus();

    return new Promise(resolve => {
        function close(result) {
            modal.hidden = true;
            modal.removeEventListener("click", answer);
            document.removeEventListener("keydown", onKey);
            resolve(result);
        }
        function answer(event) {
            const choice = event.target.closest("[data-answer]");
            if (choice) close(choice.dataset.answer === "yes");
        }
        function onKey(event) {
            if (event.key === "Escape") close(false);
        }
        modal.addEventListener("click", answer);
        document.addEventListener("keydown", onKey);
    });
}

document.addEventListener("click", async event => {
    const trigger = event.target.closest("[data-confirm]");
    if (!trigger) return;
    event.preventDefault();

    const ok = await confirmBox({
        title: trigger.dataset.confirm,
        text: trigger.dataset.confirmText,
        yes: trigger.dataset.confirmYes,
        danger: "danger" in trigger.dataset
    });
    if (!ok) return;

    if (trigger.tagName === "A") {
        window.location.href = trigger.href;
    } else {
        trigger.form.requestSubmit(trigger);
    }
});
