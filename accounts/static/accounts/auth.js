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
