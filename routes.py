# ...existing code...

@app.route('/dashboard/<chef_naam>/suppliers/<int:leverancier_id>/delete', methods=['POST'])
@login_required
def delete_supplier(chef_naam, leverancier_id):
    """Delete a supplier and all its associated ingredients"""
    if chef_naam != session.get('chef_naam'):
        flash("Je hebt geen toegang tot deze pagina", "danger")
        return redirect(url_for('dashboard', chef_naam=session.get('chef_naam')))

    chef_id = session.get('chef_id')

    conn = get_db_connection()
    if not conn:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"success": False, "error": "Database connection failed"}), 500
        flash("Database connection failed", "danger")
        return redirect(url_for('manage_suppliers', chef_naam=chef_naam))

    cur = conn.cursor(dictionary=True)
    
    try:
        # Start a transaction
        conn.start_transaction()
        
        # First check if the supplier belongs to this chef
        cur.execute("SELECT * FROM leveranciers WHERE leverancier_id = %s AND chef_id = %s", (leverancier_id, chef_id))
        supplier = cur.fetchone()
        
        if not supplier:
            conn.rollback()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({"success": False, "error": "Leverancier niet gevonden of geen toegang"}), 404
            flash("Leverancier niet gevonden of geen toegang", "danger")
            return redirect(url_for('manage_suppliers', chef_naam=chef_naam))
        
        # NEW: First delete all ingredients from this supplier
        cur.execute("SELECT ingredient_id FROM ingredients WHERE leverancier_id = %s", (leverancier_id,))
        ingredient_ids = [row['ingredient_id'] for row in cur.fetchall()]
        
        if ingredient_ids:
            # Delete ingredients from dish_ingredients first
            placeholders = ', '.join(['%s'] * len(ingredient_ids))
            cur.execute(f"DELETE FROM dish_ingredients WHERE ingredient_id IN ({placeholders})", ingredient_ids)
            
            # Now delete the ingredients themselves
            cur.execute(f"DELETE FROM ingredients WHERE ingredient_id IN ({placeholders})", ingredient_ids)
            deleted_ingredients_count = cur.rowcount
        else:
            deleted_ingredients_count = 0
            
        # Now delete the supplier
        cur.execute("DELETE FROM leveranciers WHERE leverancier_id = %s", (leverancier_id,))
        conn.commit()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                "success": True, 
                "deleted_ingredients": deleted_ingredients_count,
                "message": f"Leverancier {supplier['naam']} en {deleted_ingredients_count} ingrediënten verwijderd"
            })
            
        flash(f"Leverancier {supplier['naam']} en {deleted_ingredients_count} ingrediënten verwijderd", "success")
        return redirect(url_for('manage_suppliers', chef_naam=chef_naam))
        
    except Exception as e:
        conn.rollback()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"success": False, "error": str(e)}), 500
        flash(f"Error: {str(e)}", "danger")
        return redirect(url_for('manage_suppliers', chef_naam=chef_naam))
    finally:
        cur.close()
        conn.close()

# ...existing code...
