document.addEventListener('DOMContentLoaded', function() {
    const dishSearch = document.getElementById('dishSearch');
    const categoryFilter = document.getElementById('categoryFilter');
    const dishTable = document.querySelector('.dish-table tbody');

    function filterDishes() {
        const searchValue = dishSearch.value.toLowerCase();
        const categoryValue = categoryFilter.value.toLowerCase();
        const rows = dishTable.getElementsByTagName('tr');

        for (let row of rows) {
            const dishName = row.querySelector('.dish-name-link').textContent.toLowerCase();
            const category = row.getElementsByTagName('td')[1].textContent.toLowerCase();
            
            const matchesSearch = dishName.includes(searchValue);
            const matchesCategory = !categoryValue || category === categoryValue;
            
            row.style.display = matchesSearch && matchesCategory ? '' : 'none';
        }
    }

    // Add event listeners
    if (dishSearch) {
        dishSearch.addEventListener('input', filterDishes);
    }
    if (categoryFilter) {
        categoryFilter.addEventListener('change', filterDishes);
    }
});
