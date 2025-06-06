document.addEventListener("DOMContentLoaded", function () {
    // Toggle password visibility
    document
      .querySelector(".toggle-password")
      .addEventListener("click", function () {
        const apiKeyInput = document.getElementById("api_key");
        const type =
          apiKeyInput.getAttribute("type") === "password" ? "text" : "password";
        apiKeyInput.setAttribute("type", type);

        // Toggle eye icon
        const icon = this.querySelector("i");
        icon.classList.toggle("fa-eye");
        icon.classList.toggle("fa-eye-slash");
      });

    // Example chips
    document.querySelectorAll(".example-chip").forEach((chip) => {
      chip.addEventListener("click", function () {
        const example = this.getAttribute("data-example");
        document.getElementById("user_prompt").value = example;
      });
    });

    // Folder selection - use native Windows selector via server request
    document
      .getElementById("browseButton")
      .addEventListener("click", function () {
        // Show loading indicator
        const currentValue = document.getElementById("target_directory").value;
        document.getElementById("target_directory").value =
          "Selection in progress...";
        document.getElementById("target_directory").disabled = true;
        document.getElementById("browseButton").disabled = true;

        // Call the new route that launches a native Windows file selector
        fetch(window.URL_OPEN_FOLDER_DIALOG)
          .then((response) => response.json())
          .then((data) => {
            document.getElementById("browseButton").disabled = false;
            document.getElementById("target_directory").disabled = false;

            if (data.status === "success") {
              // Update the field with the selected full path
              document.getElementById("target_directory").value = data.path;
            } else if (data.status === "canceled") {
              // If the user canceled, restore the previous value
              document.getElementById("target_directory").value =
                currentValue || "";
            } else {
              // In case of error, display a message and restore the previous value
              console.error("Error:", data.message);
              document.getElementById("target_directory").value =
                currentValue || "";

              // Offer manual entry method as fallback
              openManualFolderDialog(currentValue);
            }
          })
          .catch((error) => {
            console.error("Error communicating with the server:", error);
            document.getElementById("browseButton").disabled = false;
            document.getElementById("target_directory").disabled = false;
            document.getElementById("target_directory").value =
              currentValue || "";

            // Offer manual entry method as fallback
            openManualFolderDialog(currentValue);
          });
      });

    // Function to open a manual entry dialog as an alternative method
    function openManualFolderDialog(currentPath) {
      // Create a custom dialog
      const dialog = document.createElement("div");
      dialog.style.position = "fixed";
      dialog.style.left = "0";
      dialog.style.top = "0";
      dialog.style.width = "100%";
      dialog.style.height = "100%";
      dialog.style.backgroundColor = "rgba(0, 0, 0, 0.5)";
      dialog.style.zIndex = "9999";
      dialog.style.display = "flex";
      dialog.style.alignItems = "center";
      dialog.style.justifyContent = "center";

      const dialogContent = document.createElement("div");
      dialogContent.style.backgroundColor = "white";
      dialogContent.style.padding = "20px";
      dialogContent.style.borderRadius = "5px";
      dialogContent.style.width = "80%";
      dialogContent.style.maxWidth = "600px";
      dialogContent.innerHTML = `
                <h5>Manual Path Entry</h5>
                <p>The native folder selector didn't work. Please manually enter the full folder path:</p>
                <div class="input-group mb-3">
                    <input type="text" class="form-control" id="manualPath" value="${
                      currentPath || ""
                    }" placeholder="e.g. E:\\Dev_maison\\my_project">
                </div>
                <div class="form-text mb-3">
                    Examples of valid paths: C:\\Users\\name\\Projects\\MyProject, E:\\Dev_maison\\test
                </div>
                <div class="d-flex justify-content-end">
                    <button class="btn btn-secondary me-2" id="cancelPathBtn">Cancel</button>
                    <button class="btn btn-primary" id="confirmPathBtn">Confirm</button>
                </div>
            `;

      dialog.appendChild(dialogContent);
      document.body.appendChild(dialog);

      // Focus on the input
      setTimeout(() => {
        document.getElementById("manualPath").focus();
        document.getElementById("manualPath").select();
      }, 100);

      // Cancel button
      document
        .getElementById("cancelPathBtn")
        .addEventListener("click", function () {
          document.body.removeChild(dialog);
        });

      // Confirm button
      document
        .getElementById("confirmPathBtn")
        .addEventListener("click", function () {
          const selectedPath = document
            .getElementById("manualPath")
            .value.trim();
          if (selectedPath) {
            // Check if the path exists and create it if necessary
            const formData = new FormData();
            formData.append("full_path", selectedPath);
            formData.append("create_if_missing", "true");

            fetch(window.URL_VALIDATE_DIRECTORY, {
              method: "POST",
              body: formData,
            })
              .then((response) => response.json())
              .then((data) => {
                if (data.valid) {
                  document.getElementById("target_directory").value = data.path;
                  document.body.removeChild(dialog);
                } else {
                  alert(
                    data.error || "Invalid path. Please check and try again."
                  );
                }
              })
              .catch((error) => {
                console.error("Error:", error);
                document.body.removeChild(dialog);
                alert("An error occurred while validating the path");
              });
          } else {
            alert("Please enter a valid path");
          }
        });

      // Handle Enter key
      document
        .getElementById("manualPath")
        .addEventListener("keydown", function (e) {
          if (e.key === "Enter") {
            document.getElementById("confirmPathBtn").click();
          }
        });
    }

    // Form submission with actual API call instead of simulation
    const form = document.getElementById("appGeneratorForm");

    // Warn if Free model selected
    document.getElementById('model').addEventListener('change', function() {
      const val = this.value;
      // Detect models tagged as free
      if (val.includes(':free') || this.options[this.selectedIndex].text.includes('(Free)')) {
        const modalEl = document.getElementById('freeModelWarningModal');
        if (modalEl) {
          const warningModal = new bootstrap.Modal(modalEl);
          warningModal.show();
        }
      }
    });

    // Also disable tools if model label includes 'No Tools'
    document.getElementById('model').addEventListener('change', function() {
      const select = this;
      const optionText = select.options[select.selectedIndex].text;
      const useMcpToggle = document.getElementById('use_mcp_tools');
      const mcpContainer = document.getElementById('mcpToolsContainer');
      const frontendOptions = document.getElementById('frontendOptions');
      if (optionText.includes('No Tools')) {
        useMcpToggle.checked = false;
        useMcpToggle.disabled = true;
        if (mcpContainer) mcpContainer.style.display = 'none';
        // Hide frontend options for models that don't support tools
        if (frontendOptions) frontendOptions.style.display = 'none';
      } else {
        useMcpToggle.disabled = false;
        if (mcpContainer) mcpContainer.style.display = '';
        if (frontendOptions) frontendOptions.style.display = '';
      }
    });

    form.addEventListener("submit", function (e) {
      e.preventDefault(); // Prevent standard form submission

      // Validate form
      if (!form.checkValidity()) {
        e.stopPropagation();
        form.classList.add("was-validated");
        return;
      }

      // Prepare form data
      const formData = new FormData(form);

      // Handle custom model option
      if (document.getElementById("model").value === "custom") {
        const customModelValue = document
          .getElementById("customModel")
          .value.trim();
        if (customModelValue) {
          formData.set("model", customModelValue);
        } else {
          alert("Please enter a valid model identifier");
          return;
        }
      }

      // Show loading modal
      const loadingModal = new bootstrap.Modal(
        document.getElementById("loadingModal")
      );
      loadingModal.show();

      // Initialize progress elements
      const progressBar = document.getElementById("progressBar");
      const currentStep = document.getElementById("currentStep");
      const tipBox = document.getElementById("tipBox");
      const tipText = document.getElementById("tipText");

      // Ajout : zone d'affichage MCP
      let mcpMessage = null;
      let mcpBox = document.getElementById("mcpBox");
      if (!mcpBox) {
        mcpBox = document.createElement("div");
        mcpBox.className = "alert alert-success mt-3 d-none";
        mcpBox.id = "mcpBox";
        // Insérer juste après la barre de progression
        const progressElem = progressBar.parentElement;
        progressElem.parentElement.insertBefore(
          mcpBox,
          progressElem.nextSibling
        );
      }

      const tips = [
        "Free models may take longer due to rate limits.",
        "The more detailed the description, the better the code generation.",
        "MCP tools allow AI to access external information to improve the generated code.",
        "Generation can take from 30 seconds to 5 minutes depending on application complexity.",
        "You can preview and test the application directly in the interface once generated.",
      ];

      // Show random tips
      let tipIndex = 0;
      tipBox.classList.remove("d-none");
      tipText.textContent = tips[tipIndex];

      const tipInterval = setInterval(() => {
        tipIndex = (tipIndex + 1) % tips.length;
        tipBox.classList.remove("d-none");
        tipText.textContent = tips[tipIndex];
      }, 12000); // Show a new tip every 12 seconds

      // Make AJAX request to generate the application
      fetch(window.URL_GENERATE, {
        method: "POST",
        body: formData,
        headers: {
          "X-Requested-With": "XMLHttpRequest",
        },
      })
        .then((response) => {
          if (!response.ok) {
            throw new Error(`HTTP Error: ${response.status}`);
          }
          return response.json();
        })
        .then((data) => {
          // Check response
          if (data.status === "success") {
            // Start progress tracking
            pollGenerationProgress();
          } else if (data.status === "error") {
            // Display errors
            clearInterval(tipInterval);
            loadingModal.hide();

            let errorMessage = "An error occurred during generation.";
            if (data.errors && data.errors.length > 0) {
              errorMessage = data.errors.join("<br>");
            } else if (data.message) {
              errorMessage = data.message;
            }

            alert(errorMessage);
          }
        })
        .catch((error) => {
          console.error("Error:", error);
          clearInterval(tipInterval);
          loadingModal.hide();
          alert(
            "An error occurred while communicating with the server: " +
              error.message
          );
        });

      // Function to poll the server for generation progress
      function pollGenerationProgress() {
        let pollInterval = setInterval(() => {
          fetch(window.URL_GENERATION_PROGRESS)
            .then((response) => response.json())
            .then((data) => {
              // Update progress bar
              const progress = data.progress || 0;
              progressBar.style.width = `${progress}%`;

              // Update current step
              if (data.current_step) {
                currentStep.textContent = data.current_step;
                // Only show MCP message if it's not the generic tools enabled message
                if (
                  (data.current_step.includes("Outils MCP activés") ||
                  data.current_step.includes("MCP tools enabled")) &&
                  !data.current_step.startsWith("Define project structure") &&
                  !data.current_step.startsWith("Generating documentation") &&
                  !data.current_step.startsWith("Generating frontend") &&
                  !data.current_step.startsWith("Generating backend")
                ) {
                  mcpMessage = data.current_step;
                  mcpBox.textContent = mcpMessage;
                  mcpBox.classList.remove("d-none");
                } else if (
                  data.current_step.includes("MCP tools enabled")
                ) {
                  // Hide the green box for the generic tools enabled message
                  mcpBox.classList.add("d-none");
                }
              }
              // Afficher le message MCP si déjà détecté
              if (mcpMessage) {
                mcpBox.textContent = mcpMessage;
                mcpBox.classList.remove("d-none");
              }

              // If generation is complete
              if (data.status === "completed") {
                clearInterval(pollInterval);
                clearInterval(tipInterval);
                currentStep.textContent = "Generation complete!";
                mcpBox.classList.add("d-none"); // Masquer à la fin
                // Redirect to results page
                setTimeout(() => {
                  window.location.href = data.redirect_url || window.URL_GENERATION_RESULT;
                }, 1500);
              }

              // If generation failed
              if (data.status === "failed") {
                clearInterval(pollInterval);
                clearInterval(tipInterval);
                loadingModal.hide();
                mcpBox.classList.add("d-none");
                alert(
                  "Error during generation: " + (data.error || "Unknown error")
                );
              }
            })
            .catch((error) => {
              console.error("Error checking progress:", error);
            });
        }, 1500); // Check progress every 1.5 seconds
      }
    });

    // Toggle MCP dependencies
    const mcpToolsCheckbox = document.getElementById("use_mcp_tools");
    const frontendOptions = document.getElementById("frontendOptions");

    mcpToolsCheckbox.addEventListener("change", function () {
      frontendOptions.style.display = this.checked ? "block" : "none";
    });

    // Initialize state
    frontendOptions.style.display = mcpToolsCheckbox.checked ? "block" : "none";

    // Toggle custom model input
    const modelSelect = document.getElementById("model");
    const customModelContainer = document.getElementById(
      "customModelContainer"
    );
    modelSelect.addEventListener("change", function () {
      if (this.value === "custom") {
        customModelContainer.classList.remove("d-none");
      } else {
        customModelContainer.classList.add("d-none");
      }
    });
  });