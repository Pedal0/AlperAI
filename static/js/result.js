document.addEventListener("DOMContentLoaded", function () {
    // Copy to clipboard functionality
    document.querySelectorAll(".copy-btn").forEach((button) => {
      button.addEventListener("click", function () {
        const value = this.getAttribute("data-value");
        navigator.clipboard.writeText(value).then(() => {
          // Change button to show copied status
          const icon = this.querySelector("i");
          icon.classList.remove("fa-copy");
          icon.classList.add("fa-check");
          setTimeout(() => {
            icon.classList.remove("fa-check");
            icon.classList.add("fa-copy");
          }, 2000);
        });
      });
    });

    // Load the actual project structure
    function loadProjectStructure() {
      const directoryTree = document.getElementById("directoryTree");
      directoryTree.innerHTML =
        '<div class="text-center py-3"><i class="fas fa-spinner fa-spin me-2"></i>Loading structure...</div>';

      // API call to retrieve the project structure
      fetch(window.URL_GET_PROJECT_STRUCTURE, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          project_dir: window.TARGET_DIR,
        }),
      })
        .then((response) => response.json())
        .then((data) => {
          if (data.status === "success" && data.structure) {
            // Clear current content
            directoryTree.innerHTML = "";

            // Recursive function to build the tree
            function buildTreeHTML(items, parentElement) {
              const ul = document.createElement("ul");

              items.forEach((item) => {
                const li = document.createElement("li");

                if (item.type === "folder") {
                  li.className = "folder-item";
                  li.innerHTML = `<i class="fas fa-folder"></i> <span>${item.name}/</span>`;

                  // Add folder children
                  if (item.children && item.children.length > 0) {
                    buildTreeHTML(item.children, li);
                  } else {
                    // Empty folder
                    const emptyUl = document.createElement("ul");
                    const emptyLi = document.createElement("li");
                    emptyLi.className = "text-muted small";
                    emptyLi.innerHTML =
                      '<i class="fas fa-info-circle"></i> Empty folder';
                    emptyUl.appendChild(emptyLi);
                    li.appendChild(emptyUl);
                  }
                } else {
                  // It's a file
                  li.className = "file-item";

                  // Determine icon based on extension
                  let fileIcon = "fa-file";
                  const extension = item.name.split(".").pop().toLowerCase();

                  if (
                    ["html", "htm", "jsx", "tsx", "xml"].includes(extension)
                  ) {
                    fileIcon = "fa-file-code";
                  } else if (
                    [
                      "js",
                      "ts",
                      "py",
                      "java",
                      "c",
                      "cpp",
                      "cs",
                      "go",
                      "php",
                      "rb",
                    ].includes(extension)
                  ) {
                    fileIcon = "fa-file-code";
                  } else if (
                    ["css", "scss", "sass", "less"].includes(extension)
                  ) {
                    fileIcon = "fa-file-code";
                  } else if (
                    ["json", "yaml", "yml", "toml"].includes(extension)
                  ) {
                    fileIcon = "fa-file-code";
                  } else if (
                    ["png", "jpg", "jpeg", "gif", "svg", "webp"].includes(
                      extension
                    )
                  ) {
                    fileIcon = "fa-file-image";
                  } else if (["pdf"].includes(extension)) {
                    fileIcon = "fa-file-pdf";
                  } else if (["md", "txt", "rtf"].includes(extension)) {
                    fileIcon = "fa-file-alt";
                  }

                  li.innerHTML = `<i class="fas ${fileIcon}"></i> <span>${item.name}</span>`;
                }

                ul.appendChild(li);
              });

              parentElement.appendChild(ul);
            }

            // Build the tree
            buildTreeHTML(data.structure, directoryTree);

            // Add event listeners for folders
            document
              .querySelectorAll(".folder-item > span")
              .forEach((folderLabel) => {
                folderLabel.addEventListener("click", function () {
                  this.parentElement.classList.toggle("collapsed");
                });
              });
          } else {
            directoryTree.innerHTML = `
                        <div class="alert alert-warning">
                            <i class="fas fa-exclamation-triangle me-2"></i>
                            Unable to load project structure: ${
                              data.message || "Unknown error"
                            }
                        </div>
                    `;
          }
        })
        .catch((error) => {
          console.error("Error loading structure:", error);
          directoryTree.innerHTML = `
                    <div class="alert alert-danger">
                        <i class="fas fa-exclamation-circle me-2"></i>
                        Error retrieving structure: ${error.message}
                    </div>
                `;
        });
    }

    // Load project structure when structure tab is shown
    document
      .getElementById("structure-tab")
      .addEventListener("shown.bs.tab", function (e) {
        loadProjectStructure();
      });

    // Download button functionality
    document.getElementById("downloadBtn").addEventListener("click", function () {
      const url = "/download_zip";
      console.log("Download button clicked. Preparing to fetch from URL:", url);

      fetch(url)
        .then((response) => {
          if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
          }
          const disposition = response.headers.get("Content-Disposition");
          let filename = "downloaded_project.zip";
          if (disposition && disposition.indexOf("attachment") !== -1) {
            const filenameRegex = /filename[^;=\n]*=((['"])(.*?)\2|[^;\n]*)/;
            const matches = filenameRegex.exec(disposition);
            if (matches != null && matches[3]) {
              filename = matches[3];
            }
          }
          console.log("Suggested filename from header:", filename);
          return response.blob().then((blob) => ({ blob, filename }));
        })
        .then(({ blob, filename }) => {
          const reader = new FileReader();
          reader.onloadend = function () {
            const base64data = reader.result.split(",")[1];
            if (
              window.pywebview &&
              window.pywebview.api &&
              typeof window.pywebview.api.save_file_via_dialog === "function"
            ) {
              console.log(
                "Calling window.pywebview.api.save_file_via_dialog with filename:",
                filename
              );
              // Appeler la fonction Python exposée pour sauvegarder le fichier
              // et gérer la promesse retournée par la fonction Python
              window.pywebview.api
                .save_file_via_dialog(filename, base64data)
                .then((result) => {
                  if (result && result.success) {
                    console.log("File saved successfully via Python:", result.path);
                  } else {
                    console.error(
                      "Error saving file via Python:",
                      result ? result.error : "Unknown error"
                    );
                  }
                })
                .catch((error) => {
                  console.error("Error calling save_file_via_dialog:", error);
                });
            } else {
              console.error(
                "The function save_file_via_dialog is not available on window.pywebview.api or is not a function."
              );
              alert(
                "Download functionality not initialized correctly. Ensure pywebview API is available."
              );
            }
          };
          reader.onerror = function (error) {
            console.error("FileReader error:", error);
            alert("Error preparing file for download.");
          };
          reader.readAsDataURL(blob);
        })
        .catch((error) => {
          console.error("Error fetching or processing blob for download:", error);
          alert("Failed to retrieve the file for download: " + error.message);
        });
    });

    // Open folder button (this would require backend support in a real implementation)
    document.querySelectorAll(".open-folder-btn").forEach((button) => {
      button.addEventListener("click", function () {
        alert(
          "This feature would open the project folder in the file explorer."
        );
      });
    });
  });
