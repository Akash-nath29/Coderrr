#!/usr/bin/env python3
"""
Fetch HTML content from a URL.

This tool makes an HTTP GET request to the specified URL and outputs
the HTML content to stdout.

Usage:
    python fetch_page.py --url https://example.com

Exit Codes:
    0 - Success
    1 - Network error or invalid URL
"""

import argparse
import sys

try:
    import requests
except ImportError:
    print("Error: 'requests' package is required. Install with: pip install requests", file=sys.stderr)
    sys.exit(1)


def fetch_page(url: str, timeout: int = 30) -> str:
    """
    Fetch the HTML content from a URL.
    
    Args:
        url: The URL to fetch
        timeout: Request timeout in seconds
        
    Returns:
        The HTML content as a string
        
    Raises:
        requests.RequestException: If the request fails
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    response = requests.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()
    
    return response.text


def main():
    parser = argparse.ArgumentParser(
        description='Fetch HTML content from a URL',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
    python fetch_page.py --url https://example.com
    python fetch_page.py --url https://example.com --timeout 60
        '''
    )
    parser.add_argument(
        '--url',
        required=True,
        help='The URL to fetch'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=30,
        help='Request timeout in seconds (default: 30)'
    )
    
    args = parser.parse_args()
    
    try:
        html = fetch_page(args.url, args.timeout)
        print(html)
    except requests.exceptions.MissingSchema:
        print(f"Error: Invalid URL format. Make sure to include http:// or https://", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.ConnectionError:
        print(f"Error: Failed to connect to {args.url}", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.Timeout:
        print(f"Error: Request timed out after {args.timeout} seconds", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(f"Error: HTTP {e.response.status_code} - {e.response.reason}", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
