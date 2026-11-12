// GPU-efficient, subtle continuous ambient background shader supporting Light & Dark Graphite modes
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

    const gl = canvas.getContext("webgl", { alpha: true, antialias: false, powerPreference: "low-power" });
    if (!gl) {
      initCanvas2DFallback(canvas);
      return;
    }

    const vsSource = `
      attribute vec2 position;
      void main() {
        gl_Position = vec4(position, 0.0, 1.0);
      }
    `;

    const fsSource = `
      precision mediump float;
      uniform vec2 u_resolution;
      uniform float u_time;
      uniform vec3 u_colA;
      uniform vec3 u_colB;
      uniform vec3 u_colC;
      uniform float u_intensity;

      void main() {
        vec2 st = gl_FragCoord.xy / u_resolution;
        float t = u_time * 0.11;

        // Subtle drifting harmonic noise
        float n1 = sin(st.x * 2.4 + t) * cos(st.y * 1.9 - t * 0.65);
        float n2 = cos(st.x * 1.7 - t * 0.75) * sin(st.y * 2.1 + t);
        float blend = smoothstep(-0.85, 0.85, n1 + n2);

        vec3 color = mix(u_colA, mix(u_colB, u_colC, blend), u_intensity);
        gl_FragColor = vec4(color, 1.0);
      }
    `;

    function createShader(gl, type, source) {
      const s = gl.createShader(type);
      gl.shaderSource(s, source);
      gl.compileShader(s);
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
    const colALocation = gl.getUniformLocation(program, "u_colA");
    const colBLocation = gl.getUniformLocation(program, "u_colB");
    const colCLocation = gl.getUniformLocation(program, "u_colC");
    const intensityLocation = gl.getUniformLocation(program, "u_intensity");

    function resize() {
      // Render at 1/2 resolution for minimal GPU footprint
      const scale = 0.5;
      const w = Math.max(320, Math.floor(window.innerWidth * scale));
      const h = Math.max(240, Math.floor(window.innerHeight * scale));
      if (canvas.width !== w || canvas.height !== h) {
        canvas.width = w;
        canvas.height = h;
        gl.viewport(0, 0, w, h);
      }
    }

    window.addEventListener("resize", resize);
    resize();

    // Palettes
    const PALETTES = {
      light: {
        colA: [0.984, 0.973, 1.0],   // #fbf8ff (base surface)
        colB: [0.914, 0.867, 1.0],   // #e9ddff (secondary-fixed)
        colC: [0.886, 0.875, 1.0],   // #e2dfff (primary-fixed)
        intensity: 0.32,
        opacity: 0.42
      },
      dark: {
        colA: [0.114, 0.122, 0.141], // #1D1F24 Graphite base
        colB: [0.133, 0.141, 0.165], // #22242A Charcoal surface
        colC: [0.224, 0.200, 0.302], // #39334D Soft Indigo
        intensity: 0.48,
        opacity: 0.45
      }
    };

    let activeTheme = document.documentElement.classList.contains("dark") ? "dark" : "light";
    let currentColA = [...PALETTES[activeTheme].colA];
    let currentColB = [...PALETTES[activeTheme].colB];
    let currentColC = [...PALETTES[activeTheme].colC];
    let currentIntensity = PALETTES[activeTheme].intensity;

    let targetColA = [...currentColA];
    let targetColB = [...currentColB];
    let targetColC = [...currentColC];
    let targetIntensity = currentIntensity;

    let startTime = performance.now();
    let lastFrame = 0;
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

      // Smooth color transition interpolation
      const lerpSpeed = 0.08;
      for (let i = 0; i < 3; i++) {
        currentColA[i] = lerp(currentColA[i], targetColA[i], lerpSpeed);
        currentColB[i] = lerp(currentColB[i], targetColB[i], lerpSpeed);
        currentColC[i] = lerp(currentColC[i], targetColC[i], lerpSpeed);
      }
      currentIntensity = lerp(currentIntensity, targetIntensity, lerpSpeed);

      // Throttle to ~30fps for ultra-low power consumption (< 0.1% GPU)
      if (now - lastFrame > 32) {
        lastFrame = now;
        gl.useProgram(program);
        gl.enableVertexAttribArray(posLocation);
        gl.bindBuffer(gl.ARRAY_BUFFER, posBuffer);
        gl.vertexAttribPointer(posLocation, 2, gl.FLOAT, false, 0, 0);

        gl.uniform2f(resLocation, canvas.width, canvas.height);
        gl.uniform1f(timeLocation, isReducedMotion ? 0.0 : (now - startTime) * 0.001);
        gl.uniform3fv(colALocation, currentColA);
        gl.uniform3fv(colBLocation, currentColB);
        gl.uniform3fv(colCLocation, currentColC);
        gl.uniform1f(intensityLocation, currentIntensity);

        gl.drawArrays(gl.TRIANGLES, 0, 6);

        if (isReducedMotion) {
          return;
        }
      }

      animFrameId = requestAnimationFrame(render);
    }

    function startLoop() {
      if (!animFrameId && isRunning) {
        animFrameId = requestAnimationFrame(render);
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
      } else if (isRunning) {
        startLoop();
      }
    });

    window.__klyptraShader = {
      setTheme: function(theme) {
        const pal = PALETTES[theme] || PALETTES.light;
        targetColA = [...pal.colA];
        targetColB = [...pal.colB];
        targetColC = [...pal.colC];
        targetIntensity = pal.intensity;
        canvas.style.opacity = pal.opacity;
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
          // Render single crisp frame
          gl.useProgram(program);
          gl.enableVertexAttribArray(posLocation);
          gl.bindBuffer(gl.ARRAY_BUFFER, posBuffer);
          gl.vertexAttribPointer(posLocation, 2, gl.FLOAT, false, 0, 0);
          gl.uniform2f(resLocation, canvas.width, canvas.height);
          gl.uniform1f(timeLocation, 0.0);
          gl.uniform3fv(colALocation, targetColA);
          gl.uniform3fv(colBLocation, targetColB);
          gl.uniform3fv(colCLocation, targetColC);
          gl.uniform1f(intensityLocation, targetIntensity);
          gl.drawArrays(gl.TRIANGLES, 0, 6);
        } else if (isRunning) {
          startLoop();
        }
      }
    };

    startLoop();
  };

  function initCanvas2DFallback(canvas) {
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    let isRunning = true;

    window.__klyptraShader = {
      setTheme: function(theme) {
        const bg = (theme === "dark") ? "#1D1F24" : "#fbf8ff";
        ctx.fillStyle = bg;
        ctx.fillRect(0, 0, canvas.width, canvas.height);
      },
      setEnabled: function(e) { isRunning = !!e; canvas.style.display = e ? "block" : "none"; },
      setReducedMotion: function() {}
    };
  }
});
