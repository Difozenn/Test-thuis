// Configuration for database applications
const databases = {
    'houtanalyse': {
        name: 'Hout Analyse',
        url: '/houtanalyse',
        description: 'Geavanceerde houtdetectie en analyse systeem voor kwaliteitscontrole en volume berekeningen',
        status: 'online',
        version: 'v2.1.0'
    },
    'cnc-datalog': {
        name: 'CNC Datalog',
        url: '/cnc-datalog',
        description: 'Machine monitoring en productie tracking voor CNC bewerkingscentra met realtime data analyse',
        status: 'online',
        version: 'v3.0.2'
    },
    'project-datalog': {
        name: 'Project Datalog',
        url: '/project-datalog',
        description: 'Project management en resource planning systeem voor optimale workflow en tijdsregistratie',
        status: 'online',
        version: 'v1.8.5'
    }
};

// System status check interval (in milliseconds)
const STATUS_CHECK_INTERVAL = 30000; // 30 seconds

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializePortal();
});

function initializePortal() {
    // Initialize app cards
    initializeAppCards();
    
    // Initialize modal
    initializeModal();
    
    // Initialize new module functionality
    initializeNewModule();
    
    // Start status monitoring
    startStatusMonitoring();
    
    // Check for deep links
    checkDeepLink();
    
    // Add keyboard shortcuts
    initializeKeyboardShortcuts();
    
    // Load saved modules
    loadSavedModules();
}

function initializeAppCards() {
    const appItems = document.querySelectorAll('.app-item[data-app]');
    
    appItems.forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            const appId = this.getAttribute('data-app');
            navigateToApp(appId);
        });
    });
}

function navigateToApp(appId) {
    const app = databases[appId];
    
    if (app) {
        // Log navigation event
        logEvent('navigation', { app: appId });
        
        // Add loading animation
        const item = document.querySelector(`[data-app="${appId}"]`);
        if (item) {
            item.style.opacity = '0.8';
            item.style.pointerEvents = 'none';
        }
        
        // Navigate after short delay
        setTimeout(() => {
            window.location.href = app.url;
        }, 200);
    }
}

function initializeModal() {
    const modal = document.getElementById('infoModal');
    const closeBtn = document.getElementById('closeModal');
    
    if (closeBtn) {
        closeBtn.addEventListener('click', function() {
            closeModal();
        });
    }
    
    if (modal) {
        // Close modal when clicking outside
        modal.addEventListener('click', function(e) {
            if (e.target === modal) {
                closeModal();
            }
        });
    }
    
    function closeModal() {
        if (modal) {
            modal.classList.remove('active');
            document.body.style.overflow = '';
        }
    }
}

function startStatusMonitoring() {
    // Check system status periodically
    checkSystemStatus();
    setInterval(checkSystemStatus, STATUS_CHECK_INTERVAL);
}

function checkSystemStatus() {
    // Simulate status check (in production, this would call your APIs)
    Object.keys(databases).forEach(appId => {
        const app = databases[appId];
        
        // Simulate random status (for demo)
        // In production, this would be an actual API call
        const isOnline = Math.random() > 0.1; // 90% uptime simulation
        
        updateAppStatus(appId, isOnline ? 'online' : 'offline');
    });
    
    updateOverallStatus();
}

function updateAppStatus(appId, status) {
    const card = document.querySelector(`[data-app="${appId}"]`);
    if (card) {
        const statusBadge = card.querySelector('.status-badge');
        if (statusBadge) {
            statusBadge.textContent = status.toUpperCase();
            statusBadge.className = `status-badge ${status}`;
        }
        
        card.setAttribute('data-status', status);
        databases[appId].status = status;
    }
}

function updateOverallStatus() {
    const statusIndicator = document.querySelector('.status-indicator');
    const statusDot = document.querySelector('.status-dot');
    
    const allSystems = Object.values(databases);
    const onlineSystems = allSystems.filter(sys => sys.status === 'online');
    
    if (onlineSystems.length === allSystems.length) {
        statusIndicator.innerHTML = '<span class="status-dot"></span>Alle systemen operationeel';
        statusDot.style.background = 'var(--success-color)';
    } else if (onlineSystems.length > 0) {
        statusIndicator.innerHTML = `<span class="status-dot"></span>${onlineSystems.length} van ${allSystems.length} systemen online`;
        statusDot.style.background = 'var(--warning-color)';
    } else {
        statusIndicator.innerHTML = '<span class="status-dot"></span>Systemen offline';
        statusDot.style.background = 'var(--error-color)';
    }
}

function initializeKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        // Number keys 1-3 for quick navigation
        if (e.key >= '1' && e.key <= '3') {
            const apps = Object.keys(databases);
            const index = parseInt(e.key) - 1;
            if (apps[index]) {
                navigateToApp(apps[index]);
            }
        }
        
        // ESC to close modal
        if (e.key === 'Escape') {
            const modal = document.getElementById('infoModal');
            if (modal && modal.classList.contains('active')) {
                const closeBtn = document.getElementById('closeModal');
                if (closeBtn) closeBtn.click();
            }
        }
    });
}

function checkDeepLink() {
    const urlParams = new URLSearchParams(window.location.search);
    const app = urlParams.get('app');
    
    if (app && databases[app]) {
        // Auto-navigate to specified app
        setTimeout(() => {
            navigateToApp(app);
        }, 100); // Small delay for DOM
    }
}

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 1rem 1.5rem;
        background: var(--bg-container);
        border-radius: 8px;
        box-shadow: var(--shadow-lg);
        z-index: 1001;
        animation: slideIn 0.3s ease-out;
    `;
    
    document.body.appendChild(notification);
    
    // Remove after 3 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => {
            notification.remove();
        }, 300);
    }, 3000);
}

function logEvent(eventType, data) {
    // Analytics logging (implement your analytics here)
    console.log(`[ANALYTICS] ${eventType}:`, data);
    
    // In production, send to your analytics service
    // Example: gtag('event', eventType, data);
}

// Public API for external configuration
window.MintjensPortal = {
    databases: databases,
    updateDatabase: function(id, config) {
        if (databases[id]) {
            databases[id] = { ...databases[id], ...config };
            // Update UI if needed
        }
    },
    navigateTo: navigateToApp,
    checkStatus: checkSystemStatus,
    showNotification: showNotification
};

// New Module Functionality
function initializeNewModule() {
    const addModuleBtn = document.getElementById('addNewModule');
    const newModuleModal = document.getElementById('newModuleModal');
    const closeNewModuleBtn = document.getElementById('closeNewModuleModal');
    const cancelNewModuleBtn = document.getElementById('cancelNewModule');
    const newModuleForm = document.getElementById('newModuleForm');
    const moduleIconInput = document.getElementById('moduleIcon');
    const iconPreview = document.getElementById('iconPreview');
    
    // Open new module modal
    if (addModuleBtn) {
        addModuleBtn.addEventListener('click', function(e) {
            e.preventDefault();
            openNewModuleModal();
        });
    }
    
    // Close modal handlers
    if (closeNewModuleBtn) {
        closeNewModuleBtn.addEventListener('click', closeNewModuleModal);
    }
    
    if (cancelNewModuleBtn) {
        cancelNewModuleBtn.addEventListener('click', closeNewModuleModal);
    }
    
    // Close modal when clicking outside
    if (newModuleModal) {
        newModuleModal.addEventListener('click', function(e) {
            if (e.target === newModuleModal) {
                closeNewModuleModal();
            }
        });
    }
    
    // Handle file upload preview
    if (moduleIconInput) {
        moduleIconInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file && file.type.startsWith('image/')) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    iconPreview.innerHTML = `<img src="${e.target.result}" alt="Preview">`;
                };
                reader.readAsDataURL(file);
            }
        });
    }
    
    // Handle form submission
    if (newModuleForm) {
        newModuleForm.addEventListener('submit', function(e) {
            e.preventDefault();
            handleNewModuleSubmit();
        });
    }
    
    // Update keyboard shortcuts for new module modal
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && newModuleModal && newModuleModal.classList.contains('active')) {
            closeNewModuleModal();
        }
    });
}

function openNewModuleModal() {
    const modal = document.getElementById('newModuleModal');
    if (modal) {
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
        // Reset form
        const form = document.getElementById('newModuleForm');
        if (form) form.reset();
        document.getElementById('iconPreview').innerHTML = '<span>Klik om een afbeelding te selecteren</span>';
    }
}

function closeNewModuleModal() {
    const modal = document.getElementById('newModuleModal');
    if (modal) {
        modal.classList.remove('active');
        document.body.style.overflow = '';
    }
}

function handleNewModuleSubmit() {
    const moduleName = document.getElementById('moduleName').value;
    const moduleUrl = document.getElementById('moduleUrl').value;
    const moduleIconFile = document.getElementById('moduleIcon').files[0];
    
    if (!moduleName || !moduleUrl || !moduleIconFile) {
        showNotification('Vul alle velden in', 'error');
        return;
    }
    
    // Read the image file
    const reader = new FileReader();
    reader.onload = async function(e) {
        const moduleData = {
            name: moduleName,
            url: moduleUrl,
            icon: e.target.result
        };
        
        try {
            // Send to server
            const response = await fetch('/api/modules', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(moduleData)
            });
            
            if (response.ok) {
                const savedModule = await response.json();
                
                // Add to page
                addModuleToGrid(savedModule);
                
                // Close modal
                closeNewModuleModal();
                
                // Show success message
                showNotification('Module succesvol toegevoegd!', 'success');
            } else {
                const error = await response.json();
                showNotification('Fout bij toevoegen module: ' + (error.error || 'Onbekende fout'), 'error');
            }
        } catch (error) {
            showNotification('Fout bij toevoegen module: ' + error.message, 'error');
        }
    };
    
    reader.readAsDataURL(moduleIconFile);
}

function loadSavedModules() {
    // Load modules from server instead of localStorage
    fetch('/api/modules')
        .then(response => response.json())
        .then(modules => {
            modules.forEach(module => {
                addModuleToGrid(module);
            });
        })
        .catch(error => {
            console.error('Error loading modules:', error);
        });
}

function addModuleToGrid(moduleData) {
    const grid = document.querySelector('.apps-grid');
    const placeholder = document.getElementById('addNewModule');
    
    if (grid && placeholder) {
        // Create new module element
        const moduleElement = document.createElement('a');
        moduleElement.href = moduleData.url;
        moduleElement.className = 'app-item custom-module';
        moduleElement.setAttribute('data-app', moduleData.id);
        moduleElement.innerHTML = `
            <img src="${moduleData.icon}" alt="${moduleData.name}" class="app-icon-image">
            <h3>${moduleData.name}</h3>
            <button class="delete-module" title="Verwijder module">×</button>
        `;
        
        // Add click handler
        moduleElement.addEventListener('click', function(e) {
            e.preventDefault();
            // Check if delete button was clicked
            if (e.target.classList.contains('delete-module')) {
                deleteModule(moduleData.id, moduleElement);
                return;
            }
            // Log event
            logEvent('navigation', { app: moduleData.id, custom: true });
            // Navigate to URL
            window.location.href = moduleData.url;
        });
        
        // Insert before placeholder
        grid.insertBefore(moduleElement, placeholder);
    }
}

function deleteModule(moduleId, moduleElement) {
    if (confirm('Weet je zeker dat je deze module wilt verwijderen?')) {
        fetch(`/api/modules/${moduleId}`, {
            method: 'DELETE'
        })
        .then(response => {
            if (response.ok) {
                // Remove from DOM
                moduleElement.remove();
                showNotification('Module verwijderd', 'success');
            } else {
                showNotification('Fout bij verwijderen module', 'error');
            }
        })
        .catch(error => {
            showNotification('Fout bij verwijderen module: ' + error.message, 'error');
        });
    }
}