import re
import requests
from urllib.parse import urlparse, parse_qs

def expand_url(url):
    try:
        response = requests.get(url, allow_redirects=True, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        return response.url
    except:
        return url

def extract_product_info(url):
    # Expand short URLs
    if any(x in url for x in ['amzn.in', 'amzn.to', 'fkrt.it']):
        url = expand_url(url)

    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    path = parsed.path
    query = parse_qs(parsed.query)

    product_info = {
        'url': url,
        'site': None,
        'product_name': None,
        'clean_name': None
    }

    # ── AMAZON ──────────────────────────────────────────
    if 'amazon' in domain:
        product_info['site'] = 'amazon'

        # Direct product URL: /product-name/dp/ASIN
        match = re.search(r'/([a-zA-Z0-9\-]+)/dp/', url)
        if match:
            name = match.group(1).replace('-', ' ')
            product_info['product_name'] = name
            product_info['clean_name'] = clean_product_name(name)

        # Search URL: /s?k=product+name
        elif query.get('k') or query.get('field-keywords'):
            search_query = query.get('k', query.get('field-keywords', ['']))[0]
            if search_query:
                name = search_query.replace('+', ' ')
                product_info['product_name'] = name
                product_info['clean_name'] = clean_product_name(name)

        # Fallback - extract from path
        else:
            parts = [p for p in path.split('/') if p and len(p) > 3]
            if parts:
                name = parts[0].replace('-', ' ')
                product_info['product_name'] = name
                product_info['clean_name'] = clean_product_name(name)

    # ── FLIPKART ─────────────────────────────────────────
    elif 'flipkart' in domain:
        product_info['site'] = 'flipkart'

        # Search URL: /search?q=product+name
        if query.get('q'):
            search_query = query.get('q', [''])[0]
            if search_query:
                name = search_query.replace('+', ' ')
                product_info['product_name'] = name
                product_info['clean_name'] = clean_product_name(name)

        # Direct product URL: /product-name/p/itemid
        else:
            parts = [p for p in path.split('/') if p and p != 'p']
            if parts:
                name = parts[0].replace('-', ' ')
                product_info['product_name'] = name
                product_info['clean_name'] = clean_product_name(name)

    # ── MEESHO ───────────────────────────────────────────
    elif 'meesho' in domain:
        product_info['site'] = 'meesho'
        parts = [p for p in path.split('/') if p]
        if parts:
            name = parts[0].replace('-', ' ')
            product_info['product_name'] = name
            product_info['clean_name'] = clean_product_name(name)

    # ── SNAPDEAL ─────────────────────────────────────────
    elif 'snapdeal' in domain:
        product_info['site'] = 'snapdeal'
        parts = [p for p in path.split('/') if p]
        if len(parts) > 1:
            name = parts[1].replace('-', ' ')
            product_info['product_name'] = name
            product_info['clean_name'] = clean_product_name(name)

    else:
        product_info['site'] = 'unknown'

    # Safety check - if no product name found set default
    if not product_info['product_name'] or len(product_info['product_name'].strip()) < 2:
        product_info['product_name'] = 'product'
        product_info['clean_name'] = 'product'
        product_info['site'] = 'unknown'

    return product_info


def clean_product_name(name):
    if not name:
        return 'product'
    stop_words = ['buy', 'online', 'price', 'india', 'best', 'with',
                  'shop', 'store', 'sale', 'offer', 'deal', 'new']
    words = name.lower().split()
    clean = [w for w in words if w not in stop_words and len(w) > 1]
    result = ' '.join(clean[:6])
    return result if result else 'product'