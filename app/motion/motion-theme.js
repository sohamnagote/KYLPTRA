/**
 * KLYPTRA Motion Theme Engine
 * Complete 3-mode theme system: Light, Dark (Graphite/Charcoal), and System.
 * Handles smooth 200ms coordinated transitions, OS preference listening, and persistence.
 */

(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory(require('./motion-tokens.js'));
  } else {
    root.KlyptraTheme = factory(root.KlyptraMotionTokens);
  }
})(typeof self !== 'undefined' ? self : this, function (Tokens) {
  'use strict';

  const STORAGE_KEY = 'klyptra_theme_mode';
  let currentMode = 'light'; // 'light' (default) | 'dark' | 'system'
  let systemDark = false;
  let isTransitioning = false;

  function init() {
    if (typeof window === 'undefined') return;

    // 1. Detect OS scheme
    const mql = window.matchMedia('(prefers-color-scheme: dark)');
    systemDark = mql.matches;
    mql.addEventListener('change', (e) => {
      systemDark = e.matches;
      if (currentMode === 'system') {
        applyTheme(false); // smoothly apply OS change
      }
    });

    // 2. Read saved mode from localStorage or default to light
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved && (saved === 'light' || saved === 'dark' || saved === 'system')) {
        currentMode = saved;
      } else {
        currentMode = 'light';
      }
    } catch (e) {
      currentMode = 'light';
    }

    // Apply immediately without flash
    applyTheme(false);
  }

  function getMode() {
    return currentMode;
  }

  function getResolvedTheme() {
    if (currentMode === 'system') {
      return systemDark ? 'dark' : 'light';
    }
    return currentMode;
  }

  function setMode(mode) {
    if (mode !== 'light' && mode !== 'dark' && mode !== 'system') return;
    if (mode === currentMode) return;

    currentMode = mode;
    try {
      localStorage.setItem(STORAGE_KEY, mode);
    } catch (e) {}

    // Apply with smooth 200ms transition
    applyTheme(true);
  }

  function applyTheme(animated = true) {
    if (typeof document === 'undefined') return;

    const resolved = getResolvedTheme();
    const html = document.documentElement;

    if (animated) {
      html.classList.add('theme-transitioning');
      isTransitioning = true;
    }

    if (resolved === 'dark') {
      html.classList.add('dark');
    } else {
      html.classList.remove('dark');
    }

    // Sync ambient background shader
    if (window.__klyptraShader && typeof window.__klyptraShader.setTheme === 'function') {
      window.__klyptraShader.setTheme(resolved);
    }

    // Sync all theme controls in Header and Settings
    syncThemeUIControls();

    if (animated) {
      setTimeout(() => {
        html.classList.remove('theme-transitioning');
        isTransitioning = false;
      }, Tokens.TIMING.themeTransition);
    }

    // Dispatch event for any other subscribers
    window.dispatchEvent(new CustomEvent('klyptra:themechange', {
      detail: { mode: currentMode, resolvedTheme: resolved }
    }));
  }

  function syncThemeUIControls() {
    // 1. Header segmented toggle buttons
    const headerBtns = document.querySelectorAll('[data-theme-choice]');
    headerBtns.forEach(btn => {
      const choice = btn.getAttribute('data-theme-choice');
      const isSelected = (choice === currentMode);
      if (isSelected) {
        btn.classList.add('bg-white', 'dark:bg-[#343740]', 'text-primary', 'dark:text-[#A796FF]', 'shadow-xs', 'font-bold');
        btn.classList.remove('text-on-surface-variant', 'opacity-70');
      } else {
        btn.classList.remove('bg-white', 'dark:bg-[#343740]', 'text-primary', 'dark:text-[#A796FF]', 'shadow-xs', 'font-bold');
        btn.classList.add('text-on-surface-variant', 'opacity-70');
      }
    });

    // 2. Settings page radio/card selectors
    const settingsRadios = document.querySelectorAll('input[name="theme-setting"]');
    settingsRadios.forEach(radio => {
      radio.checked = (radio.value === currentMode);
    });
  }

  return {
    init,
    getMode,
    getResolvedTheme,
    setMode,
    applyTheme
  };
});

