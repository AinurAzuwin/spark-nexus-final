import streamlit as st
import pandas as pd
import plotly.express as px
from utils.session_state import clear_cookies
from utils.ui_components import render_footer
from database.users import get_all_users
from database.children import get_all_children
from database.reports import get_all_reports

def logout():
    """Clears session state and cookies for logout and forces a rerun."""
    # Clear cookies
    clear_cookies(st.session_state.get('cookies'))
    # Clear session state keys related to the logged-in user
    if 'logged_in' in st.session_state:
        del st.session_state['logged_in']
    if 'user_id' in st.session_state:
        del st.session_state['user_id']
    if 'user_role' in st.session_state:
        del st.session_state['user_role']
    if 'full_name' in st.session_state:
        del st.session_state['full_name']
    if 'user_email' in st.session_state:
        del st.session_state['user_email']

    # Rerun the app to go back to the main login/home page
    st.rerun()

# Logout button in sidebar
with st.sidebar:
    if st.button("Logout", icon=":material/logout:", help="Click to securely log out", use_container_width=True):
        logout()

st.markdown("""
    <style>
        .safe-header {
            background-color: #004280;
            color: white;
            padding: 15px 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            border: 1px solid #ddd;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="safe-header">
    <h2 style="margin: 0;">Analytics Overview</h2>
    <p style="margin: 0;">This is the analytics overview for admins.</p>
</div>
""", unsafe_allow_html=True)

# Fetch data
users = get_all_users()
children = get_all_children()
reports = get_all_reports()

# User counts
parents_count = len([u for u in users if u.get('UserRole') == 'PARENT'])
therapists_count = len([u for u in users if u.get('UserRole') == 'THERAPIST'])
children_count = len(children)

# Reports count
total_reports = len(reports)

# Reports over time
#reports_df = pd.DataFrame(reports)
#if not reports_df.empty and 'Date' in reports_df.columns:
    #reports_df['Date'] = pd.to_datetime(reports_df['Date'])
    #reports_df['Month'] = reports_df['Date'].dt.to_period('M').astype(str)
    #reports_over_time = reports_df.groupby('Month').size().reset_index(name='Count')
    #fig_reports = px.line(reports_over_time, x='Month', y='Count', title='Reports Generated Over Time', color_discrete_sequence=['#004280'])
    #st.plotly_chart(fig_reports)

# Screening results (assuming diagnosis field in children table)
adhd_count = len([c for c in children if c.get('Diagnosis') == 'ADHD'])
normal_count = len([c for c in children if c.get('Diagnosis') == 'Normal'])
language_delay_count = len([c for c in children if c.get('Diagnosis') == 'Language Delay'])

# Data
user_data = pd.DataFrame({
    'User Type': ['Parents', 'Children', 'Therapists'],
    'Count': [parents_count, children_count, therapists_count]
})

# Tentukan warna untuk setiap jenis
colors = ['#004280', "#0A3645", "#2B95BE"]  # contoh warna: navy, blue, orange

fig_users = px.bar(
    user_data,
    x='Count',
    y='User Type',
    orientation='h',
    title='Registered Users by Type',
    text='Count',  # paparkan nombor di hujung bar
    color='User Type',
    color_discrete_sequence=colors
)

# Format nombor sebagai integer
fig_users.update_traces(
    texttemplate='%{text}',  # guna text yang kita masukkan
    textposition='outside'
)

# Update layout supaya X-axis integer
fig_users.update_layout(
    xaxis=dict(tickmode='linear', dtick=1),
    yaxis=dict(autorange='reversed'),  # supaya bar atas = pertama
    showlegend=False  # kalau nak hilangkan legend
)

st.plotly_chart(fig_users, use_container_width=True)

# Total reports
st.subheader("Total Reports Generated")
st.metric("Reports", total_reports)

# Screening results
st.subheader("Screening Results")
screening_data = pd.DataFrame({
    'Diagnosis': ['ADHD', 'Normal', 'Language Delay'],
    'Count': [adhd_count, normal_count, language_delay_count]
})
fig_screening = px.bar(screening_data, x='Diagnosis', y='Count', title='Screening Results', color_discrete_sequence=['#004280'])
fig_screening.update_yaxes(
    tick0=0,
    dtick=1 
)
st.plotly_chart(fig_screening)

render_footer()