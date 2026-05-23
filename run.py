import os
import sys
import uvicorn
from dotenv import load_dotenv

# Load .env from the root directory
load_dotenv()

# Add the backend folder to the Python path
# This ensures 'src' is discoverable as a top-level module
root_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(root_dir, "backend")
sys.path.append(backend_dir)

if __name__ == "__main__":
    print("Starting Code Intel System...")
    print(f"Root Directory: {root_dir}")
    print(f"Backend Directory: {backend_dir}")
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    reload_enabled = os.getenv("RELOAD", "false").strip().lower() == "true"
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"Reload: {reload_enabled}")
    
    # Run uvicorn pointing to the main app
    # We use 'src.main:app' and set the app_dir to the backend/ folder
    uvicorn.run(
        "src.main:app", 
        host=host, 
        port=port, 
        reload=reload_enabled,
        app_dir=backend_dir
    )
