/* Kallam — UI interactions v2 */

/* ── Password visibility toggle ─────────────────── */
(function () {
  document.querySelectorAll("[data-toggle-password]").forEach(function (btn) {
    var inputId = btn.getAttribute("data-toggle-password");
    var input = document.getElementById(inputId);
    if (!input) return;
    btn.setAttribute("aria-controls", inputId);
    btn.addEventListener("click", function () {
      var show = input.type === "password";
      input.type = show ? "text" : "password";
      btn.textContent = show ? "Masquer" : "Afficher";
    });
  });
})();

/* ── Register: real-time password match ──────────── */
(function () {
  var form = document.querySelector("[data-register-form]");
  if (!form) return;
  var pw = form.querySelector('input[name="password"]');
  var cw = form.querySelector('input[name="password_confirm"]');
  var err = form.querySelector("[data-password-match]");

  function check() {
    if (!pw || !cw || !err) return true;
    if (cw.value.length === 0) { err.hidden = true; cw.removeAttribute("aria-invalid"); return true; }
    var match = pw.value === cw.value;
    err.hidden = match;
    match ? cw.removeAttribute("aria-invalid") : cw.setAttribute("aria-invalid", "true");
    return match;
  }

  if (pw) pw.addEventListener("input", check);
  if (cw) cw.addEventListener("input", check);
  form.addEventListener("submit", function (e) { if (!check()) e.preventDefault(); });
})();

/* ── Composer ─────────────────────────────────────── */
(function () {
  var form = document.querySelector("[data-composer-form]");
  if (!form) return;

  var textarea = form.querySelector("textarea[name='content']");
  var imageInput = form.querySelector("input[name='image']");
  var attachUrlInput = form.querySelector("input[name='attachment_url']");
  var toggleBtn = form.querySelector("[data-attach-toggle]");
  var panel = form.querySelector("[data-attach-panel]");
  var counter = form.querySelector("[data-char-count]");
  var publishBtn = form.querySelector("[data-publish-btn]");
  if (!textarea || !publishBtn) return;

  /* Jump to composer */
  var jumpBtn = document.querySelector("[data-composer-jump]");
  if (jumpBtn) {
    jumpBtn.addEventListener("click", function () {
      var el = document.getElementById("composer");
      if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
      setTimeout(function () { textarea.focus(); }, 350);
    });
  }

  /* Attachment panel toggle */
  if (toggleBtn && panel) {
    toggleBtn.addEventListener("click", function () {
      var hidden = panel.hidden;
      panel.hidden = !hidden;
      toggleBtn.setAttribute("aria-expanded", hidden ? "true" : "false");
      if (hidden) textarea.focus();
    });
  }

  /* Reply prefill */
  document.querySelectorAll(".reply-btn[data-reply-handle]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var handle = btn.getAttribute("data-reply-handle");
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

  /* Char counter + publish gating */
  function updateCounter() {
    var len = textarea.value.length;
    if (!counter) { publishBtn.disabled = len === 0; return; }
    counter.textContent = len + "/280";
    counter.className = "char-counter" + (len > 260 ? (len > 280 ? " over-limit" : " near-limit") : "");
    var hasImg = imageInput && imageInput.files && imageInput.files.length > 0;
    var hasUrl = attachUrlInput && attachUrlInput.value.trim().length > 0;
    publishBtn.disabled = !(len > 0 && len <= 280) && !hasImg && !hasUrl;
  }

  textarea.addEventListener("input", updateCounter);
  if (imageInput) imageInput.addEventListener("change", updateCounter);
  if (attachUrlInput) attachUrlInput.addEventListener("input", updateCounter);
  updateCounter();
})();

/* ── Like button animation ────────────────────────── */
(function () {
  document.querySelectorAll(".like-btn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      btn.classList.add("pop");
      btn.addEventListener("animationend", function () {
        btn.classList.remove("pop");
      }, { once: true });
    });
  });
})();

/* ── Auto-dismiss flash messages ─────────────────── */
(function () {
  var msgs = document.querySelectorAll(".messages li");
  msgs.forEach(function (li, i) {
    setTimeout(function () {
      li.style.transition = "opacity 0.5s ease, transform 0.5s ease, max-height 0.4s ease";
      li.style.opacity = "0";
      li.style.transform = "translateY(-4px)";
      li.style.maxHeight = "0";
      li.style.overflow = "hidden";
      li.style.padding = "0";
      li.style.margin = "0";
      li.style.border = "0";
    }, 4000 + i * 200);
  });
})();

/* ── Messaging: auto-scroll + Enter send ─────────── */
(function () {
  var thread = document.getElementById("msg-thread");
  if (thread) {
    thread.scrollTop = thread.scrollHeight;
  }

  var input = document.querySelector(".msg-composer-input");
  if (!input) return;

  input.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      var form = input.closest("form");
      if (form && input.value.trim().length > 0) form.submit();
    }
  });

  /* Auto-resize textarea */
  input.addEventListener("input", function () {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 120) + "px";
  });
})();

/* ── Ripple effect on buttons ────────────────────── */
(function () {
  function addRipple(e) {
    var btn = e.currentTarget;
    var rect = btn.getBoundingClientRect();
    var r = document.createElement("span");
    var size = Math.max(rect.width, rect.height);
    r.style.cssText = [
      "position:absolute",
      "border-radius:50%",
      "pointer-events:none",
      "background:rgba(255,255,255,0.28)",
      "width:" + size + "px",
      "height:" + size + "px",
      "top:" + (e.clientY - rect.top - size / 2) + "px",
      "left:" + (e.clientX - rect.left - size / 2) + "px",
      "animation:ripple 0.5s ease-out forwards",
    ].join(";");
    if (getComputedStyle(btn).position === "static") btn.style.position = "relative";
    btn.style.overflow = "hidden";
    btn.appendChild(r);
    setTimeout(function () { r.remove(); }, 600);
  }

  var style = document.createElement("style");
  style.textContent = "@keyframes ripple{from{opacity:1;transform:scale(0)}to{opacity:0;transform:scale(2.5)}}";
  document.head.appendChild(style);

  document.querySelectorAll("button.primary, button.secondary, .action-btn").forEach(function (btn) {
    btn.addEventListener("click", addRipple);
  });
})();
