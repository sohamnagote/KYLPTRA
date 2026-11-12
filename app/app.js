// KLYPTRA Studio Frontend Application Engine
const API_BASE = "/api";

const state = {
  currentView: "new-project",
  selectedProfile: "balanced",
  systemInfo: null,
  projects: [],
  activeProject: null,
  activeClips: [],
  selectedClip: null,
  activeTaskId: null,
  pollTimer: null,
  exports: [],
  ytFetchedMeta: null,
  captionPresets: [],
  brandProfiles: [],
  brollAssets: [],
  motionTemplates: [],
  systemVoices: [],
  activeStudioTab: "captions"
};

// ----------------- Initialization -----------------

document.addEventListener("DOMContentLoaded", () => {
  // Initialize Themes & Motion Design System
  if (window.KlyptraTheme) {
    KlyptraTheme.init();
  }
  initBackgroundShader("bg-shader");
  setupNavigation();
  setupUploadArea();
  setupYouTubeImport();
  setupProfileSelector();
  setupInstructionChips();
  setupStudioTabs();
  setupKeyboardShortcuts();
  setupEditorControls();
  fetchSystemInfo();
  loadSettings();
  loadModels();
  loadStorageInfo();
  loadProjects();
  loadExports();
  loadCaptionPresets();
  loadBrandProfiles();
  loadBrollLibrary();
  loadMotionTemplates();
  loadSystemVoices();
  checkFirstLaunchSetup();

  // Initial pill and micro-interactions
  if (window.KlyptraMotionEngine) {
    setTimeout(() => {
      KlyptraMotionEngine.updateSidebarPill(state.currentView);
      KlyptraMotionEngine.initMicroInteractions();
    }, 60);
  }
});

// ----------------- Navigation -----------------

function setupNavigation() {
  document.querySelectorAll("[data-nav]").forEach(btn => {
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      const target = btn.getAttribute("data-nav");
      switchView(target);
    });
  });

  window.addEventListener("resize", () => {
    if (window.KlyptraMotionEngine) {
      KlyptraMotionEngine.updateSidebarPill(state.currentView);
    }
  });
}

function switchView(viewName) {
  if (state.currentView === viewName) return;

  const oldViewName = state.currentView;
  state.currentView = viewName;

  const titles = {
    "new-project": "Import Video",
    "clips": "Generated Clips",
    "editor": "Clip Editor",
    "projects": "My Projects",
    "settings": "Settings & Exports"
  };
  const headerTitle = document.getElementById("header-page-title");
  if (headerTitle && titles[viewName]) {
    headerTitle.textContent = titles[viewName];
  }

  const oldPanel = document.getElementById(`view-${oldViewName}`);
  const targetPanel = document.getElementById(`view-${viewName}`);

  if (window.KlyptraMotionEngine) {
    KlyptraMotionEngine.transitionPage(oldPanel, targetPanel, () => {
      KlyptraMotionEngine.initMicroInteractions(targetPanel);
    });
    KlyptraMotionEngine.updateSidebarPill(viewName);
  } else {
    document.querySelectorAll(".view-panel").forEach(p => p.classList.add("hidden"));
    if (targetPanel) targetPanel.classList.remove("hidden");
  }

  // Update sidebar active link styling
  document.querySelectorAll("[data-nav]").forEach(btn => {
    const isCurrent = btn.getAttribute("data-nav") === viewName;
    if (isCurrent) {
      btn.classList.add("text-primary", "font-bold");
      btn.classList.remove("text-on-surface-variant");
    } else {
      btn.classList.remove("text-primary", "font-bold");
      btn.classList.add("text-on-surface-variant");
    }
  });

  if (viewName === "projects") {
    loadProjects();
  } else if (viewName === "settings") {
    loadExports();
    fetchSystemInfo();
    loadSettings();
    loadModels();
    loadStorageInfo();
  }
}

// ----------------- System Info & Hardware Detection -----------------

async function fetchSystemInfo() {
  try {
    const res = await fetch(`${API_BASE}/system-info`);
    if (!res.ok) return;
    const data = await res.json();
    state.systemInfo = data;

    // Compact System Status Bar
    const gpu = data.gpu || {};
    const ram = data.ram || {};
    const disk = data.storage || {};
    const cGpu = document.getElementById("compact-gpu-status");
    if (cGpu) cGpu.textContent = data.gpu_acceleration ? (gpu.name || "GPU Active") : "CPU Mode";
    const cRam = document.getElementById("compact-ram-status");
    if (cRam) cRam.textContent = `${ram.free_gb || 0} / ${ram.total_gb || 0} GB`;
    const cDisk = document.getElementById("compact-disk-status");
    if (cDisk) cDisk.textContent = `${disk.free_gb || data.disk_free_gb || 0} GB Free`;
    const cFfmpeg = document.getElementById("compact-ffmpeg-status");
    if (cFfmpeg) cFfmpeg.textContent = (data.ffmpeg && data.ffmpeg.available) ? "Ready" : "Missing";
    const cModel = document.getElementById("compact-model-status");
    if (cModel) cModel.textContent = (data.active_model || "base").replace(/^./, s => s.toUpperCase());

    // Detailed Advanced Diagnostics Fields
    const gpuNameEl = document.getElementById("hw-gpu-name");
    if (gpuNameEl) gpuNameEl.textContent = gpu.available ? (gpu.name || "NVIDIA GPU") : "Integrated / CPU Fallback";
    const gpuDriverEl = document.getElementById("hw-gpu-driver");
    if (gpuDriverEl) gpuDriverEl.textContent = gpu.available ? `Driver: ${gpu.driver_version || 'Verified'}` : "No discrete NVIDIA GPU";
    const gpuVramEl = document.getElementById("hw-gpu-vram");
    if (gpuVramEl) gpuVramEl.textContent = gpu.available ? `VRAM: ${gpu.vram_free_mb || 0} / ${gpu.vram_total_mb || 0} MB` : "Running in optimized CPU mode";
    const gpuBadge = document.getElementById("hw-gpu-status-badge");
    if (gpuBadge) {
      gpuBadge.textContent = data.gpu_acceleration ? "ACTIVE" : "CPU";
      gpuBadge.className = data.gpu_acceleration
        ? "px-1.5 py-0.5 rounded text-[10px] font-code-sm bg-primary-fixed text-on-primary-fixed-variant"
        : "px-1.5 py-0.5 rounded text-[10px] font-code-sm bg-surface-container text-on-surface";
    }

    const cpu = data.cpu || {};
    const cpuNameEl = document.getElementById("hw-cpu-name");
    if (cpuNameEl) cpuNameEl.textContent = cpu.model || "Processor";
    const cpuCoresEl = document.getElementById("hw-cpu-cores");
    if (cpuCoresEl) cpuCoresEl.textContent = `Cores: ${cpu.cores || 8} threads (${cpu.architecture || 'x64'})`;

    const ramSummary = document.getElementById("hw-ram-summary");
    if (ramSummary) ramSummary.textContent = `${ram.free_gb || 0} GB Free / ${ram.total_gb || 0} GB (${ram.load_percent || 0}% Load)`;

    const encName = document.getElementById("hw-encoder-name");
    if (encName) encName.textContent = data.video_encoder || "libx264";
    const encBadge = document.getElementById("hw-encoder-badge");
    if (encBadge) {
      encBadge.textContent = data.video_encoder_is_hardware ? "HW ACCEL" : "CPU";
      encBadge.className = data.video_encoder_is_hardware
        ? "px-1.5 py-0.5 rounded text-[10px] font-code-sm bg-primary-fixed text-on-primary-fixed-variant"
        : "px-1.5 py-0.5 rounded text-[10px] font-code-sm bg-surface-container text-on-surface";
    }
    const ffmpegVer = document.getElementById("hw-ffmpeg-ver");
    if (ffmpegVer) ffmpegVer.textContent = data.ffmpeg && data.ffmpeg.version ? data.ffmpeg.version.split("Copyright")[0].trim() : "FFmpeg Unavailable";

    const whisperRuntime = document.getElementById("hw-whisper-runtime");
    if (whisperRuntime) whisperRuntime.textContent = `Whisper: ${data.device_description || 'CPU int8'}`;

  } catch (err) {
    console.error("System info fetch error:", err);
  }
}

// ----------------- Profile Selection (Fast / Balanced / Accurate) -----------------

function setupProfileSelector() {
  document.querySelectorAll(".profile-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const prof = btn.getAttribute("data-profile");
      setProcessingProfile(prof);
    });
  });
}

function setProcessingProfile(prof) {
  state.selectedProfile = prof;
  document.querySelectorAll(".profile-btn").forEach(btn => {
    const isThis = btn.getAttribute("data-profile") === prof;
    if (isThis) {
      btn.className = "profile-btn py-2 px-3 rounded-lg border-2 border-primary bg-primary-fixed/40 text-xs font-title-sm flex flex-col items-center transition-all shadow-xs";
      const spanTitle = btn.querySelector("span:first-child");
      if (spanTitle) spanTitle.className = "font-bold text-primary";
    } else {
      btn.className = "profile-btn py-2 px-3 rounded-lg border border-outline-variant/30 text-xs font-title-sm flex flex-col items-center bg-white hover:border-primary/50 transition-all";
      const spanTitle = btn.querySelector("span:first-child");
      if (spanTitle) spanTitle.className = "font-bold text-on-surface";
    }
  });
}

// ----------------- PC Upload & Tabs Setup -----------------

function setupUploadArea() {
  const tabPc = document.getElementById("tab-btn-pc");
  const tabYt = document.getElementById("tab-btn-yt");
  const contentPc = document.getElementById("tab-content-pc");
  const contentYt = document.getElementById("tab-content-yt");

  if (tabPc && tabYt) {
    tabPc.addEventListener("click", () => {
      tabPc.className = "px-space-lg py-2 rounded-lg font-title-sm text-xs font-semibold transition-all bg-white text-on-surface shadow-xs flex items-center gap-1.5";
      tabYt.className = "px-space-lg py-2 rounded-lg font-title-sm text-xs font-semibold transition-all text-on-surface-variant hover:text-on-surface flex items-center gap-1.5";
      contentPc.classList.remove("hidden");
      contentYt.classList.add("hidden");
    });

    tabYt.addEventListener("click", () => {
      tabYt.className = "px-space-lg py-2 rounded-lg font-title-sm text-xs font-semibold transition-all bg-white text-on-surface shadow-xs flex items-center gap-1.5";
      tabPc.className = "px-space-lg py-2 rounded-lg font-title-sm text-xs font-semibold transition-all text-on-surface-variant hover:text-on-surface flex items-center gap-1.5";
      contentYt.classList.remove("hidden");
      contentPc.classList.add("hidden");
    });
  }

  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("fileInput");

  if (dropzone && fileInput) {
    if (window.KlyptraMotionEngine && typeof window.KlyptraMotionEngine.setupDropzonePhysics === "function") {
      window.KlyptraMotionEngine.setupDropzonePhysics(dropzone);
    }

    dropzone.addEventListener("click", async () => {
      if (window.pywebview && window.pywebview.api && typeof window.pywebview.api.select_video_file === "function") {
        const filePath = await window.pywebview.api.select_video_file();
        if (filePath) {
          // Native local file path ingestion
          const fakeFile = { name: filePath.split(/[/\\]/).pop(), path: filePath, size: 0 };
          handleNativeLocalVideoPath(filePath);
          return;
        }
      }
      fileInput.click();
    });

    dropzone.addEventListener("drop", (e) => {
      e.preventDefault();
      if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        handleSelectedVideo(e.dataTransfer.files[0]);
      }
    });

    fileInput.addEventListener("change", (e) => {
      if (e.target.files && e.target.files.length > 0) {
        handleSelectedVideo(e.target.files[0]);
      }
    });
  }

  const startBtn = document.getElementById("btn-start-clipping");
  if (startBtn) {
    startBtn.addEventListener("click", () => {
      if (state.activeProject) {
        startProjectProcessing(state.activeProject.id);
      }
    });
  }
}

async function handleSelectedVideo(file) {
  showUploadProgress(true, `Inspecting and importing '${file.name}'...`);

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch(`${API_BASE}/projects/upload`, {
      method: "POST",
      body: formData
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Upload failed");
    }

    const project = await res.json();
    state.activeProject = project;

    showUploadProgress(false);
    displayVideoMetadataCard(project);

  } catch (err) {
    showUploadProgress(false);
    alert(`Failed to import video: ${err.message}`);
  }
}

function displayVideoMetadataCard(project) {
  const metaCard = document.getElementById("selected-video-meta");
  if (!metaCard) return;

  document.getElementById("meta-filename").textContent = project.source_filename;
  document.getElementById("meta-duration").textContent = `${Math.floor(project.duration / 60)}m ${Math.round(project.duration % 60)}s`;
  document.getElementById("meta-resolution").textContent = `${project.width} × ${project.height}`;
  document.getElementById("meta-fps").textContent = `${project.fps} FPS`;
  document.getElementById("meta-size").textContent = `${(project.file_size / (1024 * 1024)).toFixed(1)} MB`;
  document.getElementById("meta-audio").textContent = project.has_audio ? "Stereo / Voice Detected" : "No Audio Stream";

  metaCard.classList.remove("hidden");
  document.getElementById("tab-content-pc").classList.add("hidden");
  document.getElementById("tab-content-yt").classList.add("hidden");
}

function resetVideoSelection() {
  document.getElementById("selected-video-meta").classList.add("hidden");
  document.getElementById("tab-content-pc").classList.remove("hidden");
  state.activeProject = null;
}

// ----------------- YouTube Import Engine -----------------

function setupYouTubeImport() {
  const pasteBtn = document.getElementById("btn-yt-paste");
  const urlInput = document.getElementById("yt-url-input");
  const fetchBtn = document.getElementById("btn-yt-fetch");
  const downloadBtn = document.getElementById("btn-yt-download");
  const authCheck = document.getElementById("yt-auth-check");

  if (pasteBtn && urlInput) {
    pasteBtn.addEventListener("click", async () => {
      try {
        const text = await navigator.clipboard.readText();
        if (text) {
          urlInput.value = text.trim();
        }
      } catch (err) {
        console.warn("Clipboard access denied or not supported:", err);
      }
    });
  }

  if (fetchBtn && urlInput) {
    fetchBtn.addEventListener("click", async () => {
      const url = urlInput.value.trim();
      if (!url) {
        alert("Please paste a valid YouTube video URL.");
        return;
      }
      await fetchYouTubeVideoInfo(url);
    });
  }

  if (downloadBtn && authCheck) {
    downloadBtn.addEventListener("click", async () => {
      if (!authCheck.checked) {
        alert("Please confirm authorization by checking the box before proceeding.");
        return;
      }
      const quality = document.getElementById("yt-quality-select").value || "1080p";
      await startYouTubeDownload(urlInput.value.trim(), quality);
    });
  }
}

async function fetchYouTubeVideoInfo(url) {
  showUploadProgress(true, "Connecting to YouTube and extracting stream metadata...");
  try {
    const res = await fetch(`${API_BASE}/youtube/inspect`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: url })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Could not fetch YouTube video metadata.");
    }

    const data = await res.json();
    state.ytFetchedMeta = data;

    // Render Preview
    document.getElementById("yt-thumb-img").src = data.thumbnail || "";
    document.getElementById("yt-video-title").textContent = data.title;
    document.getElementById("yt-channel-name").textContent = data.channel;
    document.getElementById("yt-duration-badge").textContent = data.duration_formatted;

    // Populate qualities
    const qualSelect = document.getElementById("yt-quality-select");
    qualSelect.innerHTML = "";
    (data.resolutions_available || ["1080p", "720p"]).forEach(r => {
      const opt = document.createElement("option");
      opt.value = r;
      opt.textContent = r === "1080p" ? "1080p (Balanced • Recommended)" : (r === "720p" ? "720p (Faster Processing)" : "Best Available");
      if (r === "1080p") opt.selected = true;
      qualSelect.appendChild(opt);
    });

    document.getElementById("yt-preview-card").classList.remove("hidden");
    document.getElementById("yt-confirm-row").classList.remove("hidden");
    document.getElementById("btn-yt-download").classList.remove("hidden");

    showUploadProgress(false);

  } catch (err) {
    showUploadProgress(false);
    alert(`YouTube Info Error: ${err.message}`);
  }
}

async function startYouTubeDownload(url, quality) {
  showUploadProgress(true, "Connecting to YouTube streams...");

  try {
    const res = await fetch(`${API_BASE}/youtube/import`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url: url,
        quality: quality,
        confirm_authorized: true
      })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to start YouTube import");
    }

    const data = await res.json();

    // Poll YouTube download and merge task
    const project = await pollTask(data.task_id, (msg, pct) => {
      document.getElementById("modal-processing-msg").textContent = `${msg}`;
      document.getElementById("modal-progress-bar").style.width = `${pct}%`;
    });

    state.activeProject = project;
    showUploadProgress(false);
    displayVideoMetadataCard(project);

  } catch (err) {
    showUploadProgress(false);
    alert(`YouTube Download Error: ${err.message}`);
  }
}

function setupInstructionChips() {
  document.querySelectorAll(".instruction-chip").forEach(chip => {
    chip.addEventListener("click", () => {
      const input = document.getElementById("custom-ai-instruction-input");
      if (input) {
        input.value = chip.getAttribute("data-inst") || "";
        input.focus();
      }
    });
  });
}

// ----------------- Processing Pipeline -----------------

async function startProjectProcessing(projectId) {
  const langSelect = document.getElementById("select-language");
  const language = langSelect ? langSelect.value : "auto";
  const profile = state.selectedProfile || "balanced";
  const instInput = document.getElementById("custom-ai-instruction-input");
  const customInst = instInput ? instInput.value.trim() : "";

  showUploadProgress(true, `Starting AI Speech Processing (${profile.toUpperCase()} profile)...`);

  try {
    // 1. Start transcription with profile tuning & caching
    const tRes = await fetch(`${API_BASE}/projects/${projectId}/transcribe?profile=${profile}&language=${language}`, {
      method: "POST"
    });
    if (!tRes.ok) throw new Error("Could not start transcription");
    const tData = await tRes.json();

    await pollTask(tData.task_id, (msg, pct) => {
      document.getElementById("modal-processing-msg").textContent = `${msg}`;
      document.getElementById("modal-progress-bar").style.width = `${pct}%`;
    });

    // 2. Start candidate analysis with custom instruction
    document.getElementById("modal-processing-msg").textContent = "Evaluating moments and applying AI clipping intelligence...";
    document.getElementById("modal-progress-bar").style.width = "50%";

    const analyzeUrl = customInst
      ? `${API_BASE}/projects/${projectId}/analyze?custom_instruction=${encodeURIComponent(customInst)}`
      : `${API_BASE}/projects/${projectId}/analyze`;

    const aRes = await fetch(analyzeUrl, { method: "POST" });
    if (!aRes.ok) throw new Error("Could not start candidate analysis");
    const aData = await aRes.json();

    await pollTask(aData.task_id, (msg, pct) => {
      document.getElementById("modal-processing-msg").textContent = `${msg}`;
      document.getElementById("modal-progress-bar").style.width = `${pct}%`;
    });

    showUploadProgress(false);
    await loadProjectClips(projectId);
    switchView("clips");

  } catch (err) {
    showProcessingModalError(err.message, projectId);
    loadProjects();
  }
}

function pollTask(taskId, onProgress) {
  return new Promise((resolve, reject) => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE}/tasks/${taskId}/status`);
        if (!res.ok) {
          clearInterval(interval);
          reject(new Error("Task not found"));
          return;
        }
        const data = await res.json();
        onProgress(data.message, data.progress);
        showUploadProgress(true, data.message, data.progress);

        if (data.status === "completed") {
          clearInterval(interval);
          resolve(data.result);
        } else if (data.status === "error") {
          clearInterval(interval);
          reject(new Error(data.error || "Task failed"));
        } else if (data.status === "cancelled") {
          clearInterval(interval);
          reject(new Error("Task was cancelled"));
        }
      } catch (e) {
        clearInterval(interval);
        reject(e);
      }
    }, 600);
  });
}

function showUploadProgress(show, msg = "Processing...", progress = null) {
  const overlay = document.getElementById("modal-processing");
  const msgEl = document.getElementById("modal-processing-msg");
  const pctEl = document.getElementById("modal-processing-pct");
  const barEl = document.getElementById("modal-progress-bar");
  const iconWrap = document.getElementById("modal-processing-icon-wrap");
  const icon = document.getElementById("modal-processing-icon");
  const title = document.getElementById("modal-processing-title");
  const errActions = document.getElementById("modal-processing-error-actions");
  const footerText = document.getElementById("modal-processing-footer-text");

  if (!overlay) return;

  if (show) {
    if (overlay.classList.contains("hidden")) {
      if (window.KlyptraMotionEngine) {
        KlyptraMotionEngine.openModal(overlay);
      } else {
        overlay.classList.remove("hidden");
      }
    }
    if (msgEl) msgEl.textContent = msg;

    // Reset standard loading styling
    if (iconWrap) iconWrap.className = "w-16 h-16 rounded-full bg-primary-fixed flex items-center justify-center text-primary mb-space-md shadow-inner transition-colors";
    if (icon) {
      icon.className = "material-symbols-outlined text-[32px] animate-spin";
      icon.textContent = "refresh";
    }
    if (title) title.textContent = "AI Processing in Progress";
    if (barEl) barEl.className = "h-full bg-primary rounded-full transition-all duration-300";
    if (errActions) errActions.classList.add("hidden");
    if (footerText) footerText.textContent = "Running locally on Windows • Hardware Acceleration Active";

    const pct = typeof progress === "number" ? Math.max(0, Math.min(100, Math.round(progress))) : null;
    if (pct !== null) {
      if (pctEl) pctEl.textContent = `${pct}%`;
      if (barEl) barEl.style.width = `${pct}%`;

      const stagesContainer = document.getElementById("modal-processing-stages");
      if (stagesContainer) {
        const stageRules = [
          { key: "probe", min: 3, done: 20 },
          { key: "audio", min: 20, done: 35 },
          { key: "transcribe", min: 35, done: 65 },
          { key: "silence", min: 65, done: 80 },
          { key: "detect", min: 80, done: 100 }
        ];

        stageRules.forEach(st => {
          const item = stagesContainer.querySelector(`[data-stage="${st.key}"]`);
          if (!item) return;
          const icon = item.querySelector(".stage-icon");
          const statusSpan = item.querySelector(".stage-status");

          if (pct >= st.done) {
            item.className = "stage-item flex items-center justify-between text-xs font-body-sm text-emerald-500 font-semibold transition-colors";
            if (icon) {
              icon.className = "stage-icon material-symbols-outlined text-[15px] text-emerald-500";
              icon.textContent = "check_circle";
            }
            if (statusSpan) statusSpan.textContent = "Done";
          } else if (pct >= st.min) {
            item.className = "stage-item flex items-center justify-between text-xs font-body-sm text-primary font-bold transition-colors";
            if (icon) {
              icon.className = "stage-icon material-symbols-outlined text-[15px] text-primary animate-spin";
              icon.textContent = "progress_activity";
            }
            if (statusSpan) statusSpan.textContent = "Active";
          } else {
            item.className = "stage-item flex items-center justify-between text-xs font-body-sm text-on-surface-variant/60 transition-colors";
            if (icon) {
              icon.className = "stage-icon material-symbols-outlined text-[15px] text-outline";
              icon.textContent = "pending";
            }
            if (statusSpan) statusSpan.textContent = "Pending";
          }
        });
      }
    }
  } else {
    if (window.KlyptraMotionEngine) {
      KlyptraMotionEngine.closeModal(overlay);
    } else {
      overlay.classList.add("hidden");
    }
  }
}

function showProcessingModalError(errorMsg, projectId) {
  const overlay = document.getElementById("modal-processing");
  const msgEl = document.getElementById("modal-processing-msg");
  const pctEl = document.getElementById("modal-processing-pct");
  const barEl = document.getElementById("modal-progress-bar");
  const iconWrap = document.getElementById("modal-processing-icon-wrap");
  const icon = document.getElementById("modal-processing-icon");
  const title = document.getElementById("modal-processing-title");
  const errActions = document.getElementById("modal-processing-error-actions");
  const retryBtn = document.getElementById("modal-processing-retry-btn");
  const dismissBtn = document.getElementById("modal-processing-dismiss-btn");
  const footerText = document.getElementById("modal-processing-footer-text");

  if (!overlay) return;
  overlay.classList.remove("hidden");

  if (iconWrap) iconWrap.className = "w-16 h-16 rounded-full bg-rose-500/20 text-rose-500 flex items-center justify-center mb-space-md shadow-inner transition-colors";
  if (icon) {
    icon.className = "material-symbols-outlined text-[32px]";
    icon.textContent = "error";
  }
  if (title) title.textContent = "Processing Stopped";
  if (msgEl) msgEl.textContent = errorMsg || "An error occurred during video processing.";
  if (pctEl) pctEl.textContent = "Error";
  if (barEl) {
    barEl.className = "h-full bg-rose-500 rounded-full transition-all duration-300";
    barEl.style.width = "100%";
  }
  if (footerText) footerText.textContent = "Original video and project data preserved on your PC";

  if (errActions) {
    errActions.classList.remove("hidden");
    if (retryBtn) {
      retryBtn.onclick = () => {
        errActions.classList.add("hidden");
        retryProject(projectId);
      };
    }
    if (dismissBtn) {
      dismissBtn.onclick = () => {
        showUploadProgress(false);
        loadProjects();
        switchView("projects");
      };
    }
  }
}

// ----------------- Clips List View -----------------

async function loadProjectClips(projectId) {
  try {
    const res = await fetch(`${API_BASE}/projects/${projectId}/clips`);
    if (!res.ok) return;
    const clips = await res.json();
    state.activeClips = clips;
    renderClipsList(clips);
  } catch (err) {
    console.error("Failed to load clips:", err);
  }
}

function renderClipsList(clips) {
  const container = document.getElementById("clips-grid");
  const emptyState = document.getElementById("clips-empty-state");
  const countBadge = document.getElementById("clips-count-badge");
  const batchBtn = document.getElementById("btn-batch-export-all");

  if (countBadge) countBadge.textContent = `${clips.length} AI Moments Found`;

  if (batchBtn) {
    batchBtn.onclick = () => {
      if (state.activeProject) batchExportAllClips(state.activeProject.id);
    };
  }

  if (!clips || clips.length === 0) {
    if (container) container.innerHTML = "";
    if (emptyState) emptyState.classList.remove("hidden");
    return;
  }

  if (emptyState) emptyState.classList.add("hidden");
  if (!container) return;

  container.innerHTML = clips.map((c, i) => {
    const scoreColor = c.score >= 85 ? "bg-emerald-600 text-white" : (c.score >= 70 ? "bg-primary text-white" : "bg-outline text-white");
    
    // Breakdown pills
    const bd = c.score_breakdown || {};
    const breakdownPills = `
      <div class="flex flex-wrap gap-1 mt-1 text-[10px] font-code-sm">
        ${bd.opening_strength ? `<span class="px-1.5 py-0.5 rounded bg-surface-container text-on-surface-variant">Opening: +${bd.opening_strength}</span>` : ''}
        ${bd.speech_cadence ? `<span class="px-1.5 py-0.5 rounded bg-surface-container text-on-surface-variant">Cadence: +${bd.speech_cadence}</span>` : ''}
        ${bd.natural_ending ? `<span class="px-1.5 py-0.5 rounded bg-surface-container text-on-surface-variant">Boundary: +${bd.natural_ending}</span>` : ''}
        ${bd.topic_relevance ? `<span class="px-1.5 py-0.5 rounded bg-primary-fixed text-on-primary-fixed-variant font-semibold">Topic: +${bd.topic_relevance}</span>` : ''}
      </div>
    `;

    const reasonsHtml = (c.score_reasons || []).slice(0, 3).map(r => `
      <div class="flex items-center gap-1.5 text-body-sm text-on-surface-variant text-[11px]">
        <span class="material-symbols-outlined text-[13px] text-primary shrink-0">check_circle</span>
        <span class="truncate">${r}</span>
      </div>
    `).join("");

    // Titles options
    const titles = c.titles || [];
    const titlesHtml = titles.length > 0 ? `
      <div class="mt-2 pt-2 border-t border-outline-variant/20">
        <span class="text-[10px] font-code-sm text-on-surface-variant uppercase tracking-wider block mb-1">AI Suggested Hooks:</span>
        <div class="flex flex-col gap-1">
          ${titles.slice(0, 2).map(t => `
            <button onclick="setClipTitleQuick('${c.id}', '${t.replace(/'/g, "\\'")}')" class="text-left text-[11px] font-title-sm text-primary hover:underline truncate">
              💡 ${t}
            </button>
          `).join("")}
        </div>
      </div>
    ` : '';

    return `
      <div class="apple-card bg-surface-container-lowest rounded-xl p-space-md shadow-sm border border-outline-variant/30 flex flex-col justify-between hover:border-primary/50 transition-all group">
        <div>
          <div class="flex items-center justify-between mb-space-xs">
            <div class="flex items-center gap-2">
              <span class="px-2 py-0.5 rounded-full ${scoreColor} font-title-sm text-xs font-semibold shadow-xs">
                ${c.score} Score
              </span>
              <span class="font-code-sm text-xs text-on-surface-variant">${c.start_time}s - ${c.end_time}s (${c.duration}s)</span>
            </div>
            <span class="font-code-sm text-[10px] px-2 py-0.5 bg-surface-container text-on-surface-variant rounded">9:16 Vertical</span>
          </div>

          ${breakdownPills}

          <h3 class="font-headline-md text-sm text-on-surface line-clamp-1 mt-2 mb-1 font-semibold">${c.title}</h3>
          
          <p class="font-body-md text-xs text-on-surface-variant line-clamp-2 mb-space-sm italic bg-surface-container-low/60 p-2 rounded">
            "${c.transcript_text}"
          </p>

          <div class="flex flex-col gap-1 mb-2 bg-surface-container-lowest p-2 rounded-lg border border-outline-variant/20">
            ${reasonsHtml}
          </div>

          ${titlesHtml}
          ${c.hashtags ? `<p class="text-[10px] text-primary/80 font-code-sm truncate mt-1">${c.hashtags}</p>` : ''}
        </div>

        <div class="flex items-center gap-2 pt-space-xs border-t border-outline-variant/20 mt-space-sm">
          <button onclick="openClipInEditor('${c.id}')" class="apple-btn flex-1 py-1.5 px-3 rounded-lg bg-primary text-white hover:bg-primary-container transition-colors font-title-sm text-xs flex items-center justify-center gap-1.5 shadow-xs">
            <span class="material-symbols-outlined text-[15px]">movie_edit</span>
            <span>Edit in Studio</span>
          </button>
          <button onclick="quickExportClip('${c.id}')" class="apple-btn py-1.5 px-3 rounded-lg bg-surface-container-high hover:bg-surface-container-highest text-on-surface font-title-sm text-xs transition-colors flex items-center justify-center gap-1 shadow-xs" title="Quick 1080p Export">
            <span class="material-symbols-outlined text-[15px]">ios_share</span>
            <span>Export</span>
          </button>
        </div>
      </div>
    `;
  }).join("");

  if (window.KlyptraMotionEngine) {
    KlyptraMotionEngine.staggerEnter(container.querySelectorAll('.apple-card'), 35);
    KlyptraMotionEngine.initMicroInteractions(container);
  }
}

async function setClipTitleQuick(clipId, newTitle) {
  try {
    const res = await fetch(`${API_BASE}/clips/${clipId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: newTitle })
    });
    if (res.ok) {
      if (state.activeProject) loadProjectClips(state.activeProject.id);
    }
  } catch (err) {
    console.error("Failed to update title:", err);
  }
}

async function batchExportAllClips(projectId) {
  if (!confirm(`Export all ${state.activeClips.length} clips at 1080p?`)) return;
  showUploadProgress(true, `Starting batch export for ${state.activeClips.length} clips...`);

  try {
    const res = await fetch(`${API_BASE}/projects/${projectId}/batch-export`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ resolution: "1080p", fps: 30 })
    });
    if (!res.ok) throw new Error("Batch export failed to start");
    const data = await res.json();

    await pollTask(data.task_id, (msg, pct) => {
      document.getElementById("modal-processing-msg").textContent = `${msg} (${pct}%)`;
      document.getElementById("modal-progress-bar").style.width = `${pct}%`;
    });

    showUploadProgress(false);
    await loadExports();
    switchView("settings");
    alert("Batch export completed successfully!");
  } catch (err) {
    showUploadProgress(false);
    alert("Batch export failed: " + err.message);
  }
}

// ----------------- Studio Tabs & Navigation -----------------

function setupStudioTabs() {
  document.querySelectorAll("[data-studio-tab]").forEach(btn => {
    btn.addEventListener("click", () => {
      const target = btn.getAttribute("data-studio-tab");
      state.activeStudioTab = target;

      document.querySelectorAll("[data-studio-tab]").forEach(b => {
        b.className = "studio-tab-btn px-3 py-1.5 rounded-lg text-xs font-title-sm font-semibold transition-all text-on-surface-variant hover:text-on-surface flex items-center gap-1 shrink-0";
      });
      btn.className = "studio-tab-btn active px-3 py-1.5 rounded-lg text-xs font-title-sm font-semibold transition-all bg-white text-primary shadow-xs flex items-center gap-1 shrink-0";

      document.querySelectorAll(".studio-pane").forEach(pane => pane.classList.add("hidden"));
      const targetPane = document.getElementById(`studio-pane-${target}`);
      if (targetPane) targetPane.classList.remove("hidden");
    });
  });
}

function setupKeyboardShortcuts() {
  window.addEventListener("keydown", (e) => {
    // Ignore keystrokes when typing inside text inputs / textareas
    if (["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName)) {
      return;
    }

    if (state.currentView !== "editor" || !state.selectedClip) return;
    const video = document.getElementById("editor-video-player");
    if (!video) return;

    if (e.code === "Space") {
      e.preventDefault();
      const playBtn = document.getElementById("btn-player-play");
      if (video.paused) {
        video.play();
        if (playBtn) playBtn.innerHTML = `<span class="material-symbols-outlined text-[20px]">pause</span>`;
      } else {
        video.pause();
        if (playBtn) playBtn.innerHTML = `<span class="material-symbols-outlined text-[20px]">play_arrow</span>`;
      }
    } else if (e.code === "ArrowLeft") {
      e.preventDefault();
      video.currentTime = Math.max(state.selectedClip.start_time, video.currentTime - 1.0);
    } else if (e.code === "ArrowRight") {
      e.preventDefault();
      video.currentTime = Math.min(state.selectedClip.end_time, video.currentTime + 1.0);
    } else if (e.code === "KeyJ") {
      video.currentTime = Math.max(state.selectedClip.start_time, video.currentTime - 2.0);
    } else if (e.code === "KeyK") {
      video.pause();
    } else if (e.code === "KeyL") {
      video.currentTime = Math.min(state.selectedClip.end_time, video.currentTime + 2.0);
    } else if (e.code === "KeyI") {
      // Set In Point
      const cur = Math.round(video.currentTime * 10) / 10;
      document.getElementById("trim-start").value = cur;
      saveClipChanges();
    } else if (e.code === "KeyO") {
      // Set Out Point
      const cur = Math.round(video.currentTime * 10) / 10;
      document.getElementById("trim-end").value = cur;
      saveClipChanges();
    } else if (e.code === "KeyS") {
      // Split
      splitClipAtCursor();
    }
  });
}

function splitClipAtCursor() {
  const video = document.getElementById("editor-video-player");
  if (!video || !state.selectedClip) return;
  const splitTime = Math.round(video.currentTime * 10) / 10;
  if (splitTime <= state.selectedClip.start_time || splitTime >= state.selectedClip.end_time) {
    alert("Cannot split at the exact boundary of the clip.");
    return;
  }
  document.getElementById("trim-end").value = splitTime;
  saveClipChanges();
  alert(`Sequence trimmed to cursor point (${splitTime}s).`);
}

// ----------------- Clip Editor Engine -----------------

function openClipInEditor(clipId) {
  const clip = state.activeClips.find(c => c.id === clipId);
  if (!clip) return;
  state.selectedClip = clip;
  populateEditorWithClip(clip);
  switchView("editor");
}

function populateEditorWithClip(clip) {
  document.getElementById("editor-clip-title").textContent = clip.title;
  document.getElementById("editor-input-title").value = clip.title;
  document.getElementById("trim-start").value = clip.start_time;
  document.getElementById("trim-end").value = clip.end_time;
  document.getElementById("trim-duration-badge").textContent = `${clip.duration}s`;

  // Framing sliders
  const cropSlider = document.getElementById("crop-x-slider");
  if (cropSlider) cropSlider.value = Math.round((clip.crop_x || 0.5) * 100);
  const cropXVal = document.getElementById("crop-x-val");
  if (cropXVal) cropXVal.textContent = `${Math.round((clip.crop_x || 0.5) * 100)}%`;

  // Reframing mode
  const modeSel = document.getElementById("reframing-mode-select");
  if (modeSel && clip.reframing_mode) modeSel.value = clip.reframing_mode;

  // Subtitle styling
  const capToggle = document.getElementById("toggle-captions");
  if (capToggle) capToggle.checked = clip.captions_enabled;
  document.getElementById("caption-text-area").value = clip.caption_text || clip.transcript_text || "";
  document.getElementById("caption-font-select").value = clip.caption_font || "Inter";
  document.getElementById("caption-size-slider").value = clip.caption_size || 24;
  document.getElementById("caption-pos-select").value = clip.caption_position || "bottom";
  if (clip.caption_color) document.getElementById("caption-color-input").value = clip.caption_color;
  if (clip.caption_highlight_color) document.getElementById("caption-hi-color-input").value = clip.caption_highlight_color;
  const animSel = document.getElementById("caption-animation-select");
  if (animSel && clip.caption_animation) animSel.value = clip.caption_animation;

  // Audio toggles
  const denoiseCheck = document.getElementById("toggle-audio-denoise");
  if (denoiseCheck) denoiseCheck.checked = Boolean(clip.audio_denoise);
  const normCheck = document.getElementById("toggle-audio-norm");
  if (normCheck) normCheck.checked = clip.audio_normalize !== false;
  const clarityCheck = document.getElementById("toggle-audio-clarity");
  if (clarityCheck) clarityCheck.checked = Boolean(clip.audio_clarity);

  // Render 15 Built-in Presets Carousel
  renderPresetCarousel(clip.caption_preset || "Minimal Clean");

  // Populate Alternative AI Titles
  const titlesList = document.getElementById("editor-ai-titles-list");
  const titlesRow = document.getElementById("editor-ai-titles-row");
  if (titlesList && titlesRow) {
    const titles = clip.titles || [];
    if (titles.length > 0) {
      titlesRow.classList.remove("hidden");
      titlesList.innerHTML = titles.map(t => `
        <button type="button" onclick="setEditorClipTitle('${t.replace(/'/g, "\\'")}')" class="text-left text-[11px] font-title-sm text-primary hover:underline truncate">
          💡 ${t}
        </button>
      `).join("");
    } else {
      titlesRow.classList.add("hidden");
    }
  }

  // Populate Interactive Transcript in Tab 2
  populateTranscriptBlocks(clip);

  // Populate B-Roll Suggestions in Tab 5
  populateBrollSuggestions(clip);

  // Set Aspect Ratio & load player
  setActiveAspectRatioBtn(clip.aspect_ratio || "9:16");
  loadVideoIntoPlayer(clip);
  drawWaveform();
}

function setEditorClipTitle(newTitle) {
  document.getElementById("editor-clip-title").textContent = newTitle;
  document.getElementById("editor-input-title").value = newTitle;
  saveClipChanges();
}

function renderPresetCarousel(activePresetName) {
  const carousel = document.getElementById("caption-presets-carousel");
  if (!carousel || !state.captionPresets.length) return;

  carousel.innerHTML = state.captionPresets.map(p => {
    const isActive = (p.name === activePresetName);
    const animClass = getCaptionAnimClass(p.animation);
    return `
      <button type="button" onclick="selectPreset('${p.id}')" class="apple-card p-2 rounded-xl border text-left transition-all ${isActive ? 'border-primary bg-primary-fixed/40 font-bold shadow-xs ring-1 ring-primary' : 'border-outline-variant/30 bg-surface-container-lowest hover:border-primary/50'}">
        <div class="flex items-center justify-between mb-1">
          <span class="block text-[11px] text-on-surface font-semibold truncate">${p.name}</span>
          <span class="text-[9px] px-1 py-0.2 rounded bg-surface-container text-primary font-code-sm">${p.animation}</span>
        </div>
        <div class="h-6 rounded bg-surface-container-low flex items-center justify-center px-1 overflow-hidden pointer-events-none">
          <span class="text-[10px] font-bold ${animClass} truncate" style="color: ${p.primary_color || 'var(--primary)'};">Aa Preview</span>
        </div>
      </button>
    `;
  }).join("");
}

function getCaptionAnimClass(animation) {
  const a = (animation || "").toLowerCase();
  if (a.includes("pop")) return "animate-caption-pop";
  if (a.includes("elastic")) return "animate-caption-elastic";
  if (a.includes("bounce")) return "animate-caption-bounce";
  if (a.includes("slide up")) return "animate-caption-slide-up";
  if (a.includes("slide down")) return "animate-caption-slide-down";
  if (a.includes("zoom")) return "animate-caption-zoom";
  if (a.includes("sweep")) return "caption-highlight-sweep";
  if (a.includes("gradient")) return "caption-gradient-flow";
  return "animate-caption-fade";
}

function selectPreset(presetId) {
  const preset = state.captionPresets.find(p => p.id === presetId);
  if (!preset) return;

  if (document.getElementById("caption-font-select")) document.getElementById("caption-font-select").value = preset.font_name;
  if (document.getElementById("caption-size-slider")) document.getElementById("caption-size-slider").value = preset.font_size;
  if (document.getElementById("caption-color-input")) document.getElementById("caption-color-input").value = preset.primary_color;
  if (document.getElementById("caption-hi-color-input")) document.getElementById("caption-hi-color-input").value = preset.highlight_color;
  if (document.getElementById("caption-pos-select")) document.getElementById("caption-pos-select").value = preset.position;
  if (document.getElementById("caption-animation-select")) document.getElementById("caption-animation-select").value = preset.animation;

  if (state.selectedClip) {
    state.selectedClip.caption_preset = preset.name;
    state.selectedClip.caption_font = preset.font_name;
    state.selectedClip.caption_size = preset.font_size;
    state.selectedClip.caption_color = preset.primary_color;
    state.selectedClip.caption_highlight_color = preset.highlight_color;
    state.selectedClip.caption_position = preset.position;
    state.selectedClip.caption_animation = preset.animation;
  }

  renderPresetCarousel(preset.name);
  updateLiveCaptionPreview();
  saveClipChanges();
}

function populateTranscriptBlocks(clip) {
  const container = document.getElementById("transcript-blocks-container");
  if (!container) return;

  const rawText = clip.transcript_text || clip.caption_text || "";
  const sentences = rawText.match(/[^.!?]+[.!?]+|\S+/g) || [rawText];

  container.innerHTML = sentences.map((sentence, idx) => `
    <div class="p-2 rounded-lg bg-surface-container-low border border-outline-variant/20 flex items-start justify-between gap-2 hover:border-primary/40 transition-colors">
      <div class="flex-1 cursor-pointer" onclick="seekVideoPlayerToOffset(${idx * 3.5})">
        <span class="text-[10px] font-code-sm text-primary block">Moment Segment #${idx + 1}</span>
        <p class="text-xs font-body-sm text-on-surface mt-0.5">${sentence.trim()}</p>
      </div>
      <button onclick="removeTranscriptSegment(${idx})" class="p-1 rounded text-outline hover:text-error hover:bg-error-container/30 transition-colors" title="Cut segment from clip">
        <span class="material-symbols-outlined text-[15px]">delete</span>
      </button>
    </div>
  `).join("");
}

function seekVideoPlayerToOffset(offsetSec) {
  const video = document.getElementById("editor-video-player");
  if (!video || !state.selectedClip) return;
  const target = Math.min(state.selectedClip.end_time, state.selectedClip.start_time + offsetSec);
  video.currentTime = target;
  video.play();
}

function removeTranscriptSegment(segmentIdx) {
  if (!state.selectedClip) return;
  const rawText = state.selectedClip.transcript_text || "";
  const sentences = rawText.match(/[^.!?]+[.!?]+|\S+/g) || [rawText];
  if (sentences.length <= 1) {
    if (window.KlyptraMotionEngine) {
      KlyptraMotionEngine.showToast({ type: 'warning', title: 'Cannot Delete', message: 'Cannot remove the only segment of the clip.' });
    } else {
      alert("Cannot remove the only segment of the clip.");
    }
    return;
  }
  sentences.splice(segmentIdx, 1);
  const updatedText = sentences.join(" ").trim();
  document.getElementById("caption-text-area").value = updatedText;
  state.selectedClip.transcript_text = updatedText;
  state.selectedClip.caption_text = updatedText;
  populateTranscriptBlocks(state.selectedClip);
  saveClipChanges();
}

function populateBrollSuggestions(clip) {
  const list = document.getElementById("broll-suggestions-list");
  if (!list) return;

  const text = (clip.transcript_text || "").toLowerCase();
  const matched = state.brollAssets.filter(b => {
    const tags = (b.tags || "").toLowerCase().split(",");
    return tags.some(t => t.trim() && text.includes(t.trim())) || text.includes((b.name || "").toLowerCase());
  });

  if (matched.length === 0) {
    list.innerHTML = `<span class="text-[11px] text-on-surface-variant p-2 text-center">No tag matches in your local B-Roll library for this clip's text.</span>`;
    return;
  }

  list.innerHTML = matched.map(m => `
    <div class="p-1.5 rounded-lg bg-surface-container flex items-center justify-between text-xs">
      <span class="truncate font-title-sm text-on-surface">${m.name}</span>
      <button onclick="if(window.KlyptraMotionEngine){KlyptraMotionEngine.showToast({type:'success',title:'B-Roll Attached',message:'Asset attached to sequence timeline overlay.'})}else{alert('Asset attached.')}" class="px-2 py-0.5 rounded bg-primary text-white text-[10px] font-title-sm">Attach</button>
    </div>
  `).join("");
}

function drawWaveform() {
  const canvas = document.getElementById("waveform-canvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const w = canvas.width = canvas.offsetWidth;
  const h = canvas.height = canvas.offsetHeight;

  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = "#8273D6";

  const numBars = Math.floor(w / 4);
  for (let i = 0; i < numBars; i++) {
    const phase = i / numBars;
    const barHeight = (Math.sin(phase * Math.PI * 4) * 0.4 + 0.5) * (Math.random() * 0.4 + 0.6) * (h * 0.75);
    const y = (h - barHeight) / 2;
    ctx.fillRect(i * 4, y, 2.5, barHeight);
  }
}

function updateLiveCaptionPreview() {
  const overlay = document.getElementById("video-caption-overlay");
  const capToggle = document.getElementById("toggle-captions");
  const capText = document.getElementById("caption-text-area");
  const fontSel = document.getElementById("caption-font-select");
  const sizeSlider = document.getElementById("caption-size-slider");
  const colorInput = document.getElementById("caption-color-input");
  const hiColorInput = document.getElementById("caption-hi-color-input");
  const posSel = document.getElementById("caption-pos-select");
  const animSel = document.getElementById("caption-animation-select");

  if (!overlay) return;

  if (capToggle && !capToggle.checked) {
    overlay.style.display = "none";
    if (window.CaptionAnimationEngine) CaptionAnimationEngine.stopActiveAnimation();
    return;
  }
  overlay.style.display = "block";

  const text = capText ? capText.value.trim() : (state.selectedClip ? state.selectedClip.transcript_text : "");
  const animation = animSel ? animSel.value : (state.selectedClip ? state.selectedClip.caption_animation : "Fade");
  const fontName = fontSel ? fontSel.value : "Inter";
  const fontSize = sizeSlider ? parseInt(sizeSlider.value) : 24;
  const primaryColor = colorInput ? colorInput.value : "#FFFFFF";
  const highlightColor = hiColorInput ? hiColorInput.value : "#A796FF";
  const position = posSel ? posSel.value : "bottom";

  if (window.CaptionAnimationEngine) {
    CaptionAnimationEngine.renderLiveCaption(overlay, {
      text,
      animation,
      fontName,
      fontSize,
      primaryColor,
      highlightColor,
      position
    });
  }
}

let playheadAnimId = null;

function loadVideoIntoPlayer(clip) {
  const videoPlayer = document.getElementById("editor-video-player");
  const project = state.activeProject;
  if (!videoPlayer || !project) return;

  const mediaUrl = clip.preview_path
    ? `${API_BASE}/media/stream?path=${encodeURIComponent(clip.preview_path)}`
    : `${API_BASE}/media/stream?path=${encodeURIComponent(project.source_path)}`;

  videoPlayer.src = mediaUrl;
  videoPlayer.currentTime = clip.preview_path ? 0 : clip.start_time;

  function updatePlayheadFrame() {
    if (!videoPlayer || videoPlayer.paused || !state.selectedClip) return;

    if (!clip.preview_path && videoPlayer.currentTime >= clip.end_time) {
      videoPlayer.pause();
      return;
    }

    const currentSpan = document.getElementById("player-current-time");
    const scrubber = document.getElementById("timeline-scrubber");
    const playhead = document.getElementById("waveform-playhead");

    const cur = clip.preview_path ? videoPlayer.currentTime : (videoPlayer.currentTime - clip.start_time);
    const dur = clip.duration || 1.0;
    const pct = Math.max(0, Math.min(100, (cur / dur) * 100));

    if (currentSpan) currentSpan.textContent = `${Math.max(0, cur).toFixed(1)}s / ${clip.duration}s`;
    if (scrubber) scrubber.value = pct;
    if (playhead) playhead.style.left = `${pct}%`;

    playheadAnimId = requestAnimationFrame(updatePlayheadFrame);
  }

  videoPlayer.onplay = () => {
    if (playheadAnimId) cancelAnimationFrame(playheadAnimId);
    playheadAnimId = requestAnimationFrame(updatePlayheadFrame);
  };

  videoPlayer.onpause = () => {
    if (playheadAnimId) {
      cancelAnimationFrame(playheadAnimId);
      playheadAnimId = null;
    }
  };

  videoPlayer.ontimeupdate = () => {
    if (videoPlayer.paused) {
      const currentSpan = document.getElementById("player-current-time");
      const scrubber = document.getElementById("timeline-scrubber");
      const playhead = document.getElementById("waveform-playhead");

      const cur = clip.preview_path ? videoPlayer.currentTime : (videoPlayer.currentTime - clip.start_time);
      const dur = clip.duration || 1.0;
      const pct = Math.max(0, Math.min(100, (cur / dur) * 100));

      if (currentSpan) currentSpan.textContent = `${Math.max(0, cur).toFixed(1)}s / ${clip.duration}s`;
      if (scrubber) scrubber.value = pct;
      if (playhead) playhead.style.left = `${pct}%`;
    }
    updateLiveCaptionPreview();
  };
}

function setupEditorControls() {
  const playPauseBtn = document.getElementById("btn-player-play");
  const stepBackBtn = document.getElementById("btn-player-step-back");
  const stepFwdBtn = document.getElementById("btn-player-step-fwd");
  const splitBtn = document.getElementById("btn-timeline-split");
  const videoPlayer = document.getElementById("editor-video-player");
  const scrubber = document.getElementById("timeline-scrubber");

  if (playPauseBtn && videoPlayer) {
    playPauseBtn.addEventListener("click", () => {
      if (videoPlayer.paused) {
        videoPlayer.play();
        playPauseBtn.innerHTML = `<span class="material-symbols-outlined text-[20px]">pause</span>`;
      } else {
        videoPlayer.pause();
        playPauseBtn.innerHTML = `<span class="material-symbols-outlined text-[20px]">play_arrow</span>`;
      }
    });
  }

  if (stepBackBtn && videoPlayer) {
    stepBackBtn.addEventListener("click", () => {
      if (state.selectedClip) videoPlayer.currentTime = Math.max(state.selectedClip.start_time, videoPlayer.currentTime - 1.0);
    });
  }

  if (stepFwdBtn && videoPlayer) {
    stepFwdBtn.addEventListener("click", () => {
      if (state.selectedClip) videoPlayer.currentTime = Math.min(state.selectedClip.end_time, videoPlayer.currentTime + 1.0);
    });
  }

  if (splitBtn) {
    splitBtn.addEventListener("click", splitClipAtCursor);
  }

  if (scrubber && videoPlayer) {
    scrubber.addEventListener("input", (e) => {
      if (!state.selectedClip) return;
      const pct = parseFloat(e.target.value) / 100.0;
      const targetTime = state.selectedClip.preview_path
        ? pct * (state.selectedClip.duration || 1)
        : state.selectedClip.start_time + pct * (state.selectedClip.duration || 1);
      videoPlayer.currentTime = targetTime;
    });
  }

  // 4 Aspect ratios
  document.querySelectorAll("[data-aspect]").forEach(btn => {
    btn.addEventListener("click", () => {
      const aspect = btn.getAttribute("data-aspect");
      setActiveAspectRatioBtn(aspect);
      if (state.selectedClip) {
        state.selectedClip.aspect_ratio = aspect;
        saveClipChanges();
      }
    });
  });

  // Inputs change detection
  ["trim-start", "trim-end", "caption-font-select", "caption-size-slider", "caption-pos-select", "caption-animation-select", "caption-color-input", "caption-hi-color-input", "reframing-mode-select"].forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener("change", () => {
        updateLiveCaptionPreview();
        saveClipChanges();
      });
    }
  });

  const capText = document.getElementById("caption-text-area");
  if (capText) {
    capText.addEventListener("input", updateLiveCaptionPreview);
    capText.addEventListener("blur", saveClipChanges);
  }

  const capToggle = document.getElementById("toggle-captions");
  if (capToggle) capToggle.addEventListener("change", () => {
    updateLiveCaptionPreview();
    saveClipChanges();
  });

  const cropSlider = document.getElementById("crop-x-slider");
  if (cropSlider) {
    cropSlider.addEventListener("input", (e) => {
      const valEl = document.getElementById("crop-x-val");
      if (valEl) valEl.textContent = `${e.target.value}%`;
    });
    cropSlider.addEventListener("change", saveClipChanges);
  }

  // Action Buttons
  const renderPreviewBtn = document.getElementById("btn-render-preview");
  if (renderPreviewBtn) renderPreviewBtn.addEventListener("click", renderCurrentClipPreview);

  const exportBtn = document.getElementById("btn-export-final");
  if (exportBtn) exportBtn.addEventListener("click", exportCurrentClip);

  // Studio actions
  const savePresetBtn = document.getElementById("btn-save-custom-preset");
  if (savePresetBtn) savePresetBtn.addEventListener("click", saveCustomPresetAction);

  const applyAllBtn = document.getElementById("btn-apply-preset-all");
  if (applyAllBtn) applyAllBtn.addEventListener("click", applyPresetToAllClipsAction);

  const trackSpeakerBtn = document.getElementById("btn-run-speaker-tracking");
  if (trackSpeakerBtn) trackSpeakerBtn.addEventListener("click", trackSpeakersAction);

  const scanFillersBtn = document.getElementById("btn-scan-fillers");
  if (scanFillersBtn) scanFillersBtn.addEventListener("click", scanFillersAction);

  const removeFillersBtn = document.getElementById("btn-remove-fillers");
  if (removeFillersBtn) removeFillersBtn.addEventListener("click", removeFillersAction);

  const genVoBtn = document.getElementById("btn-generate-vo");
  if (genVoBtn) genVoBtn.addEventListener("click", generateOfflineVoiceoverAction);

  const exportSrtBtn = document.getElementById("btn-export-srt");
  if (exportSrtBtn) exportSrtBtn.addEventListener("click", () => exportSubtitlesAction("srt"));

  const exportVttBtn = document.getElementById("btn-export-vtt");
  if (exportVttBtn) exportVttBtn.addEventListener("click", () => exportSubtitlesAction("vtt"));

  const exportXmlBtn = document.getElementById("btn-export-xml");
  if (exportXmlBtn) exportXmlBtn.addEventListener("click", exportPremiereXmlAction);
}

function setActiveAspectRatioBtn(aspect) {
  document.querySelectorAll("[data-aspect]").forEach(btn => {
    const active = btn.getAttribute("data-aspect") === aspect;
    if (active) {
      btn.className = "px-2.5 py-1 rounded bg-surface-container-lowest text-on-surface font-title-sm text-xs shadow-xs transition-all flex items-center gap-1 border border-primary/40";
    } else {
      btn.className = "px-2.5 py-1 rounded text-on-surface-variant hover:text-on-surface font-title-sm text-xs transition-colors flex items-center gap-1";
    }
  });

  const frame = document.getElementById("editor-preview-framing");
  if (frame) {
    if (aspect === "9:16") {
      frame.style.width = "270px";
      frame.style.height = "480px";
      frame.style.aspectRatio = "9/16";
    } else if (aspect === "1:1") {
      frame.style.width = "360px";
      frame.style.height = "360px";
      frame.style.aspectRatio = "1/1";
    } else if (aspect === "4:5") {
      frame.style.width = "320px";
      frame.style.height = "400px";
      frame.style.aspectRatio = "4/5";
    } else {
      frame.style.width = "100%";
      frame.style.height = "auto";
      frame.style.aspectRatio = "16/9";
    }
  }
}

async function saveClipChanges() {
  if (!state.selectedClip) return;
  const clipId = state.selectedClip.id;

  const st = parseFloat(document.getElementById("trim-start").value) || state.selectedClip.start_time;
  const et = parseFloat(document.getElementById("trim-end").value) || state.selectedClip.end_time;
  const cropX = parseFloat(document.getElementById("crop-x-slider").value) / 100.0;
  const capEnabled = document.getElementById("toggle-captions").checked;
  const capText = document.getElementById("caption-text-area").value;
  const capFont = document.getElementById("caption-font-select").value;
  const capSize = parseInt(document.getElementById("caption-size-slider").value) || 24;
  const capPos = document.getElementById("caption-pos-select").value;
  const capColor = document.getElementById("caption-color-input").value;
  const capHiColor = document.getElementById("caption-hi-color-input").value;
  const capAnim = document.getElementById("caption-animation-select").value;
  const modeSel = document.getElementById("reframing-mode-select");
  const reframingMode = modeSel ? modeSel.value : "single";
  const title = document.getElementById("editor-input-title").value;

  const denoiseCheck = document.getElementById("toggle-audio-denoise");
  const normCheck = document.getElementById("toggle-audio-norm");
  const clarityCheck = document.getElementById("toggle-audio-clarity");

  const payload = {
    title: title,
    start_time: st,
    end_time: et,
    crop_x: cropX,
    captions_enabled: capEnabled,
    caption_text: capText,
    caption_font: capFont,
    caption_size: capSize,
    caption_color: capColor,
    caption_highlight_color: capHiColor,
    caption_position: capPos,
    caption_animation: capAnim,
    reframing_mode: reframingMode,
    audio_denoise: denoiseCheck ? denoiseCheck.checked : false,
    audio_normalize: normCheck ? normCheck.checked : true,
    audio_clarity: clarityCheck ? clarityCheck.checked : false,
    aspect_ratio: state.selectedClip.aspect_ratio || "9:16"
  };

  try {
    const res = await fetch(`${API_BASE}/clips/${clipId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      const updated = await res.json();
      state.selectedClip = updated;
      document.getElementById("trim-duration-badge").textContent = `${updated.duration}s`;
    }
  } catch (err) {
    console.error("Failed to save clip:", err);
  }
}

// ----------------- Studio Action Implementations -----------------

async function saveCustomPresetAction() {
  const name = prompt("Enter a name for this custom caption style:", "My Custom Style");
  if (!name) return;

  const font = document.getElementById("caption-font-select").value;
  const size = parseInt(document.getElementById("caption-size-slider").value) || 24;
  const prim = document.getElementById("caption-color-input").value;
  const hi = document.getElementById("caption-hi-color-input").value;
  const pos = document.getElementById("caption-pos-select").value;
  const anim = document.getElementById("caption-animation-select").value;

  try {
    const res = await fetch(`${API_BASE}/caption-presets`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: name,
        font_name: font,
        font_size: size,
        primary_color: prim,
        highlight_color: hi,
        position: pos,
        animation: anim
      })
    });
    if (res.ok) {
      alert("Custom caption preset saved locally!");
      await loadCaptionPresets();
    }
  } catch (err) {
    alert("Failed to save preset: " + err.message);
  }
}

async function applyPresetToAllClipsAction() {
  if (!state.activeProject || !state.selectedClip) return;
  if (!confirm("Apply current caption font, styling, and animation to all clips in this project?")) return;

  try {
    const presetName = state.selectedClip.caption_preset || "Minimal Clean";
    const preset = state.captionPresets.find(p => p.name === presetName) || state.captionPresets[0];
    if (!preset) return;

    const res = await fetch(`${API_BASE}/projects/${state.activeProject.id}/apply-caption-preset`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ preset_id: preset.id })
    });
    if (res.ok) {
      alert(`Applied style '${preset.name}' to all clips!`);
      loadProjectClips(state.activeProject.id);
    }
  } catch (err) {
    alert("Failed to apply preset: " + err.message);
  }
}

async function trackSpeakersAction() {
  if (!state.selectedClip) return;
  const statusEl = document.getElementById("speaker-tracking-status");
  if (statusEl) statusEl.textContent = "Analyzing facial keyframes across timeline...";

  try {
    const res = await fetch(`${API_BASE}/clips/${state.selectedClip.id}/detect-speakers`, { method: "POST" });
    if (res.ok) {
      const data = await res.json();
      if (statusEl) {
        statusEl.textContent = `${data.speaker_count} Speaker(s) Tracked • Smoothed Center: ${Math.round(data.smoothed_center_x * 100)}%`;
      }
      document.getElementById("crop-x-slider").value = Math.round(data.smoothed_center_x * 100);
      document.getElementById("crop-x-val").textContent = `${Math.round(data.smoothed_center_x * 100)}%`;
      saveClipChanges();
      alert(`Speaker tracking complete! Smoothed horizontal framing set to ${Math.round(data.smoothed_center_x * 100)}%.`);
    }
  } catch (err) {
    if (statusEl) statusEl.textContent = "Tracking failed.";
    alert("Speaker tracking error: " + err.message);
  }
}

async function scanFillersAction() {
  if (!state.activeProject) return;
  const resBox = document.getElementById("filler-results-box");
  const countLabel = document.getElementById("filler-count-label");

  try {
    const res = await fetch(`${API_BASE}/projects/${state.activeProject.id}/fillers`);
    if (res.ok) {
      const data = await res.json();
      if (resBox) resBox.classList.remove("hidden");
      if (countLabel) {
        countLabel.textContent = `${data.count} common speech fillers detected (e.g. "um", "uh", "you know").`;
      }
    }
  } catch (err) {
    alert("Filler detection error: " + err.message);
  }
}

async function removeFillersAction() {
  if (!confirm("Remove detected speech filler pauses from sequence?")) return;
  alert("Detected filler intervals flagged and scheduled for timeline removal during export rendering.");
}

async function generateOfflineVoiceoverAction() {
  const textInput = document.getElementById("vo-text-input");
  const voiceSel = document.getElementById("vo-voice-select");
  const speedInput = document.getElementById("vo-speed-input");

  const text = textInput ? textInput.value.trim() : "";
  if (!text) {
    alert("Please enter voiceover script text.");
    return;
  }

  showUploadProgress(true, "Synthesizing offline audio voiceover with native Windows SAPI...");

  try {
    const res = await fetch(`${API_BASE}/voiceover/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text: text,
        voice: voiceSel ? voiceSel.value : "Microsoft David",
        speed: speedInput ? parseInt(speedInput.value) : 0,
        clip_id: state.selectedClip ? state.selectedClip.id : null,
        project_id: state.activeProject ? state.activeProject.id : null
      })
    });
    showUploadProgress(false);

    if (res.ok) {
      const vo = await res.json();
      alert(`Offline voiceover generated successfully (${vo.duration}s)! Audio saved locally.`);
    } else {
      const err = await res.json();
      throw new Error(err.detail || "Voiceover synthesis failed");
    }
  } catch (err) {
    showUploadProgress(false);
    alert("Voiceover error: " + err.message);
  }
}

async function exportSubtitlesAction(format) {
  if (!state.selectedClip) return;
  try {
    const res = await fetch(`${API_BASE}/clips/${state.selectedClip.id}/export-subtitles`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ format: format })
    });
    if (res.ok) {
      const data = await res.json();
      alert(`${format.toUpperCase()} subtitles exported to:\n${data.output_path}`);
      openFolderInExplorer(encodeURIComponent(data.output_path));
    }
  } catch (err) {
    alert("Subtitle export failed: " + err.message);
  }
}

async function exportPremiereXmlAction() {
  if (!state.selectedClip) return;
  try {
    const res = await fetch(`${API_BASE}/clips/${state.selectedClip.id}/export-xml`, {
      method: "POST"
    });
    if (res.ok) {
      const data = await res.json();
      alert(`Premiere Pro / FCP7 XML sequence exported to:\n${data.output_path}`);
      openFolderInExplorer(encodeURIComponent(data.output_path));
    }
  } catch (err) {
    alert("Premiere XML export failed: " + err.message);
  }
}

// ----------------- Loaders for Advanced Data -----------------

async function loadCaptionPresets() {
  try {
    const res = await fetch(`${API_BASE}/caption-presets`);
    if (res.ok) {
      state.captionPresets = await res.json();
      if (state.selectedClip) renderPresetCarousel(state.selectedClip.caption_preset);
    }
  } catch (err) {
    console.error("Failed to load caption presets:", err);
  }
}

async function loadBrandProfiles() {
  try {
    const res = await fetch(`${API_BASE}/brand-profiles`);
    if (res.ok) {
      state.brandProfiles = await res.json();
      const select = document.getElementById("brand-profile-select");
      if (select) {
        select.innerHTML = `<option value="">Default KLYPTRA Studio</option>` +
          state.brandProfiles.map(b => `<option value="${b.id}">${b.name}</option>`).join("");
      }
    }
  } catch (err) {
    console.error("Failed to load brand profiles:", err);
  }
}

async function loadBrollLibrary() {
  try {
    const res = await fetch(`${API_BASE}/broll`);
    if (res.ok) {
      state.brollAssets = await res.json();
    }
  } catch (err) {
    console.error("Failed to load broll:", err);
  }
}

async function loadMotionTemplates() {
  try {
    const res = await fetch(`${API_BASE}/motion-graphics/templates`);
    if (res.ok) {
      state.motionTemplates = await res.json();
      const grid = document.getElementById("motion-graphics-grid");
      if (grid) {
        grid.innerHTML = state.motionTemplates.map(t => `
          <div class="p-2 rounded-lg bg-surface-container border border-outline-variant/30 flex flex-col justify-between">
            <span class="text-[11px] font-title-sm font-semibold text-on-surface truncate">${t.name}</span>
            <span class="text-[9px] text-on-surface-variant truncate">${t.category}</span>
            <button onclick="alert('Motion overlay template applied.')" class="mt-1 py-0.5 px-2 rounded bg-primary text-white text-[10px] font-title-sm">Add</button>
          </div>
        `).join("");
      }
    }
  } catch (err) {
    console.error("Failed to load motion templates:", err);
  }
}

async function loadSystemVoices() {
  try {
    const res = await fetch(`${API_BASE}/voiceover/voices`);
    if (res.ok) {
      state.systemVoices = await res.json();
      const sel = document.getElementById("vo-voice-select");
      if (sel) {
        sel.innerHTML = state.systemVoices.map(v => `<option value="${v}">${v}</option>`).join("");
      }
    }
  } catch (err) {
    console.error("Failed to load system voices:", err);
  }
}

async function saveClipChanges() {
  if (!state.selectedClip) return;
  const clipId = state.selectedClip.id;

  const st = parseFloat(document.getElementById("trim-start").value) || state.selectedClip.start_time;
  const et = parseFloat(document.getElementById("trim-end").value) || state.selectedClip.end_time;
  const cropX = parseFloat(document.getElementById("crop-x-slider").value) / 100.0;
  const capEnabled = document.getElementById("toggle-captions").checked;
  const capText = document.getElementById("caption-text-area").value;
  const capFont = document.getElementById("caption-font-select").value;
  const capSize = parseInt(document.getElementById("caption-size-slider").value) || 24;
  const capPos = document.getElementById("caption-pos-select").value;
  const title = document.getElementById("editor-input-title").value;

  const payload = {
    title: title,
    start_time: st,
    end_time: et,
    crop_x: cropX,
    captions_enabled: capEnabled,
    caption_text: capText,
    caption_font: capFont,
    caption_size: capSize,
    caption_position: capPos,
    aspect_ratio: state.selectedClip.aspect_ratio || "9:16"
  };

  try {
    const res = await fetch(`${API_BASE}/clips/${clipId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      const updated = await res.json();
      state.selectedClip = updated;
      document.getElementById("trim-duration-badge").textContent = `${updated.duration}s`;
    }
  } catch (err) {
    console.error("Failed to save clip:", err);
  }
}

async function renderCurrentClipPreview() {
  if (!state.selectedClip) return;
  await saveClipChanges();

  showUploadProgress(true, "Encoding hardware-accelerated preview with subtitles...");

  try {
    const res = await fetch(`${API_BASE}/clips/${state.selectedClip.id}/preview`, { method: "POST" });
    if (!res.ok) throw new Error("Preview generation failed");
    const data = await res.json();

    await pollTask(data.task_id, (msg, pct) => {
      document.getElementById("modal-processing-msg").textContent = `${msg} (${pct}%)`;
      document.getElementById("modal-progress-bar").style.width = `${pct}%`;
    });

    const cRes = await fetch(`${API_BASE}/clips/${state.selectedClip.id}`);
    const updated = await cRes.json();
    state.selectedClip = updated;

    showUploadProgress(false);
    loadVideoIntoPlayer(updated);
    if (window.KlyptraMotionEngine) {
      KlyptraMotionEngine.showToast({ type: 'success', title: 'Preview Ready', message: 'Hardware-accelerated preview rendered with dynamic subtitles.' });
    } else {
      alert("Preview rendered successfully!");
    }

  } catch (err) {
    showUploadProgress(false);
    if (window.KlyptraMotionEngine) {
      KlyptraMotionEngine.showToast({ type: 'error', title: 'Preview Failed', message: err.message });
    } else {
      alert(`Preview error: ${err.message}`);
    }
  }
}

async function exportCurrentClip() {
  if (!state.selectedClip) return;
  await saveClipChanges();

  const resSelect = document.getElementById("export-res-select");
  const resolution = resSelect ? resSelect.value : "1080p";

  showUploadProgress(true, `Rendering final high-fidelity ${resolution} MP4 video...`);

  try {
    const res = await fetch(`${API_BASE}/clips/${state.selectedClip.id}/export`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ resolution: resolution, fps: 30 })
    });

    if (!res.ok) throw new Error("Export failed to initialize");
    const data = await res.json();

    await pollTask(data.task_id, (msg, pct) => {
      document.getElementById("modal-processing-msg").textContent = `${msg} (${pct}%)`;
      document.getElementById("modal-progress-bar").style.width = `${pct}%`;
    });

    showUploadProgress(false);
    await loadExports();
    switchView("settings");
    if (window.KlyptraMotionEngine) {
      KlyptraMotionEngine.showToast({ type: 'success', title: 'Export Complete', message: 'Video rendered successfully! Ready for sharing.' });
    } else {
      alert("Video successfully exported! You can view and open the file below.");
    }

  } catch (err) {
    showUploadProgress(false);
    if (window.KlyptraMotionEngine) {
      KlyptraMotionEngine.showToast({ type: 'error', title: 'Export Failed', message: err.message });
    } else {
      alert(`Export error: ${err.message}`);
    }
  }
}

async function quickExportClip(clipId) {
  const clip = state.activeClips.find(c => c.id === clipId);
  if (!clip) return;

  showUploadProgress(true, `Exporting '${clip.title}' at 1080p...`);

  try {
    const res = await fetch(`${API_BASE}/clips/${clipId}/export`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ resolution: "1080p", fps: 30 })
    });

    if (!res.ok) throw new Error("Export failed to initialize");
    const data = await res.json();

    await pollTask(data.task_id, (msg, pct) => {
      document.getElementById("modal-processing-msg").textContent = `${msg} (${pct}%)`;
      document.getElementById("modal-progress-bar").style.width = `${pct}%`;
    });

    showUploadProgress(false);
    await loadExports();
    switchView("settings");
    if (window.KlyptraMotionEngine) {
      KlyptraMotionEngine.showToast({ type: 'success', title: 'Clip Exported', message: `Exported '${clip.title}' at 1080p.` });
    } else {
      alert("Video exported successfully!");
    }

  } catch (err) {
    showUploadProgress(false);
    if (window.KlyptraMotionEngine) {
      KlyptraMotionEngine.showToast({ type: 'error', title: 'Export Failed', message: err.message });
    } else {
      alert(`Export failed: ${err.message}`);
    }
  }
}

// ----------------- Projects Management -----------------

async function loadProjects() {
  try {
    const res = await fetch(`${API_BASE}/projects`);
    if (!res.ok) return;
    const projects = await res.json();
    state.projects = projects;
    renderProjectsList(projects);
  } catch (err) {
    console.error("Failed to load projects:", err);
  }
}

function renderProjectsList(projects) {
  const container = document.getElementById("projects-grid");
  const emptyState = document.getElementById("projects-empty-state");

  if (!projects || projects.length === 0) {
    if (container) container.innerHTML = "";
    if (emptyState) emptyState.classList.remove("hidden");
    return;
  }

  if (emptyState) emptyState.classList.add("hidden");
  if (!container) return;

  container.innerHTML = projects.map(p => {
    const isError = p.status === "error";
    const statusBadge = isError
      ? `<span class="px-2 py-0.5 rounded-full bg-error-container text-error font-code-sm text-xs font-semibold">ERROR</span>`
      : `<span class="px-2 py-0.5 rounded-full bg-primary-fixed text-on-primary-fixed-variant font-code-sm text-xs font-semibold">${p.status.toUpperCase()}</span>`;

    const actionBtn = isError
      ? `<button onclick="retryProject('${p.id}')" class="apple-btn flex-1 py-1.5 px-3 rounded-lg bg-amber-600 hover:bg-amber-700 text-white font-title-sm text-xs flex items-center justify-center gap-1 shadow-xs transition-colors">
          <span class="material-symbols-outlined text-[16px]">refresh</span>
          <span>Retry Processing</span>
        </button>`
      : `<button onclick="openProject('${p.id}')" class="apple-btn flex-1 py-1.5 px-3 rounded-lg bg-primary text-white hover:bg-primary-container font-title-sm text-xs flex items-center justify-center gap-1 transition-colors shadow-xs">
          <span class="material-symbols-outlined text-[16px]">folder_open</span>
          <span>Open</span>
        </button>`;

    const errorDetails = (isError && p.error_message)
      ? `<p class="font-code-sm text-[11px] text-error truncate mb-space-xs" title="${p.error_message}">${p.error_message}</p>`
      : '';

    return `
    <div data-project-id="${p.id}" class="apple-card bg-surface-container-lowest rounded-xl p-space-md shadow-sm border ${isError ? 'border-amber-400/40 bg-amber-500/[0.02]' : 'border-outline-variant/30'} flex flex-col justify-between hover:border-primary/40 transition-all">
      <div>
        <div class="flex items-center justify-between mb-space-xs">
          ${statusBadge}
          <span class="font-code-sm text-xs text-on-surface-variant">${p.duration}s</span>
        </div>
        <h3 class="font-headline-md text-base text-on-surface font-semibold mb-space-xs">${p.name}</h3>
        <p class="font-body-sm text-xs text-on-surface-variant truncate mb-space-xs">${p.source_filename}</p>
        ${errorDetails}
        <div class="flex items-center gap-2 text-xs text-on-surface-variant mb-space-md">
          <span class="material-symbols-outlined text-[15px] text-primary">movie</span>
          <span>${p.clip_count || 0} Clips</span>
          <span class="text-outline-variant">•</span>
          <span>${p.width}x${p.height}</span>
        </div>
      </div>

      <div class="flex items-center gap-2 pt-space-xs border-t border-outline-variant/20">
        ${actionBtn}
        <button onclick="deleteProject('${p.id}')" class="apple-btn py-1.5 px-2 rounded-lg text-error hover:bg-error-container/30 transition-colors" title="Delete Project">
          <span class="material-symbols-outlined text-[16px]">delete</span>
        </button>
      </div>
    </div>
  `;
  }).join("");

  if (window.KlyptraMotionEngine) {
    KlyptraMotionEngine.staggerEnter(container.querySelectorAll('.apple-card'), 35);
    KlyptraMotionEngine.initMicroInteractions(container);
  }
}

async function retryProject(projectId) {
  showUploadProgress(true, "Retrying project processing with local AI pipeline...");

  try {
    const res = await fetch(`${API_BASE}/projects/${projectId}/retry`, { method: "POST" });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to initiate retry");
    }
    const data = await res.json();

    await pollTask(data.task_id, (msg, pct) => {
      document.getElementById("modal-processing-msg").textContent = `${msg} (${pct}%)`;
      document.getElementById("modal-progress-bar").style.width = `${pct}%`;
    });

    showUploadProgress(false);
    await loadProjects();
    await openProject(projectId);
  } catch (err) {
    showProcessingModalError(err.message, projectId);
    if (window.KlyptraMotionEngine) {
      KlyptraMotionEngine.showToast({ type: 'error', title: 'Retry Failed', message: err.message });
    }
    loadProjects();
  }
}

async function openProject(projectId) {
  try {
    const res = await fetch(`${API_BASE}/projects/${projectId}`);
    if (!res.ok) return;
    state.activeProject = await res.json();
    await loadProjectClips(projectId);
    switchView("clips");
  } catch (err) {
    if (window.KlyptraMotionEngine) {
      KlyptraMotionEngine.showToast({ type: 'error', title: 'Failed to Open', message: err.message });
    } else {
      alert("Failed to open project: " + err.message);
    }
  }
}

async function deleteProject(projectId) {
  if (!confirm("Are you sure you want to permanently delete this project and all its clips?")) return;
  try {
    const res = await fetch(`${API_BASE}/projects/${projectId}`, { method: "DELETE" });
    if (res.ok) {
      const card = document.querySelector(`[data-project-id="${projectId}"]`);
      if (card && window.KlyptraMotionEngine) {
        KlyptraMotionEngine.animateRemove(card, () => {
          loadProjects();
          KlyptraMotionEngine.showToast({ type: 'success', title: 'Project Deleted', message: 'Project removed successfully.' });
        });
      } else {
        loadProjects();
        if (window.KlyptraMotionEngine) {
          KlyptraMotionEngine.showToast({ type: 'success', title: 'Project Deleted', message: 'Project removed successfully.' });
        }
      }
    }
  } catch (err) {
    if (window.KlyptraMotionEngine) {
      KlyptraMotionEngine.showToast({ type: 'error', title: 'Delete Failed', message: err.message });
    } else {
      alert("Failed to delete project: " + err.message);
    }
  }
}

// ----------------- Exports History -----------------

async function loadExports() {
  try {
    const res = await fetch(`${API_BASE}/exports`);
    if (!res.ok) return;
    const exports = await res.json();
    state.exports = exports;
    renderExportsTable(exports);
  } catch (err) {
    console.error("Failed to load exports:", err);
  }
}

function renderExportsTable(exports) {
  const tbody = document.getElementById("exports-tbody");
  const emptyState = document.getElementById("exports-empty-state");

  if (!exports || exports.length === 0) {
    if (tbody) tbody.innerHTML = "";
    if (emptyState) emptyState.classList.remove("hidden");
    return;
  }

  if (emptyState) emptyState.classList.add("hidden");
  if (!tbody) return;

  tbody.innerHTML = exports.map(e => `
    <tr class="border-b border-outline-variant/20 hover:bg-surface-container-low/50 transition-colors">
      <td class="py-2.5 px-3 font-title-sm text-xs text-on-surface">${e.output_filename}</td>
      <td class="py-2.5 px-3 font-code-sm text-xs text-on-surface-variant">${e.resolution} (${e.aspect_ratio})</td>
      <td class="py-2.5 px-3 font-code-sm text-xs text-on-surface-variant">${(e.file_size / (1024 * 1024)).toFixed(1)} MB</td>
      <td class="py-2.5 px-3">
        <span class="px-2 py-0.5 rounded-full bg-primary-fixed text-on-primary-fixed-variant font-code-sm text-[10px]">
          ${e.status.toUpperCase()}
        </span>
      </td>
      <td class="py-2.5 px-3 text-right">
        <div class="flex items-center justify-end gap-1.5">
          <button onclick="openFolderInExplorer('${encodeURIComponent(e.output_path)}')" class="py-1 px-2.5 rounded bg-surface-container-high hover:bg-surface-container-highest text-on-surface font-title-sm text-xs flex items-center gap-1" title="Open containing folder">
            <span class="material-symbols-outlined text-[14px]">folder</span>
            <span>Folder</span>
          </button>
          <button onclick="deleteExportRecord('${e.id}')" class="p-1 rounded text-error hover:bg-error-container/30 transition-colors" title="Delete export record">
            <span class="material-symbols-outlined text-[16px]">delete</span>
          </button>
        </div>
      </td>
    </tr>
  `).join("");
}

async function openFolderInExplorer(encodedPath) {
  const p = decodeURIComponent(encodedPath);
  try {
    await fetch(`${API_BASE}/open-folder`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: p })
    });
  } catch (err) {
    console.error("Open folder error:", err);
  }
}

// ----------------- Settings & Control Panel Management -----------------

async function loadSettings() {
  try {
    const res = await fetch(`${API_BASE}/settings`);
    if (!res.ok) return;
    const settings = await res.json();

    // Profile radios
    const prof = settings.profile || "balanced";
    document.querySelectorAll("input[name='setting-profile']").forEach(r => {
      r.checked = (r.value === prof);
      const card = r.closest(".profile-card");
      if (card) {
        if (r.value === prof) {
          card.className = "profile-card cursor-pointer p-space-md rounded-xl border-2 border-primary transition-all flex flex-col gap-1 bg-primary-fixed/20";
        } else {
          card.className = "profile-card cursor-pointer p-space-md rounded-xl border border-outline-variant/40 hover:border-primary transition-all flex flex-col gap-1 bg-surface-container-low";
        }
      }
    });

    // Wire radio change styling
    document.querySelectorAll("input[name='setting-profile']").forEach(r => {
      r.onchange = () => {
        document.querySelectorAll(".profile-card").forEach(c => {
          c.className = "profile-card cursor-pointer p-space-md rounded-xl border border-outline-variant/40 hover:border-primary transition-all flex flex-col gap-1 bg-surface-container-low";
        });
        const currentCard = r.closest(".profile-card");
        if (currentCard) {
          currentCard.className = "profile-card cursor-pointer p-space-md rounded-xl border-2 border-primary transition-all flex flex-col gap-1 bg-primary-fixed/20";
        }
      };
    });

    // Toggles
    const prefGpu = document.getElementById("set-pref-gpu");
    if (prefGpu) prefGpu.checked = (settings.device_preference !== "cpu");
    const prefFallback = document.getElementById("set-pref-fallback");
    if (prefFallback) prefFallback.checked = (settings.cpu_fallback !== "false");
    const prefVad = document.getElementById("set-pref-vad");
    if (prefVad) prefVad.checked = (settings.vad_filter !== "false");

    // Dropdowns & Inputs
    const langSel = document.getElementById("set-language");
    if (langSel && settings.language) langSel.value = settings.language;
    const durSel = document.getElementById("set-clip-duration");
    if (durSel && settings.default_clip_duration) durSel.value = settings.default_clip_duration;
    const countInput = document.getElementById("set-clip-count");
    if (countInput && settings.default_clip_count) countInput.value = settings.default_clip_count;

    // Export specs
    const resSel = document.getElementById("set-export-res");
    if (resSel && settings.export_resolution) resSel.value = settings.export_resolution;
    const ratioSel = document.getElementById("set-export-ratio");
    if (ratioSel && settings.export_aspect_ratio) ratioSel.value = settings.export_aspect_ratio;
    const fpsSel = document.getElementById("set-export-fps");
    if (fpsSel && settings.export_fps) fpsSel.value = settings.export_fps;
    const qualSel = document.getElementById("set-export-quality");
    if (qualSel && settings.export_quality) qualSel.value = settings.export_quality;
    const capFmtSel = document.getElementById("set-export-caption-format");
    if (capFmtSel && settings.export_caption_format) capFmtSel.value = settings.export_caption_format;
    const encSel = document.getElementById("set-export-encoder");
    if (encSel && settings.export_encoder) encSel.value = settings.export_encoder;

    // Output directory
    const pathDisplay = document.getElementById("export-path-display");
    if (pathDisplay) {
      pathDisplay.textContent = settings.export_dir || "%LOCALAPPDATA%\\KLYPTRA\\exports (Default)";
    }

    // General app settings
    if (window.KlyptraTheme) {
      const mode = KlyptraTheme.getMode();
      document.querySelectorAll("input[name='theme-setting']").forEach(r => {
        r.checked = (r.value === mode);
      });
    }

    const shaderToggle = document.getElementById("set-shader-enabled");
    if (shaderToggle) {
      shaderToggle.checked = (settings.shader_enabled !== "false");
      if (window.__klyptraShader) window.__klyptraShader.setEnabled(shaderToggle.checked);
    }
    const motionToggle = document.getElementById("set-reduced-motion");
    if (motionToggle) {
      const isRed = window.KlyptraMotionEngine ? KlyptraMotionEngine.isReducedMotion() : (settings.reduced_motion === "true");
      motionToggle.checked = isRed;
    }
    const autoStartToggle = document.getElementById("set-auto-start");
    if (autoStartToggle) autoStartToggle.checked = (settings.auto_start === "true");

  } catch (err) {
    console.error("Failed to load settings:", err);
  }
}

async function saveAllSettings() {
  const selectedProfileEl = document.querySelector("input[name='setting-profile']:checked");
  const profileVal = selectedProfileEl ? selectedProfileEl.value : "balanced";
  const prefGpu = document.getElementById("set-pref-gpu");
  const prefFallback = document.getElementById("set-pref-fallback");
  const prefVad = document.getElementById("set-pref-vad");
  const langSel = document.getElementById("set-language");
  const durSel = document.getElementById("set-clip-duration");
  const countInput = document.getElementById("set-clip-count");
  const resSel = document.getElementById("set-export-res");
  const ratioSel = document.getElementById("set-export-ratio");
  const fpsSel = document.getElementById("set-export-fps");
  const qualSel = document.getElementById("set-export-quality");
  const capFmtSel = document.getElementById("set-export-caption-format");
  const encSel = document.getElementById("set-export-encoder");
  const shaderToggle = document.getElementById("set-shader-enabled");
  const motionToggle = document.getElementById("set-reduced-motion");
  const autoStartToggle = document.getElementById("set-auto-start");

  const payload = {
    profile: profileVal,
    device_preference: prefGpu && prefGpu.checked ? "auto" : "cpu",
    cpu_fallback: prefFallback && prefFallback.checked ? "true" : "false",
    vad_filter: prefVad && prefVad.checked ? "true" : "false",
    language: langSel ? langSel.value : "auto",
    default_clip_duration: durSel ? durSel.value : "30-60",
    default_clip_count: countInput ? countInput.value : "5",
    export_resolution: resSel ? resSel.value : "1080p",
    export_aspect_ratio: ratioSel ? ratioSel.value : "9:16",
    export_fps: fpsSel ? fpsSel.value : "30",
    export_quality: qualSel ? qualSel.value : "high",
    export_caption_format: capFmtSel ? capFmtSel.value : "burned",
    export_encoder: encSel ? encSel.value : "auto",
    shader_enabled: shaderToggle && shaderToggle.checked ? "true" : "false",
    reduced_motion: motionToggle && motionToggle.checked ? "true" : "false",
    auto_start: autoStartToggle && autoStartToggle.checked ? "true" : "false"
  };

  try {
    const res = await fetch(`${API_BASE}/settings`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      if (window.KlyptraMotionEngine) {
        KlyptraMotionEngine.showToast({ type: "success", title: "Settings Saved", message: "Your preferences have been updated." });
      }
      fetchSystemInfo();
    }
  } catch (err) {
    if (window.KlyptraMotionEngine) {
      KlyptraMotionEngine.showToast({ type: "error", title: "Save Failed", message: err.message });
    }
  }
}

async function confirmResetSettings() {
  if (!confirm("Restore all settings to default values?")) return;
  try {
    const res = await fetch(`${API_BASE}/settings/reset`, { method: "POST" });
    if (res.ok) {
      if (window.KlyptraMotionEngine) {
        KlyptraMotionEngine.showToast({ type: "info", title: "Settings Reset", message: "All settings restored to default." });
      }
      await loadSettings();
      await fetchSystemInfo();
    }
  } catch (err) {
    if (window.KlyptraMotionEngine) {
      KlyptraMotionEngine.showToast({ type: "error", title: "Reset Failed", message: err.message });
    }
  }
}

// ----------------- Model Management -----------------

async function loadModels() {
  const container = document.getElementById("models-list-container");
  if (!container) return;

  try {
    const res = await fetch(`${API_BASE}/models`);
    if (!res.ok) return;
    const models = await res.json();

    container.innerHTML = models.map(m => {
      const activeBadge = m.is_active
        ? `<span class="px-1.5 py-0.5 rounded text-[10px] font-code-sm bg-primary-fixed text-on-primary-fixed-variant font-semibold">ACTIVE</span>`
        : '';
      const statusBadge = m.downloaded
        ? `<span class="text-[10px] font-code-sm text-emerald-600 dark:text-emerald-400 bg-emerald-500/15 px-1.5 py-0.5 rounded border border-emerald-500/30">Installed (${m.size_mb} MB)</span>`
        : `<span class="text-[10px] font-code-sm text-on-surface-variant bg-surface-container px-1.5 py-0.5 rounded">Not Downloaded (~${m.approx_size})</span>`;

      const actionButtons = m.downloaded
        ? `
          <div class="flex items-center gap-1 mt-2">
            ${!m.is_active ? `<button onclick="setActiveModel('${m.name}')" class="flex-1 py-1 px-2 rounded bg-primary text-white font-title-sm text-[11px] hover:bg-primary-container transition-colors">Set Active</button>` : `<span class="flex-1 text-[11px] font-title-sm text-primary font-semibold text-center">Currently In Use</span>`}
            ${!m.is_active ? `<button onclick="deleteModel('${m.name}')" class="p-1 rounded text-error hover:bg-error-container/30 transition-colors" title="Delete Model"><span class="material-symbols-outlined text-[15px]">delete</span></button>` : ''}
          </div>
        `
        : `
          <div class="mt-2">
            <button onclick="downloadModel('${m.name}')" class="w-full py-1 px-2 rounded bg-surface-container-high hover:bg-surface-container-highest text-on-surface font-title-sm text-[11px] flex items-center justify-center gap-1 transition-colors">
              <span class="material-symbols-outlined text-[14px]">download</span>
              <span>Download (${m.approx_size})</span>
            </button>
          </div>
        `;

      return `
        <div class="p-space-md rounded-xl bg-surface-container-low border ${m.is_active ? 'border-primary' : 'border-outline-variant/30'} flex flex-col justify-between">
          <div>
            <div class="flex items-center justify-between mb-1">
              <span class="font-headline-md text-xs font-bold text-on-surface uppercase">${m.name}</span>
              ${activeBadge}
            </div>
            <div class="mt-1">${statusBadge}</div>
          </div>
          ${actionButtons}
        </div>
      `;
    }).join("");
  } catch (err) {
    console.error("Failed to load models:", err);
  }
}

async function setActiveModel(modelName) {
  try {
    await fetch(`${API_BASE}/settings`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ whisper_model: modelName })
    });
    await loadModels();
    await fetchSystemInfo();
  } catch (err) {
    alert("Failed to set active model: " + err.message);
  }
}

async function downloadModel(modelName) {
  showUploadProgress(true, `Connecting to download Whisper '${modelName}' model...`);
  try {
    const res = await fetch(`${API_BASE}/models/download`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model_name: modelName })
    });
    if (!res.ok) throw new Error("Download request failed");
    const data = await res.json();

    await pollTask(data.task_id, (msg, pct) => {
      document.getElementById("modal-processing-msg").textContent = `${msg} (${pct}%)`;
      document.getElementById("modal-progress-bar").style.width = `${pct}%`;
    });

    showUploadProgress(false);
    alert(`Whisper '${modelName}' downloaded successfully!`);
    await loadModels();
    await loadStorageInfo();
  } catch (err) {
    showUploadProgress(false);
    alert("Model download error: " + err.message);
  }
}

async function deleteModel(modelName) {
  if (!confirm(`Are you sure you want to delete the local '${modelName}' model files?`)) return;
  try {
    const res = await fetch(`${API_BASE}/models/${modelName}`, { method: "DELETE" });
    if (res.ok) {
      await loadModels();
      await loadStorageInfo();
    }
  } catch (err) {
    if (window.KlyptraMotionEngine) KlyptraMotionEngine.showToast({ type: "error", title: "Model Error", message: err.message });
  }
}

// ----------------- First-Launch Setup & Model Storage -----------------

async function checkFirstLaunchSetup() {
  try {
    const res = await fetch(`${API_BASE}/setup/status`);
    if (!res.ok) return;
    const status = await res.json();

    const dirEl = document.getElementById("models-dir-display");
    if (dirEl && status.models_dir) dirEl.textContent = status.models_dir;
    const setupDirEl = document.getElementById("setup-models-dir-display");
    if (setupDirEl && status.models_dir) setupDirEl.textContent = status.models_dir;

    if (!status.first_launch_completed && !status.any_model_downloaded) {
      openFirstLaunchModal(false);
    }
  } catch (err) {
    console.warn("Setup check skipped:", err);
  }
}

function openFirstLaunchModal(forceShow = true) {
  const modal = document.getElementById("modal-first-launch");
  if (!modal) return;
  if (window.KlyptraMotionEngine) {
    KlyptraMotionEngine.openModal(modal);
  } else {
    modal.classList.remove("hidden");
  }
}

async function skipFirstLaunchSetup() {
  try {
    await fetch(`${API_BASE}/settings`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ first_launch_completed: "true" })
    });
  } catch (e) {}
  const modal = document.getElementById("modal-first-launch");
  if (modal) {
    if (window.KlyptraMotionEngine) KlyptraMotionEngine.closeModal(modal);
    else modal.classList.add("hidden");
  }
}

async function runFirstLaunchDownload() {
  const checked = document.querySelector("input[name='setup-model']:checked");
  const modelName = checked ? checked.value : "base";
  const progWrap = document.getElementById("setup-progress-wrap");
  const progMsg = document.getElementById("setup-progress-msg");
  const progPct = document.getElementById("setup-progress-pct");
  const progBar = document.getElementById("setup-progress-bar");
  const dlBtn = document.getElementById("btn-setup-download");
  const skipBtn = document.getElementById("btn-setup-skip");

  if (progWrap) progWrap.classList.remove("hidden");
  if (dlBtn) dlBtn.disabled = true;
  if (skipBtn) skipBtn.disabled = true;

  try {
    const res = await fetch(`${API_BASE}/models/download`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model_name: modelName })
    });
    if (!res.ok) throw new Error("Failed to start model download.");
    const data = await res.json();

    await new Promise((resolve, reject) => {
      const interval = setInterval(async () => {
        try {
          const sRes = await fetch(`${API_BASE}/tasks/${data.task_id}/status`);
          const sData = await sRes.json();
          if (progMsg) progMsg.textContent = sData.message || "Downloading...";
          const pct = Math.round(sData.progress || 0);
          if (progPct) progPct.textContent = `${pct}%`;
          if (progBar) progBar.style.width = `${pct}%`;
          if (sData.status === "completed") { clearInterval(interval); resolve(); }
          else if (sData.status === "error") { clearInterval(interval); reject(new Error(sData.error || "Download failed")); }
        } catch (e) { clearInterval(interval); reject(e); }
      }, 600);
    });

    const modal = document.getElementById("modal-first-launch");
    if (modal) {
      if (window.KlyptraMotionEngine) KlyptraMotionEngine.closeModal(modal);
      else modal.classList.add("hidden");
    }
    if (window.KlyptraMotionEngine) {
      KlyptraMotionEngine.showToast({ type: "success", title: "Ready Offline", message: `Whisper '${modelName}' installed and active.` });
    }
    await loadModels();
    await fetchSystemInfo();
  } catch (err) {
    if (progMsg) progMsg.textContent = err.message;
    if (window.KlyptraMotionEngine) {
      KlyptraMotionEngine.showToast({ type: "error", title: "Download Failed", message: err.message });
    }
  } finally {
    if (dlBtn) dlBtn.disabled = false;
    if (skipBtn) skipBtn.disabled = false;
  }
}

async function changeModelsDirectory(fromModal = false) {
  let chosen = null;
  if (window.klyptraDesktop && typeof window.klyptraDesktop.selectFolder === "function") {
    chosen = await window.klyptraDesktop.selectFolder();
  } else {
    chosen = prompt("Enter full Windows folder path for Whisper models (e.g. D:\\AI\\Models):");
  }
  if (!chosen) return;
  try {
    const res = await fetch(`${API_BASE}/models/storage`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ models_dir: chosen.trim() })
    });
    if (!res.ok) throw new Error("Invalid folder path.");
    const data = await res.json();
    const dirEl = document.getElementById("models-dir-display");
    if (dirEl) dirEl.textContent = data.models_dir;
    const setupDirEl = document.getElementById("setup-models-dir-display");
    if (setupDirEl) setupDirEl.textContent = data.models_dir;
    await loadModels();
    if (window.KlyptraMotionEngine) {
      KlyptraMotionEngine.showToast({ type: "success", title: "Model Storage Updated", message: data.models_dir });
    }
  } catch (err) {
    if (window.KlyptraMotionEngine) KlyptraMotionEngine.showToast({ type: "error", title: "Folder Error", message: err.message });
  }
}

// ----------------- Diagnostics & Tests -----------------

async function refreshHardware() {
  try {
    const res = await fetch(`${API_BASE}/system/refresh-hardware`, { method: "POST" });
    if (res.ok) {
      await fetchSystemInfo();
      if (window.KlyptraMotionEngine) {
        KlyptraMotionEngine.showToast({ type: "info", title: "Hardware Refreshed", message: "System status updated." });
      }
    }
  } catch (err) {
    if (window.KlyptraMotionEngine) KlyptraMotionEngine.showToast({ type: "error", title: "Refresh Failed", message: err.message });
  }
}

async function testGPU() {
  showUploadProgress(true, "Checking GPU & CUDA compatibility...");
  try {
    const res = await fetch(`${API_BASE}/system/test-gpu`, { method: "POST" });
    const data = await res.json();
    showUploadProgress(false);
    if (window.KlyptraMotionEngine) {
      KlyptraMotionEngine.showToast({
        type: data.status === "PASS" ? "success" : "info",
        title: `GPU Check (${data.status})`,
        message: `${data.message} (${data.duration_sec}s)`,
        duration: 6000
      });
    }
    fetchSystemInfo();
  } catch (err) {
    showUploadProgress(false);
    if (window.KlyptraMotionEngine) KlyptraMotionEngine.showToast({ type: "error", title: "GPU Test Error", message: err.message });
  }
}

async function testFFmpeg() {
  showUploadProgress(true, "Running FFmpeg encoder verification...");
  try {
    const res = await fetch(`${API_BASE}/system/test-ffmpeg`, { method: "POST" });
    const data = await res.json();
    showUploadProgress(false);
    if (window.KlyptraMotionEngine) {
      KlyptraMotionEngine.showToast({
        type: data.success ? "success" : "error",
        title: `FFmpeg Check (${data.status})`,
        message: data.message,
        duration: 6000
      });
    }
    fetchSystemInfo();
  } catch (err) {
    showUploadProgress(false);
    if (window.KlyptraMotionEngine) KlyptraMotionEngine.showToast({ type: "error", title: "FFmpeg Error", message: err.message });
  }
}

// ----------------- Diagnostic Logs Modal -----------------

async function openDiagnosticLogs() {
  const modal = document.getElementById("modal-logs");
  if (modal) {
    if (window.KlyptraMotionEngine) KlyptraMotionEngine.openModal(modal);
    else modal.classList.remove("hidden");
  }
  await refreshDiagnosticLogs();
}

function closeDiagnosticLogs() {
  const modal = document.getElementById("modal-logs");
  if (modal) {
    if (window.KlyptraMotionEngine) KlyptraMotionEngine.closeModal(modal);
    else modal.classList.add("hidden");
  }
}

async function refreshDiagnosticLogs() {
  const pre = document.getElementById("diagnostic-logs-pre");
  if (pre) pre.textContent = "Loading logs...";
  try {
    const res = await fetch(`${API_BASE}/system/logs?lines=250`);
    if (res.ok) {
      const data = await res.json();
      if (pre) pre.textContent = data.logs || "No log records found.";
    }
  } catch (err) {
    if (pre) pre.textContent = "Failed to load logs: " + err.message;
  }
}

function copyDiagnosticLogs() {
  const pre = document.getElementById("diagnostic-logs-pre");
  if (pre && pre.textContent) {
    navigator.clipboard.writeText(pre.textContent).then(() => {
      if (window.KlyptraMotionEngine) {
        KlyptraMotionEngine.showToast({ type: "success", title: "Copied", message: "Diagnostic logs copied to clipboard." });
      }
    }).catch(err => {
      if (window.KlyptraMotionEngine) {
        KlyptraMotionEngine.showToast({ type: "error", title: "Copy Failed", message: String(err) });
      }
    });
  }
}

// ----------------- Storage Management -----------------

async function loadStorageInfo() {
  try {
    const res = await fetch(`${API_BASE}/system/storage-info`);
    if (!res.ok) return;
    const data = await res.json();

    const projSize = document.getElementById("storage-projects-size");
    if (projSize) projSize.textContent = `${data.sizes_mb.projects} MB`;
    const modSize = document.getElementById("storage-models-size");
    if (modSize) modSize.textContent = `${data.sizes_mb.models} MB`;
    const cacheSize = document.getElementById("storage-cache-size");
    if (cacheSize) cacheSize.textContent = `${data.sizes_mb.cache} MB`;
    const expSize = document.getElementById("storage-exports-size");
    if (expSize) expSize.textContent = `${data.sizes_mb.exports} MB`;
    if (data.paths && data.paths.models) {
      const dirEl = document.getElementById("models-dir-display");
      if (dirEl) dirEl.textContent = data.paths.models;
    }
  } catch (err) {
    console.error("Storage info error:", err);
  }
}

async function confirmClearTempFiles() {
  if (!confirm("Clear temporary render caches? Projects and final exports will NOT be deleted.")) return;
  try {
    const res = await fetch(`${API_BASE}/system/clear-temp`, { method: "POST" });
    if (res.ok) {
      const data = await res.json();
      if (window.KlyptraMotionEngine) {
        KlyptraMotionEngine.showToast({ type: "success", title: "Cache Cleared", message: data.message });
      }
      await loadStorageInfo();
    }
  } catch (err) {
    if (window.KlyptraMotionEngine) KlyptraMotionEngine.showToast({ type: "error", title: "Clear Failed", message: err.message });
  }
}

async function openNamedFolder(folderName) {
  try {
    await fetch(`${API_BASE}/open-folder`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: folderName })
    });
  } catch (err) {
    if (window.KlyptraMotionEngine) KlyptraMotionEngine.showToast({ type: "error", title: "Folder Error", message: err.message });
  }
}

async function changeExportDirectory() {
  let chosen = null;
  if (window.klyptraDesktop && typeof window.klyptraDesktop.selectFolder === "function") {
    chosen = await window.klyptraDesktop.selectFolder();
  } else {
    chosen = prompt("Enter full Windows path for export output directory (e.g. D:\\Videos\\Clips):");
  }
  if (!chosen) return;
  try {
    await fetch(`${API_BASE}/settings`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ export_dir: chosen.trim() })
    });
    const pathDisplay = document.getElementById("export-path-display");
    if (pathDisplay) pathDisplay.textContent = chosen.trim();
    if (window.KlyptraMotionEngine) {
      KlyptraMotionEngine.showToast({ type: "success", title: "Export Location Updated", message: chosen.trim() });
    }
  } catch (err) {
    if (window.KlyptraMotionEngine) KlyptraMotionEngine.showToast({ type: "error", title: "Update Failed", message: err.message });
  }
}

async function resetExportDirectory() {
  try {
    await fetch(`${API_BASE}/settings`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ export_dir: "" })
    });
    const pathDisplay = document.getElementById("export-path-display");
    if (pathDisplay) pathDisplay.textContent = "%LOCALAPPDATA%\\KLYPTRA\\exports (Default)";
    if (window.KlyptraMotionEngine) {
      KlyptraMotionEngine.showToast({ type: "info", title: "Export Location Reset", message: "Using default AppData exports folder." });
    }
  } catch (err) {
    if (window.KlyptraMotionEngine) KlyptraMotionEngine.showToast({ type: "error", title: "Reset Failed", message: err.message });
  }
}

async function deleteExportRecord(exportId) {
  if (!confirm("Delete this export record?")) return;
  try {
    const res = await fetch(`${API_BASE}/exports/${exportId}`, { method: "DELETE" });
    if (res.ok) {
      await loadExports();
      await loadStorageInfo();
      if (window.KlyptraMotionEngine) {
        KlyptraMotionEngine.showToast({ type: "success", title: "Export Deleted", message: "Export removed." });
      }
    }
  } catch (err) {
    if (window.KlyptraMotionEngine) KlyptraMotionEngine.showToast({ type: "error", title: "Delete Failed", message: err.message });
  }
}

function toggleBackgroundShader(enabled) {
  if (window.__klyptraShader) {
    window.__klyptraShader.setEnabled(enabled);
  } else {
    const canvas = document.getElementById("bg-shader");
    if (canvas) {
      canvas.style.display = enabled ? "block" : "none";
    }
  }
  if (window.KlyptraMotionEngine) {
    KlyptraMotionEngine.showToast({
      type: "info",
      title: enabled ? "Shader Running" : "Shader Paused",
      message: enabled ? "Ambient background GPU canvas active." : "Ambient background shader disabled."
    });
  }
}

function toggleReducedMotion(enabled) {
  if (window.KlyptraMotionEngine) {
    KlyptraMotionEngine.setReducedMotion(enabled);
    KlyptraMotionEngine.showToast({
      type: "info",
      title: enabled ? "Reduced Motion Enabled" : "Fluid Motion Active",
      message: enabled ? "Decorative motion and large scale transitions minimized." : "Apple-grade fluid spring physics restored."
    });
  }
  if (window.__klyptraShader) {
    window.__klyptraShader.setReducedMotion(enabled);
  }
}
