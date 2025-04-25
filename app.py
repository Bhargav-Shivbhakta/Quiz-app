import streamlit as st
from db import users_col, quizzes_col, responses_col
import pandas as pd
import hashlib

# ------------------ UTILS ------------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_answer(correct, selected):
    return correct == selected

def get_leaderboard(quiz_id):
    scores = list(responses_col.find({"quiz_id": quiz_id}))
    scores.sort(key=lambda x: x.get("score", 0), reverse=True)
    return scores

# ------------------ AUTH ------------------
def register():
    st.subheader("Register")
    username = st.text_input("Create Username")
    password = st.text_input("Create Password", type="password")
    role = st.selectbox("Select Role", ["student", "conductor"])
    if st.button("Register"):
        if users_col.find_one({"username": username}):
            st.warning("User already exists")
        else:
            users_col.insert_one({
                "username": username,
                "password": hash_password(password),
                "role": role
            })
            st.success("Registered successfully! Please login.")

def login():
    st.subheader("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        user = users_col.find_one({
            "username": username,
            "password": hash_password(password)
        })
        if user:
            st.session_state["username"] = user["username"]
            st.session_state["role"] = user["role"]
            st.session_state["just_logged_in"] = True
            st.success(f"Logged in as {user['role']}")
            st.stop()  # stop execution to avoid re-running login logic
        else:
            st.error("Invalid credentials")

# ------------------ STUDENT DASHBOARD ------------------
def student_dashboard():
    st.subheader(f"Welcome, {st.session_state['username']} (Student)")
    quiz_list = quizzes_col.distinct("quiz_id")
    selected_quiz = st.selectbox("Select a Quiz", quiz_list)

    if selected_quiz:
        questions = list(quizzes_col.find({"quiz_id": selected_quiz}))
        user_responses = []
        score = 0

        for q in questions:
            st.markdown(f"**Q: {q['question_text']}**")
            selected = st.radio("Options", q["options"], key=str(q["_id"]))
            correct = q["correct_option"]
            is_correct = check_answer(correct, q["options"].index(selected))
            user_responses.append({
                "question_id": q["_id"],
                "selected_option": selected,
                "correct": is_correct
            })
            if is_correct:
                score += 1

        if st.button("Submit Quiz"):
            responses_col.insert_one({
                "quiz_id": selected_quiz,
                "username": st.session_state["username"],
                "score": score,
                "responses": user_responses
            })
            st.success(f"Quiz submitted! Your score: {score}")
            st.subheader("Leaderboard:")
            leaderboard = get_leaderboard(selected_quiz)
            for rank, record in enumerate(leaderboard, 1):
                st.write(f"{rank}. {record['username']} - {record['score']}")

# ------------------ CONDUCTOR DASHBOARD ------------------
def conductor_dashboard():
    st.subheader(f"Welcome, {st.session_state['username']} (Conductor)")
    st.write("### Upload Quiz Questions")

    uploaded_file = st.file_uploader("Upload CSV File with Questions", type="csv")
    quiz_id = st.text_input("Enter Quiz ID for This Upload")

    if uploaded_file and quiz_id:
        df = pd.read_csv(uploaded_file)
        for _, row in df.iterrows():
            quizzes_col.insert_one({
                "quiz_id": quiz_id,
                "question_text": row["question_text"],
                "options": [row["option1"], row["option2"], row["option3"], row["option4"]],
                "correct_option": int(row["correct_option"]) - 1
            })
        st.success("Questions uploaded successfully!")

    st.write("### View Leaderboard")
    quiz_list = quizzes_col.distinct("quiz_id")
    selected_quiz = st.selectbox("Select Quiz to View Leaderboard", quiz_list)
    if selected_quiz:
        leaderboard = get_leaderboard(selected_quiz)
        st.write("#### Leaderboard:")
        for rank, record in enumerate(leaderboard, 1):
            st.write(f"{rank}. {record['username']} - {record['score']}")

# ------------------ MAIN APP ------------------
def main():
    st.set_page_config(page_title="Quiz App", layout="centered")
    st.title("🧠 Quiz App")

    if st.session_state.get("just_logged_in"):
        del st.session_state["just_logged_in"]
        st.experimental_rerun()
        return

    if "username" not in st.session_state:
        menu = st.sidebar.radio("Menu", ["Login", "Register"])
        if menu == "Login":
            login()
        else:
            register()
    else:
        role = st.session_state["role"]
        if role == "student":
            student_dashboard()
        elif role == "conductor":
            conductor_dashboard()

        if st.sidebar.button("Logout"):
            st.session_state.clear()
            st.experimental_rerun()

if __name__ == "__main__":
    main()
