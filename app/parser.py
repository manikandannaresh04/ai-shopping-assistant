import re
import requests
from urllib.parse import urlparse, parse_qs
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

RAPIDAPI_KEY = "aa264be408msheba6d94cf2cca2fp14cf61jsnfddb3e20add6"
RAPIDAPI_HOST = "real-time-amazon-data.p.rapidapi.com"

RAPIDAPI_HEADERS = {
    "x-rapidapi-key": RAPIDAPI_KEY,
    "x-rapidapi-host": RAPIDAPI_HOST
}

def get_title_from_asin(asin):
    try:
        url = "https://real-time-amazon-data.p.rapidapi.com/product-details"
        params = {"asin": asin, "country": "IN"}
        response = requests.get(url, headers=RAPIDAPI_HEADERS, params=params, timeout=10)
        data = response.json()
        if data.get('data') and data['data'].get('product_title'):
            title = data['data']['product_title']
            return clean_product_name(title)
    except:
        pass
    return None

def is_asin(text):
    return bool(re.match(r'^[A-Z0-9]{10}$', text.upper().strip()))

def extract_product_info(url):
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

    # ── REJECT SHORT URLS ────────────────────────────────
    if 'amzn.in' in domain or 'amzn.to' in domain or 'fkrt.it' in domain:
        product_info['site'] = 'unknown'
        product_info['product_name'] = None
        product_info['clean_name'] = None
        return product_info

    # ── AMAZON ──────────────────────────────────────────
    elif 'amazon' in domain:
        product_info['site'] = 'amazon'

        asin_match = re.search(r'/dp/([A-Z0-9]{10})', url)
        asin = asin_match.group(1) if asin_match else None

        name_match = re.search(r'/([a-zA-Z0-9\-]+)/dp/', url)
        name_part = name_match.group(1) if name_match else ''

        if name_part and not is_asin(name_part) and len(name_part) > 5 and '-' in name_part:
            name = name_part.replace('-', ' ')
            product_info['product_name'] = name
            product_info['clean_name'] = clean_product_name(name)
        elif asin:
            real_title = get_title_from_asin(asin)
            if real_title:
                product_info['product_name'] = real_title
                product_info['clean_name'] = real_title
            else:
                product_info['product_name'] = asin
                product_info['clean_name'] = asin
        elif query.get('k') or query.get('field-keywords'):
            search_query = query.get('k', query.get('field-keywords', ['']))[0]
            if search_query:
                name = search_query.replace('+', ' ')
                product_info['product_name'] = name
                product_info['clean_name'] = clean_product_name(name)
        else:
            parts = [p for p in path.split('/') if p and len(p) > 3]
            if parts:
                name = parts[0].replace('-', ' ')
                product_info['product_name'] = name
                product_info['clean_name'] = clean_product_name(name)

    # ── FLIPKART ─────────────────────────────────────────
    elif 'flipkart' in domain:
        product_info['site'] = 'flipkart'

        if query.get('q'):
            search_query = query.get('q', [''])[0]
            if search_query:
                name = search_query.replace('+', ' ')
                product_info['product_name'] = name
                product_info['clean_name'] = clean_product_name(name)
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

    # Safety check
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