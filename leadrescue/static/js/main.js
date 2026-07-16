/**
 * LeadRescue — Main JavaScript
 *
 * Handles:
 * - Intersection Observer fade-in animations
 * - CountUp number animations
 * - FAQ accordion
 * - Navbar scroll behavior
 *
 * No framework dependencies. Pure vanilla JS.
 */

(function () {
  "use strict";

  // ==================================================
  // NAVBAR SCROLL BEHAVIOR
  // ==================================================
  const navbar = document.getElementById("navbar");
  if (navbar) {
    const brand = navbar.querySelector(".navbar-brand");
    const links = navbar.querySelectorAll(".navbar-link");
    const cta = navbar.querySelector(".navbar-cta");

    function updateNavbar() {
      const scrolled = window.scrollY > 50;

      if (scrolled) {
        navbar.style.backgroundColor = "rgba(250, 248, 244, 0.88)";
        navbar.style.backdropFilter = "blur(12px)";
        navbar.classList.add("shadow-sm");
      } else {
        navbar.style.backgroundColor = "transparent";
        navbar.style.backdropFilter = "none";
        navbar.classList.remove("shadow-sm");
      }

      if (brand) {
        brand.style.color = scrolled ? "#1C1C1A" : "#FAF8F4";
      }

      links.forEach(function (link) {
        link.style.color = scrolled ? "#8B7355" : "rgba(250, 248, 244, 0.85)";
      });

      if (cta) {
        if (scrolled) {
          cta.style.backgroundColor = "#1C1C1A";
          cta.style.color = "#FAF8F4";
          cta.style.border = "none";
        } else {
          cta.style.backgroundColor = "rgba(250, 248, 244, 0.15)";
          cta.style.color = "#FAF8F4";
          cta.style.border = "1.5px solid rgba(250,248,244,0.5)";
        }
      }
    }

    window.addEventListener("scroll", updateNavbar, { passive: true });
    updateNavbar(); // Initial state
  }

  // ==================================================
  // INTERSECTION OBSERVER — FADE-IN ANIMATIONS
  // ==================================================
  const fadeElements = document.querySelectorAll(".fade-in");

  if (fadeElements.length > 0) {
    // Set initial hidden state
    fadeElements.forEach(function (el) {
      el.style.opacity = "0";
      el.style.transform = "translateY(2rem)";
      el.style.transition = "opacity 1s ease, transform 1s ease";
    });

    const fadeObserver = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.style.opacity = "1";
            entry.target.style.transform = "translateY(0)";
            fadeObserver.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.2 }
    );

    fadeElements.forEach(function (el) {
      fadeObserver.observe(el);
    });
  }

  // ==================================================
  // COUNTUP ANIMATION
  // ==================================================
  const countUpElements = document.querySelectorAll(".countup");

  if (countUpElements.length > 0) {
    const countObserver = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            var el = entry.target;
            var target = parseFloat(el.getAttribute("data-target"));
            var decimals = parseInt(el.getAttribute("data-decimals") || "0", 10);
            var duration = 2000;
            var startTime = null;

            function animate(t) {
              if (!startTime) startTime = t;
              var progress = Math.min((t - startTime) / duration, 1);
              // Ease out quart
              var ease = 1 - Math.pow(1 - progress, 4);
              var current = target * ease;
              el.textContent = current.toFixed(decimals);
              if (progress < 1) {
                requestAnimationFrame(animate);
              }
            }

            requestAnimationFrame(animate);
            countObserver.unobserve(el);
          }
        });
      },
      { threshold: 0.5 }
    );

    countUpElements.forEach(function (el) {
      countObserver.observe(el);
    });
  }

  // ==================================================
  // FAQ ACCORDION
  // ==================================================
  const faqToggles = document.querySelectorAll(".faq-toggle");

  faqToggles.forEach(function (toggle) {
    toggle.addEventListener("click", function () {
      var item = toggle.closest(".faq-item");
      var content = item.querySelector(".faq-content");
      var chevron = item.querySelector(".faq-chevron");
      var isOpen = content.style.maxHeight !== "0px" && content.style.maxHeight !== "";

      // Close all other FAQ items
      document.querySelectorAll(".faq-item").forEach(function (otherItem) {
        if (otherItem !== item) {
          var otherContent = otherItem.querySelector(".faq-content");
          var otherChevron = otherItem.querySelector(".faq-chevron");
          otherContent.style.maxHeight = "0px";
          otherChevron.style.transform = "rotate(0deg)";
        }
      });

      // Toggle current item
      if (isOpen) {
        content.style.maxHeight = "0px";
        chevron.style.transform = "rotate(0deg)";
      } else {
        content.style.maxHeight = content.scrollHeight + "px";
        chevron.style.transform = "rotate(180deg)";
      }
    });
  });
})();
