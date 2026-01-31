#!/usr/bin/env python3
"""
Extract text content from HTML.

This tool parses HTML and extracts clean, readable text. It can read HTML
from a command-line argument or from stdin, making it easy to pipe from
other commands like fetch_page.

Usage:
    python extract_text.py --html "<div>Hello World</div>"
    cat page.html | python extract_text.py
    python extract_text.py --selector ".main-content" < page.html

Exit Codes:
    0 - Success
    2 - HTML parsing error
    3 - Invalid CSS selector
"""

import argparse
import sys
import re

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("Error: 'beautifulsoup4' package is required. Install with: pip install beautifulsoup4", file=sys.stderr)
    sys.exit(1)


def extract_text(html: str, selector: str = None) -> str:
    """
    Extract text content from HTML.
    
    Args:
        html: The HTML content to parse
        selector: Optional CSS selector to target specific elements
        
    Returns:
        Clean text extracted from the HTML
        
    Raises:
        ValueError: If the selector is invalid
    """
    try:
        soup = BeautifulSoup(html, 'html.parser')
    except Exception as e:
        raise ValueError(f"Failed to parse HTML: {e}")
    
    # Remove script and style elements
    for element in soup(['script', 'style', 'noscript', 'header', 'footer', 'nav']):
        element.decompose()
    
    if selector:
        try:
            elements = soup.select(selector)
            if not elements:
                return ""
            text_parts = [elem.get_text(separator=' ', strip=True) for elem in elements]
            text = '\n\n'.join(text_parts)
        except Exception as e:
            raise ValueError(f"Invalid CSS selector '{selector}': {e}")
    else:
        text = soup.get_text(separator=' ', strip=True)
    
    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = text.strip()
    
    return text


def main():
    parser = argparse.ArgumentParser(
        description='Extract text content from HTML',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
    python extract_text.py --html "<div>Hello World</div>"
    cat page.html | python extract_text.py
    python extract_text.py --selector "article" < page.html
    echo "<p>Test</p>" | python extract_text.py --selector "p"
        '''
    )
    parser.add_argument(
        '--html',
        help='HTML content to parse (if not provided, reads from stdin)'
    )
    parser.add_argument(
        '--selector',
        help='CSS selector to target specific elements (e.g., ".content", "article", "h1")'
    )
    
    args = parser.parse_args()
    
    # Get HTML from argument or stdin
    if args.html:
        html = args.html
    else:
        if sys.stdin.isatty():
            print("Error: No HTML provided. Use --html argument or pipe HTML to stdin.", file=sys.stderr)
            sys.exit(2)
        html = sys.stdin.read()
    
    if not html.strip():
        print("Error: Empty HTML content", file=sys.stderr)
        sys.exit(2)
    
    try:
        text = extract_text(html, args.selector)
        if text:
            print(text)
        else:
            if args.selector:
                print(f"No content found matching selector: {args.selector}", file=sys.stderr)
    except ValueError as e:
        if "selector" in str(e).lower():
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(3)
        else:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(2)


if __name__ == '__main__':
    main()
