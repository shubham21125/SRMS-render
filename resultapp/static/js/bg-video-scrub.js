/* ─────────────────────────────────────────────────────────────
   SRMS — Background Video Scrub & Ambient Playback Controller

   MOBILE & REDUCED-MOTION:
   ┌──────────────────────────────────────────────────────────┐
   │  Disables scroll-scrub seeking entirely to prevent       │
   │  hardware decoder stall and frame drops. Runs smooth     │
   │  ambient looped playback locked at 0.85× playbackRate    │
   │  with a silky CSS fade-in.                               │
   └──────────────────────────────────────────────────────────┘

   DESKTOP HOME PAGE:
   ┌──────────────────────────────────────────────────────────┐
   │  Monotonic LERP scroll-scrub seeking with decoder guard: │
   │  • Checks !video.seeking & readyState >= 2 before seek   │
   │  • Dynamically toggles will-change: transform on scroll  │
   │  • Minimum seek delta = 0.04s (prevents decoder jam)     │
   └──────────────────────────────────────────────────────────┘
   ───────────────────────────────────────────────────────────── */

(function () {
  'use strict';

  const video = document.getElementById('site-bg-video');
  if (!video) return;

  const isReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const isMobile = (window.SRMSPerf && window.SRMSPerf.isMobile) ||
                   window.innerWidth <= 768 ||
                   ('ontouchstart' in window && window.innerWidth <= 1024);

  const isHomePage = document.body.classList.contains('hero-page');

  // GPU compositing hint helper
  video.style.transform = 'translate3d(0, 0, 0)';
  video.style.backfaceVisibility = 'hidden';

  /* ══════════════════════════════════════════════════════════════
     AMBIENT PLAYBACK (Mobile, Reduced-Motion, or Non-Home Pages)
     Completely disables scroll-scrub seeking to eliminate decoder stalls.
     ══════════════════════════════════════════════════════════════ */
  if (!isHomePage || isMobile || isReduced) {
    video.loop = true;
    video.muted = true;
    video.playsInline = true;
    video.setAttribute('playsinline', '');
    video.playbackRate = 0.85; // Relaxed ambient playback
    video.style.willChange = 'auto';

    // Silky CSS fade-in
    video.style.opacity = '0';
    video.style.transition = 'opacity 0.6s ease';

    const onCanPlay = () => {
      video.style.opacity = '1';
      video.play().catch(() => {});
    };

    if (video.readyState >= 2) {
      onCanPlay();
    } else {
      ['loadeddata', 'canplay', 'canplaythrough'].forEach(e =>
        video.addEventListener(e, onCanPlay, { once: true })
      );
    }

    try { video.play().catch(() => {}); } catch (_) {}
    return; // Complete exit — no scroll listener, no RAF loop, no scrubbing
  }

  /* ══════════════════════════════════════════════════════════════
     DESKTOP HOME PAGE — Smooth Scroll-Scrubbed Playback
     ══════════════════════════════════════════════════════════════ */
  video.pause();
  video.removeAttribute('autoplay');
  video.loop = false;
  video.muted = true;
  video.playsInline = true;
  video.setAttribute('playsinline', '');

  let duration = 0;
  let ready = false;
  let rawTarget = 0;
  let currentTarget = 0;
  let lastSeekTime = -1;
  const MIN_SEEK_DT = 0.04; // Minimum 40ms delta between seeks

  // Dynamic will-change management to conserve GPU memory when idle
  let scrollIdleTimer = null;
  function markScrollActive() {
    video.style.willChange = 'transform';
    if (scrollIdleTimer) clearTimeout(scrollIdleTimer);
    scrollIdleTimer = setTimeout(() => {
      video.style.willChange = 'auto';
    }, 250);
  }

  window.addEventListener('scroll', markScrollActive, { passive: true });

  function markReady() {
    if (ready) return;
    if (!video.duration || !isFinite(video.duration)) return;
    duration = video.duration;
    currentTarget = scrollProgress() * duration;
    rawTarget = currentTarget;
    ready = true;
  }

  ['loadedmetadata', 'durationchange', 'loadeddata', 'canplay'].forEach(e =>
    video.addEventListener(e, markReady)
  );
  markReady();

  // Polling fallback
  let polls = 0;
  const poll = setInterval(() => {
    markReady();
    if (ready || ++polls > 40) clearInterval(poll);
  }, 200);

  function scrollProgress() {
    if (typeof window.__srmsScrollY === 'number' && typeof window.__srmsScrollMax === 'number' && window.__srmsScrollMax > 0) {
      return Math.min(1, Math.max(0, window.__srmsScrollY / window.__srmsScrollMax));
    }
    const doc = document.documentElement;
    const maxScroll = Math.max(1, doc.scrollHeight - doc.clientHeight);
    const top = window.scrollY || doc.scrollTop || document.body.scrollTop || 0;
    return Math.min(1, Math.max(0, top / maxScroll));
  }

  function tick() {
    requestAnimationFrame(tick);
    if (!ready) return;

    rawTarget = scrollProgress() * duration;
    const LERP_FACTOR = 0.08;
    currentTarget += (rawTarget - currentTarget) * LERP_FACTOR;

    const clamped = Math.min(Math.max(currentTarget, 0), duration - 0.05);

    // Seek only when delta >= 0.04s, video is ready, and browser is NOT currently seeking
    if (Math.abs(clamped - lastSeekTime) >= MIN_SEEK_DT) {
      if (video.readyState >= 2 && !video.seeking) {
        video.currentTime = clamped;
        lastSeekTime = clamped;
      }
    }
  }

  requestAnimationFrame(tick);

  // bfcache restore
  window.addEventListener('pageshow', (e) => {
    if (e.persisted) {
      video.pause();
      const t = scrollProgress() * duration;
      currentTarget = t;
      rawTarget = t;
      lastSeekTime = -1;
      markReady();
    }
  });

  // Prefetch first frame
  video.addEventListener('loadeddata', () => {
    if (video.currentTime === 0) {
      try { video.currentTime = 0.001; } catch (_) {}
    }
  }, { once: true });

})();
