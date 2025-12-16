import streamlit as st

def set_logged_in_session(user_data, cookies):
    # ---- STORE COOKIES ----
    cookies["logged_in"] = "true"
    cookies["user_role"] = user_data["UserRole"]
    cookies["user_email"] = user_data["Email"]
    cookies["full_name"] = user_data["FullName"]
    cookies["user_id"] = user_data["UserID"]
    cookies.save()

    # ---- SESSION STATE ----
    st.session_state["logged_in"] = True
    st.session_state["user_role"] = user_data["UserRole"]
    st.session_state["user_email"] = user_data["Email"]
    st.session_state["full_name"] = user_data["FullName"]
    st.session_state["user_id"] = user_data["UserID"]

def get_logged_in_from_cookies(cookies):
    cookies.ready()

    if cookies.get("logged_in") == "true":
        return {
            "logged_in": True,
            "user_role": cookies.get("user_role"),
            "user_email": cookies.get("user_email"),
            "full_name": cookies.get("full_name"),
            "user_id": cookies.get("user_id")
        }
    return None

def clear_cookies(cookies):
    cookies["logged_in"] = ""
    cookies["user_role"] = ""
    cookies["user_email"] = ""
    cookies["full_name"] = ""
    cookies["user_id"] = ""
    cookies.save()
