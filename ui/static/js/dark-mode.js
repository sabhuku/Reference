/**
 * Dark Mode Toggle - Client-Side Only
 * NO BACKEND MODIFICATIONS
 * Persists theme preference via localStorage
 */

(function () {
    'use strict';

    // Detect system preference
    const prefersDarkScheme = window.matchMedia('(prefers-color-scheme: dark)');

    // Load saved preference or use system default
    const savedTheme = localStorage.getItem('theme');
    const initialTheme = savedTheme || (prefersDarkScheme.matches ? 'dark' : 'light');

    // Apply theme immediately to prevent flash
    applyTheme(initialTheme);

    /**
     * Apply theme to document
     * @param {string} theme - 'light' or 'dark'
     */
    function applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        updateToggleIcon(theme);
    }

    /**
     * Update dark mode toggle icon
     * @param {string} theme - Current theme
     */
    function updateToggleIcon(theme) {
        const icon = document.getElementById('darkModeIcon');
        if (icon) {
            icon.className = theme === 'dark' ? 'bi bi-sun' : 'bi bi-moon-stars';
        }

        const button = document.getElementById('darkModeToggle');
        if (button) {
            button.setAttribute('aria-label',
                theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'
            );
        }
    }

    /**
     * Toggle between light and dark mode
     */
    function toggleMode() {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        applyTheme(newTheme);
        localStorage.setItem('theme', newTheme);
    }

    /**
     * Listen for system preference changes
     * Only applies if user hasn't manually set a preference
     */
    prefersDarkScheme.addEventListener('change', function (e) {
        if (!localStorage.getItem('theme')) {
            applyTheme(e.matches ? 'dark' : 'light');
        }
    });

    // Initialize on DOM ready
    document.addEventListener('DOMContentLoaded', function () {
        console.log('UI Enhancements: Initializing...');

        // Update icon state
        updateToggleIcon(document.documentElement.getAttribute('data-theme'));

        // Attach click listener to all toggle buttons (navbar, sidebar, etc)
        const buttons = document.querySelectorAll('.dark-mode-toggle, #darkModeToggle');
        console.log(`UI Enhancements: Found ${buttons.length} toggle buttons`);

        buttons.forEach(btn => {
            btn.addEventListener('click', function (e) {
                console.log('UI Enhancements: Toggle clicked');
                e.preventDefault();
                toggleMode();
            });
        });
    });

})();
