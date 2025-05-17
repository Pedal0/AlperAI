document.addEventListener("DOMContentLoaded", function () {
  // Global variables
  let childWindow = null;
  const previewSessionId = document.getElementById("preview-session-id").value;
  const appStatusBadge = document.getElementById("app-status-badge");
  const appUrlEl = document.getElementById("app-url");
  const projectPath = document.getElementById("project-path").textContent;
  const refreshBtn = document.getElementById("refreshPreviewBtn");
  let logPollInterval = null;

  // Elements for configuration tab
  const projectTypeEl = document.getElementById("project-type");
  const appPortEl = document.getElementById("app-port");
  const appUrlConfigEl = document.getElementById("app-url-config");
  const mainFilesList = document.getElementById("main-files-list");

  // Patch IA UI elements
  const aiPatchAlert = document.getElementById("ai-patch-alert");
  const aiPatchFile = document.getElementById("ai-patch-file");
  const aiPatchExcerpt = document.getElementById("ai-patch-excerpt");
  // URL correction UI
  const manualUrlGroup = document.getElementById("manual-url-group");
  const manualUrlInput = document.getElementById("manual-url-input");
  const manualUrlApply = document.getElementById("manual-url-apply");

  const launchProgressContainer = document.getElementById(
    "launch-progress-container"
  );
  const launchProgressBar = document.getElementById("launch-progress-bar");
  const launchProgressMessage = document.getElementById(
    "launch-progress-message"
  );

  function updateConfig(status) {
    projectTypeEl.textContent = status.project_type || "Unknown";
    // extract port from URL
    const url = status.url || "";
    const port = url.split(":").pop();
    appPortEl.textContent = port;
    appUrlConfigEl.textContent = url;
    // list main files
    mainFilesList.innerHTML = "";
    fetch(`/list_files?directory=${encodeURIComponent(projectPath)}`)
      .then((res) => res.json())
      .then((data) => {
        if (data.status === "success") {
          data.files.forEach((file) => {
            const a = document.createElement("a");
            a.className = "list-group-item list-group-item-action";
            a.textContent = file;
            mainFilesList.appendChild(a);
          });
        } else {
          mainFilesList.innerHTML =
            '<div class="text-center py-3 text-muted">Unable to list files</div>';
        }
      })
      .catch(() => {
        mainFilesList.innerHTML =
          '<div class="text-center py-3 text-muted">Error retrieving files</div>';
      });
  }

  function showLaunchProgress(message, percentage) {
    if (launchProgressContainer && launchProgressBar && launchProgressMessage) {
      launchProgressContainer.style.display = "block";
      launchProgressMessage.textContent = message;
      launchProgressBar.style.width = `${percentage}%`;
      launchProgressBar.setAttribute("aria-valuenow", percentage);
    }
  }

  function hideLaunchProgress() {
    if (launchProgressContainer) {
      launchProgressContainer.style.display = "none";
    }
  }

  // Affichage du patch IA si détecté dans les logs
  function updateLogs(logs) {
    let aiPatch = null;
    for (const log of logs) {
      if (log.level === "AI_PATCH_APPLIED") {
        try {
          aiPatch = JSON.parse(log.message);
        } catch {}
      }
    }
    if (aiPatch) {
      aiPatchAlert.classList.remove("d-none");
      aiPatchFile.textContent = aiPatch.file;
      aiPatchExcerpt.textContent = aiPatch.patch_excerpt;
    } else {
      aiPatchAlert.classList.add("d-none");
    }

    // Check for launch messages in logs to update progress
    const installLog = logs.find(
      (log) => log.includes("npm install") || log.includes("Installing dependencies")
    );
    const startLog = logs.find(
      (log) => log.includes("Starting development server") || log.includes("Application starting")
    );

    if (installLog && !startLog) {
      showLaunchProgress("Installing dependencies (this may take a few minutes)...", 33);
    } else if (startLog) {
      showLaunchProgress("Starting application...", 66);
    }
  }

  // Correction manuelle d'URL si non détectée
  function showManualUrlInput() {
    manualUrlGroup.classList.remove("d-none");
    manualUrlInput.value = "";
    manualUrlInput.focus();
  }
  manualUrlApply.addEventListener("click", function () {
    const url = manualUrlInput.value.trim();
    if (url) {
      appUrlEl.innerHTML = `<a href="${url}" target="_blank" class="text-primary">${url}</a> <small class="text-muted">(Manual URL)</small>`;
      manualUrlGroup.classList.add("d-none");
    }
  });

  // Add beforeunload to stop preview
  window.addEventListener("beforeunload", function () {
    if (childWindow && !childWindow.closed) {
      navigator.sendBeacon(
        window.URL_PREVIEW_STOP_ON_EXIT,
        JSON.stringify({ session_id: previewSessionId })
      );
    }
  });

  // Navigation hooks to stop preview on link click
  document
    .querySelectorAll('a[href]:not([target="_blank"])')
    .forEach((link) => {
      link.addEventListener("click", function (e) {
        if (this.getAttribute("data-bs-toggle") === "tab") return;

        if (childWindow && !childWindow.closed) {
          e.preventDefault();
          fetch(window.URL_PREVIEW_STOP, { method: "POST" })
            .then(() => {
              window.location.href = this.href;
            })
            .catch(() => {
              window.location.href = this.href;
            });
        }
      });
    });

  function startApp() {
    showLaunchProgress("Initiating application launch...", 10);
    fetch(window.URL_PREVIEW_START, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: previewSessionId }),
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.status === "success") {
          showLaunchProgress("Application running.", 100);
          appStatusBadge.textContent = "Running";
          appStatusBadge.className = "badge bg-success me-2";
          if (data.url && data.url !== "null" && data.url !== "") {
            appUrlEl.innerHTML = `<a href="${data.url}" target="_blank" class="text-primary">${data.url}</a> <small class="text-muted">(Click to open in a new tab)</small>`;
          } else {
            appUrlEl.textContent = "Address not available";
            showManualUrlInput();
          }

          // Try to open in a new tab as a second step, but handle if blocked
          try {
            // Add a small delay before opening to ensure UI is updated
            setTimeout(() => {
              childWindow = window.open(data.url, "_blank");
              if (
                !childWindow ||
                childWindow.closed ||
                typeof childWindow.closed === "undefined"
              ) {
                // Popup was blocked
                console.log(
                  "Popup blocked. URL already shown as clickable link."
                );
              }
            }, 500);
          } catch (e) {
            console.error("Error opening new window:", e);
          }

          logPollInterval = setInterval(() => {
            fetch(window.URL_PREVIEW_STATUS)
              .then((r) => r.json())
              .then((s) => updateLogs(s.logs || []));
          }, 3000);
          // update configuration
          updateConfig(data);
          // Hide progress bar after a short delay if successful
          setTimeout(hideLaunchProgress, 2000);
        } else {
          alert(data.message);
          hideLaunchProgress(); // Hide on error
        }
      })
      .catch((e) => {
        alert("Error: " + e);
        hideLaunchProgress(); // Hide on error
      });
  }

  // Iteration button handler
  const iterateBtn = document.getElementById("iteratePreviewBtn");
  const iterationStatus = document.getElementById("iterationStatus");
  function startIteration() {
    const feedback = document.getElementById("interactionInput").value.trim();
    if (!feedback) {
      alert("Please enter feedback for iteration.");
      return;
    }
    iterateBtn.disabled = true;
    iterationStatus.innerHTML = "<em>Iteration started...</em>";
    const form = new FormData();
    form.append("api_key", window.API_KEY);
    form.append("model", window.MODEL);
    form.append("feedback", feedback);
    form.append("regenerate_code", "off");
    fetch(window.URL_CONTINUE_ITERATION, { method: "POST", body: form })
      .then((res) => res.json())
      .then((data) => {
        if (data.status === "success") {
          pollIteration();
        } else {
          iterationStatus.textContent =
            data.message || "Error starting iteration";
          iterateBtn.disabled = false;
        }
      })
      .catch((err) => {
        iterationStatus.textContent = "Network error: " + err;
        iterateBtn.disabled = false;
      });
  }
  function pollIteration() {
    const interval = setInterval(() => {
      fetch(window.URL_GENERATION_PROGRESS)
        .then((res) => res.json())
        .then((data) => {
          iterationStatus.textContent = `Progress: ${data.progress}% - ${data.current_step}`;
          if (data.status === "completed" || data.status === "failed") {
            clearInterval(interval);
            if (data.status === "completed") {
              iterationStatus.textContent = "Iteration completed.";
              // restart preview to apply changes without changing port
              restartApp();
            } else {
              iterationStatus.textContent =
                "Iteration failed: " + (data.error || "Unknown error");
            }
            iterateBtn.disabled = false;
          }
        })
        .catch((err) => {
          clearInterval(interval);
          iterationStatus.textContent = "Error during polling: " + err;
          iterateBtn.disabled = false;
        });
    }, 2000);
  }
  iterateBtn.addEventListener("click", startIteration);

  // Event Listeners
  refreshBtn.addEventListener("click", () => fetch(window.URL_PREVIEW_REFRESH));

  // Auto-start application on preview load
  if (previewSessionId) {
    startApp();
  }

  // Désactive la gestion des boutons start/stop/restart car ils n'existent plus
  // (Pas d'ajout d'eventListener sur startAppBtn, stopAppBtn, restartAppBtn, openInNewTabBtn)
});
