/**
 * SRMS Animations — Reveal Module
 * Handles scroll-driven and load-time fade/slide-in reveals.
 */
(function () {
  'use strict';

  function init() {
    const isReduced = (window.SRMSPerf && window.SRMSPerf.reducedMotion) || 
                      (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);

    if (isReduced) {
      // Instant reduced motion fallback: clear styles and set opacity to 1 immediately
      document.querySelectorAll('.gsap-up, .gsap-scale, .gsap-left, tbody tr').forEach(function (el) {
        el.style.opacity = '1';
        el.style.transform = 'none';
        el.style.scale = '1';
      });
      return;
    }

    if (typeof gsap === 'undefined' || typeof ScrollTrigger === 'undefined') return;

    const lite = window.SRMSPerf && window.SRMSPerf.isLite;

    // 1. Scroll-reveal up (.gsap-up)
    gsap.utils.toArray('.gsap-up').forEach(function (el, i) {
      gsap.fromTo(el,
        { opacity: 0, y: lite ? 10 : 38 },
        {
          opacity: 1,
          y: 0,
          duration: lite ? 0.35 : 0.65,
          delay: lite ? 0 : i * 0.08,
          ease: 'power3.out',
          scrollTrigger: {
            trigger: el,
            start: 'top 90%',
            toggleActions: 'play none none none'
          }
        }
      );
    });

    // 2. Scroll-reveal scale (.gsap-scale)
    gsap.utils.toArray('.gsap-scale').forEach(function (el, i) {
      gsap.fromTo(el,
        { opacity: 0, scale: 0.9 },
        {
          opacity: 1,
          scale: 1,
          duration: lite ? 0.35 : 0.55,
          delay: lite ? 0 : i * 0.07,
          ease: lite ? 'power2.out' : 'back.out(1.7)',
          scrollTrigger: {
            trigger: el,
            start: 'top 90%',
            toggleActions: 'play none none none'
          }
        }
      );
    });

    // 3. Scroll-reveal left (.gsap-left)
    gsap.utils.toArray('.gsap-left').forEach(function (el) {
      gsap.fromTo(el,
        { opacity: 0, x: lite ? -10 : -35 },
        {
          opacity: 1,
          x: 0,
          duration: lite ? 0.35 : 0.6,
          ease: 'power3.out',
          scrollTrigger: {
            trigger: el,
            start: 'top 90%',
            toggleActions: 'play none none none'
          }
        }
      );
    });

    // 4. Staggered Table Rows (manage lists/tables)
    const tableRows = document.querySelectorAll('tbody tr');
    if (tableRows.length) {
      gsap.fromTo(tableRows,
        { opacity: 0, x: lite ? 0 : -10 },
        {
          opacity: 1,
          x: 0,
          duration: lite ? 0.1 : 0.15,
          stagger: lite ? 0.005 : 0.008,
          ease: 'power2.out',
          delay: lite ? 0.05 : 0.08
        }
      );
    }

    // 5. Form Field Entrances (staggered fields)
    const formFields = document.querySelectorAll(
      'main .form-control, main .form-select, main textarea, main .form-check'
    );
    if (formFields.length) {
      gsap.fromTo(formFields,
        { opacity: 0, x: lite ? 0 : -14 },
        {
          opacity: 1,
          x: 0,
          duration: lite ? 0.2 : 0.38,
          stagger: lite ? 0.02 : 0.05,
          ease: 'power3.out',
          delay: lite ? 0.1 : 0.5
        }
      );
    }

    // 6. Form/Page Heading Entrances
    const pageHeading = document.querySelector('main h2, main h3, main h4');
    if (pageHeading && !pageHeading.classList.contains('gsap-left')) {
      gsap.fromTo(pageHeading,
        { opacity: 0, x: lite ? -10 : -28 },
        {
          opacity: 1,
          x: 0,
          duration: lite ? 0.25 : 0.55,
          ease: 'power3.out',
          delay: lite ? 0.05 : 0.3
        }
      );
    }

    // 7. Button Entrances
    const pageButtons = document.querySelectorAll(
      'main form .btn, main > div > .btn, main .d-flex .btn:not(.dropdown-toggle)'
    );
    if (pageButtons.length) {
      gsap.fromTo(pageButtons,
        { opacity: 0, y: lite ? 5 : 12 },
        {
          opacity: 1,
          y: 0,
          duration: lite ? 0.2 : 0.38,
          stagger: lite ? 0.02 : 0.07,
          ease: 'power3.out',
          delay: lite ? 0.15 : 0.7
        }
      );
    }
  }

  window.SRMSAnimations = window.SRMSAnimations || {};
  window.SRMSAnimations.reveal = { init: init };
})();
