"use strict";

document.querySelectorAll(".dismiss-alert").forEach((button) => {
  button.addEventListener("click", () => button.closest(".alert").remove());
});

const noteInput = document.getElementById("note");
if (noteInput) {
  const counter = document.getElementById("character-count");
  noteInput.addEventListener("input", () => {
    counter.textContent = noteInput.value.length;
    noteInput.setCustomValidity("");
  });
  document.getElementById("note-form").addEventListener("submit", (event) => {
    if (!noteInput.value.trim()) {
      event.preventDefault();
      noteInput.setCustomValidity("Write something before saving your note.");
      noteInput.reportValidity();
    }
  });
}

const deleteDialog = document.getElementById("delete-dialog");
if (deleteDialog) {
  const cancelButton = document.getElementById("cancel-delete");
  const confirmButton = document.getElementById("confirm-delete");
  const feedback = document.getElementById("note-feedback");
  let selectedButton = null;

  document.querySelectorAll(".delete-note").forEach((button) => {
    button.addEventListener("click", () => {
      selectedButton = button;
      deleteDialog.showModal();
      cancelButton.focus();
    });
  });
  cancelButton.addEventListener("click", () => deleteDialog.close());
  confirmButton.addEventListener("click", async () => {
    if (!selectedButton) return;
    const button = selectedButton;
    confirmButton.disabled = true;
    cancelButton.disabled = true;
    try {
      const response = await fetch(button.dataset.deleteUrl, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": document.querySelector('meta[name="csrf-token"]').content,
        },
        body: JSON.stringify({ noteId: Number(button.dataset.noteId) }),
      });
      if (!response.ok) {
        let message = "We couldn't delete this note. Please try again.";
        try { message = (await response.json()).error || message; } catch (_) { /* Non-JSON server error. */ }
        throw new Error(message);
      }
      // Preserve the server-rendered empty state and count after deletion.
      window.location.reload();
    } catch (error) {
      deleteDialog.close();
      feedback.textContent = error.message || "Connection lost. Please try again.";
      feedback.className = "alert alert-error";
      feedback.hidden = false;
      feedback.scrollIntoView({ block: "nearest" });
    } finally {
      confirmButton.disabled = false;
      cancelButton.disabled = false;
    }
  });
}
