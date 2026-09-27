/**
 * SRMS Animations — Main Loader
 * Coordinates ScrollTrigger, Lenis momentum scroll, and module triggers.
 */
document.addEventListener('DOMContentLoaded', function () {
  'use strict';

  if (typeof gsap === 'undefined') return;

  // 1. Register ScrollTrigger
  if (typeof ScrollTrigger !== 'undefined') {
    gsap.registerPlugin(ScrollTrigger);
  }

  // 2. Lenis Momentum scroll setup
  const useLenis = window.SRMSPerf ? window.SRMSPerf.useLenis : !window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (typeof Lenis !== 'undefined' && useLenis) {
    const lenis = new Lenis({
      lerp: 0.08,
      smoothWheel: true,
      touchMultiplier: 1.5
    });

    // Seed global scroll state for coupling with bg-video-scrub.js if loaded
    window.__srmsScrollY = window.scrollY;
    window.__srmsScrollMax = Math.max(1, document.documentElement.scrollHeight - window.innerHeight);

    lenis.on('scroll', function (e) {
      window.__srmsScrollY = e.scroll;
      window.__srmsScrollMax = Math.max(1, e.limit);
      if (typeof ScrollTrigger !== 'undefined') {
        ScrollTrigger.update();
      }
    });

    if (typeof ScrollTrigger !== 'undefined') {
      gsap.ticker.add(function (time) {
        lenis.raf(time * 1000);
      });
      gsap.ticker.lagSmoothing(0);
    } else {
      const raf = function (time) {
        lenis.raf(time);
        requestAnimationFrame(raf);
      };
      requestAnimationFrame(raf);
    }
  }

  // 3. Initialize all modules in sequence
  if (window.SRMSAnimations) {
    if (window.SRMSAnimations.transitions) window.SRMSAnimations.transitions.init();
    if (window.SRMSAnimations.reveal)      window.SRMSAnimations.reveal.init();
    if (window.SRMSAnimations.counters)    window.SRMSAnimations.counters.init();
    if (window.SRMSAnimations.micro)       window.SRMSAnimations.micro.init();
  }
});
