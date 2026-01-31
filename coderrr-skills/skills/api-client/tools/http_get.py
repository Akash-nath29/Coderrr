#!/usr/bin/env python3
"""
Make HTTP GET requests.

This tool makes GET requests to URLs and outputs the response body.
JSON responses are automatically pretty-printed.

Usage:
    python http_get.py --url https://api.example.com/users
    python http_get.py --url https://api.example.com/users --headers '{"Auth": "token"}'

Exit Codes:
    0 - Success
    1 - Invalid arguments or URL
    2 - Network/connection error
    3 - HTTP error (4xx, 5xx)
"""

import argparse
import sys
import json

try:
    import requests
except ImportError:
    print("Error: 'requests' package is required. Install with: pip install requests", file=sys.stderr)
    sys.exit(1)


def http_get(url: str, headers: dict = None, timeout: int = 30) -> str:
    """
    Make an HTTP GET request.
    
    Args:
        url: The URL to request
        headers: Optional headers dictionary
        timeout: Request timeout in seconds
        
    Returns:
        Response body as string
    """
    default_headers = {
        'User-Agent': 'Coderrr-API-Client/1.0',
        'Accept': 'application/json'
    }
    
    if headers:
        default_headers.update(headers)
    
    response = requests.get(url, headers=default_headers, timeout=timeout)
    response.raise_for_status()
    
    return response.text


def main():
    parser = argparse.ArgumentParser(
        description='Make HTTP GET requests',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
    python http_get.py --url https://api.example.com/users
    python http_get.py --url https://api.example.com/data --headers '{"Authorization": "Bearer token"}'
        '''
    )
    parser.add_argument(
        '--url',
        required=True,
        help='The URL to request'
    )
    parser.add_argument(
        '--headers',
        help='JSON string of headers'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=30,
        help='Request timeout in seconds (default: 30)'
    )
    
    args = parser.parse_args()
    
    # Parse headers if provided
    headers = None
    if args.headers:
        try:
            headers = json.loads(args.headers)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid headers JSON - {e}", file=sys.stderr)
            sys.exit(1)
    
    try:
        response = http_get(args.url, headers, args.timeout)
        
        # Try to pretty-print if JSON
        try:
            data = json.loads(response)
            print(json.dumps(data, indent=2, ensure_ascii=False))
        except json.JSONDecodeError:
            # Not JSON, print as-is
            print(response)
            
    except requests.exceptions.MissingSchema:
        print(f"Error: Invalid URL. Include http:// or https://", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.ConnectionError as e:
        print(f"Error: Connection failed - {e}", file=sys.stderr)
        sys.exit(2)
    except requests.exceptions.Timeout:
        print(f"Error: Request timed out after {args.timeout} seconds", file=sys.stderr)
        sys.exit(2)
    except requests.exceptions.HTTPError as e:
        print(f"Error: HTTP {e.response.status_code} - {e.response.reason}", file=sys.stderr)
        # Still output the response body if available
        if e.response.text:
            try:
                data = json.loads(e.response.text)
                print(json.dumps(data, indent=2), file=sys.stderr)
            except json.JSONDecodeError:
                print(e.response.text, file=sys.stderr)
        sys.exit(3)
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == '__main__':
    main()
