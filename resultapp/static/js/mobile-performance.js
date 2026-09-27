/* ============================================================
   SRMS MOBILE PERFORMANCE LAYER
   Runs first, synchronously, before any other page script.
   Detects phones / low-power devices and exposes window.SRMSPerf
   so the rest of the page (particles, Lenis, GSAP) can scale
   itself down automatically. Also fixes the two biggest sources
   of mobile lag in this template set:
     1. A full-screen autoplaying background video decoding on
        every frame on a phone GPU.
     2. The sidebar stacking full height above page content
        instead of behaving like a drawer.
   ============================================================ */
(function () {
  'use strict';

  var widthMq  = window.matchMedia('(max-width: 768px)');
  var coarseMq = window.matchMedia('(pointer: coarse)');
  var reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  var conn = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
  var saveData  = !!(conn && conn.saveData);
  var slowConn  = !!(conn && /(^|-)2g/.test(conn.effectiveType || ''));
  var lowMemory = !!(navigator.deviceMemory && navigator.deviceMemory <= 4);
  var lowCores  = !!(navigator.hardwareConcurrency && navigator.hardwareConcurrency <= 4);

  var isTouch  = ('ontouchstart' in window) || navigator.maxTouchPoints > 0;
  var isMobile = widthMq.matches || (isTouch && coarseMq.matches);
  var isLite   = isMobile || saveData || slowConn || (lowMemory && lowCores);

  function applyClasses() {
    document.documentElement.classList.toggle('srms-mobile', isMobile);
    document.documentElement.classList.toggle('srms-lite', isLite);
  }
  applyClasses();

  window.SRMSPerf = {
    isMobile: isMobile,
    isLite: isLite,
    reducedMotion: reducedMotion,
    // Lenis (momentum scroll) fights native touch scrolling and is a
    // common source of "laggy" feeling scroll on phones — skip it there.
    useLenis: !isMobile && !reducedMotion,
    // The background video stays on mobile — it's only dropped for
    // people who've explicitly asked for less motion/data (OS-level
    // reduced-motion, or a save-data / very slow connection).
    skipVideo: reducedMotion || saveData || slowConn,
    // How many decorative particles to spawn — 0 on phones/low-end.
    particleCount: function (desktopCount) {
      if (reducedMotion || isLite) return 0;
      return desktopCount;
    },
    // Lighter GSAP stagger timings on mobile so long tables/forms
    // don't queue up dozens of animation frames at once.
    stagger: function (desktopStagger) {
      return isLite ? 0 : desktopStagger;
    },
    duration: function (desktopDuration) {
      return isLite ? Math.min(desktopDuration, 0.25) : desktopDuration;
    },
    // rAF-throttled event handler wrapper for scroll/resize listeners.
    rafThrottle: function (fn) {
      var ticking = false;
      return function () {
        var ctx = this, args = arguments;
        if (!ticking) {
          ticking = true;
          requestAnimationFrame(function () {
            fn.apply(ctx, args);
            ticking = false;
          });
        }
      };
    }
  };

  // ── Background video: kept everywhere (including mobile), but
  //    made cheap to run instead of being removed. ────────────────
  //   - Dropped only for save-data/slow-connection/reduced-motion,
  //     where playing a video at all would be the wrong call.
  //   - Paused whenever the tab/app isn't visible, so it doesn't
  //     burn battery and CPU in the background — this is the single
  //     biggest real-world win for a fixed, always-on video loop.
  //   - Left fully alone otherwise: no scroll-tied seeking, no
  //     resolution swapping, no extra JS touching it per frame.
  function setupBackgroundVideo() {
    var v = document.getElementById('site-bg-video');
    if (!v) return;

    if (window.SRMSPerf.skipVideo) {
      try { v.pause(); } catch (e) {}
      v.removeAttribute('autoplay');
      v.querySelectorAll('source').forEach(function (s) { s.removeAttribute('src'); });
      v.removeAttribute('src');
      try { v.load(); } catch (e) {}
      v.style.display = 'none';
      return;
    }

    document.addEventListener('visibilitychange', function () {
      if (document.hidden) {
        try { v.pause(); } catch (e) {}
      } else {
        v.play().catch(function () {});
      }
    });
  }

  // ── Auto-wrap any bare <table> so it scrolls horizontally
  //    instead of breaking the page layout on narrow screens ──
  function wrapTables() {
    document.querySelectorAll('table').forEach(function (t) {
      if (t.closest('.table-responsive, .table-responsive-auto')) return;
      var wrap = document.createElement('div');
      wrap.className = 'table-responsive-auto';
      t.parentNode.insertBefore(wrap, t);
      wrap.appendChild(t);
    });
  }

  // ── Turn the admin/parent sidebar into a proper off-canvas
  //    drawer on mobile instead of a full-width stacked block ──
  function setupSidebarDrawer() {
    var sidebarWrapper = document.querySelector('.sidebar-wrapper');
    var navbarInner = document.querySelector('.navbar-public .container, .navbar-public .container-fluid');
    if (!sidebarWrapper || !navbarInner) return;

    var backdrop = document.createElement('div');
    backdrop.className = 'sidebar-backdrop';
    document.body.appendChild(backdrop);

    var toggle = document.createElement('button');
    toggle.type = 'button';
    toggle.className = 'sidebar-mobile-toggle';
    toggle.setAttribute('aria-label', 'Toggle menu');
    toggle.setAttribute('aria-expanded', 'false');
    toggle.innerHTML = '<i class="fas fa-bars"></i>';

    var brand = navbarInner.querySelector('.navbar-brand');
    if (brand && brand.parentNode === navbarInner) {
      navbarInner.insertBefore(toggle, brand);
    } else {
      navbarInner.insertBefore(toggle, navbarInner.firstChild);
    }

    function closeDrawer() {
      sidebarWrapper.classList.remove('sidebar-open');
      backdrop.classList.remove('show');
      toggle.setAttribute('aria-expanded', 'false');
    }
    function openDrawer() {
      sidebarWrapper.classList.add('sidebar-open');
      backdrop.classList.add('show');
      toggle.setAttribute('aria-expanded', 'true');
    }

    toggle.addEventListener('click', function () {
      sidebarWrapper.classList.contains('sidebar-open') ? closeDrawer() : openDrawer();
    });
    backdrop.addEventListener('click', closeDrawer);

    // Close automatically if the viewport grows back to desktop size.
    window.addEventListener('resize', window.SRMSPerf.rafThrottle(function () {
      if (!widthMq.matches) closeDrawer();
    }), { passive: true });
  }

  function init() {
    setupBackgroundVideo();
    wrapTables();
    setupSidebarDrawer();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Keep classes in sync on rotation / resize across the breakpoint.
  var onMqChange = function () {
    isMobile = widthMq.matches || (isTouch && coarseMq.matches);
    isLite = isMobile || saveData || slowConn || (lowMemory && lowCores);
    window.SRMSPerf.isMobile = isMobile;
    window.SRMSPerf.isLite = isLite;
    window.SRMSPerf.useLenis = !isMobile && !reducedMotion;
    applyClasses();
  };
  if (widthMq.addEventListener) widthMq.addEventListener('change', onMqChange);
  else widthMq.addListener(onMqChange);
})();
