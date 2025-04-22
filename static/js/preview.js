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
      projectTypeEl.textContent = status.project_type || 'Unknown';
      // extract port from URL
      const url = status.url || '';
      const port = url.split(':').pop();
      appPortEl.textContent = port;
      appUrlConfigEl.textContent = url;
      // list main files
      mainFilesList.innerHTML = '';
      fetch(`/list_files?directory=${encodeURIComponent(projectPath)}`)
        .then(res => res.json())
        .then(data => {
          if (data.status === 'success') {
            data.files.forEach(file => {
              const a = document.createElement('a');
              a.className = 'list-group-item list-group-item-action';
              a.textContent = file;
              mainFilesList.appendChild(a);
            });
          } else {
            mainFilesList.innerHTML = '<div class="text-center py-3 text-muted">Unable to list files</div>';
          }
        }).catch(() => {
          mainFilesList.innerHTML = '<div class="text-center py-3 text-muted">Error retrieving files</div>';
        });
    }

    // Add beforeunload to stop preview
    window.addEventListener("beforeunload", function () {
      if (childWindow && !childWindow.closed) {
        navigator.sendBeacon(window.URL_PREVIEW_STOP_ON_EXIT, JSON.stringify({ session_id: previewSessionId }));
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
            appUrlEl.textContent = data.url;
            childWindow = window.open(data.url, "_blank");
            startAppBtn.disabled = true;
            stopAppBtn.disabled = false;
            restartAppBtn.disabled = false;
            openInNewTabBtn.disabled = false;
            logPollInterval = setInterval(() => {
              fetch(window.URL_PREVIEW_STATUS).then((r) => r.json()).then((s) => updateLogs(s.logs || []));
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
            if (childWindow && !childWindow.closed) childWindow.close();
            childWindow = window.open(data.url, "_blank");
            // update configuration after restart
            updateConfig(data);
          } else alert(data.message);
        })
        .catch((e) => alert("Error: " + e));
    }

    // Initialize logs polling on start
    // Event Listeners
    startAppBtn.addEventListener("click", startApp);
    stopAppBtn.addEventListener("click", stopApp);
    restartAppBtn.addEventListener("click", restartApp);
    openInNewTabBtn.addEventListener("click", () => { if (childWindow) childWindow.focus(); });
    refreshBtn.addEventListener("click", () => fetch(window.URL_PREVIEW_REFRESH));
    
    // Auto-start application on preview load
    startApp();
  });
