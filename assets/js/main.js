(function () {
  "use strict";

  var root = document.documentElement;
  var THEME_KEY = "dcc-site-theme";

  function applyTheme(theme) {
    root.setAttribute("data-theme", theme);
    var btn = document.getElementById("theme-toggle");
    if (btn) btn.setAttribute("aria-pressed", theme === "dark" ? "true" : "false");
    var meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute("content", theme === "dark" ? "#1b1f26" : "#f4f5f7");
  }

  function initTheme() {
    var stored = localStorage.getItem(THEME_KEY);
    var theme = stored || (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    applyTheme(theme);

    var btn = document.getElementById("theme-toggle");
    if (btn) {
      btn.addEventListener("click", function () {
        var current = root.getAttribute("data-theme") === "dark" ? "dark" : "light";
        var next = current === "dark" ? "light" : "dark";
        applyTheme(next);
        localStorage.setItem(THEME_KEY, next);
      });
    }
  }

  function initNav() {
    var nav = document.getElementById("site-nav");
    var toggle = document.getElementById("nav-toggle");
    if (!nav || !toggle) return;
    toggle.addEventListener("click", function () {
      var isOpen = nav.classList.toggle("open");
      toggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
    });
    nav.querySelectorAll(".nav-links a").forEach(function (link) {
      link.addEventListener("click", function () {
        nav.classList.remove("open");
        toggle.setAttribute("aria-expanded", "false");
      });
    });
  }

  function initYear() {
    var el = document.getElementById("year");
    if (el) el.textContent = new Date().getFullYear();
  }

  function initShotFilters() {
    var filters = document.querySelectorAll(".shot-filter");
    var cards = document.querySelectorAll(".shot-card");
    filters.forEach(function (btn) {
      btn.addEventListener("click", function () {
        filters.forEach(function (b) { b.classList.remove("active"); });
        btn.classList.add("active");
        var group = btn.getAttribute("data-group");
        cards.forEach(function (card) {
          var show = group === "all" || card.getAttribute("data-group") === group;
          card.style.display = show ? "" : "none";
        });
      });
    });
  }

  function initLightbox() {
    var cards = Array.prototype.slice.call(document.querySelectorAll(".shot-card"));
    if (!cards.length) return;

    var lightbox = document.getElementById("lightbox");
    var lightboxImg = document.getElementById("lightbox-img");
    var lightboxCaption = document.getElementById("lightbox-caption");
    var closeBtn = document.getElementById("lightbox-close");
    var prevBtn = document.getElementById("lightbox-prev");
    var nextBtn = document.getElementById("lightbox-next");
    var currentIndex = 0;

    function open(index) {
      currentIndex = (index + cards.length) % cards.length;
      var card = cards[currentIndex];
      lightboxImg.src = card.getAttribute("data-full");
      lightboxImg.alt = card.getAttribute("data-alt") || "";
      lightboxCaption.textContent = card.getAttribute("data-alt") || "";
      lightbox.classList.add("open");
      lightbox.setAttribute("aria-hidden", "false");
      document.body.style.overflow = "hidden";
    }

    function close() {
      lightbox.classList.remove("open");
      lightbox.setAttribute("aria-hidden", "true");
      document.body.style.overflow = "";
    }

    cards.forEach(function (card, index) {
      card.addEventListener("click", function () { open(index); });
    });

    closeBtn.addEventListener("click", close);
    nextBtn.addEventListener("click", function () { open(currentIndex + 1); });
    prevBtn.addEventListener("click", function () { open(currentIndex - 1); });
    lightbox.addEventListener("click", function (e) {
      if (e.target === lightbox) close();
    });
    document.addEventListener("keydown", function (e) {
      if (!lightbox.classList.contains("open")) return;
      if (e.key === "Escape") close();
      if (e.key === "ArrowRight") open(currentIndex + 1);
      if (e.key === "ArrowLeft") open(currentIndex - 1);
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initTheme();
    initNav();
    initYear();
    initShotFilters();
    initLightbox();
  });
})();
