from textblob import TextBlob
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np
import re
import nltk

try:
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
except:
    pass


def clean_text(text):
    if not text:
        return ''
    text = re.sub(r'[^a-zA-Z\s]', '', str(text))
    text = text.lower().strip()
    return text


def analyse_sentiment(reviews):
    if not reviews:
        return {
            'results': [],
            'overall_sentiment': 'Neutral',
            'sentiment_score': 50,
            'avg_polarity': 0
        }

    results = []
    total_polarity = 0

    for review in reviews:
        blob = TextBlob(str(review))
        polarity = blob.sentiment.polarity

        if polarity > 0.1:
            sentiment = 'Positive'
        elif polarity < -0.1:
            sentiment = 'Negative'
        else:
            sentiment = 'Neutral'

        results.append({
            'review': review,
            'sentiment': sentiment,
            'polarity': round(polarity, 2)
        })
        total_polarity += polarity

    avg_polarity = total_polarity / len(reviews) if reviews else 0

    if avg_polarity > 0.1:
        overall = 'Positive'
    elif avg_polarity < -0.1:
        overall = 'Negative'
    else:
        overall = 'Neutral'

    score = round((avg_polarity + 1) / 2 * 100, 1)

    return {
        'results': results,
        'overall_sentiment': overall,
        'sentiment_score': score,
        'avg_polarity': round(avg_polarity, 2)
    }


def detect_fake_reviews(reviews):
    if not reviews or len(reviews) < 2:
        return [False] * len(reviews)

    cleaned = [clean_text(r) for r in reviews]
    cleaned = [c for c in cleaned if c]

    if len(cleaned) < 2:
        return [False] * len(reviews)

    try:
        vectorizer = TfidfVectorizer(max_features=100, stop_words='english')
        tfidf_matrix = vectorizer.fit_transform(cleaned)
        scores = np.array(tfidf_matrix.sum(axis=1)).flatten()

        mean_score = np.mean(scores)
        std_score = np.std(scores)

        fake_flags = []
        for score in scores:
            if std_score == 0:
                fake_flags.append(False)
            else:
                z_score = abs(score - mean_score) / std_score
                fake_flags.append(bool(z_score > 2.0))

        return fake_flags

    except Exception as e:
        print(f"Fake detection error: {e}")
        return [False] * len(reviews)


def extract_pros_cons(reviews, sentiment_results):
    pros = []
    cons = []

    # Strong positive words
    positive_keywords = [
        'excellent', 'amazing', 'great', 'good', 'love', 'best',
        'perfect', 'fantastic', 'awesome', 'superb', 'wonderful',
        'satisfied', 'happy', 'recommend', 'quality', 'fast'
    ]

    # Strong negative words
    negative_keywords = [
        'bad', 'poor', 'terrible', 'worst', 'disappoint', 'issue',
        'problem', 'broke', 'broken', 'slow', 'expensive', 'waste',
        'return', 'refund', 'damage', 'fake', 'stop', 'fail'
    ]

    for i, result in enumerate(sentiment_results):
        if i >= len(reviews):
            break

        review = str(reviews[i])
        sentences = re.split(r'[.!?]', review)

        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 15:
                continue

            sentence_lower = sentence.lower()
            blob = TextBlob(sentence)
            polarity = blob.sentiment.polarity

            # Check for negative keywords — must have negative word AND negative polarity
            has_negative_word = any(word in sentence_lower for word in negative_keywords)
            has_positive_word = any(word in sentence_lower for word in positive_keywords)

            # Pro: positive polarity AND positive keywords
            if polarity > 0.2 and has_positive_word and len(pros) < 5:
                if sentence not in pros:
                    pros.append(sentence)

            # Con: negative polarity AND negative keywords (strict check)
            elif polarity < -0.1 and has_negative_word and not has_positive_word and len(cons) < 5:
                if sentence not in cons:
                    cons.append(sentence)

    if not pros:
        pros = ['Good product overall', 'Reasonable quality for the price']
    if not cons:
        cons = ['No major issues reported by customers']

    return pros, cons


def analyse_reviews(scraped_results):
    analysed = []

    for site_data in scraped_results:
        if not site_data.get('available', True):
            analysed.append({
                **site_data,
                'sentiment_score': 0,
                'overall_sentiment': 'N/A',
                'sentiment_results': [],
                'fake_count': 0,
                'pros': [],
                'cons': []
            })
            continue

        reviews = site_data.get('reviews', [])

        if not reviews:
            analysed.append({
                **site_data,
                'sentiment_score': 50,
                'overall_sentiment': 'Neutral',
                'sentiment_results': [],
                'fake_count': 0,
                'pros': ['No reviews available'],
                'cons': ['No reviews available']
            })
            continue

        sentiment_data = analyse_sentiment(reviews)
        fake_flags = detect_fake_reviews(reviews)
        fake_count = sum(fake_flags)
        pros, cons = extract_pros_cons(reviews, sentiment_data['results'])

        analysed.append({
            **site_data,
            'sentiment_score': sentiment_data['sentiment_score'],
            'overall_sentiment': sentiment_data['overall_sentiment'],
            'sentiment_results': sentiment_data['results'],
            'avg_polarity': sentiment_data['avg_polarity'],
            'fake_count': fake_count,
            'fake_flags': fake_flags,
            'pros': pros,
            'cons': cons
        })

    return analysed