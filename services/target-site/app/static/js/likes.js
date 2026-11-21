// Лайки и удаление комментариев без перезагрузки страницы.
(function () {
    const COOKIE_TOKEN_KEY = "access_token";

    function getTokenFromCookie() {
        // На сервере cookie httponly — JS её не видит.
        // Поэтому используем /api/me для проверки, а лайк шлём с credentials: "include".
        return null;
    }

    async function toggleLike(btn) {
        const postId = btn.dataset.postId;
        const countEl = btn.querySelector(".like-count");
        const liked = btn.dataset.liked === "true";

        const method = liked ? "DELETE" : "POST";
        const url = `/posts/${postId}/like?format=json`;

        try {
            const resp = await fetch(url, {
                method,
                credentials: "include",
                headers: { Accept: "application/json" },
            });

            if (resp.status === 401) {
                window.location.href = "/login";
                return;
            }
            if (!resp.ok) {
                console.error("like failed", resp.status, await resp.text());
                return;
            }
            const data = await resp.json();
            btn.dataset.liked = data.liked ? "true" : "false";
            countEl.textContent = data.likes_count;
        } catch (e) {
            console.error("like error", e);
        }
    }

    async function deleteComment(btn) {
        const id = btn.dataset.commentId;
        if (!confirm("Удалить комментарий?")) return;
        try {
            const resp = await fetch(`/comments/${id}`, {
                method: "DELETE",
                credentials: "include",
                headers: { Accept: "application/json" },
            });
            if (resp.status === 401) {
                window.location.href = "/login";
                return;
            }
            if (!resp.ok) {
                console.error("delete comment failed", resp.status);
                return;
            }
            const el = document.getElementById(`comment-${id}`);
            if (el) el.remove();
        } catch (e) {
            console.error(e);
        }
    }

    document.addEventListener("click", (ev) => {
        const likeBtn = ev.target.closest(".like-btn");
        if (likeBtn) {
            ev.preventDefault();
            toggleLike(likeBtn);
            return;
        }
        const delBtn = ev.target.closest(".js-delete-comment");
        if (delBtn) {
            ev.preventDefault();
            deleteComment(delBtn);
        }
    });
})();