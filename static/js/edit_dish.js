document.addEventListener('DOMContentLoaded', function() {
    // Verwijder alle oude event listeners door nieuwe elementen te maken
    const dietForm = document.getElementById('dietForm');
    const allergeenForm = document.getElementById('allergeenForm');

    // Initialiseer nieuwe checkboxes voor diëten
    dietForm.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
        const newCheckbox = checkbox.cloneNode(true);
        checkbox.parentNode.replaceChild(newCheckbox, checkbox);
    });

    // Initialiseer nieuwe checkboxes voor allergenen
    allergeenForm.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
        const newCheckbox = checkbox.cloneNode(true);
        checkbox.parentNode.replaceChild(newCheckbox, checkbox);
    });

    // Voeg simpele submit handlers toe
    dietForm.addEventListener('submit', handleDietSubmit);
    allergeenForm.addEventListener('submit', handleAllergenSubmit);

    // Initialiseer dieet tags click handlers
    document.querySelectorAll('.dieet-tag').forEach(tag => {
        tag.addEventListener('click', function(e) {
            // Voorkom dat het event naar parent elements gaat
            e.stopPropagation();
            
            // Toggle active class
            this.classList.toggle('active');
            
            // Update checkbox status
            const checkbox = this.querySelector('input[type="checkbox"]');
            if (checkbox) {
                checkbox.checked = !checkbox.checked;
            }

            // Visuele feedback
            if (this.classList.contains('active')) {
                this.style.transform = 'scale(1.05)';
                setTimeout(() => this.style.transform = '', 200);
            }
        });
    });
});

function handleDietSubmit(e) {
    e.preventDefault();
    const form = e.target;
    submitForm(form, 'Diëten');
}

function handleAllergenSubmit(e) {
    e.preventDefault();
    const form = e.target;
    submitForm(form, 'Allergenen');
}

function submitForm(form, type) {
    const formData = new FormData(form);
    
    fetch(form.action, {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': formData.get('csrf_token'),
            'Cache-Control': 'no-cache'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Voeg een kleine vertraging toe voor betere UX
            setTimeout(() => {
                window.location.reload();
            }, 100);
        } else {
            // Als er een specifieke foutmelding is, toon deze
            const errorMessage = data.error || `Fout bij opslaan ${type.toLowerCase()}`;
            throw new Error(errorMessage);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        // Toon een gebruiksvriendelijke foutmelding
        if (error.message.includes("Deadlock")) {
            alert(`Er is een tijdelijk probleem bij het opslaan van de ${type.toLowerCase()}. ` +
                  "De pagina wordt opnieuw geladen om het opnieuw te proberen.");
            window.location.reload();
        } else {
            alert(`Er is een fout opgetreden bij het opslaan van de ${type.toLowerCase()}: ${error.message}`);
        }
    });
}

function updateDieten() {
    // Corrigeer de URL
    const form = document.createElement('form');
    form.method = 'POST';
    // Update dit pad om overeen te komen met de Flask route
    form.action = window.location.pathname.replace('/dishes/', '/dish/') + '/dieten';
    
    // Voeg CSRF token toe
    const csrfToken = document.querySelector('input[name="csrf_token"]').value;
    const csrfInput = document.createElement('input');
    csrfInput.type = 'hidden';
    csrfInput.name = 'csrf_token';
    csrfInput.value = csrfToken;
    form.appendChild(csrfInput);

    // Verzamel alle actieve diëten
    document.querySelectorAll('.dieet-tag input[type="checkbox"]:checked').forEach(input => {
        const clonedInput = input.cloneNode(true);
        form.appendChild(clonedInput);
    });

    // Debug logging
    console.log('Submitting to URL:', form.action);
    console.log('Selected diets:', Array.from(form.elements).filter(el => el.name === 'dieten[]').map(el => el.value));

    // Submit het formulier via fetch
    fetch(form.action, {
        method: 'POST',
        body: new FormData(form),
        headers: {
            'X-CSRFToken': csrfToken
        }
    })
    .then(response => {
        if (!response.ok) throw new Error('Network response was not ok');
        return response.json();
    })
    .then(data => {
        if (data.success) {
            showSuccessMessage('Diëten succesvol opgeslagen');
            setTimeout(() => location.reload(), 1000);
        } else {
            throw new Error(data.error || 'Onbekende fout');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showErrorMessage('Er is een fout opgetreden bij het opslaan van de diëten');
    });
}

function showSuccessMessage(message) {
    const alert = document.createElement('div');
    alert.className = 'alert alert-success alert-dismissible fade show';
    alert.innerHTML = `
        ${message}
        <button type="button" class="close" data-dismiss="alert" aria-label="Close">
            <span aria-hidden="true">&times;</span>
        </button>
    `;

    // Zoek eerst de juiste container
    const container = document.querySelector('.dieet-selector');
    if (container) {
        container.insertBefore(alert, container.firstChild);
    } else {
        // Fallback naar card-body als dieet-selector niet bestaat
        const cardBody = document.querySelector('.card-body');
        if (cardBody) {
            cardBody.insertBefore(alert, cardBody.firstChild);
        }
    }

    // Verwijder de melding na 3 seconden
    setTimeout(() => {
        if (alert.parentNode) {
            alert.remove();
        }
    }, 3000);
}

function showErrorMessage(message) {
    const alert = document.createElement('div');
    alert.className = 'alert alert-danger alert-dismissible fade show';
    alert.innerHTML = `
        ${message}
        <button type="button" class="close" data-dismiss="alert" aria-label="Close">
            <span aria-hidden="true">&times;</span>
        </button>
    `;

    // Zoek eerst de juiste container
    const container = document.querySelector('.dieet-selector');
    if (container) {
        container.insertBefore(alert, container.firstChild);
    } else {
        // Fallback naar card-body als dieet-selector niet bestaat
        const cardBody = document.querySelector('.card-body');
        if (cardBody) {
            cardBody.insertBefore(alert, cardBody.firstChild);
        }
    }
}
