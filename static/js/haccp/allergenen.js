function saveAllergenControl() {
    const form = document.getElementById('allergenControlForm');
    if (!form) {
        console.error('Form not found');
        return;
    }

    const formData = new FormData();

    // Add form fields with error checking
    try {
        formData.append('locatie', form.querySelector('[name="locatie"]')?.value || '');
        formData.append('procedure_gevolgd', form.querySelector('[name="procedure_gevolgd"]')?.checked || false);
        formData.append('werkplek_schoon', form.querySelector('[name="werkplek_schoon"]')?.checked || false);
        formData.append('gereedschap_schoon', form.querySelector('[name="gereedschap_schoon"]')?.checked || false);
        formData.append('gescheiden_bereid', form.querySelector('[name="gescheiden_bereid"]')?.checked || false);
        formData.append('opmerking', form.querySelector('[name="opmerking"]')?.value || '');
    } catch (e) {
        console.error('Error getting form values:', e);
        showAlert('danger', 'Er is een fout opgetreden bij het verzamelen van de formuliergegevens');
        return;
    }

    // Get CSRF token with fallback
    let csrf_token;
    try {
        const metaTag = document.querySelector('meta[name="csrf-token"]');
        if (!metaTag) {
            throw new Error('CSRF token meta tag not found');
        }
        csrf_token = metaTag.getAttribute('content');
        if (!csrf_token) {
            throw new Error('CSRF token is empty');
        }
    } catch (e) {
        console.error('Error getting CSRF token:', e);
        showAlert('danger', 'Beveiligingstoken ontbreekt. Vernieuw de pagina.');
        return;
    }

    // Send request
    fetch('/api/haccp/allergenen/add', {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': csrf_token
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Hide modal first
            const modalElement = document.getElementById('newAllergenModal');
            const modalInstance = bootstrap.Modal.getInstance(modalElement);
            modalInstance.hide();
            
            // Reset form
            form.reset();
            
            // Remove modal backdrop and show success message
            document.querySelector('.modal-backdrop')?.remove();
            document.body.classList.remove('modal-open');
            
            // Refresh page after a short delay
            setTimeout(() => {
                window.location.reload();
            }, 500);
            
            showAlert('success', 'Allergenen controle succesvol toegevoegd');
        } else {
            showAlert('danger', data.error || 'Er is een fout opgetreden');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showAlert('danger', 'Er is een fout opgetreden');
    });
}

function loadAllergenControls() {
    fetch('/api/haccp/allergenen/list')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const tbody = document.getElementById('allergenControlsList');
                tbody.innerHTML = '';
                
                data.controls.forEach(control => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${new Date(control.datum_controle).toLocaleString()}</td>
                        <td>${control.locatie}</td>
                        <td>${control.procedure_gevolgd ? '✅' : '❌'}</td>
                        <td>${control.werkplek_schoon ? '✅' : '❌'}</td>
                        <td>${control.gereedschap_schoon ? '✅' : '❌'}</td>
                        <td>${control.gescheiden_bereid ? '✅' : '❌'}</td>
                        <td>${control.opmerking || ''}</td>
                        <td>
                            <button class="btn btn-sm btn-primary" onclick="editAllergenControl(${control.controle_id}, '${control.locatie}', ${control.procedure_gevolgd}, ${control.werkplek_schoon}, ${control.gereedschap_schoon}, ${control.gescheiden_bereid}, '${control.opmerking || ''}')">
                                <i class="fas fa-edit"></i>
                            </button>
                            <button class="btn btn-sm btn-danger" onclick="deleteAllergenControl(${control.controle_id})">
                                <i class="fas fa-trash"></i>
                            </button>
                        </td>
                    `;
                    tbody.appendChild(row);
                });
            } else {
                showAlert('danger', data.error || 'Er is een fout opgetreden bij het laden van de controles');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('danger', 'Er is een fout opgetreden bij het laden van de controles');
        });
}

function editAllergenControl(controle_id, locatie, procedure_gevolgd, werkplek_schoon, gereedschap_schoon, gescheiden_bereid, opmerking) {
    document.getElementById('edit_controle_id').value = controle_id;
    document.getElementById('edit_locatie').value = locatie;
    document.getElementById('edit_procedure_gevolgd').checked = procedure_gevolgd;
    document.getElementById('edit_werkplek_schoon').checked = werkplek_schoon;
    document.getElementById('edit_gereedschap_schoon').checked = gereedschap_schoon;
    document.getElementById('edit_gescheiden_bereid').checked = gescheiden_bereid;
    document.getElementById('edit_opmerking').value = opmerking;
    
    const modal = new bootstrap.Modal(document.getElementById('editAllergenModal'));
    modal.show();
}

function updateAllergenControl() {
    const form = document.getElementById('editAllergenControlForm');
    const controle_id = document.getElementById('edit_controle_id').value;
    const formData = new FormData(form);
    
    const csrf_token = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

    fetch(`/api/haccp/allergenen/${controle_id}/update`, {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': csrf_token
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const modal = bootstrap.Modal.getInstance(document.getElementById('editAllergenModal'));
            modal.hide();
            document.querySelector('.modal-backdrop')?.remove();
            document.body.classList.remove('modal-open');
            setTimeout(() => {
                window.location.reload();
            }, 500);
            showAlert('success', 'Controle bijgewerkt');
        } else {
            showAlert('danger', data.error || 'Er is een fout opgetreden');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showAlert('danger', 'Er is een fout opgetreden');
    });
}

function deleteAllergenControl(controle_id) {
    if (!confirm('Weet je zeker dat je deze controle wilt verwijderen?')) {
        return;
    }

    const csrf_token = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

    fetch(`/api/haccp/allergenen/${controle_id}/delete`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrf_token
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            loadAllergenControls();
            showAlert('success', 'Controle verwijderd');
        } else {
            showAlert('danger', data.error || 'Er is een fout opgetreden');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showAlert('danger', 'Er is een fout opgetreden');
    });
}

function showAlert(type, message) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    const container = document.querySelector('.container');
    container.insertBefore(alertDiv, container.firstChild);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

// Load controls when page loads
document.addEventListener('DOMContentLoaded', loadAllergenControls);
