import re

def extract_price_value(price_str):
    try:
        # Remove all currency symbols and commas
        cleaned = str(price_str).replace(',', '').replace('₹', '').replace('Rs.', '').replace('Rs', '').replace('$', '').strip()
        numbers = re.findall(r'[\d]+', cleaned)
        if numbers:
            return int(numbers[0])
    except:
        pass
    return 0


def get_recommendation_score(site_data):
    scores = {}

    # Sentiment Score (40%)
    sentiment_score = float(site_data.get('sentiment_score', 50))
    sentiment_score = max(0, min(100, sentiment_score))
    scores['sentiment'] = sentiment_score * 0.4

    # Fake Review Score (20%)
    fake_count = int(site_data.get('fake_count', 0))
    reviews_count = int(site_data.get('reviews_count', 0))
    if reviews_count > 0:
        fake_ratio = min(1.0, max(0, fake_count / reviews_count))
    else:
        fake_ratio = 0
    authenticity_score = max(0, (1 - fake_ratio) * 100)
    scores['authenticity'] = authenticity_score * 0.2

    # Price raw value
    scores['price_raw'] = extract_price_value(site_data.get('price', '0'))

    return scores


def calculate_price_scores(all_scores):
    prices = [(site, s['price_raw']) for site, s in all_scores.items()
              if s['price_raw'] > 0]

    if not prices:
        for site in all_scores:
            all_scores[site]['price'] = 50 * 0.4
        return all_scores

    if len(prices) == 1:
        site = prices[0][0]
        for s in all_scores:
            if s == site:
                all_scores[s]['price'] = 100 * 0.4
            else:
                all_scores[s]['price'] = 50 * 0.4
        return all_scores

    min_price = min(p for _, p in prices)
    max_price = max(p for _, p in prices)
    price_range = max_price - min_price

    for site, score in all_scores.items():
        price = score['price_raw']
        if price == 0:
            all_scores[site]['price'] = 50 * 0.4
        elif price_range == 0:
            all_scores[site]['price'] = 100 * 0.4
        else:
            price_score = ((max_price - price) / price_range) * 100
            price_score = max(0, min(100, price_score))
            all_scores[site]['price'] = price_score * 0.4

    return all_scores


def get_verdict(total_score):
    if total_score >= 65:
        return {
            'verdict': 'Buy',
            'emoji': '✅',
            'color': '#2e7d32',
            'message': 'Great choice! This product has good reviews, fair price and trustworthy ratings.'
        }
    elif total_score >= 45:
        return {
            'verdict': 'Consider',
            'emoji': '🤔',
            'color': '#f57c00',
            'message': 'This product is decent but check the cons before buying. Compare with alternatives.'
        }
    else:
        return {
            'verdict': 'Avoid',
            'emoji': '❌',
            'color': '#c62828',
            'message': 'This product has poor reviews or suspicious activity. We recommend looking at alternatives.'
        }


def get_best_site(site_totals):
    if not site_totals:
        return None
    return max(site_totals, key=site_totals.get)


def generate_recommendation(analysed_results):
    available_sites = [r for r in analysed_results if r.get('available', True)]

    if not available_sites:
        return {
            'verdict': 'No Data',
            'emoji': '❓',
            'color': '#888',
            'message': 'No data available to make a recommendation.',
            'best_site': None,
            'site_scores': {},
            'site_breakdown': {},
            'overall_score': 0
        }

    all_scores = {}
    for site_data in available_sites:
        site = site_data.get('site', 'Unknown')
        all_scores[site] = get_recommendation_score(site_data)

    all_scores = calculate_price_scores(all_scores)

    site_totals = {}
    site_breakdown = {}
    for site, scores in all_scores.items():
        sentiment_c = round(scores['sentiment'], 1)
        auth_c = round(scores['authenticity'], 1)
        price_c = round(scores['price'], 1)
        total = round(sentiment_c + auth_c + price_c, 1)

        site_totals[site] = total
        site_breakdown[site] = {
            'sentiment_contribution': sentiment_c,
            'authenticity_contribution': auth_c,
            'price_contribution': price_c,
            'total': total
        }

    overall_score = round(sum(site_totals.values()) / len(site_totals), 1)
    verdict_data = get_verdict(overall_score)
    best_site = get_best_site(site_totals)

    return {
        **verdict_data,
        'best_site': best_site,
        'site_scores': site_totals,
        'site_breakdown': site_breakdown,
        'overall_score': overall_score
    }