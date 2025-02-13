import os
from app import create_app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("\n" + "="*60)
    print(" Server is running!")
    print(" You can access the application at:")
    print(f" * http://127.0.0.1:{port}")
    print(f" * http://localhost:{port} (alternative)")
    print("="*60 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=port)
