from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User
from app.parser import extract_product_info
from app.scraper.scraper import scrape_sites
from app.ml.analyser import analyse_reviews
from app.ml.recommender import generate_recommendation
import bcrypt

auth = Blueprint('auth', __name__)

@auth.route('/')
def home():
    return redirect(url_for('auth.login'))

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        user = User(username=username, email=email, password=hashed.decode('utf-8'))
        db.session.add(user)
        db.session.commit()
        flash('Account created! Please login.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('register.html')

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
            login_user(user)
            return redirect(url_for('auth.dashboard'))
        flash('Invalid email or password.', 'danger')
    return render_template('login.html')

@auth.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@auth.route('/input', methods=['GET', 'POST'])
@login_required
def input_page():
    if request.method == 'POST':
        url = request.form['url']
        if not url.startswith('http'):
            flash('Please enter a valid URL starting with http', 'danger')
            return render_template('input.html')

        if 'amzn.in' in url or 'amzn.to' in url or 'fkrt.it' in url:
            flash('Short URLs like amzn.in are not supported. Please copy the full URL from your browser address bar.', 'danger')
            return render_template('input.html')

        product_info = extract_product_info(url)
        if product_info['site'] == 'unknown':
            flash('URL not recognised. Please use full Amazon or Flipkart product URLs.', 'danger')
            return render_template('input.html')

        session['product_name'] = product_info['clean_name']
        return redirect(url_for('auth.scrape_mode'))
    return render_template('input.html')

@auth.route('/scrape-mode', methods=['GET', 'POST'])
@login_required
def scrape_mode():
    product_name = session.get('product_name', '')
    if request.method == 'POST':
        mode = request.form['mode']
        specific_site = request.form.get('specific_site')
        selected_sites = request.form.getlist('sites')
        review_limit = int(request.form.get('review_limit', 50))

        # Scrape data
        scraped_results = scrape_sites(
            product_name, mode, specific_site, selected_sites, review_limit
        )

        # Update product name from real Amazon title
        for r in scraped_results:
            if r.get('site') == 'Amazon' and r.get('available'):
                real_title = r.get('real_title')
                if real_title and len(real_title) > 3:
                    product_name = real_title
                    session['product_name'] = product_name
                break

        # Run ML Analysis
        analysed_results = analyse_reviews(scraped_results)

        # Generate Recommendation
        recommendation = generate_recommendation(analysed_results)

        # Store in session
        session_data = []
        for r in analysed_results:
            reviews_list = r.get('reviews', [])
            session_data.append({
                'site': r.get('site'),
                'price': r.get('price'),
                'rating': r.get('rating'),
                'available': r.get('available', True),
                'reason': r.get('reason', ''),
                'sentiment_score': r.get('sentiment_score', 50),
                'overall_sentiment': r.get('overall_sentiment', 'Neutral'),
                'fake_count': r.get('fake_count', 0),
                'reviews_count': r.get('reviews_count', len(reviews_list)),
                'pros': r.get('pros', [])[:3],
                'cons': r.get('cons', [])[:3],
                'reviews': reviews_list[:3]
            })

        session['analysed_results'] = session_data
        session['recommendation'] = recommendation
        session['product_name'] = product_name
        return redirect(url_for('auth.analysis_results'))

    return render_template('scrape_mode.html', product_name=product_name)

@auth.route('/analysis-results')
@login_required
def analysis_results():
    analysed_results = session.get('analysed_results', [])
    product_name = session.get('product_name', '')
    recommendation = session.get('recommendation', {})
    return render_template('analysis_results.html',
                          results=analysed_results,
                          product_name=product_name,
                          recommendation=recommendation)

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))