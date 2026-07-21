/**
 * LeadSathi — Main JavaScript
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
  var faqToggles = document.querySelectorAll(".faq-toggle");

  faqToggles.forEach(function (toggle) {
    toggle.addEventListener("click", function () {
      var item = toggle.closest(".faq-item");
      var content = item.querySelector(".faq-content");
      var chevron = item.querySelector(".faq-chevron");
      var isOpen = content.style.maxHeight !== "0px" && content.style.maxHeight !== "";

      document.querySelectorAll(".faq-item").forEach(function (otherItem) {
        if (otherItem !== item) {
          var otherContent = otherItem.querySelector(".faq-content");
          var otherChevron = otherItem.querySelector(".faq-chevron");
          otherContent.style.maxHeight = "0px";
          otherChevron.style.transform = "rotate(0deg)";
        }
      });

      if (isOpen) {
        content.style.maxHeight = "0px";
        chevron.style.transform = "rotate(0deg)";
      } else {
        content.style.maxHeight = content.scrollHeight + "px";
        chevron.style.transform = "rotate(180deg)";
      }
    });
  });

  // ==================================================
  // PULL-TO-REFRESH
  // ==================================================
  var PULL_THRESHOLD = 70;

  function createPTRIndicator() {
    var indicator = document.createElement("div");
    indicator.className = "ptr-indicator";
    indicator.innerHTML =
      '<div class="ptr-spinner">' +
        '<svg class="ptr-arrow" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#7e6f67" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
          '<polyline points="23 4 23 10 17 10"></polyline>' +
          '<path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>' +
        '</svg>' +
      '</div>' +
      '<span class="ptr-text">Pull to refresh</span>';
    document.body.appendChild(indicator);
    return indicator;
  }

  function initPullToRefresh() {
    var containers = document.querySelectorAll("[data-ptr-container]");
    if (!containers.length) return;

    var indicator = createPTRIndicator();
    var arrow = indicator.querySelector(".ptr-arrow");
    var text = indicator.querySelector(".ptr-text");

    containers.forEach(function (container) {
      var startY = 0;
      var pulling = false;
      var refreshing = false;

      container.style.overscrollBehaviorY = "contain";
      container.style.webkitOverflowScrolling = "touch";

      container.addEventListener("touchstart", function (e) {
        if (refreshing) return;
        if (container.scrollTop > 0) return;
        startY = e.touches[0].clientY;
        pulling = true;
      }, { passive: true });

      container.addEventListener("touchmove", function (e) {
        if (!pulling || refreshing) return;
        var currentY = e.touches[0].clientY;
        var distance = currentY - startY;

        if (distance < 0 || container.scrollTop > 0) {
          pulling = false;
          indicator.classList.remove("ptr-visible");
          return;
        }

        var progress = Math.min(distance / PULL_THRESHOLD, 1);
        indicator.classList.add("ptr-visible");
        arrow.style.transform = "rotate(" + (progress * 180) + "deg)";

        if (distance >= PULL_THRESHOLD) {
          text.textContent = "Release to refresh";
          arrow.classList.add("ptr-rotate");
        } else {
          text.textContent = "Pull to refresh";
          arrow.classList.remove("ptr-rotate");
        }

        if (distance > 0 && distance < 150) {
          e.preventDefault();
        }
      }, { passive: false });

      container.addEventListener("touchend", function () {
        if (!pulling || refreshing) return;
        pulling = false;

        var pullDistance = parseInt(indicator.style.transform
          ? indicator.style.transform.replace(/[^0-9]/g, "") : "0", 10) || 0;

        var currentText = text.textContent;
        if (currentText === "Release to refresh") {
          refreshing = true;
          indicator.classList.add("ptr-loading");
          text.textContent = "Refreshing...";
          arrow.style.transform = "";

          var refreshUrl = container.getAttribute("data-ptr-url") || window.location.href;
          var targetId = container.getAttribute("data-ptr-container");

          if (typeof htmx !== "undefined") {
            htmx.ajax("GET", refreshUrl, {
              target: targetId ? "#" + targetId : "body",
              swap: "innerHTML"
            });
          } else {
            window.location.reload();
          }
        } else {
          indicator.classList.remove("ptr-visible");
          arrow.style.transform = "";
        }
      });
    });

    document.addEventListener("htmx:afterSwap", function () {
      refreshing = false;
      indicator.classList.remove("ptr-loading", "ptr-visible");
      text.textContent = "Pull to refresh";
      arrow.style.transform = "";
    });
  }

  initPullToRefresh();

  // ==================================================
  // INFINITE SCROLL SENTINEL
  // ==================================================
  function initInfiniteScroll() {
    var sentinels = document.querySelectorAll("[data-infinite-scroll]");
    if (!sentinels.length) return;

    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;

        var el = entry.target;
        var hxGet = el.getAttribute("hx-get");
        var hxTarget = el.getAttribute("hx-target");
        var hxSwap = el.getAttribute("hx-swap") || "beforeend";

        if (!hxGet) return;

        observer.unobserve(el);

        var spinner = document.createElement("div");
        spinner.className = "ls-infinite-scroll-spinner";
        spinner.style.cssText =
          "display:flex;justify-content:center;padding:16px;opacity:0.7;";
        spinner.innerHTML =
          '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#b56a30" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="animation:ptr-spin 800ms linear infinite;">' +
            '<line x1="12" y1="2" x2="12" y2="6"></line>' +
            '<line x1="12" y1="18" x2="12" y2="22"></line>' +
            '<line x1="4.93" y1="4.93" x2="7.76" y2="7.76"></line>' +
            '<line x1="16.24" y1="16.24" x2="19.07" y2="19.07"></line>' +
            '<line x1="2" y1="12" x2="6" y2="12"></line>' +
            '<line x1="18" y1="12" x2="22" y2="12"></line>' +
            '<line x1="4.93" y1="19.07" x2="7.76" y2="16.24"></line>' +
            '<line x1="16.24" y1="7.76" x2="19.07" y2="4.93"></line>' +
          '</svg>';
        el.parentNode.insertBefore(spinner, el);

        if (typeof htmx !== "undefined") {
          htmx.ajax("GET", hxGet, {
            target: hxTarget || "body",
            swap: hxSwap
          });
        }

        document.addEventListener("htmx:afterSwap", function handler() {
          spinner.remove();
          document.removeEventListener("htmx:afterSwap", handler);
        });
      });
    }, { rootMargin: "200px" });

    sentinels.forEach(function (el) {
      observer.observe(el);
    });
  }

  initInfiniteScroll();

  // ==================================================
  // HTMX BODY SWAP — Alpine.js re-init + scroll unlock
  // ==================================================
  // When HTMX replaces <body>, Alpine components in the new DOM
  // may not auto-initialize. Also, body scroll lock from More sheet
  // or modals must be cleared so the new page isn't stuck.
  document.addEventListener("htmx:beforeSwap", function () {
    // Unlock body scroll (reset More sheet / modal scroll lock)
    document.body.style.overflow = "";
    document.body.style.position = "";
    document.body.style.width = "";
  });

  document.addEventListener("htmx:afterSwap", function (evt) {
    // Re-initialize Alpine.js on the new body content
    if (typeof Alpine !== "undefined") {
      // Alpine 3.x: initTree scans for un-initialized x-data directives
      Alpine.initTree(document.body);
    }

    // Re-bind the profile dropdown (vanilla JS, lost on body swap)
    var profileBtn = document.getElementById("profile-menu-button");
    var dropdown = document.getElementById("profile-dropdown");
    if (profileBtn && dropdown) {
      profileBtn.addEventListener("click", function (e) {
        e.stopPropagation();
        dropdown.classList.toggle("show");
        var isExpanded = profileBtn.getAttribute("aria-expanded") === "true";
        profileBtn.setAttribute("aria-expanded", !isExpanded);
      });
      document.addEventListener("click", function (e) {
        if (!profileBtn.contains(e.target) && !dropdown.contains(e.target)) {
          dropdown.classList.remove("show");
          profileBtn.setAttribute("aria-expanded", "false");
        }
      });
      document.addEventListener("keydown", function (e) {
        if (e.key === "Escape" && dropdown.classList.contains("show")) {
          dropdown.classList.remove("show");
          profileBtn.setAttribute("aria-expanded", "false");
        }
      });
    }

    // Re-initialize pull-to-refresh and infinite scroll on new content
    initPullToRefresh();
    initInfiniteScroll();

    // Re-bind fade-in animations
    var newFadeEls = document.querySelectorAll(".fade-in");
    if (newFadeEls.length > 0) {
      var fadeObs = new IntersectionObserver(
        function (entries) {
          entries.forEach(function (entry) {
            if (entry.isIntersecting) {
              entry.target.style.opacity = "1";
              entry.target.style.transform = "translateY(0)";
              fadeObs.unobserve(entry.target);
            }
          });
        },
        { threshold: 0.2 }
      );
      newFadeEls.forEach(function (el) {
        fadeObs.observe(el);
      });
    }

    // Re-bind count-up animations
    var newCountEls = document.querySelectorAll(".countup");
    if (newCountEls.length > 0) {
      var countObs = new IntersectionObserver(
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
                var ease = 1 - Math.pow(1 - progress, 4);
                el.textContent = (target * ease).toFixed(decimals);
                if (progress < 1) requestAnimationFrame(animate);
              }
              requestAnimationFrame(animate);
              countObs.unobserve(el);
            }
          });
        },
        { threshold: 0.5 }
      );
      newCountEls.forEach(function (el) {
        countObs.observe(el);
      });
    }
  });
})();
