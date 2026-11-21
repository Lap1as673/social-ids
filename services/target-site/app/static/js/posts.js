// Создание поста с опциональной загрузкой картинки.
(function () {
    const form = document.getElementById("create-post-form");
    if (!form) return;

    const errEl = document.getElementById("post-error");

    function showError(msg) {
        if (!errEl) return;
        errEl.textContent = msg;
        errEl.hidden = false;
    }

    function hideError() {
        if (!errEl) return;
        errEl.hidden = true;
        errEl.textContent = "";
    }

    form.addEventListener("submit", async (ev) => {
        ev.preventDefault();
        hideError();

        const content = form.querySelector('textarea[name="content"]').value.trim();
        if (!content) {
            showError("Введите текст поста.");
            return;
        }

        const fileInput = form.querySelector('input[name="image"]');
        const file = fileInput.files[0];

        let image_url = null;

        try {
            // 1) Если есть файл — загружаем
            if (file) {
                const fd = new FormData();
                fd.append("file", file);

                const up = await fetch("/upload", {
                    method: "POST",
                    credentials: "include",
                    headers: { Accept: "application/json" },
                    body: fd,
                });

                if (up.status === 401) {
                    window.location.href = "/login";
                    return;
                }
                if (!up.ok) {
                    const t = await up.text();
                    showError("Ошибка загрузки файла: " + up.status + " " + t);
                    return;
                }
                const upData = await up.json();
                image_url = upData.url;
            }

            // 2) Создаём пост
            const resp = await fetch("/posts?format=json", {
                method: "POST",
                credentials: "include",
                headers: {
                    "Content-Type": "application/json",
                    Accept: "application/json",
                },
                body: JSON.stringify({ content, image_url }),
            });

            if (resp.status === 401) {
                window.location.href = "/login";
                return;
            }
            if (!resp.ok) {
                const t = await resp.text();
                showError("Ошибка создания поста: " + resp.status + " " + t);
                return;
            }

            // 3) Перезагружаем ленту (просто и надёжно)
            window.location.reload();
        } catch (e) {
            showError("Сетевая ошибка: " + e);
        }
    });
})();