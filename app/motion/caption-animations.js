/**
 * KLYPTRA Caption Studio Animations Engine
 * Real-time animated live preview system for all 15 subtitle presets:
 * 1. Fade
 * 2. Pop
 * 3. Slide Up
 * 4. Slide Down
 * 5. Typewriter
 * 6. Karaoke
 * 7. Word Reveal
 * 8. Highlight Sweep
 * 9. Bounce
 * 10. Smooth Zoom
 * 11. Character Reveal
 * 12. Gradient Highlight
 * 13. Elastic Pop
 * 14. Minimal Fade
 * 15. Split Word Reveal
 *
 * Synchronized with the ASS tags generated for FFmpeg rendering.
 */

(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.CaptionAnimationEngine = factory();
  }
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  let activeAnimationTimer = null;
  let activeKaraokeWordIdx = 0;

  const PRESET_ANIMATIONS = [
    { id: 'fade', name: 'Fade', label: 'Smooth Fade', desc: 'Gentle opacity dissolve' },
    { id: 'pop', name: 'Pop', label: 'Spring Pop', desc: 'Snappy spring scale entrance' },
    { id: 'slide-up', name: 'Slide Up', label: 'Slide Up', desc: 'Upward gliding motion' },
    { id: 'slide-down', name: 'Slide Down', label: 'Slide Down', desc: 'Downward gliding motion' },
    { id: 'typewriter', name: 'Typewriter', label: 'Typewriter', desc: 'Sequential letter typing' },
    { id: 'karaoke', name: 'Karaoke', label: 'Karaoke', desc: 'Active spoken word tracking' },
    { id: 'word-reveal', name: 'Word Reveal', label: 'Word Reveal', desc: 'Staggered word appearances' },
    { id: 'highlight-sweep', name: 'Highlight Sweep', label: 'Highlight Sweep', desc: 'Glowing highlight beam' },
    { id: 'bounce', name: 'Bounce', label: 'Bounce', desc: 'Rhythmic spring bounce' },
    { id: 'smooth-zoom', name: 'Smooth Zoom', label: 'Smooth Zoom', desc: 'Slow cinematic push-in' },
    { id: 'character-reveal', name: 'Character Reveal', label: 'Character Reveal', desc: 'Letter-by-letter float' },
    { id: 'gradient-highlight', name: 'Gradient Highlight', label: 'Gradient Highlight', desc: 'Flowing iridescent gradient' },
    { id: 'elastic-pop', name: 'Elastic Pop', label: 'Elastic Pop', desc: 'Playful overshoot elasticity' },
    { id: 'minimal-fade', name: 'Minimal Fade', label: 'Minimal Fade', desc: 'Subtle high-contrast fade' },
    { id: 'split-word-reveal', name: 'Split Word Reveal', label: 'Split Word Reveal', desc: 'Multi-directional word entry' }
  ];

  function stopActiveAnimation() {
    if (activeAnimationTimer) {
      clearInterval(activeAnimationTimer);
      activeAnimationTimer = null;
    }
  }

  /**
   * Renders the animated live caption onto the video preview overlay
   */
  function renderLiveCaption(containerEl, options = {}) {
    if (!containerEl) return;
    stopActiveAnimation();

    const {
      text = "KLYPTRA creates viral AI clips in seconds.",
      animation = "Fade",
      fontName = "Inter",
      fontSize = 24,
      primaryColor = "#FFFFFF",
      highlightColor = "#A796FF",
      bgColor = "",
      position = "bottom"
    } = options;

    const animLower = (animation || "fade").toLowerCase().trim();
    const cleanText = (text && text.trim().length > 0) ? text.trim() : "Viral moments that engage viewers";
    const words = cleanText.split(/\s+/);

    containerEl.style.fontFamily = fontName;
    containerEl.style.fontSize = `${Math.round(fontSize * 0.65)}px`;
    containerEl.style.fontWeight = '700';
    containerEl.style.lineHeight = '1.3';
    containerEl.style.textAlign = 'center';
    containerEl.style.textShadow = '0 2px 6px rgba(0,0,0,0.85), 0 0 1px #000000';

    if (bgColor && bgColor.length > 2) {
      containerEl.style.backgroundColor = bgColor;
      containerEl.style.backdropFilter = 'blur(4px)';
      containerEl.style.padding = '4px 10px';
      containerEl.style.borderRadius = '8px';
    } else {
      containerEl.style.backgroundColor = 'transparent';
      containerEl.style.backdropFilter = 'none';
      containerEl.style.padding = '2px 6px';
    }

    // Set position
    if (position === "top") {
      containerEl.style.top = "12px";
      containerEl.style.bottom = "auto";
      containerEl.style.transform = "none";
    } else if (position === "middle") {
      containerEl.style.top = "50%";
      containerEl.style.bottom = "auto";
      containerEl.style.transform = "translateY(-50%)";
    } else {
      containerEl.style.bottom = "16px";
      containerEl.style.top = "auto";
      containerEl.style.transform = "none";
    }

    // Reset classes
    containerEl.className = "absolute left-3 right-3 text-center pointer-events-none transition-all";

    // 1. Karaoke Tracking
    if (animLower.includes("karaoke")) {
      containerEl.innerHTML = words.map((w, idx) => `
        <span class="karaoke-word transition-colors duration-150" data-idx="${idx}" style="color: ${idx === 0 ? highlightColor : primaryColor}; font-weight: ${idx === 0 ? '800' : '700'};">
          ${w}
        </span>
      `).join(" ");

      activeKaraokeWordIdx = 0;
      activeAnimationTimer = setInterval(() => {
        const wordEls = containerEl.querySelectorAll('.karaoke-word');
        if (wordEls.length === 0) return;
        activeKaraokeWordIdx = (activeKaraokeWordIdx + 1) % wordEls.length;
        wordEls.forEach((el, i) => {
          if (i === activeKaraokeWordIdx) {
            el.style.color = highlightColor;
            el.style.transform = 'scale(1.1)';
            el.style.display = 'inline-block';
            el.style.textShadow = `0 0 12px ${highlightColor}`;
          } else {
            el.style.color = primaryColor;
            el.style.transform = 'scale(1.0)';
            el.style.textShadow = '0 2px 6px rgba(0,0,0,0.85)';
          }
        });
      }, 340);
      return;
    }

    // 2. Typewriter Effect
    if (animLower.includes("typewriter")) {
      containerEl.style.color = primaryColor;
      let charIdx = 0;
      containerEl.innerHTML = `<span id="typewriter-text"></span><span class="typewriter-caret font-normal opacity-90 animate-pulse">|</span>`;
      const textEl = containerEl.querySelector('#typewriter-text');

      activeAnimationTimer = setInterval(() => {
        charIdx++;
        if (charIdx > cleanText.length) {
          // Pause then restart
          setTimeout(() => {
            charIdx = 0;
            if (textEl) textEl.textContent = "";
          }, 800);
          return;
        }
        if (textEl) textEl.textContent = cleanText.slice(0, charIdx);
      }, 65);
      return;
    }

    // 3. Word Reveal / Staggered Words
    if (animLower.includes("word reveal") || animLower.includes("reveal")) {
      containerEl.innerHTML = words.map((w, idx) => `
        <span class="inline-block animate-caption-word-reveal" style="color: ${primaryColor}; animation-delay: ${idx * 110}ms;">
          ${w}&nbsp;
        </span>
      `).join("");
      return;
    }

    // 4. Highlight Sweep
    if (animLower.includes("sweep") || animLower.includes("highlight sweep")) {
      containerEl.innerHTML = `
        <span class="caption-highlight-sweep" style="color: ${primaryColor}; --highlight-col: ${highlightColor};">
          ${cleanText}
        </span>
      `;
      return;
    }

    // 5. Gradient Highlight
    if (animLower.includes("gradient")) {
      containerEl.innerHTML = `
        <span class="caption-gradient-flow" style="--col-a: ${primaryColor}; --col-b: ${highlightColor};">
          ${cleanText}
        </span>
      `;
      return;
    }

    // 6. Character Reveal
    if (animLower.includes("character")) {
      const chars = cleanText.split("");
      containerEl.innerHTML = chars.map((ch, idx) => `
        <span class="inline-block animate-caption-char" style="color: ${primaryColor}; animation-delay: ${idx * 30}ms;">
          ${ch === " " ? "&nbsp;" : ch}
        </span>
      `).join("");
      return;
    }

    // 7. Elastic Pop
    if (animLower.includes("elastic")) {
      containerEl.innerHTML = `<span class="inline-block animate-caption-elastic" style="color: ${primaryColor};">${cleanText}</span>`;
      return;
    }

    // 8. Pop
    if (animLower.includes("pop")) {
      containerEl.innerHTML = `<span class="inline-block animate-caption-pop" style="color: ${primaryColor};">${cleanText}</span>`;
      return;
    }

    // 9. Bounce
    if (animLower.includes("bounce")) {
      containerEl.innerHTML = `<span class="inline-block animate-caption-bounce" style="color: ${primaryColor};">${cleanText}</span>`;
      return;
    }

    // 10. Slide Up
    if (animLower.includes("slide up")) {
      containerEl.innerHTML = `<span class="inline-block animate-caption-slide-up" style="color: ${primaryColor};">${cleanText}</span>`;
      return;
    }

    // 11. Slide Down
    if (animLower.includes("slide down")) {
      containerEl.innerHTML = `<span class="inline-block animate-caption-slide-down" style="color: ${primaryColor};">${cleanText}</span>`;
      return;
    }

    // 12. Smooth Zoom
    if (animLower.includes("zoom")) {
      containerEl.innerHTML = `<span class="inline-block animate-caption-zoom" style="color: ${primaryColor};">${cleanText}</span>`;
      return;
    }

    // 13. Minimal Fade
    if (animLower.includes("minimal fade")) {
      containerEl.innerHTML = `<span class="inline-block animate-caption-minimal-fade" style="color: ${primaryColor};">${cleanText}</span>`;
      return;
    }

    // 14. Split Word Reveal
    if (animLower.includes("split")) {
      containerEl.innerHTML = words.map((w, idx) => `
        <span class="inline-block ${idx % 2 === 0 ? 'animate-caption-slide-up' : 'animate-caption-slide-down'}" style="color: ${idx % 2 === 0 ? highlightColor : primaryColor}; animation-delay: ${idx * 90}ms;">
          ${w}&nbsp;
        </span>
      `).join("");
      return;
    }

    // 15. Default: Fade
    containerEl.innerHTML = `<span class="inline-block animate-caption-fade" style="color: ${primaryColor};">${cleanText}</span>`;
  }

  return {
    PRESET_ANIMATIONS,
    renderLiveCaption,
    stopActiveAnimation
  };
});

