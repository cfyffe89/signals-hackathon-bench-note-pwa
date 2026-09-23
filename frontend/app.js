// Signals BenchNote Copilot - Client Application Logic

document.addEventListener("DOMContentLoaded", () => {
  // PWA Service Worker Registration
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/sw.js").catch((err) => {
      console.log("SW registration skipped or error:", err);
    });
  }

  // DOM Elements
  const experimentSelect = document.getElementById("experimentSelect");
  const refreshExpBtn = document.getElementById("refreshExpBtn");
  const cameraInput = document.getElementById("cameraInput");
  const photoTriggerBox = document.getElementById("photoTriggerBox");
  const photoPlaceholder = document.getElementById("photoPlaceholder");
  const photoPreviewContainer = document.getElementById("photoPreviewContainer");
  const photoPreview = document.getElementById("photoPreview");
  const removePhotoBtn = document.getElementById("removePhotoBtn");
  const micBtn = document.getElementById("micBtn");
  const micLabel = document.getElementById("micLabel");
  const micIcon = document.getElementById("micIcon");
  const transcriptInput = document.getElementById("transcriptInput");
  const charCount = document.getElementById("charCount");
  const demoDataBtn = document.getElementById("demoDataBtn");
  const analyzeBtn = document.getElementById("analyzeBtn");
  const aiResultCard = document.getElementById("aiResultCard");
  const aiTitleInput = document.getElementById("aiTitleInput");
  const aiBadgesContainer = document.getElementById("aiBadgesContainer");
  const aiHtmlPreview = document.getElementById("aiHtmlPreview");
  const commitBtn = document.getElementById("commitBtn");
  const successCard = document.getElementById("successCard");
  const successDetail = document.getElementById("successDetail");
  const newNoteBtn = document.getElementById("newNoteBtn");
  const statusBadge = document.getElementById("statusBadge");
  const statusText = document.getElementById("statusText");

  let capturedPhotoFile = null;
  let recognition = null;
  let isRecording = false;

  // 1. Load Experiments from Signals API
  async function loadExperiments() {
    experimentSelect.innerHTML = '<option disabled selected>Loading active experiments...</option>';
    try {
      const res = await fetch("/api/experiments");
      const data = await res.json();
      experimentSelect.innerHTML = "";
      
      if (!data.experiments || data.experiments.length === 0) {
        experimentSelect.innerHTML = '<option value="default:exp-1">Default Experiment</option>';
        return;
      }

      data.experiments.forEach((exp, idx) => {
        const opt = document.createElement("option");
        opt.value = exp.eid;
        opt.textContent = exp.name;
        if (idx === 0) opt.selected = true;
        experimentSelect.appendChild(opt);
      });
      statusText.textContent = `${data.experiments.length} Active Exp`;
    } catch (err) {
      console.error("Failed to load experiments:", err);
      experimentSelect.innerHTML = '<option value="experiment:demo-fallback">EXP-2026-DEMO: Active Formulation Bench</option>';
      statusText.textContent = "Offline / Demo";
    }
  }

  loadExperiments();
  refreshExpBtn.addEventListener("click", loadExperiments);

  // 2. Camera & Photo Handler
  photoTriggerBox.addEventListener("click", (e) => {
    if (e.target === removePhotoBtn || removePhotoBtn.contains(e.target)) return;
    cameraInput.click();
  });

  cameraInput.addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setPhoto(file);
  });

  function setPhoto(file) {
    const reader = new FileReader();
    reader.onload = (event) => {
      const img = new Image();
      img.onload = () => {
        // Downscale large camera photos to fast ~40-60KB JPEG
        const maxDim = 800;
        let width = img.width;
        let height = img.height;
        if (width > maxDim || height > maxDim) {
          if (width > height) {
            height = Math.round((height * maxDim) / width);
            width = maxDim;
          } else {
            width = Math.round((width * maxDim) / height);
            height = maxDim;
          }
        }
        const canvas = document.createElement("canvas");
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext("2d");
        ctx.drawImage(img, 0, 0, width, height);

        canvas.toBlob((blob) => {
          capturedPhotoFile = new File([blob], "bench_photo.jpg", { type: "image/jpeg" });
          photoPreview.src = canvas.toDataURL("image/jpeg", 0.85);
          photoPlaceholder.classList.add("hidden");
          photoPreviewContainer.classList.remove("hidden");
          console.log(`Mobile photo compressed: ${file.size} -> ${blob.size} bytes (${width}x${height})`);
        }, "image/jpeg", 0.85);
      };
      img.onerror = () => {
        capturedPhotoFile = file;
        photoPreview.src = event.target.result;
        photoPlaceholder.classList.add("hidden");
        photoPreviewContainer.classList.remove("hidden");
      };
      img.src = event.target.result;
    };
    reader.readAsDataURL(file);
  }

  removePhotoBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    capturedPhotoFile = null;
    cameraInput.value = "";
    photoPreview.src = "";
    photoPreviewContainer.classList.add("hidden");
    photoPlaceholder.classList.remove("hidden");
  });

  // 3. Web Speech API (Hands-Free Voice Dictation)
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

  if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = "en-US";

    recognition.onresult = (event) => {
      let current = "";
      for (let i = 0; i < event.results.length; i++) {
        current += event.results[i][0].transcript;
      }
      transcriptInput.value = current;
      updateWordCount();
    };

    recognition.onerror = (event) => {
      console.warn("Speech recognition error:", event.error);
      stopRecording();
    };

    recognition.onend = () => {
      stopRecording();
    };
  } else {
    console.log("Web Speech API not supported on this browser.");
    micLabel.textContent = "Open in Safari for voice on iPhone";
  }

  function startRecording() {
    if (!recognition) {
      alert("Apple restricts voice dictation to Safari on iOS. Please open this link in Mobile Safari to dictate notes hands-free, or type directly in the box below!");
      return;
    }
    try {
      recognition.start();
      isRecording = true;
      micBtn.classList.remove("bg-slate-700");
      micBtn.classList.add("bg-rose-600", "pulse-ring");
      micLabel.textContent = "Listening... Tap to Stop";
      micIcon.classList.remove("text-rose-400");
      micIcon.classList.add("text-white");
    } catch (e) {
      console.error(e);
    }
  }

  function stopRecording() {
    if (recognition && isRecording) {
      recognition.stop();
    }
    isRecording = false;
    micBtn.classList.remove("bg-rose-600", "pulse-ring");
    micBtn.classList.add("bg-slate-700");
    micLabel.textContent = "Tap to Dictate Bench Notes";
    micIcon.classList.add("text-rose-400");
    micIcon.classList.remove("text-white");
  }

  micBtn.addEventListener("click", () => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  });

  transcriptInput.addEventListener("input", updateWordCount);

  function updateWordCount() {
    const text = transcriptInput.value.trim();
    const words = text ? text.split(/\s+/).length : 0;
    charCount.textContent = `${words} words`;
  }

  // 4. Demo Data Simulator Button
  demoDataBtn.addEventListener("click", () => {
    transcriptInput.value = "Sample 4B at 45°C turned cloudy with fine white precipitate after 15 minutes incubation. Viscosity noticeably increased compared to control. Recommend centrifugation at 4,000 RPM before reading absorbance.";
    updateWordCount();

    // Create a mock canvas image for visual testing
    const canvas = document.createElement("canvas");
    canvas.width = 400;
    canvas.height = 300;
    const ctx = canvas.getContext("2d");
    ctx.fillStyle = "#0f172a";
    ctx.fillRect(0, 0, 400, 300);
    ctx.fillStyle = "#38bdf8";
    ctx.font = "bold 20px sans-serif";
    ctx.fillText("Signals Test Assay - Batch 4B", 40, 100);
    ctx.fillStyle = "#f59e0b";
    ctx.font = "14px sans-serif";
    ctx.fillText("Visual Observation: Turbid precipitate", 40, 140);
    ctx.fillText("Condition: 45°C / 15 min", 40, 170);

    canvas.toBlob((blob) => {
      const mockFile = new File([blob], "demo_vial_turbidity.jpg", { type: "image/jpeg" });
      setPhoto(mockFile);
    }, "image/jpeg");
  });

  // 5. Synthesize Observation with Gemini 2.0 Flash
  analyzeBtn.addEventListener("click", async () => {
    const transcript = transcriptInput.value.trim();
    if (!transcript && !capturedPhotoFile) {
      alert("Please capture a photo or speak/type an observation first!");
      return;
    }

    analyzeBtn.disabled = true;
    analyzeBtn.innerHTML = '<span>⏳ Processing with Gemini Flash...</span>';

    const formData = new FormData();
    formData.append("transcript", transcript);
    if (capturedPhotoFile) {
      formData.append("photo", capturedPhotoFile);
    }

    try {
      const res = await fetch("/api/analyze-note", {
        method: "POST",
        body: formData
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({ detail: "Unknown server error" }));
        throw new Error(errData.detail || `Server error ${res.status}`);
      }
      const data = await res.json();
      
      if (data.status === "success") {
        const analysis = data.analysis;
        aiTitleInput.value = analysis.title || "Bench Note Observation";
        aiHtmlPreview.innerHTML = analysis.structured_html || "<p>Observation synthesized.</p>";

        const aiModelBadge = document.getElementById("aiModelBadge");
        if (aiModelBadge && analysis.source) {
          aiModelBadge.textContent = analysis.source;
        }

        // Badges for flags and tags
        aiBadgesContainer.innerHTML = "";
        (analysis.flags || []).forEach(flag => {
          const b = document.createElement("span");
          b.className = "text-[10px] bg-rose-900/60 text-rose-300 border border-rose-700 px-2 py-0.5 rounded font-semibold";
          b.textContent = `⚠️ ${flag}`;
          aiBadgesContainer.appendChild(b);
        });

        (analysis.tags || []).forEach(tag => {
          const b = document.createElement("span");
          b.className = "text-[10px] bg-cyan-950/60 text-cyan-300 border border-cyan-800 px-2 py-0.5 rounded font-medium";
          b.textContent = `#${tag}`;
          aiBadgesContainer.appendChild(b);
        });

        aiResultCard.classList.remove("hidden");
        aiResultCard.scrollIntoView({ behavior: "smooth" });
      }
    } catch (err) {
      console.error(err);
      alert("Failed to analyze note: " + (err.message || err));
    } finally {
      analyzeBtn.disabled = false;
      analyzeBtn.innerHTML = '<span>✨ Synthesize with Gemini Flash</span>';
    }
  });

  // 6. Commit to Signals Notebook
  commitBtn.addEventListener("click", async () => {
    const selectedEid = experimentSelect.value;
    if (!selectedEid) {
      alert("Please select a target experiment first!");
      return;
    }

    commitBtn.disabled = true;
    commitBtn.innerHTML = '<span>📤 Uploading to Signals Notebook...</span>';

    const formData = new FormData();
    formData.append("experiment_eid", selectedEid);
    formData.append("title", aiTitleInput.value);
    formData.append("structured_html", aiHtmlPreview.innerHTML);
    if (capturedPhotoFile) {
      formData.append("photo", capturedPhotoFile);
    }

    try {
      const res = await fetch("/api/commit-to-signals", {
        method: "POST",
        body: formData
      });
      const data = await res.json();

      if (data.status === "success") {
        aiResultCard.classList.add("hidden");
        successCard.classList.remove("hidden");
        successDetail.innerHTML = `Note &amp; photo linked to <strong>${selectedEid}</strong>.<br/><span class="text-[11px] text-emerald-400">Signals child entities created successfully with force=true</span>`;
        successCard.scrollIntoView({ behavior: "smooth" });
      } else {
        alert("Upload returned unexpected response: " + JSON.stringify(data));
      }
    } catch (err) {
      console.error(err);
      alert("Failed to commit to Signals Notebook: " + err.message);
    } finally {
      commitBtn.disabled = false;
      commitBtn.innerHTML = '<span>🚀 Commit to Signals Notebook</span>';
    }
  });

  newNoteBtn.addEventListener("click", () => {
    successCard.classList.add("hidden");
    removePhotoBtn.click();
    transcriptInput.value = "";
    updateWordCount();
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
});
