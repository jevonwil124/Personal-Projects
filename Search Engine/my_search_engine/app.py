from flask import Flask, request, render_template_string, url_for
import os
import sys
import json
import re
import random # <--- NEW: Import the random module

# Add the parent directory to the Python path to allow importing searcher.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from searcher import SearchEngine

app = Flask(__name__)

# Initialize the search engine
search_engine_instance = SearchEngine()

# --- NEW: Define LOCAL background images in Python ---
# Make sure these filenames exist in your 'static' folder!
LOCAL_BACKGROUND_IMAGES = [
    "istockphoto-1455772765-640x640.jpg",
    "tumblr_static_tumblr_static__focused_v3.gif",
    "4ede5a33c5490195b2b17466ad26d124.gif",
    "source.gif"  # Make sure you have this image in your static folder
    # Add more local images here if you have them, e.g.:
    # "another_background.png",
    # "third_image.jpeg",
]

# HTML template for the search interface and results
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mini Search Engine</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">
    <style>
        /* Global styles */
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Inter', sans-serif;
        }

        body {
            margin: 0;
            background-color: #1a1a2e; /* Darker base color */
            color: #fff;
            transition: background-image 1s ease-in-out; /* Smooth transition for background */
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            display: flex; /* Use flexbox for body to center content */
            justify-content: center; /* Center horizontally */
            align-items: center; /* Center vertically */
            min-height: 100vh; /* Full viewport height */
            /* --- KEY CHANGE: background image set directly by Flask via background_url --- */
            background-image: url('{{ background_url }}');
        }

        .container {
            width: 100%;
            max-width: 800px; /* Increased max-width for content */
            padding: 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 20px; /* Reduced gap as elements are less distinct */
        }

        .search-bar {
            width: 100%;
            max-width: 600px; /* Max width for the search bar */
            background: rgba(255, 255, 255, 0.1); /* More subtle background */
            display: flex;
            align-items: center;
            border-radius: 60px;
            padding: 8px 18px; /* Slightly smaller padding */
            backdrop-filter: blur(8px) saturate(180%); /* Stronger blur for glass effect */
            -webkit-backdrop-filter: blur(8px) saturate(180%); /* For Safari */
            border: 1px solid rgba(255, 255, 255, 0.15); /* Subtle border */
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2); /* Softer shadow */
        }

        .search-bar input {
            background: transparent;
            flex: 1;
            border: 0;
            outline: none;
            padding: 18px 15px; /* Adjusted padding */
            font-size: 18px;
            color: #e0e0e0; /* Lighter text color */
        }

        .search-bar input::placeholder {
            color: #b0b0b0; /* Lighter placeholder */
        }

        .search-bar button {
            border: 0;
            border-radius: 50%;
            width: 50px; /* Smaller button */
            height: 50px; /* Smaller button */
            background: #6a05ad; /* Purple shade */
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: background 0.3s ease;
        }

        .search-bar button:hover {
            background: #8e2de2; /* Lighter purple on hover */
        }

        .search-bar button svg {
            width: 22px;
            height: 22px;
            fill: #fff;
        }

        .filter-nav {
            width: 100%;
            max-width: 600px; /* Match search bar width */
            display: flex;
            justify-content: center;
            gap: 20px;
            margin-bottom: 20px;
        }

        .filter-nav a {
            color: #cac7ff;
            text-decoration: none;
            padding: 8px 15px;
            border-radius: 20px;
            transition: background 0.3s ease, color 0.3s ease;
            font-weight: 600;
        }

        .filter-nav a:hover {
            background: rgba(255, 255, 255, 0.15);
        }

        .filter-nav a.active {
            background: #a0c4ff;
            color: #1a1a2e; /* Darker text for active tab */
        }

        .results-container {
            width: 100%;
            max-width: 700px;
            background: rgba(255, 255, 255, 0.05); /* Very subtle background */
            border-radius: 15px; /* Slightly smaller radius */
            padding: 25px; /* Adjusted padding */
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
            backdrop-filter: blur(6px) saturate(150%);
            -webkit-backdrop-filter: blur(6px) saturate(150%);
            max-height: 65vh; /* Allow more height for scrollability */
            overflow-y: auto;
            border: 1px solid rgba(255, 255, 255, 0.08); /* Subtle border */
        }

        .results-container h2 {
            color: #a0c4ff;
            margin-bottom: 15px;
            text-align: center;
            font-size: 1.8em;
        }

        .results-list {
            list-style: none;
            padding: 0;
        }

        .results-list li {
            background: rgba(255, 255, 255, 0.03); /* Even more subtle item background */
            border-radius: 8px;
            padding: 12px 18px;
            margin-bottom: 12px;
            border: 1px solid rgba(255, 255, 255, 0.05); /* Very light border */
            transition: background 0.2s ease;
        }

        .results-list li:hover {
            background: rgba(255, 255, 255, 0.06);
        }

        .results-list li a {
            color: #a0c4ff;
            text-decoration: none;
            font-size: 1.05em;
            word-wrap: break-word;
        }

        .results-list li a:hover {
            text-decoration: underline;
        }

        .results-list li strong {
            color: #a0c4ff;
            font-size: 1.05em;
        }

        .results-list li p {
            font-size: 0.85em;
            color: #c0c0c0;
            margin-top: 4px;
        }

        .no-results {
            text-align: center;
            color: #e0e0e0;
            font-style: italic;
            padding: 20px;
        }

        /* Styles for images and videos */
        .media-container {
            display: flex;
            flex-wrap: wrap;
            gap: 8px; /* Slightly smaller gap */
            margin-top: 10px;
            justify-content: center;
        }

        .media-container img {
            max-width: 100%;
            height: auto;
            max-height: 120px; /* Slightly smaller max height for images */
            border-radius: 4px;
            object-fit: contain;
            background-color: rgba(0, 0, 0, 0.1); /* More subtle media background */
            box-shadow: 0 2px 8px rgba(0,0,0,0.1); /* Subtle shadow */
        }

        .media-container video {
            max-width: 100%;
            height: auto;
            max-height: 180px; /* Slightly smaller max height for videos */
            border-radius: 4px;
            object-fit: contain;
            background-color: rgba(0, 0, 0, 0.1);
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        .media-container iframe {
            max-width: 100%;
            width: 300px; /* Adjusted width for embeds */
            height: 170px; /* Adjusted height for embeds */
            border-radius: 4px;
            border: none;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

    </style>
</head>
<body>
    <div class="container">
        <form action="{{ url_for('search_results') }}" method="get" class="search-bar">
            <input type="text" placeholder="Search anything" name="query" value="{{ query if query }}">
            <button type="submit">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-search">
                    <circle cx="11" cy="11" r="8"/>
                    <path d="m21 21-4.3-4.3"/>
                </svg>
            </button>
        </form>

        {% if results is not none %}
        <div class="filter-nav">
            <a href="{{ url_for('search_results', query=query, filter='all', bg=background_url) }}" class="{{ 'active' if current_filter == 'all' }}">All</a>
            <a href="{{ url_for('search_results', query=query, filter='images', bg=background_url) }}" class="{{ 'active' if current_filter == 'images' }}">Images</a>
            <a href="{{ url_for('search_results', query=query, filter='videos', bg=background_url) }}" class="{{ 'active' if current_filter == 'videos' }}">Videos</a>
        </div>

        <div class="results-container">
            <h2>Search Results for "{{ query }}"</h2>
            {% if results %}
            <ul class="results-list">
                {% for score, doc_info in results %}
                {% set show_item = false %}
                {% if current_filter == 'all' %}
                    {% set show_item = true %}
                {% elif current_filter == 'images' and doc_info.images %}
                    {% set show_item = true %}
                {% elif current_filter == 'videos' and doc_info.videos %}
                    {% set show_item = true %}
                {% endif %}

                {% if show_item %}
                <li>
                    <strong>{{ loop.index }}. <a href="{{ doc_info.url }}" target="_blank" rel="noopener noreferrer">{{ doc_info.url }}</a></strong>
                    <p>Relevance Score: {{ '%.2f' | format(score) }}</p>

                    {% if (current_filter == 'all' or current_filter == 'images') and doc_info.images %}
                        <div class="media-container">
                        {% for image in doc_info.images %}
                            <img src="{{ image.src }}" alt="{{ image.alt }}" loading="lazy">
                        {% endfor %}
                        </div>
                    {% endif %}

                    {% if (current_filter == 'all' or current_filter == 'videos') and doc_info.videos %}
                        <div class="media-container">
                        {% for video in doc_info.videos %}
                            {% if video.type == 'direct' %}
                                <video controls preload="none">
                                    <source src="{{ video.src }}" type="video/mp4">
                                    Your browser does not support the video tag.
                                </video>
                            {% elif video.type == 'embed' %}
                                <iframe src="{{ video.src }}" frameborder="0" allowfullscreen></iframe>
                            {% endif %}
                        {% endfor %}
                        </div>
                    {% endif %}
                </li>
                {% endif %}
                {% endfor %}
            </ul>
            {% else %}
            <p class="no-results">No results found for your query.</p>
            {% endif %}
        </div>
        {% endif %}
    </div>

    </body>
</html>
"""

@app.route('/')
def home():
    """Renders the initial search page."""
    # Select a random background image URL from your LOCAL_BACKGROUND_IMAGES
    selected_bg_filename = random.choice(LOCAL_BACKGROUND_IMAGES)
    background_url = url_for('static', filename=selected_bg_filename)

    return render_template_string(HTML_TEMPLATE, results=None, query="", current_filter="all", background_url=background_url)

@app.route('/search')
def search_results():
    """Handles search queries and displays results with media, filtered by type."""
    user_query = request.args.get('query', '').strip()
    current_filter = request.args.get('filter', 'all')

    # --- KEY CHANGE: Get the background URL from the request arguments if present ---
    # This keeps the background image consistent across filters/searches
    background_url = request.args.get('bg')

    # If no background URL is in the arguments (e.g., initial search or direct /search access)
    # or if it's somehow not a valid static URL, pick a new random one
    if not background_url or not background_url.startswith('/static/'):
        selected_bg_filename = random.choice(LOCAL_BACKGROUND_IMAGES)
        background_url = url_for('static', filename=selected_bg_filename)

    results_to_display = []

    if user_query:
        raw_results = search_engine_instance.search(user_query)

        for score, doc_id in raw_results:
            doc_info = search_engine_instance.document_map.get(str(doc_id))

            if doc_info:
                try:
                    score_float = float(score)
                except ValueError:
                    score_float = 0.0
                results_to_display.append((score_float, doc_info))
            else:
                results_to_display.append((0.0, {'url': f"Unknown Document (ID: {doc_id})", 'images': [], 'videos': []}))
    else:
        results_to_display = []

    # Pass the determined background_url to the template
    return render_template_string(HTML_TEMPLATE, results=results_to_display, query=user_query, current_filter=current_filter, background_url=background_url)

if __name__ == '__main__':
    app.run(debug=True)