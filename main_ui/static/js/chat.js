"use strict";

(() => {
    const configEl = document.getElementById("tutor-config");
    const config = JSON.parse(configEl.textContent);

    const messageList = document.getElementById("message-list");
    const composerForm = document.getElementById("composer");
    const composerInput = document.getElementById("composer-input");
    const sendButton = document.getElementById("send-button");
    const errorBanner = document.getElementById("error-banner");
    const errorText = document.getElementById("error-text");
    const errorDismiss = document.getElementById("error-dismiss");

    const emailModal = document.getElementById("email-modal");
    const emailForm = document.getElementById("email-form");
    const emailInput = document.getElementById("email-input");
    const emailSubmit = document.getElementById("email-submit");
    const emailSkip = document.getElementById("email-skip");
    const emailError = document.getElementById("email-error");

    let conversationId = null;
    let isSending = false;
    let studentMessageCount = 0;
    let modalOpen = false;
    let dismissedThisSession = false;

    function updateSendButton() {
        sendButton.disabled = isSending || composerInput.value.trim().length === 0;
    }

    function setSending(sending) {
        isSending = sending;
        composerInput.disabled = sending;
        updateSendButton();
    }

    function renderMessage(role, content) {
        const li = document.createElement("li");
        li.className = "message message-" + role;
        // textContent — never innerHTML — to prevent XSS from tutor or student text.
        li.textContent = content;
        messageList.appendChild(li);
        // Always auto-scroll to bottom. Known papercut: fights user scrolling.
        messageList.scrollTop = messageList.scrollHeight;
        return li;
    }

    function renderThinking() {
        const li = document.createElement("li");
        li.className = "message message-thinking";
        li.textContent = "AskTIM is thinking…";
        messageList.appendChild(li);
        messageList.scrollTop = messageList.scrollHeight;
        return li;
    }

    function showError(reason) {
        errorText.textContent = reason;
        errorBanner.hidden = false;
    }

    function hideError() {
        errorBanner.hidden = true;
        errorText.textContent = "";
    }

    function hasEmailSet() {
        // The `tutor_email` cookie is HttpOnly so JS can't read it directly.
        // The server stamps document.body.dataset.hasEmail on every render
        // based on the request's cookie; we also flip it locally after a
        // successful submission so the modal doesn't re-open this page load.
        return document.body.dataset.hasEmail === "true";
    }

    function emailLooksValid(value) {
        return value.includes("@") && value.includes(".");
    }

    function updateEmailSubmit() {
        emailSubmit.disabled = !emailLooksValid(emailInput.value.trim());
    }

    function openEmailModal() {
        if (modalOpen) return;
        modalOpen = true;
        emailError.hidden = true;
        emailError.textContent = "";
        emailInput.value = "";
        updateEmailSubmit();
        emailModal.hidden = false;
        emailInput.focus();
    }

    function closeEmailModal({ dismissed = false } = {}) {
        if (!modalOpen) return;
        modalOpen = false;
        emailModal.hidden = true;
        if (dismissed) {
            dismissedThisSession = true;
        }
        composerInput.focus();
    }

    function maybeShowEmailModal(count) {
        if (count < 3) return;
        if (hasEmailSet()) return;
        if (dismissedThisSession) return;
        openEmailModal();
    }

    async function submitEmail(event) {
        event.preventDefault();
        const value = emailInput.value.trim();
        if (!emailLooksValid(value)) return;

        emailSubmit.disabled = true;
        emailError.hidden = true;

        try {
            const response = await fetch("/api/email", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email: value }),
            });

            if (!response.ok) {
                let reason = "Could not save your email. Please try again.";
                try {
                    const body = await response.json();
                    if (body && body.reason) reason = body.reason;
                } catch (_) {
                    /* ignore body-parse errors */
                }
                emailError.textContent = reason;
                emailError.hidden = false;
                emailSubmit.disabled = false;
                return;
            }

            // Mark local state so maybeShowEmailModal won't reopen this page load.
            // The actual cookie was set by the server response.
            document.body.dataset.hasEmail = "true";
            closeEmailModal();
        } catch (err) {
            emailError.textContent = "Cannot reach AskTIM. Check your connection and try again.";
            emailError.hidden = false;
            emailSubmit.disabled = false;
        }
    }

    async function sendMessage() {
        const text = composerInput.value.trim();
        if (!text || isSending) return;

        hideError();
        // Optimistically render the student bubble + a "thinking" placeholder
        // where the tutor reply will land. Rollback both on error.
        const studentBubble = renderMessage("student", text);
        const thinkingBubble = renderThinking();
        const originalText = composerInput.value;
        composerInput.value = "";
        setSending(true);

        const payload = {
            text: text,
            course: config.course,
            exercise: config.exercise,
            tutor: config.tutor,
        };
        if (conversationId) {
            payload.conversation_id = conversationId;
        }

        try {
            const response = await fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });

            if (!response.ok) {
                let reason = "Something went wrong. Please try again.";
                try {
                    const body = await response.json();
                    if (body && body.reason) reason = body.reason;
                } catch (_) {
                    /* ignore body-parse errors */
                }
                thinkingBubble.remove();
                studentBubble.remove();
                composerInput.value = originalText;
                showError(reason);
                return;
            }

            const data = await response.json();
            conversationId = data.conversation_id;
            studentMessageCount = data.student_message_count;
            thinkingBubble.remove();
            renderMessage("tutor", data.reply);
            maybeShowEmailModal(studentMessageCount);
        } catch (err) {
            thinkingBubble.remove();
            studentBubble.remove();
            composerInput.value = originalText;
            showError("Cannot reach AskTIM. Check your connection and try again.");
        } finally {
            setSending(false);
            composerInput.focus();
        }
    }

    composerForm.addEventListener("submit", (event) => {
        event.preventDefault();
        sendMessage();
    });

    composerInput.addEventListener("input", updateSendButton);

    composerInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            sendMessage();
        }
    });

    errorDismiss.addEventListener("click", hideError);

    // Email modal wiring (Step 7)
    emailInput.addEventListener("input", updateEmailSubmit);
    emailForm.addEventListener("submit", submitEmail);
    emailSkip.addEventListener("click", () => closeEmailModal({ dismissed: true }));
    emailModal.addEventListener("click", (event) => {
        // Backdrop click = skip; clicks inside the card are ignored
        if (event.target === emailModal) {
            closeEmailModal({ dismissed: true });
        }
    });
    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && modalOpen) {
            closeEmailModal({ dismissed: true });
        }
    });

    // Auto-focus the composer so an embedded iframe is immediately typable
    // (works once the iframe has focus; harmless on first paint otherwise).
    composerInput.focus();
    updateSendButton();
})();
