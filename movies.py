import requests
import random
from flask import Flask, request, jsonify

API_KEY = "76cfa8fbd70d94bc4d81d7922c785b03"
BASE_URL = "https://api.themoviedb.org/3"
SLACK_VERIFICATION_TOKEN = "lLED5gubUYQnRnGvTea2cqBt"

app = Flask(__name__)

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

def get_movies_by_genres_and_date(genres, year_filter):
    """Fetches movies from TMDb based on genres and release year."""
    genre_ids = [str(GENRE_MAP[g]) for g in genres if g in GENRE_MAP]
    if not genre_ids:
        return None
    
    url = f"{BASE_URL}/discover/movie?api_key={API_KEY}&with_genres={','.join(genre_ids)}"
    
    if year_filter == "recent":
        url += "&primary_release_year=2023"
    elif year_filter == "last 10 years":
        url += "&primary_release_date.gte=2013-01-01"
    elif year_filter.isdigit():
        url += f"&primary_release_year={year_filter}"
    
    response = requests.get(url)
    
    if response.status_code == 200:
        movies = response.json().get("results", [])
        return [movie["title"] for movie in movies]
    else:
        return None

def recommend_movie(user_id):
    """Recommends a random movie based on stored user selections."""
    user_data = USER_SESSIONS.get(user_id, {})
    occasion = user_data.get("occasion")
    genres = user_data.get("genres", [])
    year_filter = user_data.get("year")
    
    suggested_genres = OCCASIONS.get(occasion, genres)
    movies = get_movies_by_genres_and_date(suggested_genres, year_filter)
    
    if movies:
        return random.choice(movies)
    else:
        return "Could not fetch movies. Try again later."

@app.route("/slack/movies", methods=["POST"])
def slack_movie_recommendation():
    """Handles Slack slash command /movies in a step-by-step conversational way."""
    data = request.form
    user_id = data.get("user_id")
    text = data.get("text", "").strip()
    
    if data.get("token") != SLACK_VERIFICATION_TOKEN:
        return jsonify({"text": "Unauthorized request."}), 403
    
    if user_id not in USER_SESSIONS:
        USER_SESSIONS[user_id] = {}
    
    user_data = USER_SESSIONS[user_id]
    
    if "occasion" not in user_data:
        user_data["occasion"] = text if text in OCCASIONS else None
        return jsonify({
            "response_type": "ephemeral",
            "text": f"Great! Now, choose your preferred genres (comma-separated): {', '.join(GENRE_MAP.keys())}"
        })
    
    if "genres" not in user_data:
        selected_genres = [g.strip() for g in text.split(",") if g.strip() in GENRE_MAP]
        if selected_genres:
            user_data["genres"] = selected_genres
            return jsonify({
                "response_type": "ephemeral",
                "text": "Now, are you looking to watch a modern flick, or something older: recent, last 10 years, or a specific year (e.g., 2015)."
            })
        else:
            return jsonify({
                "response_type": "ephemeral",
                "text": f"Invalid genres. Choose from: {', '.join(GENRE_MAP.keys())}"
            })
    
    if "year" not in user_data:
        user_data["year"] = text
        recommendation = recommend_movie(user_id)
        USER_SESSIONS.pop(user_id, None)  # Clear session after completion
        return jsonify({"response_type": "in_channel", "text": f"You should watch: {recommendation}"})
    
    return jsonify({"response_type": "ephemeral", "text": "Something went wrong. Please start over with /movies."})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)