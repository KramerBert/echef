document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('dishSearch');
    const categoryFilter = document.getElementById('categoryFilter');
    const table = document.querySelector('.dish-table');

    if (!table) {
        console.warn("Table with class 'dish-table' not found on this page. Skipping script.");
        return;
    }

    const rows = Array.from(table.getElementsByTagName('tr'));

    function filterTable() {
        const searchTerm = searchInput.value.toLowerCase();
        const category = categoryFilter.value.toLowerCase();

        rows.forEach((row, index) => {
            if (index === 0) return; // Skip header row
            const name = row.cells[0].textContent.toLowerCase();
            const rowCategory = row.cells[1].textContent.toLowerCase();
            
            const matchesSearch = name.includes(searchTerm);
            const matchesCategory = category === '' || rowCategory === category;

            row.classList.toggle('hidden', !(matchesSearch && matchesCategory));
        });
    }

    searchInput.addEventListener('input', filterTable);
    categoryFilter.addEventListener('change', filterTable);
});
