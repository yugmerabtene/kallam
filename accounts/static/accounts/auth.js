(function () {
  var toggles = document.querySelectorAll("[data-toggle-password]");
  toggles.forEach(function (btn) {
    var inputId = btn.getAttribute("data-toggle-password");
    var input = document.getElementById(inputId);
    if (!input) return;

    btn.setAttribute("aria-controls", inputId);
    btn.setAttribute("aria-label", "Afficher le mot de passe");
    btn.addEventListener("click", function () {
      var show = input.type === "password";
      input.type = show ? "text" : "password";
      btn.textContent = show ? "Masquer" : "Afficher";
      btn.setAttribute(
        "aria-label",
        show ? "Masquer le mot de passe" : "Afficher le mot de passe"
      );
    });
  });

  var registerForm = document.querySelector("[data-register-form]");
  if (!registerForm) return;
  var password = registerForm.querySelector('input[name="password"]');
  var confirm = registerForm.querySelector('input[name="password_confirm"]');
  var error = registerForm.querySelector("[data-password-match]");

  function validatePasswordMatch() {
    if (!password || !confirm || !error) return true;
    var match = password.value === confirm.value;
    if (confirm.value.length === 0) {
      error.hidden = true;
      confirm.removeAttribute("aria-invalid");
      return true;
    }
    error.hidden = match;
    if (match) {
      confirm.removeAttribute("aria-invalid");
    } else {
      confirm.setAttribute("aria-invalid", "true");
    }
    return match;
  }

  if (password) password.addEventListener("input", validatePasswordMatch);
  if (confirm) confirm.addEventListener("input", validatePasswordMatch);
  registerForm.addEventListener("submit", function (event) {
    if (!validatePasswordMatch()) {
      event.preventDefault();
    }
  });
})();

(function () {
  var composerForm = document.querySelector("[data-composer-form]");
  if (!composerForm) return;
  var textarea = composerForm.querySelector("textarea[name='content']");
  var counter = composerForm.querySelector("[data-char-count]");
  var publishBtn = composerForm.querySelector("[data-publish-btn]");
  if (!textarea || !counter || !publishBtn) return;

  var replyButtons = document.querySelectorAll(".reply-btn[data-reply-handle]");
  replyButtons.forEach(function (button) {
    button.addEventListener("click", function () {
      var handle = button.getAttribute("data-reply-handle");
      if (!handle) return;
      if (!textarea.value.startsWith(handle)) {
        textarea.value = handle + " " + textarea.value;
      }
      textarea.focus();
      textarea.setSelectionRange(textarea.value.length, textarea.value.length);
      updateCounter();
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  });

  function updateCounter() {
    var length = textarea.value.length;
    counter.textContent = length + "/280";
    var canPublish = length > 0 && length <= 280;
    publishBtn.disabled = !canPublish;
  }

  textarea.addEventListener("input", updateCounter);
  updateCounter();
})();
