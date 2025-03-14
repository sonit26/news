import re
import random
import logging
import requests
import urllib.parse
from flask import Flask, request, jsonify
from textblob import TextBlob
import dateparser
from datetime import datetime

API_KEY = "76cfa8fbd70d94bc4d81d7922c785b03"
BASE_URL = "https://api.themoviedb.org/3"
SLACK_VERIFICATION_TOKEN = "6gm7fou9ko96frmC03BGyNDv"
JUSTWATCH_BASE_URL = "https://www.justwatch.com/in/movie/"


app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

GENRE_MAP = {
    "Action": 28, "Comedy": 35, "Drama": 18,
    "Sci-Fi": 878, "Horror": 27, "Romance": 10749,
    "Thriller": 53, "Animation": 16, "Fantasy": 14
}

OCCASIONS = {
    "Date Night": ["Romance", "Drama"],
    "Family Time": ["Comedy", "Animation"],
    "Solo Watch": ["Thriller", "Sci-Fi"],
    "Horror Night": ["Horror", "Thriller"]
}

USER_SESSIONS = {}

# Use TextBlob for NLP
def extract_preferences(text):
    blob = TextBlob(text)

    # Extract possible genres from the text
    genres = [g for g in GENRE_MAP.keys() if g.lower() in text.lower()]

    # Extract occasion
    occasion = None
    for occ in OCCASIONS:
        if occ.lower() in text.lower():
            occasion = occ
            break

    # Try to parse the year or decade with dateparser
    detected_dates = []

    # Check for decade-based keywords like "2000s", "90s", etc.
    if "2000s" in text:
        detected_dates.append("2000-2009")
    elif "90s" in text:
        detected_dates.append("1990-1999")
    elif "80s" in text:
        detected_dates.append("1980-1989")
    else:
        parsed_date = dateparser.parse(text)
        if parsed_date:
            detected_dates.append(str(parsed_date.year))
        
        # Explicitly capture any specific year mentioned in the text (1940 onwards)
        year_match = re.search(r"\b(19[4-9]\d|20\d{2})\b", text)  # Captures years like 1940, 2024, etc.
        if year_match:
            detected_dates.append(year_match.group(1))

    # Set the year range if detected
    if detected_dates:
        year_range = detected_dates[0]  # Use the first detected range or year
    else:
        year_range = None

    logging.debug(f"Detected preferences: genres: {genres}, occasion: {occasion}, year_range: {year_range}")
    
    return {
        "occasion": occasion,
        "genres": genres,
        "year_range": year_range
    }

def get_movies_by_genres_and_date(genres, year_filter):
    logging.debug(f"Fetching movies for genres: {genres} and year filter: {year_filter}")
    genre_ids = [str(GENRE_MAP[g]) for g in genres if g in GENRE_MAP]
    if not genre_ids:
        return None
    
    url = f"{BASE_URL}/discover/movie?api_key={API_KEY}&with_genres={','.join(genre_ids)}"
    
    if year_filter and "-" in year_filter:
        start_year, end_year = year_filter.split("-")
        url += f"&primary_release_date.gte={start_year}-01-01&primary_release_date.lte={end_year}-12-31"
    elif year_filter:
        url += f"&primary_release_year={year_filter}"
    
    logging.debug(f"Fetching movies from URL: {url}")
    response = requests.get(url)
    
    if response.status_code == 200:
        movies = response.json().get("results", [])
        logging.debug(f"Movies fetched: {movies}")
        return [f"{movie['title']} ({movie['release_date'][:4]})" for movie in movies if 'release_date' in movie and movie['release_date']]

    else:
        logging.error(f"Failed to fetch movies, status code: {response.status_code}")
        return None

def recommend_movie(user_id, text):
    preferences = extract_preferences(text)
    logging.debug(f"Extracted preferences: {preferences}")
    
    occasion = preferences.get("occasion")
    genres = preferences.get("genres", [])
    year_filter = preferences.get("year_range")
    
    # Use occasion-based genres if no genres were provided explicitly
    suggested_genres = OCCASIONS.get(occasion, []) or genres
    logging.debug(f"Final genre selection: {suggested_genres}")
    
    movies = get_movies_by_genres_and_date(suggested_genres, year_filter)
    
    if movies:
        movie_choice = random.choice(movies)  # Already a formatted string like "Movie Title (2024)"
        
        # Extract title and year from the formatted string
        match = re.match(r"(.+?) \((\d{4})\)", movie_choice)
        if match:
            movie_title, movie_year = match.groups()
        else:
            movie_title, movie_year = movie_choice, ""

        # Clean up title for JustWatch link
        title_cleaned = re.sub(r"[:']", "", movie_title)  # Remove colons and apostrophes
        title_cleaned = title_cleaned.lower().replace(" ", "-")  # Convert spaces to hyphens

        # Generate the JustWatch link
        justwatch_link = f"{JUSTWATCH_BASE_URL}{title_cleaned}"

        return f"<{justwatch_link}|{movie_title} ({movie_year})>"
    else:
        return "Could not fetch movies. Try again later."

@app.route("/slack/movies", methods=["POST"])
def slack_movie_recommendation():
    data = request.form
    user_id = data.get("user_id")
    text = data.get("text", "").strip()
    logging.debug(f"Received input: {text} from user {user_id}")
    
    if data.get("token") != SLACK_VERIFICATION_TOKEN:
        return jsonify({"text": "Unauthorized request."}), 403
    
    # Store session data
    if user_id not in USER_SESSIONS:
        USER_SESSIONS[user_id] = {}

    # Extract movie preferences and generate recommendation
    recommendation = recommend_movie(user_id, text)
    logging.debug(f"Movie recommendation: {recommendation}")
    
    return jsonify({"response_type": "in_channel", "text": f"You should watch: {recommendation}"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)