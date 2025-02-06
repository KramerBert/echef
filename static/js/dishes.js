document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('dishSearch');
    const categoryFilter = document.getElementById('categoryFilter');
    const table = document.querySelector('.dish-table');

    if (!table) {
        console.error("Table with class 'dish-table' not found!");
        return;
    }

    const rows = table.getElementsByTagName('tr');

    function filterTable() {
        const searchTerm = searchInput.value.toLowerCase();
        const category = categoryFilter.value.toLowerCase();

        for (let i = 1; i < rows.length; i++) {
            const row = rows[i];
            const name = row.cells[0].textContent.toLowerCase();
            const rowCategory = row.cells[1].textContent.toLowerCase();
            
            const matchesSearch = name.includes(searchTerm);
            const matchesCategory = category === '' || rowCategory === category;

            row.style.display = matchesSearch && matchesCategory ? '' : 'none';
        }
    }

    searchInput.addEventListener('input', filterTable);
    categoryFilter.addEventListener('change', filterTable);
});
