from textblob import TextBlob
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np
import re
import nltk

# Download required NLTK data
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

    # Convert polarity (-1 to 1) to score (0 to 100)
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

    for i, result in enumerate(sentiment_results):
        if i >= len(reviews):
            break

        review = str(reviews[i])
        sentences = re.split(r'[.!?]', review)

        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:
                continue

            blob = TextBlob(sentence)
            polarity = blob.sentiment.polarity

            if polarity > 0.2 and len(pros) < 5:
                pros.append(sentence)
            elif polarity < -0.1 and len(cons) < 5:
                cons.append(sentence)

    if not pros:
        pros = ['Good product overall', 'Reasonable quality for the price']
    if not cons:
        cons = ['No major issues reported by customers']

    return pros, cons


def analyse_reviews(scraped_results):
    analysed = []

    for site_data in scraped_results:
        # Skip unavailable sites
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

        # Run Sentiment Analysis
        sentiment_data = analyse_sentiment(reviews)

        # Run Fake Review Detection
        fake_flags = detect_fake_reviews(reviews)
        fake_count = sum(fake_flags)

        # Extract Pros and Cons
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