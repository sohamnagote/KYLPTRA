// KLYPTRA Flowfield — Real GPU-accelerated organic fluid motion shader
// Continuously animated domain-warped ribbon flowfield beneath Liquid Glass
(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.initBackgroundShader = factory();
  }
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  return function initBackgroundShader(canvasId = "bg-shader") {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;

    // Use WebGL2 if available for optimal performance, fallback to WebGL1
    let gl = canvas.getContext("webgl2", { alpha: false, antialias: false, powerPreference: "high-performance" });
    let isWebGL2 = true;
    if (!gl) {
      isWebGL2 = false;
      gl = canvas.getContext("webgl", { alpha: false, antialias: false, powerPreference: "default" });
    }
    if (!gl) {
      initCanvas2DFallback(canvas);
      return;
    }

    const vsSource = isWebGL2 ? `#version 300 es
      in vec2 position;
      void main() {
        gl_Position = vec4(position, 0.0, 1.0);
      }
    ` : `
      attribute vec2 position;
      void main() {
        gl_Position = vec4(position, 0.0, 1.0);
      }
    `;

    const fsSource = isWebGL2 ? `#version 300 es
      precision highp float;
      out vec4 fragColor;
      uniform vec2 u_resolution;
      uniform float u_time;
      uniform vec3 u_base;
      uniform vec3 u_ribbon1;
      uniform vec3 u_ribbon2;
      uniform vec3 u_highlight;

      // 2D Rotation
      mat2 rot(float a) {
        float c = cos(a), s = sin(a);
        return mat2(c, -s, s, c);
      }

      // Smooth organic gradient noise
      vec2 hash2(vec2 p) {
        p = vec2(dot(p, vec2(127.1, 311.7)), dot(p, vec2(269.5, 183.3)));
        return -1.0 + 2.0 * fract(sin(p) * 43758.5453123);
      }

      float gnoise(vec2 p) {
        vec2 i = floor(p);
        vec2 f = fract(p);
        vec2 u = f * f * (3.0 - 2.0 * f);
        return mix(mix(dot(hash2(i + vec2(0.0, 0.0)), f - vec2(0.0, 0.0)),
                       dot(hash2(i + vec2(1.0, 0.0)), f - vec2(1.0, 0.0)), u.x),
                   mix(dot(hash2(i + vec2(0.0, 1.0)), f - vec2(0.0, 1.0)),
                       dot(hash2(i + vec2(1.0, 1.0)), f - vec2(1.0, 1.0)), u.x), u.y);
      }

      float fbm(vec2 p) {
        float v = 0.0;
        float a = 0.55;
        mat2 r = rot(0.55);
        for (int i = 0; i < 4; i++) {
          v += a * gnoise(p);
          p = r * p * 2.05;
          a *= 0.5;
        }
        return v;
      }

      void main() {
        vec2 p = (gl_FragCoord.xy * 2.0 - u_resolution.xy) / min(u_resolution.x, u_resolution.y);
        float t = u_time * 0.16;

        // KLYPTRA Flowfield: 2-stage organic domain warping
        vec2 q = vec2(
          fbm(p * 1.2 + vec2(t * 0.14, t * 0.08)),
          fbm(p * 1.2 + vec2(2.4, 1.8) - vec2(t * 0.09, t * 0.12))
        );

        vec2 r = vec2(
          fbm(p * 1.4 + 2.8 * q + vec2(1.7, 9.2) + vec2(t * 0.12, -t * 0.08)),
          fbm(p * 1.4 + 2.8 * q + vec2(8.3, 2.8) + vec2(-t * 0.07, t * 0.11))
        );

        float f = fbm(p * 1.6 + 3.2 * r);

        // Fluid ribbon contours & caustics
        float ribbon = smoothstep(-0.35, 0.55, f + 0.3 * sin(p.x * 1.5 + t));
        float contour = smoothstep(0.35, 0.8, sin(f * 4.71 + t * 0.6) * 0.5 + 0.5);
        float sheen = pow(clamp(f * 1.25 + 0.25, 0.0, 1.0), 3.2) * 0.4;

        vec3 col = mix(u_base, u_ribbon1, ribbon);
        col = mix(col, u_ribbon2, contour * 0.55);
        col += u_highlight * sheen;

        fragColor = vec4(col, 1.0);
      }
    ` : `
      precision highp float;
      uniform vec2 u_resolution;
      uniform float u_time;
      uniform vec3 u_base;
      uniform vec3 u_ribbon1;
      uniform vec3 u_ribbon2;
      uniform vec3 u_highlight;

      mat2 rot(float a) {
        float c = cos(a), s = sin(a);
        return mat2(c, -s, s, c);
      }

      vec2 hash2(vec2 p) {
        p = vec2(dot(p, vec2(127.1, 311.7)), dot(p, vec2(269.5, 183.3)));
        return -1.0 + 2.0 * fract(sin(p) * 43758.5453123);
      }

      float gnoise(vec2 p) {
        vec2 i = floor(p);
        vec2 f = fract(p);
        vec2 u = f * f * (3.0 - 2.0 * f);
        return mix(mix(dot(hash2(i + vec2(0.0, 0.0)), f - vec2(0.0, 0.0)),
                       dot(hash2(i + vec2(1.0, 0.0)), f - vec2(1.0, 0.0)), u.x),
                   mix(dot(hash2(i + vec2(0.0, 1.0)), f - vec2(0.0, 1.0)),
                       dot(hash2(i + vec2(1.0, 1.0)), f - vec2(1.0, 1.0)), u.x), u.y);
      }

      float fbm(vec2 p) {
        float v = 0.0;
        float a = 0.55;
        mat2 r = rot(0.55);
        for (int i = 0; i < 4; i++) {
          v += a * gnoise(p);
          p = r * p * 2.05;
          a *= 0.5;
        }
        return v;
      }

      void main() {
        vec2 p = (gl_FragCoord.xy * 2.0 - u_resolution.xy) / min(u_resolution.x, u_resolution.y);
        float t = u_time * 0.16;

        vec2 q = vec2(
          fbm(p * 1.2 + vec2(t * 0.14, t * 0.08)),
          fbm(p * 1.2 + vec2(2.4, 1.8) - vec2(t * 0.09, t * 0.12))
        );

        vec2 r = vec2(
          fbm(p * 1.4 + 2.8 * q + vec2(1.7, 9.2) + vec2(t * 0.12, -t * 0.08)),
          fbm(p * 1.4 + 2.8 * q + vec2(8.3, 2.8) + vec2(-t * 0.07, t * 0.11))
        );

        float f = fbm(p * 1.6 + 3.2 * r);

        float ribbon = smoothstep(-0.35, 0.55, f + 0.3 * sin(p.x * 1.5 + t));
        float contour = smoothstep(0.35, 0.8, sin(f * 4.71 + t * 0.6) * 0.5 + 0.5);
        float sheen = pow(clamp(f * 1.25 + 0.25, 0.0, 1.0), 3.2) * 0.4;

        vec3 col = mix(u_base, u_ribbon1, ribbon);
        col = mix(col, u_ribbon2, contour * 0.55);
        col += u_highlight * sheen;

        gl_FragColor = vec4(col, 1.0);
      }
    `;

    function createShader(gl, type, source) {
      const s = gl.createShader(type);
      gl.shaderSource(s, source);
      gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) {
        console.warn("Shader compile error:", gl.getShaderInfoLog(s));
      }
      return s;
    }

    const vs = createShader(gl, gl.VERTEX_SHADER, vsSource);
    const fs = createShader(gl, gl.FRAGMENT_SHADER, fsSource);
    const program = gl.createProgram();
    gl.attachShader(program, vs);
    gl.attachShader(program, fs);
    gl.linkProgram(program);

    const posBuffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, posBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([
      -1, -1,
       1, -1,
      -1,  1,
      -1,  1,
       1, -1,
       1,  1,
    ]), gl.STATIC_DRAW);

    const posLocation = gl.getAttribLocation(program, "position");
    const resLocation = gl.getUniformLocation(program, "u_resolution");
    const timeLocation = gl.getUniformLocation(program, "u_time");
    const baseLocation = gl.getUniformLocation(program, "u_base");
    const ribbon1Location = gl.getUniformLocation(program, "u_ribbon1");
    const ribbon2Location = gl.getUniformLocation(program, "u_ribbon2");
    const highlightLocation = gl.getUniformLocation(program, "u_highlight");

    function resize() {
      // Crisp 0.75 device resolution balance for smooth 60 FPS
      const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
      const w = Math.max(320, Math.floor(window.innerWidth * dpr * 0.75));
      const h = Math.max(240, Math.floor(window.innerHeight * dpr * 0.75));
      if (canvas.width !== w || canvas.height !== h) {
        canvas.width = w;
        canvas.height = h;
        gl.viewport(0, 0, w, h);
      }
    }

    window.addEventListener("resize", resize);
    resize();

    // Curated KLYPTRA Flowfield Palettes:
    // Light: Sophisticated pearl base, soft silver contours, muted lavender drift, clean specular rim
    // Dark: Graphite slate base, rich charcoal ribbons, subtle deep indigo flow, gentle surface sheen
    const PALETTES = {
      light: {
        base: [0.953, 0.957, 0.968],      // #F3F4F7 Pearl Base
        ribbon1: [0.886, 0.902, 0.937],   // #E2E6EF Soft Silver
        ribbon2: [0.815, 0.839, 0.886],   // #D0D6E2 Muted Lavender Drift
        highlight: [0.28, 0.32, 0.40]     // Specular diffusion
      },
      dark: {
        base: [0.075, 0.080, 0.092],      // #131417 Deep Graphite Base
        ribbon1: [0.110, 0.120, 0.145],   // #1C1E25 Rich Charcoal Ribbon
        ribbon2: [0.155, 0.175, 0.225],   // #272C39 Subtle Muted Indigo
        highlight: [0.22, 0.25, 0.34]     // Restrained rim sheen
      }
    };

    let activeTheme = document.documentElement.classList.contains("dark") ? "dark" : "light";
    let curBase = [...PALETTES[activeTheme].base];
    let curRib1 = [...PALETTES[activeTheme].ribbon1];
    let curRib2 = [...PALETTES[activeTheme].ribbon2];
    let curHigh = [...PALETTES[activeTheme].highlight];

    let targetBase = [...curBase];
    let targetRib1 = [...curRib1];
    let targetRib2 = [...curRib2];
    let targetHigh = [...curHigh];

    let startTime = performance.now();
    let isRunning = true;
    let isReducedMotion = false;
    let animFrameId = null;

    if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      isReducedMotion = true;
    }

    function lerp(a, b, t) {
      return a + (b - a) * t;
    }

    function render(now) {
      if (!isRunning) return;

      // Color transition lerping
      const tLerp = 0.06;
      for (let i = 0; i < 3; i++) {
        curBase[i] = lerp(curBase[i], targetBase[i], tLerp);
        curRib1[i] = lerp(curRib1[i], targetRib1[i], tLerp);
        curRib2[i] = lerp(curRib2[i], targetRib2[i], tLerp);
        curHigh[i] = lerp(curHigh[i], targetHigh[i], tLerp);
      }

      gl.useProgram(program);
      gl.enableVertexAttribArray(posLocation);
      gl.bindBuffer(gl.ARRAY_BUFFER, posBuffer);
      gl.vertexAttribPointer(posLocation, 2, gl.FLOAT, false, 0, 0);

      gl.uniform2f(resLocation, canvas.width, canvas.height);
      const elapsed = isReducedMotion ? 0.0 : (now - startTime) * 0.001;
      gl.uniform1f(timeLocation, elapsed);
      gl.uniform3fv(baseLocation, curBase);
      gl.uniform3fv(ribbon1Location, curRib1);
      gl.uniform3fv(ribbon2Location, curRib2);
      gl.uniform3fv(highlightLocation, curHigh);

      gl.drawArrays(gl.TRIANGLES, 0, 6);

      if (!isReducedMotion) {
        animFrameId = requestAnimationFrame(render);
      }
    }

    function startLoop() {
      if (!animFrameId && isRunning && !isReducedMotion) {
        animFrameId = requestAnimationFrame(render);
      } else if (isReducedMotion) {
        render(performance.now());
      }
    }

    function stopLoop() {
      if (animFrameId) {
        cancelAnimationFrame(animFrameId);
        animFrameId = null;
      }
    }

    document.addEventListener("visibilitychange", () => {
      if (document.hidden) {
        stopLoop();
      } else if (isRunning && !isReducedMotion) {
        startLoop();
      }
    });

    window.__klyptraShader = {
      setTheme: function(theme) {
        const pal = PALETTES[theme] || PALETTES.light;
        targetBase = [...pal.base];
        targetRib1 = [...pal.ribbon1];
        targetRib2 = [...pal.ribbon2];
        targetHigh = [...pal.highlight];
        if (!animFrameId && isRunning) {
          startLoop();
        }
      },
      setEnabled: function(enabled) {
        isRunning = !!enabled;
        canvas.style.display = enabled ? "block" : "none";
        if (isRunning) {
          startLoop();
        } else {
          stopLoop();
        }
      },
      setReducedMotion: function(reduced) {
        isReducedMotion = !!reduced;
        if (isReducedMotion) {
          stopLoop();
          render(performance.now());
        } else if (isRunning) {
          startLoop();
        }
      },
      // Diagnostics hook for tests
      getFrameState: function() {
        return {
          isRunning,
          isReducedMotion,
          theme: targetBase[0] < 0.5 ? "dark" : "light",
          elapsedSeconds: (performance.now() - startTime) * 0.001
        };
      }
    };

    startLoop();
  };

  function initCanvas2DFallback(canvas) {
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    let isRunning = true;
    let animId = null;
    let t = 0;

    function drawFallback() {
      if (!isRunning) return;
      t += 0.02;
      const isDark = document.documentElement.classList.contains("dark");
      const w = canvas.width = window.innerWidth;
      const h = canvas.height = window.innerHeight;

      const grad = ctx.createLinearGradient(
        w * 0.5 + Math.sin(t) * 100,
        0,
        w * 0.5 + Math.cos(t) * 100,
        h
      );

      if (isDark) {
        grad.addColorStop(0, "#131417");
        grad.addColorStop(0.5, "#1C1E25");
        grad.addColorStop(1, "#272C39");
      } else {
        grad.addColorStop(0, "#F3F4F7");
        grad.addColorStop(0.5, "#E2E6EF");
        grad.addColorStop(1, "#D0D6E2");
      }

      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, w, h);
      animId = requestAnimationFrame(drawFallback);
    }

    drawFallback();

    window.__klyptraShader = {
      setTheme: function() {},
      setEnabled: function(e) {
        isRunning = !!e;
        canvas.style.display = e ? "block" : "none";
        if (isRunning && !animId) animId = requestAnimationFrame(drawFallback);
      },
      setReducedMotion: function(r) {
        if (r && animId) { cancelAnimationFrame(animId); animId = null; }
      },
      getFrameState: function() {
        return { isRunning, isReducedMotion: false, fallback: true, elapsedSeconds: t };
      }
    };
  }
});
