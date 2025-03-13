import requests
import random
from flask import Flask, request, jsonify

API_KEY = "76cfa8fbd70d94bc4d81d7922c785b03"
BASE_URL = "https://api.themoviedb.org/3"
SLACK_VERIFICATION_TOKEN = "your_slack_verification_token"

app = Flask(__name__)

def get_movies_by_genre(genre):
    """Fetches movies from TMDb based on genre."""
    genre_map = {
        "Action": 28, "Comedy": 35, "Drama": 18,
        "Sci-Fi": 878, "Horror": 27
    }
    
    if genre not in genre_map:
        return None
    
    url = f"{BASE_URL}/discover/movie?api_key={API_KEY}&with_genres={genre_map[genre]}"
    response = requests.get(url)
    
    if response.status_code == 200:
        movies = response.json().get("results", [])
        return [movie["title"] for movie in movies]
    else:
        return None

def recommend_movie(genre=None):
    """Recommends a random movie from TMDb based on genre."""
    movies = get_movies_by_genre(genre) if genre else None
    
    if movies:
        return random.choice(movies)
    else:
        return "Could not fetch movies. Try again later."

@app.route("/slack/movies", methods=["POST"])
def slack_movie_recommendation():
    """Handles Slack slash command /movies."""
    data = request.form
    if data.get("token") != SLACK_VERIFICATION_TOKEN:
        return jsonify({"text": "Unauthorized request."}), 403
    
    genre = data.get("text", "").strip()
    recommendation = recommend_movie(genre if genre else None)
    
    return jsonify({"response_type": "in_channel", "text": f"You should watch: {recommendation}"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
