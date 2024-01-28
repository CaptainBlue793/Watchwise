"""MOVIES RECOMMENDATION SYSTEM"""

import base64
import pickle

# Importing Libraries
import pandas as pd
import requests
import streamlit as st


# Integrating Streamlit app with our ML File (ipynb)
def poster(movie_ID):
    response = requests.get(
        "https://api.themoviedb.org/3/movie/{}?api_key=e49ee15fc4cf141aff585cab7b7998d9".format(
            movie_ID
        )
    )
    data = response.json()
    return "https://image.tmdb.org/t/p/w500/" + data["poster_path"]


def recommend(movie):
    movie_index = Movies[Movies["title"] == movie].index[0]
    distances = similarity[movie_index]
    movies_list = sorted(list(enumerate(distances)), reverse=True, key=lambda x: x[1])[
        1:13
    ]
    recommended_movies = []
    posters = []
    for i in movies_list:
        movie_ID = Movies.iloc[i[0]].movie_id
        # Fetch Poster from API
        posters.append(poster(movie_ID))
        # Fetch Movie Title
        recommended_movies.append(Movies.iloc[i[0]].title)
    return recommended_movies, posters


Movies_List = pickle.load(open("movies_list.pkl", "rb"))
Movies = pd.DataFrame(Movies_List)
similarity = pickle.load(open("similarity.pkl", "rb"))

# Streamlit Code
st.set_page_config(layout="wide")


# Display Background
def add_bg_from_local(image_file):
    with open(image_file, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read())
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url(data:image/{"png"};base64,{encoded_string.decode()});
            background-size: cover;
            opacity:0.9;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


add_bg_from_local("1234.jpg")

# Font Style
with open("font.css") as f:
    st.markdown("<style>{}</style>".format(f.read()), unsafe_allow_html=True)

# Main content
st.markdown(
    """
    <style>
    .watchwise-title {
        font-size:60px;
        color: #84b7ff;
        text-align: center;
        transition: transform 0.2s ease-in-out;
    }
    .watchwise-title:hover {
        transform: scale(1.15);
    }
    </style>
    """,
    unsafe_allow_html=True,
)
st.markdown('<h1 class="watchwise-title">WATCHWISE</h1>', unsafe_allow_html=True)
st.markdown(
    '<h2 style="color: #F5FEFD; text-align: center;">Movies Recommendation System</h2>',
    unsafe_allow_html=True,
)

choice = st.selectbox("SEARCH FOR YOUR MOVIE", Movies["title"].values)

if st.button("Recommend"):
    names, posters = recommend(choice)

    # CSS styling for columns
    st.markdown(
        """
        <style>
        .column-content {
        padding: 10px;
        text-align: center;
        background-color: #1F2143;
        color: ##F5FEFD;
        border-radius: 10px;
        box-shadow: 0 0 10px rgba(0, 0, 0, 0.3);
        margin-bottom: 20px;
        transition: transform 0.3s ease-in-out;
    }
    .column-content:hover {
        transform: scale(1.08);
        background-color:#07071C;
    }
    .column-image {
        display: flex;
        justify-content: center;
        margin-bottom: 10px;
    }
    .movie-title {
        color: #F5FEFD;
        font: Open sans;
        font-size: 14px;
        margin-bottom: 5px;
    }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Displaying recommended movies in a grid layout
    cols = st.columns(6)
    for i in range(len(names)):
        with cols[i % 6]:
            st.markdown(
                """
                <div class="column-content">
                    <h3 class="movie-title">{}</h3>
                    <div class="column-image">
                        <img src="{}" alt="Movie Poster" width="200" height="300">
                    </div>
                </div>
                """.format(
                    names[i], posters[i]
                ),
                unsafe_allow_html=True,
            )
