import streamlit as st
import requests
import uuid
from datetime import datetime

def main():
    st.set_page_config(
        page_title="Soul Connect - Login",
        page_icon="❤️",
        layout="centered"
    )
    
    # Custom CSS
    st.markdown("""
    <style>
        .main {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 50px;
            border-radius: 20px;
        }
        .login-box {
            background: white;
            padding: 40px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        .stButton>button {
            width: 100%;
            border-radius: 10px;
            height: 50px;
            font-size: 18px;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Main container
    with st.container():
        col1, col2, col3 = st.columns([1,2,1])
        
        with col2:
            st.markdown('<div class="login-box">', unsafe_allow_html=True)
            
            # Header
            st.markdown("""
            <div style='text-align: center; margin-bottom: 30px;'>
                <h1 style='color: #6a0dad; margin-bottom: 10px;'>❤️ Soul Connect</h1>
                <p style='color: #666; font-size: 16px;'>Connecting minds, healing hearts</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Login Options
            option = st.radio(
                "Choose your login method:",
                ["🔒 Anonymous Login", "👤 Create Account", "🔑 Existing User"],
                index=0
            )
            
            st.markdown("---")
            
            if option == "🔒 Anonymous Login":
                st.info("**Private & Secure:** No personal information required")
                if st.button("Start Anonymous Session", type="primary"):
                    # Create anonymous user
                    try:
                        response = requests.post("http://localhost:8080/create-user")
                        if response.status_code == 200:
                            user_data = response.json()
                            st.session_state.user_id = user_data['user_id']
                            st.session_state.anonymous_id = user_data['anonymous_id']
                            st.session_state.logged_in = True
                            st.session_state.session_id = str(uuid.uuid4())
                            st.success("✅ Anonymous session created!")
                            st.rerun()
                        else:
                            st.error("Failed to create session. Please check backend.")
                    except:
                        st.error("❌ Cannot connect to server. Make sure backend is running.")
            
            elif option == "👤 Create Account":
                st.info("**Create a permanent account** (Optional)")
                with st.form("signup_form"):
                    email = st.text_input("📧 Email")
                    username = st.text_input("👤 Username")
                    password = st.text_input("🔑 Password", type="password")
                    confirm_password = st.text_input("✅ Confirm Password", type="password")
                    
                    if st.form_submit_button("Create Account", type="primary"):
                        if password == confirm_password:
                            st.success("Account created successfully! (Demo)")
                            # In real app, you'd save to database
                        else:
                            st.error("Passwords don't match!")
            
            elif option == "🔑 Existing User":
                st.info("**Login to your existing account**")
                with st.form("login_form"):
                    username = st.text_input("👤 Username")
                    password = st.text_input("🔑 Password", type="password")
                    
                    if st.form_submit_button("Login", type="primary"):
                        st.success("Login successful! (Demo)")
                        # In real app, you'd verify credentials
            
            st.markdown("---")
            st.markdown("""
            <div style='text-align: center; color: #888; font-size: 12px;'>
                <p>💡 Your privacy and safety are our priority</p>
                <p>🔒 All conversations are encrypted and anonymous</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    # If logged in, show option to proceed to chat
    if st.session_state.get('logged_in'):
        st.markdown("---")
        st.success(f"✅ Logged in as: **{st.session_state.anonymous_id}**")
        if st.button("🚀 Proceed to Soul Connect Chat"):
            st.switch_page("app.py")

if __name__ == "__main__":
    # Initialize session state
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    if 'anonymous_id' not in st.session_state:
        st.session_state.anonymous_id = None
    
    main()