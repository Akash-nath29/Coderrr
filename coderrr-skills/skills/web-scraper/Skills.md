---
name: web-scraper
description: Fetch, parse, and extract content from web pages. Use this skill when the user asks to scrape websites, extract text from URLs, parse HTML content, download web pages, or analyze website content. Handles HTTP requests, HTML parsing, CSS selector targeting, and clean text extraction.
---

This skill enables fetching and parsing web content with production-grade error handling. It handles the full pipeline from HTTP request to clean text output, with support for CSS selectors to target specific elements.

The user provides a URL or HTML content to process. They may want the raw HTML, extracted text, or content from specific elements on the page.

## Approach

Before invoking tools, understand what the user needs:
- **Raw HTML**: Use `fetch_page` alone when they need the full page source
- **Clean Text**: Chain `fetch_page` with `extract_text` for readable content
- **Specific Elements**: Use `--selector` to target navigation, articles, headers, or any CSS-selectable content
- **Batch Processing**: For multiple URLs, invoke `fetch_page` sequentially and aggregate results

## Tools

### fetch_page

Fetches raw HTML content from any URL. Includes proper User-Agent headers to avoid bot detection.

```bash
python tools/fetch_page.py --url <url> [--timeout <seconds>]
```

**Arguments:**
- `--url` (required): The complete URL including http:// or https://
- `--timeout` (optional): Request timeout in seconds (default: 30)

**Output:** Raw HTML to stdout. Errors to stderr with appropriate exit codes.

**When to use:**
- User wants to see the page source
- First step before text extraction
- Checking if a URL is accessible
- Downloading page content for later analysis

---

### extract_text

Parses HTML and extracts clean, readable text. Automatically removes scripts, styles, navigation, headers, and footers for cleaner output.

```bash
python tools/extract_text.py [--html <html_string>] [--selector <css_selector>]
```

**Arguments:**
- `--html` (optional): HTML string to parse. If omitted, reads from stdin (for piping)
- `--selector` (optional): CSS selector to target specific elements (e.g., `.article`, `#main`, `h1, h2, h3`)

**Output:** Clean text with normalized whitespace.

**When to use:**
- User wants readable text, not HTML
- Extracting article content from news sites
- Getting text from specific page sections
- Processing HTML that was previously fetched or provided

## Common Patterns

### Full Page Text Extraction
```bash
python tools/fetch_page.py --url https://example.com | python tools/extract_text.py
```

### Extract Only Main Content
```bash
python tools/fetch_page.py --url https://blog.example.com/post | python tools/extract_text.py --selector "article, .post-content, main"
```

### Extract Headlines
```bash
python tools/fetch_page.py --url https://news.site.com | python tools/extract_text.py --selector "h1, h2, h3"
```

### Check Page Accessibility
```bash
python tools/fetch_page.py --url https://example.com --timeout 10
```

## Best Practices

1. **Always handle errors gracefully** - Network requests can fail. Check exit codes and stderr.
2. **Use specific selectors when possible** - `.article-body` gives cleaner results than extracting everything.
3. **Respect rate limits** - Add delays between requests when processing multiple URLs.
4. **Verify URLs** - Ensure URLs include the protocol (http:// or https://).
5. **Consider timeouts** - Long timeouts for slow servers, short for quick checks.

## Error Handling

| Exit Code | Meaning | Recovery |
|-----------|---------|----------|
| 0 | Success | - |
| 1 | Network error, invalid URL, or HTTP error | Check URL format, verify site is accessible |
| 2 | HTML parsing error | Verify HTML is valid, check selector syntax |
| 3 | Invalid CSS selector | Fix selector syntax |

## Dependencies

Requires `requests>=2.28.0` and `beautifulsoup4>=4.11.0`. These are automatically installed with the skill.
