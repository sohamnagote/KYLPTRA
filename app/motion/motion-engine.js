/**
 * KLYPTRA Motion Design Engine
 * Centralized motion coordinator, spring physics solver, directional workspace transitions,
 * cursor-reactive drag-and-drop, tactile micro-interactions, modal transitions, and launch reveal.
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

  // Workspace index map for directional physical transition flow
  const WORKSPACE_ORDER = {
    'new-project': 0,
    'clips': 1,
    'editor': 2,
    'projects': 3,
    'settings': 4
  };

  let reducedMotionPreference = false;
  let activePageTransition = false;
  let currentNavId = 'new-project';

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

  // ----------------- Sidebar Active Indicator Glider -----------------
  function setupSidebarPill() {
    const nav = document.querySelector('aside nav');
    if (!nav) return;

    let pill = document.getElementById('sidebar-active-pill');
    if (!pill) {
      pill = document.createElement('div');
      pill.id = 'sidebar-active-pill';
      pill.className = 'sidebar-active-pill absolute left-2 right-2 rounded-xl pointer-events-none z-0 bg-slate-200/60 dark:bg-white/10 border border-slate-300/40 dark:border-white/10';
      nav.style.position = 'relative';
      nav.prepend(pill);
    }
  }

  function updateSidebarPill(activeNavName) {
    currentNavId = activeNavName;
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

    nav.querySelectorAll('[data-nav]').forEach(item => {
      const isCurrent = item.getAttribute('data-nav') === activeNavName;
      item.classList.toggle('active', isCurrent);
      item.classList.toggle('text-on-surface', isCurrent);
      item.classList.toggle('text-on-surface-variant', !isCurrent);
      const icon = item.querySelector('.material-symbols-outlined');
      if (icon) {
        icon.style.transform = isCurrent ? 'scale(1.08)' : 'scale(1.0)';
        icon.style.transition = `transform ${TIMING.micro}ms ${EASING.smoothOut}, color ${TIMING.micro}ms ease`;
      }
    });
  }

  // ----------------- Directional Natural Workspace Transition -----------------
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
      if (fromViewEl) fromViewEl.classList.add('hidden');
      toViewEl.classList.remove('hidden');
      if (onComplete) onComplete();
      return;
    }

    activePageTransition = true;

    // Determine directional movement based on workspace sequence
    const fromId = fromViewEl ? fromViewEl.id.replace('view-', '') : '';
    const toId = toViewEl.id.replace('view-', '');
    const fromIdx = WORKSPACE_ORDER[fromId] ?? 0;
    const toIdx = WORKSPACE_ORDER[toId] ?? 0;
    const isForward = toIdx >= fromIdx;
    const exitOffset = isForward ? -16 : 16;
    const enterOffset = isForward ? 20 : -20;

    // Phase 1: Smooth Exit of Previous View (110ms)
    if (fromViewEl && fromViewEl !== toViewEl && !fromViewEl.classList.contains('hidden')) {
      fromViewEl.style.transition = `opacity 110ms ${EASING.standard}, transform 110ms ${EASING.standard}`;
      fromViewEl.style.opacity = '0';
      fromViewEl.style.transform = `translateX(${exitOffset}px) scale(0.99)`;

      setTimeout(() => {
        fromViewEl.classList.add('hidden');
        fromViewEl.style.transform = '';
        fromViewEl.style.opacity = '';

        // Phase 2: Smooth Natural Workspace Entry
        executeEntrance(toViewEl, enterOffset, onComplete);
      }, 110);
    } else {
      executeEntrance(toViewEl, enterOffset, onComplete);
    }
  }

  function executeEntrance(viewEl, enterOffset, onComplete) {
    viewEl.classList.remove('hidden');
    viewEl.style.opacity = '0';
    viewEl.style.transform = `translateX(${enterOffset}px) scale(0.992)`;
    viewEl.style.transition = 'none';

    void viewEl.offsetHeight; // Force reflow

    viewEl.style.transition = `opacity ${TIMING.standard}ms ${EASING.smoothOut}, transform ${TIMING.panel}ms ${EASING.smoothOut}`;
    viewEl.style.opacity = '1';
    viewEl.style.transform = 'translateX(0) scale(1)';

    const staggerItems = viewEl.querySelectorAll('.apple-card, .liquid-glass-card, .motion-stagger-item');
    if (staggerItems.length > 0 && !isReducedMotion()) {
      staggerEnter(Array.from(staggerItems).slice(0, 10), 30);
    }

    setTimeout(() => {
      viewEl.style.transition = '';
      viewEl.style.transform = '';
      viewEl.style.opacity = '';
      activePageTransition = false;
      if (onComplete) onComplete();
    }, TIMING.panel);
  }

  function staggerEnter(elements, staggerDelay = 35) {
    if (!elements || elements.length === 0 || isReducedMotion()) return;

    elements.forEach((el, idx) => {
      el.style.opacity = '0';
      el.style.transform = 'translateY(12px)';
      el.style.transition = 'none';

      setTimeout(() => {
        el.style.transition = `opacity ${TIMING.standard}ms ${EASING.smoothOut}, transform ${TIMING.panel}ms ${EASING.smoothOut}`;
        el.style.opacity = '1';
        el.style.transform = 'translateY(0)';
      }, idx * staggerDelay);
    });
  }

  // ----------------- Distinctive Cursor-Reactive Dropzone Interaction -----------------
  function setupDropzonePhysics(dropzoneEl) {
    if (!dropzoneEl) return;

    let isHovering = false;
    let isDraggingOver = false;

    // 3D Perspective Tilt following cursor
    dropzoneEl.addEventListener('mousemove', (e) => {
      if (isReducedMotion() || isDraggingOver) return;
      const rect = dropzoneEl.getBoundingClientRect();
      const xRel = (e.clientX - rect.left) / rect.width - 0.5;
      const yRel = (e.clientY - rect.top) / rect.height - 0.5;

      dropzoneEl.style.transform = `perspective(900px) rotateX(${-yRel * 6}deg) rotateY(${xRel * 6}deg) scale(1.01)`;
      dropzoneEl.style.transition = 'transform 80ms ease-out';
    });

    dropzoneEl.addEventListener('mouseleave', () => {
      if (isReducedMotion()) return;
      dropzoneEl.style.transform = 'perspective(900px) rotateX(0deg) rotateY(0deg) scale(1)';
      dropzoneEl.style.transition = 'transform 320ms cubic-bezier(0.34, 1.56, 0.64, 1)';
    });

    // File Drag In and Out Physics
    ['dragenter', 'dragover'].forEach(eventType => {
      dropzoneEl.addEventListener(eventType, (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (isDraggingOver) return;
        isDraggingOver = true;
        dropzoneEl.classList.add('dropzone-active-drag');
        dropzoneEl.style.transform = 'perspective(900px) scale(1.025) translateY(-4px)';
        dropzoneEl.style.transition = 'transform 240ms cubic-bezier(0.34, 1.56, 0.64, 1)';
      });
    });

    ['dragleave', 'dragend'].forEach(eventType => {
      dropzoneEl.addEventListener(eventType, (e) => {
        e.preventDefault();
        e.stopPropagation();
        isDraggingOver = false;
        dropzoneEl.classList.remove('dropzone-active-drag');
        dropzoneEl.style.transform = 'perspective(900px) scale(1) translateY(0)';
        dropzoneEl.style.transition = 'transform 260ms cubic-bezier(0.22, 1, 0.36, 1)';
      });
    });

    dropzoneEl.addEventListener('drop', (e) => {
      isDraggingOver = false;
      dropzoneEl.classList.remove('dropzone-active-drag');
      // Satisfying physical spring impact on drop
      dropzoneEl.style.transform = 'scale(0.975)';
      setTimeout(() => {
        dropzoneEl.style.transform = 'scale(1)';
        dropzoneEl.style.transition = 'transform 350ms cubic-bezier(0.34, 1.56, 0.64, 1)';
      }, 100);
    });
  }

  // ----------------- Modal Transition System -----------------
  function openModal(modalEl) {
    if (!modalEl) return;
    modalEl.classList.remove('hidden');

    if (isReducedMotion()) {
      modalEl.style.opacity = '1';
      return;
    }

    const backdrop = modalEl.querySelector('.modal-backdrop') || modalEl;
    const card = modalEl.querySelector('.modal-card, .liquid-glass-card') || modalEl.firstElementChild;

    modalEl.style.opacity = '0';
    if (card) {
      card.style.transform = 'scale(0.94) translateY(12px)';
      card.style.opacity = '0';
    }

    void modalEl.offsetHeight;

    modalEl.style.transition = `opacity ${TIMING.standard}ms ${EASING.smoothOut}`;
    modalEl.style.opacity = '1';

    if (card) {
      card.style.transition = `transform ${TIMING.panel}ms cubic-bezier(0.34, 1.56, 0.64, 1), opacity ${TIMING.standard}ms ${EASING.smoothOut}`;
      card.style.transform = 'scale(1) translateY(0)';
      card.style.opacity = '1';
    }
  }

  function closeModal(modalEl, onClosed) {
    if (!modalEl) return;

    if (isReducedMotion()) {
      modalEl.classList.add('hidden');
      if (onClosed) onClosed();
      return;
    }

    const card = modalEl.querySelector('.modal-card, .liquid-glass-card') || modalEl.firstElementChild;

    modalEl.style.transition = `opacity ${TIMING.instant}ms ${EASING.standard}`;
    modalEl.style.opacity = '0';

    if (card) {
      card.style.transition = `transform ${TIMING.instant}ms ${EASING.standard}`;
      card.style.transform = 'scale(0.96) translateY(8px)';
    }

    setTimeout(() => {
      modalEl.classList.add('hidden');
      modalEl.style.opacity = '';
      if (card) {
        card.style.transform = '';
        card.style.opacity = '';
      }
      if (onClosed) onClosed();
    }, TIMING.instant);
  }

  // ----------------- Launch Opening Sequence -----------------
  function playLaunchReveal() {
    const splash = document.getElementById('klyptra-launch-splash');
    if (!splash) return;

    if (isReducedMotion()) {
      splash.style.display = 'none';
      return;
    }

    const mark = splash.querySelector('.splash-mark');
    const wordmark = splash.querySelector('.splash-wordmark');

    if (mark) {
      mark.style.transform = 'scale(0.85) rotate(-6deg)';
      mark.style.opacity = '0';
      void mark.offsetHeight;
      mark.style.transition = 'transform 600ms cubic-bezier(0.34, 1.56, 0.64, 1), opacity 400ms ease';
      mark.style.transform = 'scale(1) rotate(0deg)';
      mark.style.opacity = '1';
    }

    if (wordmark) {
      wordmark.style.opacity = '0';
      wordmark.style.letterSpacing = '6px';
      setTimeout(() => {
        wordmark.style.transition = 'letter-spacing 500ms cubic-bezier(0.22, 1, 0.36, 1), opacity 400ms ease';
        wordmark.style.letterSpacing = '3px';
        wordmark.style.opacity = '1';
      }, 150);
    }

    // Seamless fade away to reveal studio
    setTimeout(() => {
      splash.style.transition = 'opacity 350ms cubic-bezier(0.2, 0, 0, 1)';
      splash.style.opacity = '0';
      setTimeout(() => {
        splash.style.display = 'none';
      }, 350);
    }, 750);
  }

  return {
    isReducedMotion,
    setReducedMotion,
    updateSidebarPill,
    transitionPage,
    staggerEnter,
    setupDropzonePhysics,
    openModal,
    closeModal,
    playLaunchReveal
  };
});
