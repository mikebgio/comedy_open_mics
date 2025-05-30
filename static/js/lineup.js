// Lineup management JavaScript functionality

document.addEventListener('DOMContentLoaded', function() {
    // Auto-refresh functionality for live lineup
    if (window.location.pathname.includes('/lineup/')) {
        initializeAutoRefresh();
    }
    
    // Initialize drag and drop for lineup management
    if (document.getElementById('lineup-container')) {
        initializeDragAndDrop();
    }
    
    // Initialize tooltips
    initializeTooltips();
    
    // Initialize confirmation dialogs
    initializeConfirmations();
});

function initializeAutoRefresh() {
    const refreshInterval = 30000; // 30 seconds
    let countdown = refreshInterval / 1000;
    
    // Create countdown display
    const countdownElement = document.createElement('small');
    countdownElement.className = 'text-muted';
    countdownElement.id = 'refresh-countdown';
    
    const lastUpdatedElement = document.getElementById('last-updated');
    if (lastUpdatedElement && lastUpdatedElement.parentNode) {
        lastUpdatedElement.parentNode.appendChild(document.createElement('br'));
        lastUpdatedElement.parentNode.appendChild(countdownElement);
    }
    
    // Update countdown every second
    const countdownTimer = setInterval(function() {
        countdown--;
        if (countdownElement) {
            countdownElement.textContent = `Auto-refresh in ${countdown}s`;
        }
        
        if (countdown <= 0) {
            location.reload();
        }
    }, 1000);
    
    // Manual refresh button
    const refreshButton = document.getElementById('refresh-lineup');
    if (refreshButton) {
        refreshButton.addEventListener('click', function() {
            clearInterval(countdownTimer);
            location.reload();
        });
    }
}

function initializeDragAndDrop() {
    const container = document.getElementById('lineup-container');
    if (!container) return;
    
    let draggedElement = null;
    let placeholder = null;
    
    // Create placeholder element
    function createPlaceholder() {
        const div = document.createElement('div');
        div.className = 'lineup-placeholder border rounded p-3 mb-2';
        div.style.border = '2px dashed var(--bs-primary)';
        div.style.background = 'var(--bs-primary-bg-subtle)';
        div.innerHTML = '<div class="text-center text-muted">Drop here</div>';
        return div;
    }
    
    const items = container.querySelectorAll('.lineup-item');
    items.forEach(item => {
        item.draggable = true;
        
        item.addEventListener('dragstart', function(e) {
            draggedElement = this;
            this.style.opacity = '0.5';
            
            // Create and insert placeholder
            placeholder = createPlaceholder();
            this.parentNode.insertBefore(placeholder, this.nextSibling);
        });
        
        item.addEventListener('dragend', function(e) {
            this.style.opacity = '';
            draggedElement = null;
            
            // Remove placeholder
            if (placeholder && placeholder.parentNode) {
                placeholder.parentNode.removeChild(placeholder);
            }
            placeholder = null;
        });
        
        item.addEventListener('dragover', function(e) {
            e.preventDefault();
            
            if (draggedElement && draggedElement !== this && placeholder) {
                const rect = this.getBoundingClientRect();
                const midpoint = rect.top + rect.height / 2;
                
                if (e.clientY < midpoint) {
                    this.parentNode.insertBefore(placeholder, this);
                } else {
                    this.parentNode.insertBefore(placeholder, this.nextSibling);
                }
            }
        });
        
        item.addEventListener('drop', function(e) {
            e.preventDefault();
            
            if (draggedElement && placeholder) {
                placeholder.parentNode.insertBefore(draggedElement, placeholder);
            }
        });
    });
}

function initializeTooltips() {
    // Initialize Bootstrap tooltips if available
    if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function(tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
}

function initializeConfirmations() {
    // Add confirmation dialogs to dangerous actions
    const dangerousActions = document.querySelectorAll('a[href*="cancel"], a[href*="delete"], button[data-confirm]');
    
    dangerousActions.forEach(element => {
        element.addEventListener('click', function(e) {
            const message = this.getAttribute('data-confirm') || 'Are you sure you want to proceed?';
            if (!confirm(message)) {
                e.preventDefault();
                return false;
            }
        });
    });
}

// Utility functions for AJAX requests
function makeRequest(url, options = {}) {
    const defaultOptions = {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        }
    };
    
    const finalOptions = { ...defaultOptions, ...options };
    
    return fetch(url, finalOptions)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        });
}

function showNotification(message, type = 'info') {
    // Simple notification system
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alertDiv.style.top = '20px';
    alertDiv.style.right = '20px';
    alertDiv.style.zIndex = '9999';
    alertDiv.style.minWidth = '300px';
    
    // Create message element safely using textContent to prevent XSS
    const messageElement = document.createElement('span');
    messageElement.textContent = message;
    
    // Create close button
    const closeButton = document.createElement('button');
    closeButton.type = 'button';
    closeButton.className = 'btn-close';
    closeButton.setAttribute('data-bs-dismiss', 'alert');
    
    // Append elements safely
    alertDiv.appendChild(messageElement);
    alertDiv.appendChild(closeButton);
    
    document.body.appendChild(alertDiv);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.parentNode.removeChild(alertDiv);
        }
    }, 5000);
}

// Export functions for use in other scripts
window.ComedyMicApp = {
    makeRequest,
    showNotification,
    initializeAutoRefresh,
    initializeDragAndDrop,
    initializeTooltips,
    initializeConfirmations
};
