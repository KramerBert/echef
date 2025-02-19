document.addEventListener('DOMContentLoaded', function() {
    const categoryFilter = document.getElementById('categoryFilter');
    
    // Check of we op de juiste pagina zijn
    if (!categoryFilter) {
        console.log('Search elements not found, probably not on dishes page');
        return;
    }

    const table = document.querySelector('.dish-table');
    if (!table) {
        console.log('Dish table not found, probably not on dishes page');
        return;
    }

    const rows = Array.from(table.getElementsByTagName('tr'));

    function filterTable() {
        const category = categoryFilter.value.toLowerCase();

        rows.forEach((row, index) => {
            if (index === 0) return; // Skip header row
            const cells = row.cells;
            if (!cells || cells.length < 2) return; // Skip invalid rows
            
            const rowCategory = cells[1].textContent.toLowerCase();
            
            const matchesCategory = category === '' || rowCategory === category;

            row.style.display = matchesCategory ? '' : 'none';
        });
    }

    categoryFilter.addEventListener('change', filterTable);
});
