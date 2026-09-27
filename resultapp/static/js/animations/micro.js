/**
 * SRMS Animations — Micro Interactions Module
 * Handles hover lifts, button presses, focus glow effects, and alerts.
 */
(function () {
  'use strict';

  function init() {
    const isReduced = (window.SRMSPerf && window.SRMSPerf.reducedMotion) || 
                      (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);

    if (isReduced) return;
    if (typeof gsap === 'undefined') return;

    // 1. Button / Nav link hover scales
    document.querySelectorAll('.btn, .sidebar-nav a, .nav-link').forEach(function (btn) {
      btn.addEventListener('mouseenter', function () {
        gsap.to(btn, { scale: 1.015, duration: 0.18, ease: 'power2.out' });
      });
      btn.addEventListener('mouseleave', function () {
        gsap.to(btn, { scale: 1, duration: 0.22, ease: 'power2.out' });
      });
      btn.addEventListener('mousedown', function () {
        gsap.to(btn, { scale: 0.97, duration: 0.08 });
      });
      btn.addEventListener('mouseup', function () {
        gsap.to(btn, { scale: 1.015, duration: 0.08 });
      });
    });

    // 2. Stat card / Standard card lift
    if (!(window.SRMSPerf && window.SRMSPerf.isMobile)) {
      document.querySelectorAll('.stat-card, .card').forEach(function (card) {
        card.addEventListener('mouseenter', function () {
          gsap.to(card, { y: -4, duration: 0.22, ease: 'power2.out' });
        });
        card.addEventListener('mouseleave', function () {
          gsap.to(card, { y: 0, duration: 0.3, ease: 'power2.out' });
        });
      });
    }

    // 3. Form input focus glow (box-shadow)
    const inputs = document.querySelectorAll(
      'main .form-control, main .form-select, main textarea'
    );
    inputs.forEach(function (inp) {
      inp.addEventListener('focus', function () {
        gsap.to(inp, {
          boxShadow: '0 0 0 3px rgba(245, 197, 24, 0.18)',
          duration: 0.18
        });
      });
      inp.addEventListener('blur', function () {
        gsap.to(inp, {
          boxShadow: 'none',
          duration: 0.2
        });
      });
    });

    // 4. Message Alert entry slide-in
    document.querySelectorAll('main .alert').forEach(function (al) {
      gsap.fromTo(al,
        { opacity: 0, x: 24, scale: 0.98 },
        { opacity: 1, x: 0, scale: 1, duration: 0.45, ease: 'power3.out' }
      );
    });
  }

  window.SRMSAnimations = window.SRMSAnimations || {};
  window.SRMSAnimations.micro = { init: init };
})();
