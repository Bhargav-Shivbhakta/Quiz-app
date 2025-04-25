from pymongo import MongoClient
import streamlit as st

# Load the URI from secrets
MONGO_URI = st.secrets["mongo_uri"]

client = MongoClient(MONGO_URI)
db = client["quiz_app"]

users_col = db["users"]
quizzes_col = db["quizzes"]
responses_col = db["responses"]
