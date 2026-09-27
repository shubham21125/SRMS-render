/**
 * SRMS Animations — Counters Module
 * Handles stat card number count-up animations for both data-count and data-target metrics.
 */
(function () {
  'use strict';

  function init() {
    const counters = document.querySelectorAll('.stat-card [data-count], .counter[data-target]');
    if (!counters.length) return;

    const isReduced = (window.SRMSPerf && window.SRMSPerf.reducedMotion) || 
                      (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);

    if (isReduced) {
      // Instant reduced motion fallback: snap to final value immediately
      counters.forEach(function (el) {
        const target = parseFloat(el.getAttribute('data-count') || el.getAttribute('data-target')) || 0;
        const isFloat = el.dataset.float === 'true' || target % 1 !== 0;
        el.textContent = target.toFixed(isFloat ? 1 : 0);
      });
      return;
    }

    if (typeof gsap === 'undefined' || typeof ScrollTrigger === 'undefined') return;

    counters.forEach(function (el) {
      const target = parseFloat(el.getAttribute('data-count') || el.getAttribute('data-target')) || 0;
      if (isNaN(target)) return;

      const isFloat = el.dataset.float === 'true' || target % 1 !== 0;

      // Reset text content to 0 initially
      el.textContent = '0';

      // Animate from 0 to target value on scroll view entry
      gsap.fromTo({ val: 0 }, { val: target }, {
        duration: 1.3,
        ease: 'power2.out',
        delay: 0.45,
        scrollTrigger: {
          trigger: el,
          start: 'top 95%',
          toggleActions: 'play none none none'
        },
        onUpdate: function () {
          el.textContent = this.targets()[0].val.toFixed(isFloat ? 1 : 0);
        },
        onComplete: function () {
          el.textContent = target;
        }
      });
    });
  }

  window.SRMSAnimations = window.SRMSAnimations || {};
  window.SRMSAnimations.counters = { init: init };
})();
