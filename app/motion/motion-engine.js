/**
 * KLYPTRA Motion Design Engine
 * Centralized motion coordinator, spring solver, page transitions,
 * micro-interactions, layout animations, modals, and toast notifications.
 */

(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory(require('./motion-tokens.js'));
  } else {
    root.KlyptraMotionEngine = factory(root.KlyptraMotionTokens);
  }
})(typeof self !== 'undefined' ? self : this, function (Tokens) {
  'use strict';

  const { TIMING, SPRINGS, EASING } = Tokens;

  // Local state
  let reducedMotionPreference = false;
  let activePageTransition = false;
  let toastContainer = null;

  // Initialize reduced motion detection
  if (typeof window !== 'undefined') {
    const mql = window.matchMedia('(prefers-reduced-motion: reduce)');
    reducedMotionPreference = mql.matches;
    mql.addEventListener('change', (e) => {
      reducedMotionPreference = e.matches;
      applyReducedMotionState();
    });
  }

  function isReducedMotion() {
    return reducedMotionPreference;
  }

  function setReducedMotion(enable) {
    reducedMotionPreference = !!enable;
    applyReducedMotionState();
  }

  function applyReducedMotionState() {
    if (typeof document === 'undefined') return;
    if (reducedMotionPreference) {
      document.documentElement.classList.add('reduced-motion');
    } else {
      document.documentElement.classList.remove('reduced-motion');
    }
  }

  // ----------------- Analytical Spring to CSS Linear Generator -----------------
  function generateSpringLinear(springSpec, steps = 30) {
    const { stiffness, damping, mass } = springSpec;
    const w0 = Math.sqrt(stiffness / mass);
    const zeta = damping / (2 * Math.sqrt(stiffness * mass));

    if (zeta >= 1) {
      // Overdamped / critically damped fallback
      return EASING.smoothOut;
    }

    const wd = w0 * Math.sqrt(1 - zeta * zeta);
    const points = [];
    const duration = 0.5; // normalized 500ms duration

    for (let i = 0; i <= steps; i++) {
      const t = (i / steps) * duration;
      const decay = Math.exp(-zeta * w0 * t);
      const val = 1 - decay * (Math.cos(wd * t) + (zeta * w0 / wd) * Math.sin(wd * t));
      points.push(Math.round(val * 1000) / 1000);
    }

    return `linear(${points.join(', ')})`;
  }

  // ----------------- Sidebar Active Indicator Glider -----------------
  function setupSidebarPill() {
    const nav = document.querySelector('aside nav');
    if (!nav) return;

    let pill = document.getElementById('sidebar-active-pill');
    if (!pill) {
      pill = document.createElement('div');
      pill.id = 'sidebar-active-pill';
      pill.className = 'sidebar-active-pill absolute left-space-md right-space-md rounded-xl pointer-events-none z-0';
      nav.style.position = 'relative';
      nav.prepend(pill);
    }
  }

  function updateSidebarPill(activeNavName) {
    const nav = document.querySelector('aside nav');
    if (!nav) return;

    setupSidebarPill();
    const pill = document.getElementById('sidebar-active-pill');
    if (!pill) return;

    const activeItem = nav.querySelector(`[data-nav="${activeNavName}"]`);
    if (!activeItem) {
      pill.style.opacity = '0';
      return;
    }

    const navRect = nav.getBoundingClientRect();
    const itemRect = activeItem.getBoundingClientRect();
    const top = itemRect.top - navRect.top + nav.scrollTop;
    const height = itemRect.height;

    pill.style.opacity = '1';
    pill.style.top = `${top}px`;
    pill.style.height = `${height}px`;

    // Ensure icon & label elements inside items have smooth subtle scale
    nav.querySelectorAll('[data-nav]').forEach(item => {
      const isCurrent = item.getAttribute('data-nav') === activeNavName;
      const icon = item.querySelector('.material-symbols-outlined');
      if (icon) {
        icon.style.transform = isCurrent ? 'scale(1.08)' : 'scale(1.0)';
        icon.style.transition = `transform ${TIMING.micro}ms ${EASING.smoothOut}, color ${TIMING.micro}ms ease`;
      }
    });
  }

  // ----------------- Global Page Transitions -----------------
  function transitionPage(fromViewEl, toViewEl, onComplete) {
    if (!toViewEl) {
      if (onComplete) onComplete();
      return;
    }

    if (isReducedMotion()) {
      if (fromViewEl) fromViewEl.classList.add('hidden');
      toViewEl.classList.remove('hidden');
      if (onComplete) onComplete();
      return;
    }

    if (activePageTransition) {
      // Clean up previous transition immediately
      if (fromViewEl) fromViewEl.classList.add('hidden');
      toViewEl.classList.remove('hidden');
      if (onComplete) onComplete();
      return;
    }

    activePageTransition = true;

    // Phase 1: Smooth Exit of Previous View (120ms)
    if (fromViewEl && fromViewEl !== toViewEl && !fromViewEl.classList.contains('hidden')) {
      fromViewEl.style.transition = `opacity ${TIMING.instant}ms ${EASING.standard}, transform ${TIMING.instant}ms ${EASING.standard}`;
      fromViewEl.style.opacity = '0';
      fromViewEl.style.transform = 'translateY(-6px) scale(0.995)';

      setTimeout(() => {
        fromViewEl.classList.add('hidden');
        fromViewEl.style.transform = '';
        fromViewEl.style.opacity = '';

        // Phase 2: Smooth Entrance of Next View (240ms)
        executeEntrance(toViewEl, onComplete);
      }, TIMING.instant);
    } else {
      executeEntrance(toViewEl, onComplete);
    }
  }

  function executeEntrance(viewEl, onComplete) {
    viewEl.classList.remove('hidden');
    viewEl.style.opacity = '0';
    viewEl.style.transform = 'translateY(12px) scale(0.992)';
    viewEl.style.transition = 'none';

    // Force reflow
    void viewEl.offsetHeight;

    viewEl.style.transition = `opacity ${TIMING.standard}ms ${EASING.smoothOut}, transform ${TIMING.panel}ms ${EASING.smoothOut}`;
    viewEl.style.opacity = '1';
    viewEl.style.transform = 'translateY(0) scale(1)';

    // Stagger immediate interactive children cards or sections
    const staggerItems = viewEl.querySelectorAll('.apple-card, .motion-stagger-item');
    if (staggerItems.length > 0 && !isReducedMotion()) {
      staggerEnter(Array.from(staggerItems).slice(0, 12), 35);
    }

    setTimeout(() => {
      viewEl.style.transition = '';
      viewEl.style.transform = '';
      viewEl.style.opacity = '';
      activePageTransition = false;
      if (onComplete) onComplete();
    }, TIMING.panel);
  }

  // ----------------- Restrained Stagger Coordinator -----------------
  function staggerEnter(elements, staggerDelay = 40) {
    if (!elements || elements.length === 0 || isReducedMotion()) return;

    elements.forEach((el, idx) => {
      el.style.opacity = '0';
      el.style.transform = 'translateY(14px)';
      el.style.transition = 'none';

      setTimeout(() => {
        el.style.transition = `opacity ${TIMING.standard}ms ${EASING.smoothOut}, transform ${TIMING.panel}ms ${EASING.smoothOut}`;
        el.style.opacity = '1';
        el.style.transform = 'translateY(0)';
      }, idx * staggerDelay);
    });
  }

  // ----------------- Animated Card Removal with Layout Collapse -----------------
  function animateRemove(element, onRemoved) {
    if (!element) return;

    if (isReducedMotion()) {
      if (onRemoved) onRemoved();
      return;
    }

    // 1. Initial shrink & fade
    element.style.pointerEvents = 'none';
    element.style.transition = `opacity ${TIMING.micro}ms ${EASING.standard}, transform ${TIMING.micro}ms ${EASING.springPop}`;
    element.style.opacity = '0';
    element.style.transform = 'scale(0.9) translateY(8px)';

    setTimeout(() => {
      // 2. Smoothly collapse height and margins to avoid abrupt snap
      const height = element.offsetHeight;
      element.style.height = `${height}px`;
      element.style.overflow = 'hidden';
      element.style.transition = `height ${TIMING.standard}ms ${EASING.smoothOut}, margin ${TIMING.standard}ms ${EASING.smoothOut}, padding ${TIMING.standard}ms ${EASING.smoothOut}`;

      void element.offsetHeight; // Reflow

      element.style.height = '0px';
      element.style.marginTop = '0px';
      element.style.marginBottom = '0px';
      element.style.paddingTop = '0px';
      element.style.paddingBottom = '0px';

      setTimeout(() => {
        if (onRemoved) onRemoved();
      }, TIMING.standard);
    }, TIMING.micro);
  }

  // ----------------- Modal Transition System -----------------
  function openModal(modalEl) {
    if (!modalEl) return;
    const dialogBox = modalEl.querySelector('div') || modalEl;

    modalEl.classList.remove('hidden');

    if (isReducedMotion()) {
      modalEl.style.opacity = '1';
      return;
    }

    modalEl.style.opacity = '0';
    dialogBox.style.opacity = '0';
    dialogBox.style.transform = 'scale(0.95) translateY(10px)';

    void modalEl.offsetHeight;

    modalEl.style.transition = `opacity ${TIMING.standard}ms ${EASING.standard}`;
    modalEl.style.opacity = '1';

    dialogBox.style.transition = `opacity ${TIMING.standard}ms ${EASING.smoothOut}, transform ${TIMING.panel}ms ${EASING.smoothOut}`;
    dialogBox.style.opacity = '1';
    dialogBox.style.transform = 'scale(1) translateY(0)';
  }

  function closeModal(modalEl, onClosed) {
    if (!modalEl) return;
    const dialogBox = modalEl.querySelector('div') || modalEl;

    if (isReducedMotion()) {
      modalEl.classList.add('hidden');
      if (onClosed) onClosed();
      return;
    }

    modalEl.style.transition = `opacity ${TIMING.micro}ms ${EASING.standard}`;
    modalEl.style.opacity = '0';

    dialogBox.style.transition = `opacity ${TIMING.micro}ms ${EASING.standard}, transform ${TIMING.micro}ms ${EASING.standard}`;
    dialogBox.style.opacity = '0';
    dialogBox.style.transform = 'scale(0.96) translateY(6px)';

    setTimeout(() => {
      modalEl.classList.add('hidden');
      modalEl.style.opacity = '';
      dialogBox.style.opacity = '';
      dialogBox.style.transform = '';
      if (onClosed) onClosed();
    }, TIMING.micro);
  }

  // ----------------- Toast Notification System -----------------
  function getOrCreateToastContainer() {
    if (toastContainer && document.body.contains(toastContainer)) {
      return toastContainer;
    }
    toastContainer = document.getElementById('klyptra-toast-container');
    if (!toastContainer) {
      toastContainer = document.createElement('div');
      toastContainer.id = 'klyptra-toast-container';
      toastContainer.className = 'fixed bottom-6 right-6 z-50 flex flex-col gap-2.5 max-w-sm w-full pointer-events-none select-none';
      document.body.appendChild(toastContainer);
    }
    return toastContainer;
  }

  function showToast({ type = 'info', title = '', message = '', duration = 4000 }) {
    const container = getOrCreateToastContainer();
    const toast = document.createElement('div');
    toast.className = `klyptra-toast toast-${type} pointer-events-auto rounded-xl shadow-lg border p-3 flex items-start gap-3 backdrop-blur-md relative overflow-hidden`;

    const iconMap = {
      success: 'check_circle',
      error: 'error',
      warning: 'warning',
      info: 'info'
    };

    const iconName = iconMap[type] || 'info';

    toast.innerHTML = `
      <div class="toast-icon-wrap w-7 h-7 rounded-lg flex items-center justify-center shrink-0">
        <span class="material-symbols-outlined text-[18px]">${iconName}</span>
      </div>
      <div class="flex-1 min-w-0 pr-2">
        ${title ? `<h4 class="font-title-sm text-xs font-bold leading-tight truncate">${title}</h4>` : ''}
        <p class="font-body-sm text-[11px] leading-snug mt-0.5 opacity-90">${message}</p>
      </div>
      <button class="toast-close-btn w-5 h-5 flex items-center justify-center rounded hover:bg-black/10 dark:hover:bg-white/10 opacity-70 hover:opacity-100 transition-opacity">
        <span class="material-symbols-outlined text-[14px]">close</span>
      </button>
      <div class="toast-progress-bar absolute bottom-0 left-0 right-0 h-[3px]">
        <div class="toast-progress-fill h-full w-full"></div>
      </div>
    `;

    container.appendChild(toast);

    // Initial entrance setup
    if (!isReducedMotion()) {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(16px) scale(0.95)';
      void toast.offsetHeight;
      toast.style.transition = `opacity ${TIMING.standard}ms ${EASING.smoothOut}, transform ${TIMING.panel}ms ${EASING.smoothOut}`;
      toast.style.opacity = '1';
      toast.style.transform = 'translateY(0) scale(1)';
    }

    // Timed progress bar animation
    const progressFill = toast.querySelector('.toast-progress-fill');
    if (progressFill && duration > 0 && !isReducedMotion()) {
      progressFill.style.transition = `transform ${duration}ms linear`;
      progressFill.style.transformOrigin = 'left';
      progressFill.style.transform = 'scaleX(1)';
      void progressFill.offsetHeight;
      progressFill.style.transform = 'scaleX(0)';
    }

    let dismissTimer = null;
    const dismiss = () => {
      if (dismissTimer) clearTimeout(dismissTimer);
      if (isReducedMotion()) {
        toast.remove();
        return;
      }
      toast.style.transition = `opacity ${TIMING.micro}ms ${EASING.standard}, transform ${TIMING.micro}ms ${EASING.standard}, height ${TIMING.standard}ms ${EASING.smoothOut}`;
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(20px) scale(0.95)';
      setTimeout(() => {
        toast.style.height = `${toast.offsetHeight}px`;
        void toast.offsetHeight;
        toast.style.height = '0px';
        toast.style.marginTop = '0px';
        toast.style.marginBottom = '0px';
        toast.style.paddingTop = '0px';
        toast.style.paddingBottom = '0px';
        setTimeout(() => toast.remove(), TIMING.standard);
      }, TIMING.micro);
    };

    toast.querySelector('.toast-close-btn').addEventListener('click', dismiss);
    if (duration > 0) {
      dismissTimer = setTimeout(dismiss, duration);
    }

    return toast;
  }

  // ----------------- Micro-Interactions Setup -----------------
  function initMicroInteractions(root = document) {
    // 1. Apple-Style Button Physical Press Physics
    const buttons = root.querySelectorAll('button:not([data-motion-bound]), .apple-btn:not([data-motion-bound])');
    buttons.forEach(btn => {
      btn.setAttribute('data-motion-bound', 'true');
      btn.addEventListener('mousedown', () => {
        if (!isReducedMotion() && !btn.disabled) {
          btn.style.transform = 'scale(0.975)';
          btn.style.transition = `transform ${TIMING.instant}ms ${EASING.smoothOut}`;
        }
      });
      btn.addEventListener('mouseup', () => {
        if (!isReducedMotion()) {
          btn.style.transform = '';
          btn.style.transition = `transform ${TIMING.micro}ms ${EASING.smoothOut}`;
        }
      });
      btn.addEventListener('mouseleave', () => {
        if (!isReducedMotion()) {
          btn.style.transform = '';
          btn.style.transition = `transform ${TIMING.micro}ms ${EASING.smoothOut}`;
        }
      });
    });

    // 2. Interactive Card Elevation & Scale Response
    const cards = root.querySelectorAll('.apple-card:not([data-motion-bound])');
    cards.forEach(card => {
      card.setAttribute('data-motion-bound', 'true');
      card.addEventListener('mouseenter', () => {
        if (!isReducedMotion()) {
          card.style.transform = 'translateY(-3px) scale(1.008)';
          card.style.transition = `transform ${TIMING.micro}ms ${EASING.smoothOut}, box-shadow ${TIMING.micro}ms ${EASING.smoothOut}, border-color ${TIMING.micro}ms ease`;
        }
      });
      card.addEventListener('mouseleave', () => {
        if (!isReducedMotion()) {
          card.style.transform = '';
          card.style.transition = `transform ${TIMING.standard}ms ${EASING.smoothOut}, box-shadow ${TIMING.standard}ms ${EASING.smoothOut}, border-color ${TIMING.standard}ms ease`;
        }
      });
    });
  }

  return {
    TIMING,
    SPRINGS,
    EASING,
    isReducedMotion,
    setReducedMotion,
    transitionPage,
    updateSidebarPill,
    staggerEnter,
    animateRemove,
    openModal,
    closeModal,
    showToast,
    initMicroInteractions,
    generateSpringLinear
  };
});

