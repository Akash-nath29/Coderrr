#!/usr/bin/env python3
"""
Preview artifact in browser.

Usage:
    python preview_artifact.py --artifact-dir ./my-artifact
"""

import argparse
import sys
import json
from pathlib import Path
import http.server
import socketserver
import webbrowser
import threading


def preview_artifact(artifact_dir: str, port: int = 3000):
    """Start preview server and open browser."""
    artifact_path = Path(artifact_dir)
    
    if not artifact_path.exists():
        raise ValueError(f"Artifact directory not found: {artifact_dir}")
    
    index_file = artifact_path / 'index.html'
    if not index_file.exists():
        raise ValueError("index.html not found in artifact directory")
    
    # Create simple HTTP server
    Handler = http.server.SimpleHTTPRequestHandler
    
    class QuietHandler(Handler):
        def log_message(self, format, *args):
            pass  # Suppress logging
    
    try:
        with socketserver.TCPServer(("", port), QuietHandler) as httpd:
            url = f"http://localhost:{port}/"
            print(json.dumps({
                "status": "running",
                "url": url,
                "port": port,
                "message": "Press Ctrl+C to stop"
            }))
            
            # Open browser
            webbrowser.open(url)
            
            # Change to artifact directory
            import os
            os.chdir(artifact_path)
            
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped")
    except OSError as e:
        if "Address already in use" in str(e):
            print(json.dumps({
                "error": f"Port {port} is already in use",
                "suggestion": f"Try --port {port + 1}"
            }))
        else:
            raise


def main():
    parser = argparse.ArgumentParser(description='Preview artifact')
    parser.add_argument('--artifact-dir', required=True, help='Artifact directory')
    parser.add_argument('--port', type=int, default=3000, help='Server port')
    
    args = parser.parse_args()
    
    try:
        preview_artifact(args.artifact_dir, args.port)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
