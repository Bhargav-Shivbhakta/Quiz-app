from pymongo import MongoClient
import streamlit as st

# ✅ Use Streamlit Secret for secure password
password = st.secrets["db_password"]

# ✅ Final formatted URI
MONGO_URI = f"mongodb+srv://admin:{password}@quizzzzzzzzz.w23wq2q.mongodb.net/?retryWrites=true&w=majority&appName=Quizzzzzzzzz"

# ✅ MongoDB Client
client = MongoClient(MONGO_URI)

# ✅ Collections
db = client["quiz_app"]
users_col = db["users"]
quizzes_col = db["quizzes"]
responses_col = db["responses"]
