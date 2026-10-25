document.querySelectorAll("[data-print]").forEach(button => {
    button.addEventListener("click", () => window.print());
});

document.querySelectorAll("[data-share]").forEach(button => {
    const label = button.querySelector("span");
    button.addEventListener("click", async () => {
        const link = { title: button.dataset.title, text: button.dataset.text, url: button.dataset.share };
        if (navigator.share) {
            try {
                await navigator.share(link);
            } catch (error) {}
            return;
        }
        try {
            await navigator.clipboard.writeText(link.url);
            label.textContent = "Link copied";
        } catch (error) {
            window.prompt("Copy this link", link.url);
        }
        setTimeout(() => label.textContent = "Share", 2000);
    });
});
