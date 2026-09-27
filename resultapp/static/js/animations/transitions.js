/**
 * SRMS Animations — Page Transitions Module
 * Handles MPA page-enter/leave animations for smooth navigation.
 */
(function () {
  'use strict';

  function init() {
    const mainContent = document.querySelector('main') || document.body;

    const isReduced = (window.SRMSPerf && window.SRMSPerf.reducedMotion) || 
                      (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);

    if (isReduced) {
      if (mainContent) mainContent.style.opacity = '1';
      return;
    }

    if (typeof gsap === 'undefined') return;

    const lite = window.SRMSPerf && window.SRMSPerf.isLite;

    // 1. Page-enter fade and slide-up
    gsap.fromTo(mainContent,
      { opacity: 0, y: lite ? 0 : 18 },
      {
        opacity: 1,
        y: 0,
        duration: lite ? 0.2 : 0.48,
        delay: 0.15,
        ease: 'power3.out'
      }
    );

    // 2. Intercept local link clicks for page-leave exit fade
    document.addEventListener('click', function (e) {
      const link = e.target.closest('a');
      if (!link) return;

      const url = link.getAttribute('href');
      const target = link.getAttribute('target');

      // Ignore if empty, opens in new tab, anchor/JS link, or external
      if (!url ||
          url.startsWith('#') ||
          url.startsWith('javascript:') ||
          target === '_blank' ||
          link.hostname !== window.location.hostname ||
          e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) {
        return;
      }

      // Ignore standard downloads, file exports, or logout links that redirect/terminate sessions
      if (url.includes('logout') || url.includes('export') || url.includes('download') || url.includes('csv')) {
        return;
      }

      e.preventDefault();

      gsap.to(mainContent, {
        opacity: 0,
        y: lite ? 0 : -14,
        duration: lite ? 0.15 : 0.3,
        ease: 'power2.in',
        onComplete: function () {
          window.location.href = url;
        }
      });
    });
  }

  window.SRMSAnimations = window.SRMSAnimations || {};
  window.SRMSAnimations.transitions = { init: init };
})();
