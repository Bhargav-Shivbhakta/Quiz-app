
from pymongo import MongoClient
import streamlit as st

MONGO_URI = f"mongodb+srv://admin:{st.secrets['db_password']}@quizzzzzzzzz.w23wq2q.mongodb.net/?retryWrites=true&w=majority&appName=Quizzzzzzzzz"
client = MongoClient(MONGO_URI)

db = client["quiz_app"]
users_col = db["users"]
quizzes_col = db["quizzes"]
responses_col = db["responses"]
