from utils.db import get_db_connection
import logging
import json
import time
from decimal import Decimal

logger = logging.getLogger(__name__)

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

def import_ingredients_from_supplier(chef_id, supplier_id, data=None):
    """
    Background task to import ingredients from a supplier
    """
    logger.info(f"Starting background import for chef {chef_id} from supplier {supplier_id}")
    
    try:
        # Initialize result data structure for progress tracking
        result = {
            'status': 'PROGRESS',
            'current': 0,
            'total': len(data) if data else 0,
            'processed': 0,
            'skipped': 0
        }
        
        conn = get_db_connection()
        if conn is None:
            return {'status': 'error', 'message': 'Database connection failed'}
            
        cur = conn.cursor(dictionary=True)
        
        # Get supplier information
        cur.execute("""
            SELECT * FROM leveranciers
            WHERE leverancier_id = %s AND chef_id = %s
        """, (supplier_id, chef_id))
        supplier = cur.fetchone()
        
        if not supplier:
            return {'status': 'error', 'message': 'Supplier not found'}
        
        # Process ingredients - implement the same logic as your synchronous endpoint
        # but in this background task
        processed = 0
        skipped = 0
        total_items = len(data) if data else 0
        
        # Process ingredients here
        for index, item in enumerate(data or []):
            try:
                # Update progress
                if index % 10 == 0:
                    result = {
                        'status': 'PROGRESS',
                        'current': index,
                        'total': total_items,
                        'processed': processed,
                        'skipped': skipped
                    }
                
                # Your ingredient processing logic here
                # ...
                
                processed += 1
                # Simulate work (remove in production)
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error processing ingredient: {str(e)}")
                skipped += 1
        
        # Final result
        result = {
            'status': 'complete',
            'processed': processed,
            'skipped': skipped,
            'total': total_items
        }
        
        cur.close()
        conn.close()
        
        return result
        
    except Exception as e:
        logger.error(f"Error in import task: {str(e)}", exc_info=True)
        return {'status': 'error', 'message': str(e)}
