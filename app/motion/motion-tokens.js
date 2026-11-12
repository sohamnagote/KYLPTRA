/**
 * KLYPTRA Motion Design System - Tokens & Presets
 * Inspired by Apple iOS & macOS fluid physics
 */

(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.KlyptraMotionTokens = factory();
  }
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  // 1. Motion Timing Tokens (Milliseconds)
  const TIMING = {
    instant: 100,       // 80–120ms: Instant feedback, toggles, active taps
    micro: 150,         // 120–180ms: Micro-interactions, hover highlights, icon turns
    standard: 220,      // 180–260ms: Standard UI transitions, tabs, chip selects
    panel: 280,         // 220–340ms: Panel slide-ins, modals, dropdown reveals
    layout: 360,        // 300–450ms: Larger layout transitions, page changes, card reordering
    themeTransition: 200 // 180–240ms: Smooth coordinated theme fade
  };

  // 2. Spring Physics Specifications
  const SPRINGS = {
    snappy: {
      stiffness: 420,
      damping: 34,
      mass: 0.8,
      name: 'snappy'
    },
    gentle: {
      stiffness: 320,
      damping: 30,
      mass: 1.0,
      name: 'gentle'
    },
    soft: {
      stiffness: 260,
      damping: 28,
      mass: 1.0,
      name: 'soft'
    }
  };

  // 3. Apple-Inspired Cubic-Bezier Easing Curves
  const EASING = {
    smoothOut: 'cubic-bezier(0.22, 1, 0.36, 1)',   // Ultra smooth decelerate
    standard: 'cubic-bezier(0.2, 0, 0, 1)',        // Standard interface movement
    gentleInOut: 'cubic-bezier(0.4, 0, 0.2, 1)',   // Symmetrical ease-in-out
    springPop: 'cubic-bezier(0.34, 1.56, 0.64, 1)', // Restrained physical pop
    springBounce: 'cubic-bezier(0.175, 0.885, 0.32, 1.275)' // Playful bounce
  };

  // 4. Color Palette Tokens for Light and Graphite Dark Themes
  const THEME_PALETTES = {
    light: {
      appBg: '#fbf8ff',
      sidebarBg: '#ffffff',
      surfacePrimary: '#ffffff',
      surfaceSecondary: '#f4f2fd',
      surfaceElevated: '#eeedf7',
      surfaceHighest: '#e3e1ec',
      inputBg: '#f4f2fd',
      borderDefault: '#c7c4d8',
      borderSubtle: 'rgba(199, 196, 216, 0.35)',
      textPrimary: '#1a1b22',
      textSecondary: '#464555',
      textMuted: '#777587',
      accentPrimary: '#493ee5',
      accentHover: '#3c32cc',
      accentContainer: '#635bff',
      accentFixed: '#e2dfff',
      onAccentFixed: '#321ed2',
      accentSoft: '#e9ddff',
      success: '#10B981',
      warning: '#F59E0B',
      error: '#ba1a1a',
      errorContainer: '#ffdad6',
      cardShadow: '0 4px 20px -2px rgba(73, 62, 229, 0.05), 0 2px 6px -1px rgba(0, 0, 0, 0.04)',
      cardShadowHover: '0 12px 30px -4px rgba(73, 62, 229, 0.12), 0 4px 10px -2px rgba(0, 0, 0, 0.06)'
    },
    dark: {
      // Graphite & Charcoal specification
      appBg: '#1D1F24',
      sidebarBg: '#22242A',
      surfacePrimary: '#282A30',
      surfaceSecondary: '#2D3037',
      surfaceElevated: '#343740',
      surfaceHighest: '#3e424c',
      inputBg: '#25272D',
      borderDefault: '#3B3E47',
      borderSubtle: 'rgba(59, 62, 71, 0.65)',
      textPrimary: '#F3F3F5',
      textSecondary: '#B8BBC5',
      textMuted: '#9297A3',
      accentPrimary: '#A796FF',
      accentHover: '#B8AAFF',
      accentContainer: '#8455ef',
      accentFixed: '#39334D',
      onAccentFixed: '#F3F3F5',
      accentSoft: '#39334D',
      success: '#67C99A',
      warning: '#E8BB70',
      error: '#EA858A',
      errorContainer: '#5c2024',
      cardShadow: '0 4px 20px -2px rgba(0, 0, 0, 0.45), 0 2px 6px -1px rgba(0, 0, 0, 0.3)',
      cardShadowHover: '0 14px 34px -4px rgba(0, 0, 0, 0.65), 0 6px 12px -2px rgba(167, 150, 255, 0.1)'
    }
  };

  // 5. Shader Color Palette Vectors
  const SHADER_PALETTES = {
    light: {
      colA: [0.984, 0.973, 1.0],   // #fbf8ff
      colB: [0.914, 0.867, 1.0],   // #e9ddff
      colC: [0.886, 0.875, 1.0],   // #e2dfff
      colD: [0.878, 0.949, 0.996], // subtle pale blue/cyan
      opacity: 0.45
    },
    dark: {
      colA: [0.114, 0.122, 0.141], // #1D1F24 Graphite
      colB: [0.133, 0.141, 0.165], // #22242A Charcoal Sidebar
      colC: [0.224, 0.200, 0.302], // #39334D Muted Lavender
      colD: [0.176, 0.208, 0.282], // Subtle Indigo/Blue Highlight
      opacity: 0.35
    }
  };

  return {
    TIMING,
    SPRINGS,
    EASING,
    THEME_PALETTES,
    SHADER_PALETTES
  };
});

