import streamlit as st
from db import users_col, quizzes_col, responses_col
import pandas as pd
import hashlib
import time

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
            st.stop()
        else:
            st.error("Invalid credentials")

def reset_password():
    st.subheader("Reset Password")
    username = st.text_input("Enter your username")
    new_password = st.text_input("Enter new password", type="password")

    if st.button("Update Password"):
        user = users_col.find_one({"username": username})
        if user:
            users_col.update_one(
                {"username": username},
                {"$set": {"password": hash_password(new_password)}}
            )
            st.success("Password updated successfully.")
        else:
            st.error("User not found.")

def admin_reset_data():
    st.subheader("🚨 Admin: Delete All Data")
    st.warning("⚠️ This will delete ALL users, quizzes, and responses.")
    confirm = st.checkbox("Yes, I want to delete everything permanently.")
    if confirm and st.button("Delete All"):
        users_col.delete_many({})
        quizzes_col.delete_many({})
        responses_col.delete_many({})
        st.success("✅ All data deleted successfully.")

# ------------------ STUDENT DASHBOARD ------------------
def student_dashboard():
    import time

    st.subheader(f"Welcome, {st.session_state['username']} (Student)")
    quiz_list = quizzes_col.distinct("quiz_id")
    selected_quiz = st.selectbox("Select a Quiz", quiz_list)

    if "quiz_started" not in st.session_state:
        st.session_state.quiz_started = False

    if selected_quiz and not st.session_state.quiz_started:
        if st.button("Start Quiz"):
            questions = list(quizzes_col.find({"quiz_id": selected_quiz}))
            st.session_state.quiz_data = questions
            st.session_state.quiz_id = selected_quiz
            st.session_state.current_q = 0
            st.session_state.score = 0
            st.session_state.timer_expired = False
            st.session_state.quiz_started = True
            st.experimental_rerun()

    if st.session_state.quiz_started:
        questions = st.session_state.quiz_data
        q_index = st.session_state.current_q

        if q_index < len(questions):
            q = questions[q_index]
            st.markdown(f"**Q{q_index + 1}: {q['question_text']}**")

            selected_option = st.radio("Options", q["options"], key=f"q_{q_index}", index=None)

            # Initialize timer
            if f"start_time_{q_index}" not in st.session_state:
                st.session_state[f"start_time_{q_index}"] = time.time()

            remaining = q["question_time"] - int(time.time() - st.session_state[f"start_time_{q_index}"])

            if remaining <= 0:
                st.session_state.timer_expired = True
                remaining = 0

            st.markdown(f"⏳ Time Remaining: **{remaining}** seconds")

            next_clicked = st.button("Next", key=f"next_{q_index}")

            # Move to next question if:
            # 1. Timer expires OR
            # 2. User clicks next
            if st.session_state.timer_expired or next_clicked:
                is_correct = False
                if selected_option:
                    is_correct = q["correct_option"] == q["options"].index(selected_option)
                if is_correct:
                    st.session_state.score += 1

                # Reset timer and move to next
                st.session_state.timer_expired = False
                st.session_state.current_q += 1
                st.experimental_rerun()

        else:
            responses_col.insert_one({
                "quiz_id": st.session_state.quiz_id,
                "username": st.session_state["username"],
                "score": st.session_state.score,
                "responses": []
            })
            st.success(f"Quiz completed! Your score: {st.session_state.score}")
            leaderboard = get_leaderboard(st.session_state.quiz_id)
            st.subheader("Leaderboard:")
            for rank, record in enumerate(leaderboard, 1):
                st.write(f"{rank}. {record['username']} - {record['score']}")
            st.session_state.quiz_started = False


# ------------------ CONDUCTOR DASHBOARD ------------------
def conductor_dashboard():
    st.subheader(f"Welcome, {st.session_state['username']} (Conductor)")
    st.write("### Upload Quiz Questions")

    uploaded_file = st.file_uploader("Upload CSV File with Questions", type="csv")
    quiz_id = st.text_input("Enter Quiz ID for This Upload")
    time_limit = st.number_input("Set time per question (in seconds)", min_value=5, max_value=300, value=30)

    if uploaded_file and quiz_id:
        df = pd.read_csv(uploaded_file)
        total_qs = len(df)
        num_qs = st.number_input(f"How many questions do you want in this quiz? (max {total_qs})",
                                 min_value=1, max_value=total_qs, value=total_qs)

        if st.button("Upload Quiz"):
            df = df.sample(num_qs).reset_index(drop=True)
            for _, row in df.iterrows():
                quizzes_col.insert_one({
                    "quiz_id": quiz_id,
                    "question_text": row["question_text"],
                    "options": [row["option1"], row["option2"], row["option3"], row["option4"]],
                    "correct_option": int(row["correct_option"]) - 1,
                    "question_time": time_limit,
                    "created_by": st.session_state["username"]
                })
            st.success(f"{num_qs} questions uploaded successfully with {time_limit} sec/question.")

    st.write("### View Leaderboard")
    quiz_list = quizzes_col.distinct("quiz_id", {"created_by": st.session_state["username"]})
    selected_quiz = st.selectbox("Select Quiz to View Leaderboard", quiz_list)
    if selected_quiz:
        leaderboard = get_leaderboard(selected_quiz)
        st.write("#### Leaderboard:")
        for rank, record in enumerate(leaderboard, 1):
            st.write(f"{rank}. {record['username']} - {record['score']}")

    st.write("---")
    admin_reset_data()
    st.write("---")
    st.write("🗑️ **Delete a Quiz**")

    quiz_list = quizzes_col.distinct("quiz_id", {"created_by": st.session_state["username"]})
    delete_quiz_id = st.selectbox("Select Quiz to Delete", quiz_list, key="delete_quiz")

    if st.button("Delete This Quiz"):
        quizzes_col.delete_many({"quiz_id": delete_quiz_id})
        responses_col.delete_many({"quiz_id": delete_quiz_id})
        st.success(f"✅ Quiz '{delete_quiz_id}' and all associated responses deleted.")

# ------------------ MAIN APP ------------------
def main():
    st.set_page_config(page_title="Quiz App", layout="centered")
    st.title("🧠 Quiz App")

    # ✅ Fixed: Proper redirection after login
    if st.session_state.get("just_logged_in"):
        del st.session_state["just_logged_in"]
        st.experimental_rerun()

    # 🔐 If user is not logged in
    if "username" not in st.session_state:
        menu = st.sidebar.radio("Menu", ["Login", "Register", "Reset Password"])
        if menu == "Login":
            login()
        elif menu == "Register":
            register()
        elif menu == "Reset Password":
            reset_password()

    # 👤 If logged in
    else:
        st.sidebar.success(f"Logged in as {st.session_state['username']}")
        sidebar_choice = st.sidebar.radio("Navigation", ["Dashboard", "Reset Password", "Logout"])

        if sidebar_choice == "Dashboard":
            if st.session_state["role"] == "student":
                student_dashboard()
            elif st.session_state["role"] == "conductor":
                conductor_dashboard()

        elif sidebar_choice == "Reset Password":
            reset_password()

        elif sidebar_choice == "Logout":
            st.session_state.clear()
            st.experimental_rerun()

if __name__ == "__main__":
    main()
