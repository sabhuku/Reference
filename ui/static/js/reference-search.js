/**
 * Client-Side Reference Search
 * NO BACKEND MODIFICATIONS
 * Filters references by title and type without server calls
 */

(function () {
    'use strict';

    /**
     * Filter references based on search inputs
     * Uses data-* attributes added in template
     * Does NOT modify reference content or call formatting filters
     */
    window.filterReferences = function () {
        const titleQuery = document.getElementById('searchTitle')?.value.toLowerCase() || '';
        const typeFilter = document.getElementById('filterType')?.value.toLowerCase() || '';

        const cards = document.querySelectorAll('.ref-card');
        let visibleCount = 0;
        let totalCount = cards.length;

        cards.forEach(function (card) {
            // Read from data attributes (set in template)
            const title = card.getAttribute('data-title') || '';
            const type = card.getAttribute('data-type') || '';

            // Simple substring matching
            const matchesTitle = !titleQuery || title.includes(titleQuery);
            const matchesType = !typeFilter || type.includes(typeFilter);

            if (matchesTitle && matchesType) {
                card.classList.remove('hidden-by-search');
                card.style.display = '';
                visibleCount++;
            } else {
                card.classList.add('hidden-by-search');
                card.style.display = 'none';
            }
        });

        // Update result count
        updateResultCount(visibleCount, totalCount);
    };

    /**
     * Clear all search filters
     */
    window.clearFilters = function () {
        const titleInput = document.getElementById('searchTitle');
        const typeSelect = document.getElementById('filterType');

        if (titleInput) titleInput.value = '';
        if (typeSelect) typeSelect.value = '';

        filterReferences();
    };

    /**
     * Update search result count display
     * @param {number} visible - Number of visible references
     * @param {number} total - Total number of references
     */
    function updateResultCount(visible, total) {
        const countElement = document.getElementById('searchResultCount');
        if (countElement) {
            if (visible === total) {
                countElement.textContent = `Showing all ${total} references`;
            } else {
                countElement.textContent = `Showing ${visible} of ${total} references`;
            }
        }
    }

    /**
     * Initialize search on page load
     */
    document.addEventListener('DOMContentLoaded', function () {
        const cards = document.querySelectorAll('.ref-card');
        updateResultCount(cards.length, cards.length);
    });

})();
