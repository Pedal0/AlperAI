/**
 * Main JavaScript file for the AI Application Generator
 * Handles UI interactions, animations, and form submissions
 */

// Helper function to show error messages
function showError(message) {
    const errorModal = new bootstrap.Modal(document.getElementById('errorModal'));
    const errorMessage = document.getElementById('errorMessage');
    
    if (errorMessage) {
        errorMessage.textContent = message;
        errorModal.show();
    } else {
        alert('Erreur: ' + message);
    }
}

// Helper function to toggle between sections
function toggleSection(showSectionId, hideSectionId) {
    const showSection = document.getElementById(showSectionId);
    const hideSection = document.getElementById(hideSectionId);
    
    if (showSection && hideSection) {
        hideSection.classList.add('d-none');
        showSection.classList.remove('d-none');
    }
}

// Initialize tooltips and popovers when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Copy to clipboard functionality
    document.querySelectorAll('.copy-btn').forEach(button => {
        button.addEventListener('click', function() {
            const value = this.getAttribute('data-value');
            if (!value) return;
            
            navigator.clipboard.writeText(value).then(() => {
                // Show success indicator
                const originalIcon = this.querySelector('i').className;
                this.querySelector('i').className = 'fas fa-check';
                
                // Reset icon after 2 seconds
                setTimeout(() => {
                    this.querySelector('i').className = originalIcon;
                }, 2000);
            }).catch(err => {
                console.error('Failed to copy text: ', err);
                showError('Impossible de copier: ' + err);
            });
        });
    });
    
    // Form validation and AJAX submission
    const forms = document.querySelectorAll('.needs-validation');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            } else if (form.getAttribute('data-ajax') === 'true') {
                event.preventDefault();
                
                // For forms that require AJAX submission
                const formData = new FormData(form);
                const submitUrl = form.getAttribute('action') || window.location.href;
                const loadingModalId = form.getAttribute('data-loading-modal');
                
                // Show loading modal if specified
                if (loadingModalId) {
                    const loadingModal = new bootstrap.Modal(document.getElementById(loadingModalId));
                    loadingModal.show();
                }
                
                // Make AJAX call
                fetch(submitUrl, {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        if (data.redirect) {
                            window.location.href = data.redirect;
                        } else if (data.message) {
                            alert(data.message);
                        }
                    } else {
                        showError(data.message || 'Une erreur est survenue.');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    showError('Erreur de connexion au serveur.');
                });
            }
            
            form.classList.add('was-validated');
        }, false);
    });
    
    // Initialize directory tree if present
    const directoryTree = document.getElementById('directoryTree');
    if (directoryTree) {
        document.querySelectorAll('.folder-item > span').forEach(folderLabel => {
            folderLabel.addEventListener('click', function() {
                this.parentElement.classList.toggle('collapsed');
            });
        });
    }
    
    // Application preview functionality
    const previewFrame = document.getElementById('previewFrame');
    if (previewFrame) {
        const refreshButton = document.getElementById('refreshPreview');
        if (refreshButton) {
            refreshButton.addEventListener('click', function() {
                if (previewFrame.contentWindow) {
                    previewFrame.contentWindow.location.reload();
                }
            });
        }
    }
    
    // Add animations to elements with data-animate attribute
    document.querySelectorAll('[data-animate]').forEach(element => {
        const animationClass = element.getAttribute('data-animate');
        if (animationClass) {
            // Check if element is in viewport
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add('animate__animated', animationClass);
                        observer.unobserve(entry.target);
                    }
                });
            });
            
            observer.observe(element);
        }
    });
});