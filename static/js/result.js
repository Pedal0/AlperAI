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
      window.location.href = window.URL_DOWNLOAD_ZIP;
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
