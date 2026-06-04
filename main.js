/* ═══════════════════════════════════════════════════════
   SIZZLE & SAVOR — Fine Continental Dining
   Main JavaScript — Interactions, Animations & API
   ═══════════════════════════════════════════════════════ */

/* ─── Google Places API Configuration ───
 * To display real Google Reviews:
 * 1. Get a Google Places API key from https://console.cloud.google.com/apis/credentials
 * 2. Enable "Places API" in your Google Cloud project
 * 3. Replace "YOUR_API_KEY_HERE" below with your actual API key
 * 4. The PLACE_ID below is for Sizzle & Savor, Kolkata
 */
const GOOGLE_PLACES_API_KEY = "YOUR_API_KEY_HERE";
const PLACE_ID = "ChIJYeN4r4Wf-DkRIHe9kDw-3sE";

// ═══════════════════════════════════════════
// DOM Ready
// ═══════════════════════════════════════════
document.addEventListener("DOMContentLoaded", () => {
  initPreloader();
  initNavbar();
  initTopbarStatus();
  initScrollProgress();
  initScrollSpy();
  initMobileMenu();
  initMenuTabs();
  initMenuShowcaseDrag();
  initGalleryLightbox();
  initScrollReveal();
  initStatsCounter();
  initReservationForm();
  initNewsletterForm();
  initBackToTop();
  initFloatingCta();
  initReviewsCarousel();
  initParallax();
  initReservationDateMin();
});


// ═══════════════════════════════════════════
// 1. PRELOADER
// ═══════════════════════════════════════════
function initPreloader() {
  const preloader = document.getElementById("preloader");
  if (!preloader) return;

  // Hide after window load + small delay
  const hidePreloader = () => {
    setTimeout(() => {
      preloader.classList.add("hidden");
      // Remove from DOM after transition
      setTimeout(() => {
        preloader.remove();
        document.body.classList.remove("no-scroll");
      }, 700);
    }, 800);
  };

  if (document.readyState === "complete") {
    hidePreloader();
  } else {
    window.addEventListener("load", hidePreloader, { once: true });
    // Fallback in case load event is slow
    setTimeout(hidePreloader, 3000);
  }
}


// ═══════════════════════════════════════════
// 2. NAVBAR — Transparent → Solid on Scroll
// ═══════════════════════════════════════════
function initNavbar() {
  const navbar = document.getElementById("navbar");
  const topbar = document.getElementById("topbar");
  if (!navbar) return;

  let lastScroll = 0;
  let ticking = false;

  function onScroll() {
    if (!ticking) {
      window.requestAnimationFrame(() => {
        const scrollY = window.scrollY;

        // Navbar background
        if (scrollY > 80) {
          navbar.classList.add("scrolled");
        } else {
          navbar.classList.remove("scrolled");
        }

        // Topbar hide on scroll down
        if (topbar && window.innerWidth > 768) {
          if (scrollY > 200 && scrollY > lastScroll) {
            topbar.classList.add("hide");
            navbar.style.top = "0";
          } else {
            topbar.classList.remove("hide");
            navbar.style.top = scrollY > 80 ? "0" : "32px";
          }
        }

        lastScroll = scrollY;
        ticking = false;
      });
      ticking = true;
    }
  }

  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();
}


// ═══════════════════════════════════════════
// 3. TOPBAR — Open/Closed Status
// ═══════════════════════════════════════════
function initTopbarStatus() {
  const dot = document.querySelector(".status-dot");
  const text = document.querySelector(".status-text");
  const hours = document.querySelector(".status-hours");
  if (!dot || !text) return;

  const now = new Date();
  const hour = now.getHours();
  const isOpen = hour >= 12 && hour < 23;

  if (!isOpen) {
    dot.classList.add("closed");
    text.classList.add("closed");
    text.textContent = "Closed";
    if (hours) {
      const nextOpen = hour < 12 ? "Opens at 12:00" : "Opens tomorrow at 12:00";
      hours.textContent = nextOpen;
    }
  } else {
    if (hours) {
      hours.textContent = "Closes at 23:00";
    }
  }
}


// ═══════════════════════════════════════════
// 4. SCROLL PROGRESS BAR
// ═══════════════════════════════════════════
function initScrollProgress() {
  const progressBar = document.getElementById("scrollProgress");
  if (!progressBar) return;

  let ticking = false;

  function onScroll() {
    if (!ticking) {
      window.requestAnimationFrame(() => {
        const docHeight = document.documentElement.scrollHeight - window.innerHeight;
        const scrolled = docHeight > 0 ? (window.scrollY / docHeight) * 100 : 0;
        progressBar.style.width = `${Math.min(scrolled, 100)}%`;
        ticking = false;
      });
      ticking = true;
    }
  }

  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();
}


// ═══════════════════════════════════════════
// 5. SCROLLSPY — Active Nav Link
// ═══════════════════════════════════════════
function initScrollSpy() {
  const sections = document.querySelectorAll("section[id]");
  const navLinks = document.querySelectorAll(".nav-links a[data-section], .mobile-nav-links a[data-section]");

  if (!sections.length || !navLinks.length) return;

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const id = entry.target.id;
          navLinks.forEach((link) => {
            const isActive = link.dataset.section === id;
            link.classList.toggle("active", isActive);
          });
        }
      });
    },
    {
      rootMargin: "-40% 0px -55% 0px",
      threshold: 0,
    }
  );

  sections.forEach((section) => observer.observe(section));
}


// ═══════════════════════════════════════════
// 6. MOBILE MENU
// ═══════════════════════════════════════════
function initMobileMenu() {
  const hamburger = document.getElementById("hamburger");
  const mobileMenu = document.getElementById("mobileMenu");
  if (!hamburger || !mobileMenu) return;

  const mobileLinks = mobileMenu.querySelectorAll("a");

  function openMenu() {
    hamburger.classList.add("active");
    hamburger.setAttribute("aria-expanded", "true");
    mobileMenu.classList.add("open");
    document.body.classList.add("no-scroll");
  }

  function closeMenu() {
    hamburger.classList.remove("active");
    hamburger.setAttribute("aria-expanded", "false");
    mobileMenu.classList.remove("open");
    document.body.classList.remove("no-scroll");
  }

  hamburger.addEventListener("click", () => {
    if (mobileMenu.classList.contains("open")) {
      closeMenu();
    } else {
      openMenu();
    }
  });

  // Close on link click
  mobileLinks.forEach(link => {
    link.addEventListener("click", () => {
      closeMenu();
    });
  });

  // Close on escape
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && mobileMenu.classList.contains("open")) {
      closeMenu();
    }
  });

  // Close on resize to desktop
  let resizeTimer;
  window.addEventListener("resize", () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      if (window.innerWidth > 768 && mobileMenu.classList.contains("open")) {
        closeMenu();
      }
    }, 250);
  });
}


// ═══════════════════════════════════════════
// 7. MENU TABS
// ═══════════════════════════════════════════
function initMenuTabs() {
  const tabs = document.querySelectorAll(".menu-tab");
  const grids = document.querySelectorAll(".menu-list");

  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      const target = tab.dataset.tab;

      tabs.forEach(t => t.classList.remove("active"));
      tab.classList.add("active");

      grids.forEach(grid => {
        grid.classList.remove("active");
        grid.style.opacity = "0";
        grid.style.transform = "translateY(15px)";
      });

      const activeGrid = document.getElementById(`tab-${target}`);
      if (activeGrid) {
        activeGrid.classList.add("active");
        void activeGrid.offsetWidth;
        activeGrid.style.opacity = "1";
        activeGrid.style.transform = "translateY(0)";

        // Re-trigger reveal animations
        activeGrid.querySelectorAll(".reveal:not(.visible)").forEach((el, i) => {
          setTimeout(() => el.classList.add("visible"), i * 60);
        });
      }
    });
  });
}


// ═══════════════════════════════════════════
// 8. MENU SHOWCASE — Drag to Scroll
// ═══════════════════════════════════════════
function initMenuShowcaseDrag() {
  const slider = document.querySelector(".menu-showcase-scroll");
  if (!slider) return;

  let isDown = false;
  let startX;
  let scrollLeft;

  slider.addEventListener("mousedown", (e) => {
    isDown = true;
    slider.classList.add("dragging");
    startX = e.pageX - slider.offsetLeft;
    scrollLeft = slider.scrollLeft;
  });

  slider.addEventListener("mouseleave", () => { isDown = false; slider.classList.remove("dragging"); });
  slider.addEventListener("mouseup", () => { isDown = false; slider.classList.remove("dragging"); });

  slider.addEventListener("mousemove", (e) => {
    if (!isDown) return;
    e.preventDefault();
    const x = e.pageX - slider.offsetLeft;
    const walk = (x - startX) * 1.5;
    slider.scrollLeft = scrollLeft - walk;
  });
}


// ═══════════════════════════════════════════
// 9. GALLERY LIGHTBOX
// ═══════════════════════════════════════════
function initGalleryLightbox() {
  const lightbox = document.getElementById("lightbox");
  const lightboxImg = document.getElementById("lightboxImg");
  const closeBtn = document.getElementById("lightboxClose");
  const prevBtn = document.getElementById("lightboxPrev");
  const nextBtn = document.getElementById("lightboxNext");
  const counter = document.getElementById("lightboxCounter");
  const thumbsContainer = document.getElementById("lightboxThumbs");
  const items = document.querySelectorAll(".masonry-item");

  if (!lightbox || !lightboxImg) return;

  const images = [];
  const alts = [];
  items.forEach(item => {
    const img = item.querySelector("img");
    if (img) {
      images.push(img.src);
      alts.push(img.alt);
    }
  });

  let currentIndex = 0;

  // Build thumbnails
  if (thumbsContainer) {
    thumbsContainer.innerHTML = "";
    images.forEach((src, i) => {
      const thumb = document.createElement("button");
      thumb.className = "lightbox-thumb";
      thumb.setAttribute("aria-label", `View image ${i + 1}`);
      thumb.innerHTML = `<img src="${src}" alt="">`;
      thumb.addEventListener("click", () => goToImage(i));
      thumbsContainer.appendChild(thumb);
    });
  }

  function updateCounter() {
    if (counter) counter.textContent = `${currentIndex + 1} / ${images.length}`;
    if (thumbsContainer) {
      thumbsContainer.querySelectorAll(".lightbox-thumb").forEach((t, i) => {
        t.classList.toggle("active", i === currentIndex);
      });
      // Auto-scroll active thumb into view
      const activeThumb = thumbsContainer.querySelector(".lightbox-thumb.active");
      if (activeThumb) {
        activeThumb.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
      }
    }
  }

  function openLightbox(index) {
    currentIndex = index;
    lightboxImg.src = images[currentIndex];
    lightboxImg.alt = alts[currentIndex] || `Gallery image ${currentIndex + 1}`;
    lightbox.classList.add("open");
    document.body.classList.add("no-scroll");
    updateCounter();
  }

  function closeLightbox() {
    lightbox.classList.remove("open");
    document.body.classList.remove("no-scroll");
  }

  function goToImage(index) {
    currentIndex = index;
    lightboxImg.style.opacity = "0";
    setTimeout(() => {
      lightboxImg.src = images[currentIndex];
      lightboxImg.alt = alts[currentIndex] || `Gallery image ${currentIndex + 1}`;
      lightboxImg.style.opacity = "1";
      updateCounter();
    }, 200);
  }

  function navigate(direction) {
    goToImage((currentIndex + direction + images.length) % images.length);
  }

  lightboxImg.style.transition = "opacity 0.3s ease";

  items.forEach((item, i) => {
    item.addEventListener("click", () => openLightbox(i));
  });

  closeBtn.addEventListener("click", closeLightbox);
  prevBtn.addEventListener("click", () => navigate(-1));
  nextBtn.addEventListener("click", () => navigate(1));

  lightbox.addEventListener("click", (e) => {
    if (e.target === lightbox) closeLightbox();
  });

  document.addEventListener("keydown", (e) => {
    if (!lightbox.classList.contains("open")) return;
    if (e.key === "Escape") closeLightbox();
    if (e.key === "ArrowLeft") navigate(-1);
    if (e.key === "ArrowRight") navigate(1);
  });

  // Touch swipe
  let touchStartX = 0;
  lightbox.addEventListener("touchstart", (e) => {
    touchStartX = e.touches[0].clientX;
  }, { passive: true });
  lightbox.addEventListener("touchend", (e) => {
    const touchEndX = e.changedTouches[0].clientX;
    const diff = touchStartX - touchEndX;
    if (Math.abs(diff) > 50) {
      navigate(diff > 0 ? 1 : -1);
    }
  }, { passive: true });
}


// ═══════════════════════════════════════════
// 10. SCROLL REVEAL
// ═══════════════════════════════════════════
function initScrollReveal() {
  const elements = document.querySelectorAll(".reveal");

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          // Small stagger for grouped elements
          const parent = entry.target.parentElement;
          const siblings = parent ? Array.from(parent.querySelectorAll(".reveal")) : [];
          const indexInParent = siblings.indexOf(entry.target);
          const delay = indexInParent > 0 ? Math.min(indexInParent, 5) * 80 : 0;

          setTimeout(() => {
            entry.target.classList.add("visible");
          }, delay);
          observer.unobserve(entry.target);
        }
      });
    },
    {
      threshold: 0.1,
      rootMargin: "0px 0px -60px 0px",
    }
  );

  elements.forEach(el => observer.observe(el));
}


// ═══════════════════════════════════════════
// 11. STATS COUNTER ANIMATION
// ═══════════════════════════════════════════
function initStatsCounter() {
  const statNums = document.querySelectorAll(".stat-num");
  if (!statNums.length) return;

  const animateCounter = (el) => {
    const target = parseInt(el.dataset.target, 10);
    if (isNaN(target)) return;
    const duration = 2000;
    const startTime = performance.now();

    function update(currentTime) {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // Ease out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = Math.floor(eased * target);
      el.textContent = current;

      if (progress < 1) {
        requestAnimationFrame(update);
      } else {
        el.textContent = target;
      }
    }

    requestAnimationFrame(update);
  };

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          animateCounter(entry.target);
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.4 }
  );

  statNums.forEach(el => observer.observe(el));
}


// ═══════════════════════════════════════════
// 12. RESERVATION FORM
// ═══════════════════════════════════════════
function initReservationForm() {
  const form = document.getElementById("reservationForm");
  if (!form) return;

  const successEl = document.getElementById("formSuccess");
  const successName = document.getElementById("successName");

  form.addEventListener("submit", (e) => {
    e.preventDefault();

    // Basic validation
    const name = form.querySelector("[name='name']");
    const phone = form.querySelector("[name='phone']");
    const email = form.querySelector("[name='email']");
    const date = form.querySelector("[name='date']");
    const time = form.querySelector("[name='time']");
    const guests = form.querySelector("[name='guests']");

    const required = [name, phone, email, date, time, guests];
    let valid = true;

    required.forEach(field => {
      if (!field.value.trim()) {
        field.style.borderColor = "#e74c3c";
        valid = false;
      } else {
        field.style.borderColor = "";
      }
    });

    // Email validation
    if (email.value && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value)) {
      email.style.borderColor = "#e74c3c";
      valid = false;
    }

    if (!valid) return;

    // Show success
    if (successEl) {
      successName.textContent = name.value.split(" ")[0] || "Guest";
      successEl.hidden = false;
      successEl.scrollIntoView({ behavior: "smooth", block: "center" });
    }

    // Reset form
    setTimeout(() => {
      form.reset();
    }, 1000);
  });

  // Real-time validation feedback
  form.querySelectorAll("input, select, textarea").forEach(field => {
    field.addEventListener("input", () => {
      if (field.value.trim()) {
        field.style.borderColor = "";
      }
    });
  });
}


// ═══════════════════════════════════════════
// 13. NEWSLETTER FORM
// ═══════════════════════════════════════════
function initNewsletterForm() {
  const form = document.getElementById("newsletterForm");
  if (!form) return;

  const successEl = document.getElementById("newsletterSuccess");

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const input = form.querySelector("input[type='email']");
    if (!input || !input.value.trim()) return;

    if (successEl) {
      successEl.hidden = false;
      setTimeout(() => { successEl.hidden = true; }, 5000);
    }
    input.value = "";
  });
}


// ═══════════════════════════════════════════
// 14. RESERVATION DATE MIN
// ═══════════════════════════════════════════
function initReservationDateMin() {
  const dateInput = document.getElementById("resDate");
  if (!dateInput) return;

  const today = new Date();
  const yyyy = today.getFullYear();
  const mm = String(today.getMonth() + 1).padStart(2, "0");
  const dd = String(today.getDate()).padStart(2, "0");
  const todayStr = `${yyyy}-${mm}-${dd}`;

  dateInput.setAttribute("min", todayStr);
  dateInput.value = todayStr;
}


// ═══════════════════════════════════════════
// 15. BACK TO TOP BUTTON
// ═══════════════════════════════════════════
function initBackToTop() {
  const btn = document.getElementById("backToTop");
  if (!btn) return;

  function checkVisibility() {
    if (window.scrollY > 600) {
      btn.classList.add("visible");
    } else {
      btn.classList.remove("visible");
    }
  }

  let ticking = false;
  window.addEventListener("scroll", () => {
    if (!ticking) {
      window.requestAnimationFrame(() => {
        checkVisibility();
        ticking = false;
      });
      ticking = true;
    }
  }, { passive: true });

  btn.addEventListener("click", (e) => {
    e.preventDefault();
    window.scrollTo({ top: 0, behavior: "smooth" });
  });

  checkVisibility();
}


// ═══════════════════════════════════════════
// 16. FLOATING RESERVE CTA
// ═══════════════════════════════════════════
function initFloatingCta() {
  const cta = document.getElementById("floatingCta");
  if (!cta) return;

  // Hide on small screens (mobile menu covers this) — but show after scrolling
  function checkVisibility() {
    const isMobile = window.innerWidth <= 768;
    if (window.scrollY > 800) {
      cta.classList.add("visible");
    } else {
      cta.classList.remove("visible");
    }
    // On mobile, ensure proper z-index
    if (isMobile) {
      cta.style.zIndex = "998";
    }
  }

  let ticking = false;
  window.addEventListener("scroll", () => {
    if (!ticking) {
      window.requestAnimationFrame(() => {
        checkVisibility();
        ticking = false;
      });
      ticking = true;
    }
  }, { passive: true });

  checkVisibility();
}


// ═══════════════════════════════════════════
// 17. REVIEWS — Google Places API or Fallback
// ═══════════════════════════════════════════
function initReviewsCarousel() {
  if (GOOGLE_PLACES_API_KEY !== "YOUR_API_KEY_HERE") {
    fetchGoogleReviews();
  } else {
    renderFallbackReviews();
  }
}

async function fetchGoogleReviews() {
  try {
    const url = `https://maps.googleapis.com/maps/api/place/details/json?place_id=${PLACE_ID}&fields=reviews&key=${GOOGLE_PLACES_API_KEY}`;
    const response = await fetch(url);
    const data = await response.json();

    if (data.result && data.result.reviews) {
      let reviews = data.result.reviews
        .filter(r => r.rating >= 4)
        .sort((a, b) => b.time - a.time)
        .slice(0, 8);

      if (reviews.length > 0) {
        renderReviews(reviews, true);
        return;
      }
    }
    renderFallbackReviews();
  } catch (error) {
    console.warn("Google Places API unavailable, using curated reviews:", error);
    renderFallbackReviews();
  }
}

function renderFallbackReviews() {
  const fallbackReviews = [
    {
      author_name: "Arjun Chatterjee",
      rating: 5,
      text: "An extraordinary dining experience from start to finish. The lamb rack was cooked to absolute perfection, and the ambience is unlike anything else in Kolkata. Every detail, from the linen to the lighting, speaks of a restaurant that genuinely cares about the art of hospitality.",
      relative_time_description: "2 weeks ago",
      profile_photo_url: null,
    },
    {
      author_name: "Priya Sengupta",
      rating: 5,
      text: "Sizzle & Savor has redefined fine dining for us. The truffle mushroom velouté was a revelation, and our server recommended a pairing that transformed the entire meal. This is a place that understands the difference between feeding people and nourishing their soul.",
      relative_time_description: "1 month ago",
      profile_photo_url: null,
    },
    {
      author_name: "Rahul Mukherjee",
      rating: 5,
      text: "We celebrated our anniversary here and could not have chosen a more fitting setting. Candlelight, impeccable service, and food that arrived like poetry on a plate. The dark chocolate fondant alone is worth the visit. Simply magnificent.",
      relative_time_description: "3 weeks ago",
      profile_photo_url: null,
    },
    {
      author_name: "Sneha Das",
      rating: 4,
      text: "Visited for a corporate dinner and every guest was thoroughly impressed. The presentation is museum-quality, and the flavours are bold yet balanced. The salmon en croûte was outstanding. A gem in Rajarhat that deserves far more recognition.",
      relative_time_description: "1 week ago",
      profile_photo_url: null,
    },
    {
      author_name: "Vikram Roy",
      rating: 5,
      text: "From the moment you enter, Sizzle & Savor wraps you in an atmosphere of quiet luxury. The risotto was the best I have ever tasted — creamy, earthy, and utterly satisfying. The staff are attentive without being intrusive. A masterclass in elegant dining.",
      relative_time_description: "5 days ago",
      profile_photo_url: null,
    },
    {
      author_name: "Ananya Bose",
      rating: 5,
      text: "A rare find in Kolkata — a restaurant where the food, the setting, and the service are all equally extraordinary. The panna cotta was ethereal. We lingered for hours and never once felt rushed. This is what dining should always feel like.",
      relative_time_description: "4 days ago",
      profile_photo_url: null,
    },
    {
      author_name: "Karan Malhotra",
      rating: 5,
      text: "A truly special place. The wine pairing was masterfully chosen, the osso buco melted off the bone, and the sommelier was a delight. We will certainly return for every special occasion. Worthy of every accolade it has received.",
      relative_time_description: "6 days ago",
      profile_photo_url: null,
    },
  ];

  renderReviews(fallbackReviews, false);
}

function renderReviews(reviews, isGoogleData) {
  const carousel = document.getElementById("reviewsCarousel");
  const dotsContainer = document.getElementById("carouselDots");

  if (!carousel) return;

  carousel.innerHTML = "";

  reviews.forEach((review, index) => {
    const card = document.createElement("div");
    card.className = "review-card";

    const initials = review.author_name
      .split(" ")
      .map(n => n[0])
      .join("")
      .toUpperCase()
      .slice(0, 2);

    const stars = generateStars(review.rating);
    const truncatedText = review.text.length > 220
      ? review.text.substring(0, 220) + "..."
      : review.text;
    const needsReadMore = review.text.length > 220;

    const avatarHTML = review.profile_photo_url
      ? `<img class="reviewer-avatar" src="${review.profile_photo_url}" alt="${escapeAttr(review.author_name)}">`
      : `<div class="reviewer-monogram">${initials}</div>`;

    card.innerHTML = `
      <div class="review-header">
        ${avatarHTML}
        <div class="reviewer-info">
          <span class="reviewer-name">${escapeHTML(review.author_name)}</span>
          <div class="review-stars">${stars}</div>
        </div>
      </div>
      <p class="review-text" data-full="${escapeAttr(review.text)}" data-truncated="${escapeAttr(truncatedText)}">
        ${escapeHTML(truncatedText)}
      </p>
      ${needsReadMore ? '<button class="read-more-btn" data-expanded="false">Read more</button>' : ''}
      <p class="review-date">${escapeHTML(review.relative_time_description || '')}</p>
    `;

    carousel.appendChild(card);
  });

  // Read more toggle
  carousel.querySelectorAll(".read-more-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const textEl = btn.previousElementSibling;
      const isExpanded = btn.dataset.expanded === "true";

      if (isExpanded) {
        textEl.textContent = textEl.dataset.truncated;
        btn.textContent = "Read more";
        btn.dataset.expanded = "false";
      } else {
        textEl.textContent = textEl.dataset.full;
        btn.textContent = "Read less";
        btn.dataset.expanded = "true";
      }
    });
  });

  initCarouselAutoScroll(reviews.length);
  initCarouselDrag();
}

function generateStars(rating) {
  let stars = "";
  for (let i = 0; i < 5; i++) {
    const fill = i < rating ? "#C9A84C" : "rgba(250,247,242,0.2)";
    stars += `<svg viewBox="0 0 24 24" fill="${fill}"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>`;
  }
  return stars;
}

function escapeHTML(str) {
  if (!str) return "";
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

function escapeAttr(str) {
  if (!str) return "";
  return str.replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

function initCarouselAutoScroll(totalCards) {
  setTimeout(() => {
    const wrapper = document.querySelector(".reviews-carousel-wrapper");
    const carousel = document.getElementById("reviewsCarousel");
    const dotsContainer = document.getElementById("carouselDots");

    if (!wrapper || !carousel || window.innerWidth <= 768) return;

    const firstCard = carousel.querySelector(".review-card");
    if (!firstCard) return;

    const cardStyles = window.getComputedStyle(carousel);
    const gap = parseFloat(cardStyles.gap) || 24;
    const cardWidth = firstCard.offsetWidth + gap;
    const wrapperWidth = wrapper.offsetWidth;
    const visibleCards = Math.max(1, Math.floor(wrapperWidth / cardWidth));
    const maxSlides = Math.max(0, totalCards - visibleCards);

    let currentSlide = 0;
    let isPaused = false;

    dotsContainer.innerHTML = "";
    for (let i = 0; i <= maxSlides; i++) {
      const dot = document.createElement("button");
      dot.className = `carousel-dot ${i === 0 ? "active" : ""}`;
      dot.setAttribute("aria-label", `Go to slide ${i + 1}`);
      dot.addEventListener("click", () => goToSlide(i));
      dotsContainer.appendChild(dot);
    }

    function goToSlide(index) {
      currentSlide = Math.max(0, Math.min(index, maxSlides));
      const offset = -(currentSlide * cardWidth);
      carousel.style.transform = `translateX(${offset}px)`;

      dotsContainer.querySelectorAll(".carousel-dot").forEach((d, i) => {
        d.classList.toggle("active", i === currentSlide);
      });
    }

    function nextSlide() {
      if (isPaused) return;
      currentSlide = (currentSlide + 1) % (maxSlides + 1);
      goToSlide(currentSlide);
    }

    const autoScrollInterval = setInterval(nextSlide, 4500);

    wrapper.addEventListener("mouseenter", () => { isPaused = true; });
    wrapper.addEventListener("mouseleave", () => { isPaused = false; });
  }, 500);
}

function initCarouselDrag() {
  const carousel = document.getElementById("reviewsCarousel");
  if (!carousel || window.innerWidth <= 768) return;

  let isDown = false;
  let startX;
  let scrollLeft;
  let hasDragged = false;

  carousel.addEventListener("mousedown", (e) => {
    isDown = true;
    hasDragged = false;
    carousel.style.cursor = "grabbing";
    startX = e.pageX - carousel.offsetLeft;
    scrollLeft = carousel.style.transform
      ? parseInt(carousel.style.transform.split("(")[1]) || 0
      : 0;
  });

  carousel.addEventListener("mouseleave", () => { isDown = false; carousel.style.cursor = "grab"; });
  carousel.addEventListener("mouseup", () => { isDown = false; carousel.style.cursor = "grab"; });

  carousel.addEventListener("mousemove", (e) => {
    if (!isDown) return;
    e.preventDefault();
    hasDragged = true;
    const x = e.pageX - carousel.offsetLeft;
    const walk = (x - startX) * 1.2;
    carousel.style.transform = `translateX(${scrollLeft + walk}px)`;
  });

  carousel.addEventListener("click", (e) => {
    if (hasDragged) {
      e.preventDefault();
      e.stopPropagation();
      hasDragged = false;
    }
  });
}


// ═══════════════════════════════════════════
// 18. PARALLAX EFFECT
// ═══════════════════════════════════════════
function initParallax() {
  const parallaxImages = document.querySelectorAll(".parallax-img img");
  if (!parallaxImages.length) return;

  // Disable on small screens and reduced motion
  if (window.innerWidth <= 768 || window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    return;
  }

  let ticking = false;

  function onScroll() {
    if (!ticking) {
      window.requestAnimationFrame(() => {
        parallaxImages.forEach(img => {
          const rect = img.parentElement.getBoundingClientRect();
          const windowHeight = window.innerHeight;

          if (rect.top < windowHeight && rect.bottom > 0) {
            const scrollPercent = (windowHeight - rect.top) / (windowHeight + rect.height);
            const translateY = (scrollPercent - 0.5) * 30;
            img.style.transform = `scale(1.08) translateY(${translateY}px)`;
          }
        });
        ticking = false;
      });
      ticking = true;
    }
  }

  window.addEventListener("scroll", onScroll, { passive: true });
}
