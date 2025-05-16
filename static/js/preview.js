document.addEventListener("DOMContentLoaded", function () {
  // Global variables
  let childWindow = null;
  const previewSessionId = document.getElementById("preview-session-id").value;
  const appStatusBadge = document.getElementById("app-status-badge");
  const appUrlEl = document.getElementById("app-url");
  const logsContent = document.getElementById("logsContent");
  const logLevelSelect = document.querySelector(".log-level");
  const startAppBtn = document.getElementById("startAppBtn");
  const stopAppBtn = document.getElementById("stopAppBtn");
  const restartAppBtn = document.getElementById("restartAppBtn");
  const openInNewTabBtn = document.getElementById("openInNewTab");
  const projectPath = document.getElementById("project-path").textContent;
  const refreshBtn = document.getElementById("refreshPreviewBtn");
  let logPollInterval = null;

  // Elements for configuration tab
  const projectTypeEl = document.getElementById("project-type");
  const appPortEl = document.getElementById("app-port");
  const appUrlConfigEl = document.getElementById("app-url-config");
  const mainFilesList = document.getElementById("main-files-list");

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

  // Add updateLogs to render log entries
  function updateLogs(logs) {
    logsContent.innerHTML = logs.map((entry) => `<div>${entry}</div>`).join("");
  }

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
    fetch(window.URL_PREVIEW_START, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: previewSessionId }),
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.status === "success") {
          appStatusBadge.textContent = "Running";
          appStatusBadge.className = "badge bg-success me-2";
          appUrlEl.textContent = data.url; // Always show the clickable URL first, then try to open window
          document.getElementById(
            "app-url"
          ).innerHTML = `<a href="${data.url}" target="_blank" class="text-primary">${data.url}</a> 
               <small class="text-muted">(Click to open in a new tab)</small>`;

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

          startAppBtn.disabled = true;
          stopAppBtn.disabled = false;
          restartAppBtn.disabled = false;
          openInNewTabBtn.disabled = false;
          logPollInterval = setInterval(() => {
            fetch(window.URL_PREVIEW_STATUS)
              .then((r) => r.json())
              .then((s) => updateLogs(s.logs || []));
          }, 3000);
          // update configuration
          updateConfig(data);
        } else {
          alert(data.message);
        }
      })
      .catch((e) => alert("Error: " + e));
  }

  function stopApp() {
    fetch(window.URL_PREVIEW_STOP, { method: "POST" })
      .then((r) => r.json())
      .then((data) => {
        if (data.status === "success") {
          if (childWindow && !childWindow.closed) childWindow.close();
          clearInterval(logPollInterval);
          appStatusBadge.textContent = "Stopped";
          appStatusBadge.className = "badge bg-secondary me-2";
          startAppBtn.disabled = false;
          stopAppBtn.disabled = true;
          restartAppBtn.disabled = true;
        } else alert(data.message);
      })
      .catch((e) => alert("Error: " + e));
  }
  function restartApp() {
    fetch(window.URL_PREVIEW_RESTART, { method: "POST" })
      .then((r) => r.json())
      .then((data) => {
        if (data.status === "success") {
          // Close existing window if it exists
          if (childWindow && !childWindow.closed) childWindow.close();

          // Always show the clickable URL first, then try to open window
          document.getElementById(
            "app-url"
          ).innerHTML = `<a href="${data.url}" target="_blank" class="text-primary">${data.url}</a> 
               <small class="text-muted">(Click to open in a new tab)</small>`;

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
                  "Popup blocked on restart. URL already shown as clickable link."
                );
              }
            }, 500);
          } catch (e) {
            console.error("Error opening new window:", e);
          }

          // update configuration after restart
          updateConfig(data);
        } else alert(data.message);
      })
      .catch((e) => alert("Error: " + e));
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

  // Initialize logs polling on start
  // Event Listeners
  startAppBtn.addEventListener("click", startApp);
  stopAppBtn.addEventListener("click", stopApp);
  restartAppBtn.addEventListener("click", restartApp);
  openInNewTabBtn.addEventListener("click", () => {
    if (childWindow) childWindow.focus();
  });
  refreshBtn.addEventListener("click", () => fetch(window.URL_PREVIEW_REFRESH));

  // Auto-start application on preview load
  startApp();
});
