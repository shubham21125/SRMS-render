/* ==========================================================================
   SRMS — shared admin list/interaction helpers
   Debounced search, delete-modal wiring, submit-loading states, confetti,
   and page-fade transitions. Loaded once from admin_base.html / parent_base.html
   and used by individual list-page templates.
   ========================================================================== */
(function () {
  'use strict';

  function debounce(fn, wait) {
    var t;
    return function () {
      var ctx = this, args = arguments;
      clearTimeout(t);
      t = setTimeout(function () { fn.apply(ctx, args); }, wait);
    };
  }

  window.SRMSList = window.SRMSList || {};

  // ── Animated stat counters ───────────────────────────────────────────────
  // Usage: <span class="counter" data-target="{{ value }}">0</span>
  // then call window.SRMSList.initCounters() once on page load, or pass
  // { scrollTrigger: true } for stats that sit below the fold.
  window.SRMSList.initCounters = function (opts) {
    opts = opts || {};
    var duration = opts.duration || 1.2;
    var els = document.querySelectorAll('.counter[data-target]');
    if (!els.length || typeof gsap === 'undefined') return;

    function animate(el) {
      var target = parseFloat(el.dataset.target) || 0;
      var obj = { val: 0 };
      gsap.to(obj, {
        val: target, duration: duration, ease: 'power2.out',
        onUpdate: function () { el.textContent = Math.round(obj.val); }
      });
    }

    if (opts.scrollTrigger && typeof ScrollTrigger !== 'undefined') {
      els.forEach(function (el) {
        ScrollTrigger.create({
          trigger: el, start: 'top 88%', once: true,
          onEnter: function () { animate(el); }
        });
      });
    } else {
      els.forEach(animate);
    }
  };

  // ── Debounced live search / filter over table rows (client-side; only
  //    safe for pages that render the FULL list, not paginated ones) ──────
  // opts: { wait: ms, noResultsId: 'elementId' }
  window.SRMSList.initSearch = function (inputId, rowSelector, opts) {
    var input = document.getElementById(inputId);
    if (!input) return;
    opts = opts || {};
    var wait = opts.wait || 250;

    function run() {
      var q = input.value.trim().toLowerCase();
      var rows = document.querySelectorAll(rowSelector);
      var visible = 0;
      rows.forEach(function (row) {
        var match = row.textContent.toLowerCase().indexOf(q) !== -1;
        row.style.display = match ? '' : 'none';
        if (match) visible++;
      });
      if (opts.noResultsId) {
        var msgEl = document.getElementById(opts.noResultsId);
        if (msgEl) msgEl.style.display = (visible === 0 && q.length > 0) ? '' : 'none';
      }
    }
    input.addEventListener('input', debounce(run, wait));
  };

  // ── Debounced SERVER-SIDE search ─────────────────────────────────────────
  // Submits the input's <form method="get"> after the user pauses typing,
  // so list pages that are paginated (search must run on the full table,
  // not just the rows already on the current page) re-query the server.
  // Always resets to page 1 by stripping any existing ?page= param.
  window.SRMSList.initServerSearch = function (inputId, opts) {
    var input = document.getElementById(inputId);
    if (!input || !input.form) return;
    opts = opts || {};
    var wait = opts.wait || 400;
    var form = input.form;

    function run() {
      if (typeof form.requestSubmit === 'function') form.requestSubmit();
      else form.submit();
    }
    input.addEventListener('input', debounce(run, wait));

    // Keep the cursor at the end of the field after the page reloads with
    // the previous query pre-filled, rather than jumping to the start.
    if (opts.focusEnd && document.activeElement !== input) {
      var val = input.value;
      input.focus();
      input.value = '';
      input.value = val;
    }
  };

  // ── Generic delete-confirmation modal wiring ─────────────────────────────
  // cfg: { modalId, idFieldId, labelFieldId, buttonSelector }
  window.SRMSList.initDeleteModal = function (cfg) {
    var modalEl = document.getElementById(cfg.modalId);
    if (!modalEl || typeof bootstrap === 'undefined') return;
    document.querySelectorAll(cfg.buttonSelector).forEach(function (btn) {
      btn.addEventListener('click', function () {
        if (cfg.idFieldId) document.getElementById(cfg.idFieldId).value = btn.dataset.id;
        if (cfg.labelFieldId) document.getElementById(cfg.labelFieldId).textContent = btn.dataset.label || '';
        new bootstrap.Modal(modalEl).show();
      });
    });
  };

  // ── Confetti burst (lightweight, no external library) ───────────────────
  // Fires at most once per page load — safe to call from both the global
  // auto-detect below AND explicit per-template triggers without stacking.
  window.SRMSList.confetti = function () {
    if (window.SRMSList._confettiFired) return;
    window.SRMSList._confettiFired = true;

    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    if (window.SRMSPerf && window.SRMSPerf.isLite) return;

    var canvas = document.createElement('canvas');
    canvas.style.cssText = 'position:fixed;inset:0;width:100vw;height:100vh;pointer-events:none;z-index:9999;';
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    document.body.appendChild(canvas);
    var ctx = canvas.getContext('2d');
    var colors = ['#f5c518', '#d9a441', '#ffffff', '#34D399', '#93C5FD'];
    var pieces = [];
    for (var i = 0; i < 90; i++) {
      pieces.push({
        x: Math.random() * canvas.width,
        y: -20 - Math.random() * canvas.height * 0.25,
        w: 6 + Math.random() * 6,
        h: 8 + Math.random() * 8,
        color: colors[Math.floor(Math.random() * colors.length)],
        vy: 5 + Math.random() * 5,
        vx: -2.4 + Math.random() * 4.8,
        rot: Math.random() * 360,
        vrot: -10 + Math.random() * 20
      });
    }
    var frame = 0;
    (function tick() {
      frame++;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      pieces.forEach(function (p) {
        p.x += p.vx; p.y += p.vy; p.rot += p.vrot;
        ctx.save();
        ctx.translate(p.x, p.y);
        ctx.rotate(p.rot * Math.PI / 180);
        ctx.fillStyle = p.color;
        ctx.fillRect(-p.w / 2, -p.h / 2, p.w, p.h);
        ctx.restore();
      });
      if (frame < 50) { // ~0.8s at 60fps — quick burst, not a gimmicky long show
        requestAnimationFrame(tick);
      } else {
        canvas.remove();
      }
    })();
  };

  // Auto-fire confetti and handle alert auto-dismissal
  document.addEventListener('DOMContentLoaded', function () {
    // 1. Confetti trigger
    document.querySelectorAll('.alert-success').forEach(function (al) {
      var t = al.textContent.toLowerCase();
      if (/(added|created|registered)/.test(t)) {
        window.SRMSList.confetti();
      }
    });

    // 2. Alert auto-dismiss (4.5 seconds delay)
    document.querySelectorAll('.alert').forEach(function (alert) {
      // Don't auto-dismiss critical database/validation errors
      if (alert.classList.contains('alert-danger')) return;

      setTimeout(function () {
        if (typeof gsap !== 'undefined') {
          gsap.to(alert, {
            opacity: 0,
            y: -12,
            duration: 0.3,
            ease: 'power2.in',
            onComplete: function () {
              var btn = alert.querySelector('.btn-close');
              if (btn) btn.click();
              else alert.remove();
            }
          });
        } else {
          var btn = alert.querySelector('.btn-close');
          if (btn) btn.click();
          else alert.remove();
        }
      }, 4500);
    });
  });

  // ── Submit-loading state (button click → visible feedback) ──────────────
  // Add data-no-loading to a <form> to opt out.
  // NOTE: We defer the disable via setTimeout so the browser sends the full
  // form POST before the button is marked disabled. Disabling synchronously
  // inside the submit event can prevent the form data from being submitted
  // in certain browsers / Bootstrap-modal contexts (the delete-class bug).
  document.addEventListener('submit', function (e) {
    var form = e.target;
    if (!(form instanceof HTMLFormElement)) return;
    if (form.hasAttribute('data-no-loading')) return;
    var btn = form.querySelector('button[type="submit"]');
    if (!btn || btn.disabled) return;
    var originalHtml = btn.innerHTML;
    setTimeout(function () {
      btn.disabled = true;
      btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Please wait…';
    }, 0);
  }, true);

  // ── Page-fade transition on internal navigation ──────────────────────────
  // IMPORTANT: every path that sets opacity to 0 MUST have a matching reset,
  // or a bfcache-restored page (browser back/forward, and some redirect
  // flows) comes back permanently invisible — looks exactly like a "frozen"
  // screen. `pageshow` fires on both fresh loads and bfcache restores, so
  // resetting there covers every case.
  function resetPageFade() {
    document.body.style.transition = 'opacity .18s ease';
    document.body.style.opacity = '1';
  }
  window.addEventListener('pageshow', resetPageFade);
  document.addEventListener('DOMContentLoaded', resetPageFade);

  document.addEventListener('click', function (e) {
    var a = e.target.closest('a[href]');
    if (!a) return;
    if (a.target === '_blank' || a.hasAttribute('download')) return;
    if (a.dataset.bsToggle || a.dataset.bsDismiss) return;
    var href = a.getAttribute('href');
    if (!href || href.charAt(0) === '#') return;
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0) return;
    var url;
    try { url = new URL(a.href, window.location.origin); } catch (err) { return; }
    if (url.origin !== window.location.origin) return;
    if (url.pathname === window.location.pathname && url.search === window.location.search) return;
    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

    e.preventDefault();
    document.body.style.transition = 'opacity .16s ease';
    document.body.style.opacity = '0';
    // Safety net: if navigation is ever blocked (popup blocker, JS error
    // elsewhere, slow network) the page must not stay invisible forever.
    var safetyTimer = setTimeout(resetPageFade, 2000);
    setTimeout(function () {
      clearTimeout(safetyTimer);
      window.location.href = a.href;
    }, 150);
  }, true);
})();
