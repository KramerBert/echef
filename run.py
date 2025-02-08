import os
from app import create_app
from waitress import serve

application = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting server on port {port}")  # Debug output
    serve(application, host='0.0.0.0', port=port)
