/**
 * Harvard Citation Preview Tooltips
 * NO BACKEND MODIFICATIONS
 * Uses ALREADY-RENDERED citation text from DOM
 * Does NOT call formatting filters or modify reference data
 */

(function () {
    'use strict';

    /**
     * Initialize citation preview tooltips
     * Extracts already-rendered citation text from .citation-text elements
     * Does NOT reinvoke any formatting filters
     */
    function initCitationPreviews() {
        const refCards = document.querySelectorAll('.ref-card');

        refCards.forEach(function (card) {
            // Extract ALREADY-RENDERED citation text from DOM
            const citationElement = card.querySelector('.citation-text');
            if (!citationElement) return;

            // Use textContent (not innerHTML) to avoid XSS
            const citationText = citationElement.textContent.trim();
            if (!citationText) return;

            // Initialize Bootstrap 5 tooltip
            // Uses already-rendered content only
            try {
                new bootstrap.Tooltip(card, {
                    title: citationText,
                    placement: 'top',
                    trigger: 'hover focus',
                    html: false, // Security: no HTML injection
                    customClass: 'citation-tooltip',
                    delay: { show: 300, hide: 100 },
                    boundary: 'viewport'
                });
            } catch (e) {
                // Graceful degradation if Bootstrap not loaded
                console.warn('Bootstrap Tooltip not available:', e);
            }
        });
    }

    /**
     * Initialize on DOM ready
     * Waits for Bootstrap to be available
     */
    document.addEventListener('DOMContentLoaded', function () {
        // Check if Bootstrap is loaded
        if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
            initCitationPreviews();
        } else {
            console.warn('Bootstrap not loaded, citation previews disabled');
        }
    });

})();
