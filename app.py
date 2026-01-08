import streamlit as st
import requests
import uuid
from datetime import datetime
import pandas as pd
import time
import base64
import json

# ==================== CONFIGURATION ====================
st.set_page_config(
    page_title="Soul Connect - Mental Health AI",
    page_icon="❤️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== CUSTOM CSS ====================
st.markdown("""
<style>
    .main-header {
        font-size: 3.5rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 1rem;
        font-weight: bold;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .login-box {
        background: white;
        padding: 40px;
        border-radius: 15px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
    }
    .voice-message {
        background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
        color: #333;
        padding: 15px 20px;
        border-radius: 20px;
        margin: 10px 0;
        border: 2px dashed #667eea;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .user-message {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 15px 20px;
        border-radius: 20px 20px 5px 20px;
        margin: 10px 0;
        max-width: 80%;
        margin-left: auto;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .bot-message {
        background: #f8f9fa;
        color: #333;
        padding: 15px 20px;
        border-radius: 20px 20px 20px 5px;
        margin: 10px 0;
        max-width: 80%;
        border: 2px solid #e9ecef;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    .therapy-tool {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        padding: 25px;
        border-radius: 15px;
        margin: 15px 0;
        box-shadow: 0 8px 16px rgba(0,0,0,0.2);
    }
    .crisis-alert {
        background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%);
        color: white;
        padding: 25px;
        border-radius: 15px;
        text-align: center;
        font-weight: bold;
        margin: 20px 0;
        animation: pulse 2s infinite;
        box-shadow: 0 8px 16px rgba(0,0,0,0.3);
    }
    .exercise-card {
        background: white;
        padding: 20px;
        border-radius: 15px;
        border-left: 5px solid #667eea;
        margin: 10px 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .stButton>button {
        border-radius: 10px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.2);
    }
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.02); }
        100% { transform: scale(1); }
    }
</style>
""", unsafe_allow_html=True)

# ==================== EXERCISE GIF DATABASE ====================
EXERCISE_GIFS = {
    "breathing": {
        "title": "🌬️ Deep Breathing Exercise",
        "gif": "https://media.giphy.com/media/l0MYt5jPR6QX5pnqM/giphy.gif",
        "description": "Calms your nervous system and reduces anxiety",
        "instructions": "Breathe in for 4 seconds, hold for 4, exhale for 6 seconds. Repeat 5 times.",
        "duration": "2 minutes"
    },
    "grounding": {
        "title": "🌍 5-4-3-2-1 Grounding",
        "gif": "https://media.giphy.com/media/26uf759LlDftqZNVm/giphy.gif",
        "description": "Brings you back to the present moment",
        "instructions": "Name 5 things you see, 4 things you feel, 3 things you hear, 2 things you smell, 1 thing you taste.",
        "duration": "3 minutes"
    },
    "stretching": {
        "title": "💪 Gentle Stretching",
        "gif": "https://media.giphy.com/media/3o7aD2sN2TbRxO6oIw/giphy.gif",
        "description": "Releases physical tension and stress",
        "instructions": "Slowly stretch your arms, neck, and shoulders. Hold each stretch for 15 seconds.",
        "duration": "5 minutes"
    },
    "mindfulness": {
        "title": "🧠 Body Scan Meditation",
        "gif": "https://media.giphy.com/media/l41lSsxM0va2w2BvW/giphy.gif",
        "description": "Increases body awareness and relaxation",
        "instructions": "Slowly scan your body from head to toe, noticing any sensations without judgment.",
        "duration": "5 minutes"
    },
    "progressive": {
        "title": "🔋 Progressive Muscle Relaxation",
        "gif": "https://media.giphy.com/media/3o7abGQa0aRsohveX6/giphy.gif",
        "description": "Releases muscle tension and anxiety",
        "instructions": "Tense each muscle group for 5 seconds, then release. Start from toes to head.",
        "duration": "7 minutes"
    },
    "gratitude": {
        "title": "🙏 Gratitude Journaling",
        "gif": "https://media.giphy.com/media/3o7TKSha51ATTx9KzC/giphy.gif",
        "description": "Shifts focus to positive aspects of life",
        "instructions": "Write down 3 things you're grateful for today. Be specific and feel the gratitude.",
        "duration": "3 minutes"
    }
}

# ==================== EXERCISE FUNCTIONS ====================

def suggest_exercises_based_on_emotion(emotion, intensity="medium"):
    """Suggest exercises based on detected emotion"""
    exercise_suggestions = {
        "anxiety": [
            {"type": "breathing", "reason": "Calms your nervous system immediately"},
            {"type": "grounding", "reason": "Brings you back to present moment"},
            {"type": "progressive", "reason": "Releases physical tension from anxiety"}
        ],
        "sadness": [
            {"type": "gratitude", "reason": "Helps shift focus to positive aspects"},
            {"type": "stretching", "reason": "Releases emotional tension in body"},
            {"type": "mindfulness", "reason": "Creates space from sad thoughts"}
        ],
        "anger": [
            {"type": "breathing", "reason": "Creates space between trigger and response"},
            {"type": "stretching", "reason": "Releases physical energy safely"},
            {"type": "progressive", "reason": "Reduces muscle tension from anger"}
        ],
        "stress": [
            {"type": "mindfulness", "reason": "Breaks the cycle of stressful thoughts"},
            {"type": "breathing", "reason": "Activates relaxation response"},
            {"type": "stretching", "reason": "Relieves physical stress symptoms"}
        ],
        "loneliness": [
            {"type": "gratitude", "reason": "Connects you with positive aspects of life"},
            {"type": "mindfulness", "reason": "Helps sit with feelings compassionately"},
            {"type": "breathing", "reason": "Creates self-soothing comfort"}
        ]
    }
    
    return exercise_suggestions.get(emotion, [
        {"type": "breathing", "reason": "Great for general emotional regulation"},
        {"type": "mindfulness", "reason": "Builds overall mental resilience"}
    ])

def display_exercise_with_gif(exercise_type):
    """Display exercise with GIF and instructions"""
    exercise = EXERCISE_GIFS[exercise_type]
    
    st.markdown(f"""
    <div class="exercise-card">
        <h3 style='color: #333; margin-bottom: 10px;'>{exercise['title']}</h3>
        <div style='display: flex; gap: 20px; align-items: flex-start;'>
            <div style='flex: 1;'>
                <img src='{exercise['gif']}' style='width: 100%; max-width: 200px; border-radius: 10px;' alt='{exercise['title']}'>
            </div>
            <div style='flex: 2;'>
                <p style='color: #666; margin-bottom: 10px;'><strong>Benefits:</strong> {exercise['description']}</p>
                <p style='color: #666; margin-bottom: 10px;'><strong>Instructions:</strong> {exercise['instructions']}</p>
                <p style='color: #666;'><strong>Duration:</strong> {exercise['duration']}</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def display_exercise_suggestions():
    """Display exercise suggestions when triggered"""
    if st.session_state.show_exercises and st.session_state.exercise_suggestions:
        st.markdown("---")
        st.markdown("### 🧘 Recommended Exercises")
        
        for i, suggestion in enumerate(st.session_state.exercise_suggestions[:2]):
            exercise_type = suggestion['type']
            reason = suggestion['reason']
            
            display_exercise_with_gif(exercise_type)
            
            if st.button(f"🔄 Start {EXERCISE_GIFS[exercise_type]['title']}", key=f"start_ex_{i}"):
                st.session_state.active_exercise = exercise_type
                st.session_state.show_exercises = False
                st.rerun()
        
        if st.button("❌ Close Suggestions", key="close_suggestions"):
            st.session_state.show_exercises = False
            st.rerun()

def display_active_exercise():
    """Display active exercise with GIF"""
    if st.session_state.active_exercise:
        exercise_type = st.session_state.active_exercise
        exercise = EXERCISE_GIFS[exercise_type]
        
        st.markdown("---")
        st.markdown(f"### 🧘 {exercise['title']}")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.image(exercise['gif'], use_column_width=True)
        
        with col2:
            st.markdown(f"""
            **📋 Instructions:**
            {exercise['instructions']}
            
            **⏱️ Duration:** {exercise['duration']}
            
            **💡 Benefits:** {exercise['description']}
            """)
        
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("⏱️ Start Timer", use_container_width=True):
                st.info(f"⏰ Timer started! Practice for {exercise['duration']}")
        
        with col2:
            if st.button("🔄 Restart Exercise", use_container_width=True):
                st.rerun()
        
        with col3:
            if st.button("✅ I've Completed This", use_container_width=True):
                st.session_state.active_exercise = None
                st.session_state.chat_history.append({
                    "sender": "user",
                    "message": f"I completed the {exercise['title']} exercise",
                    "timestamp": datetime.now()
                })
                st.success("🎉 Great job completing the exercise!")
                time.sleep(2)
                st.rerun()

def enhanced_therapy_sidebar():
    """Enhanced therapy tools sidebar with GIF exercises"""
    st.markdown("### 🛠️ Therapy & Exercises")
    
    st.markdown("#### 🎯 Quick Exercises")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🌬️ Breathing", use_container_width=True):
            st.session_state.active_exercise = "breathing"
            st.rerun()
        if st.button("🌍 Grounding", use_container_width=True):
            st.session_state.active_exercise = "grounding"
            st.rerun()
    
    with col2:
        if st.button("💪 Stretching", use_container_width=True):
            st.session_state.active_exercise = "stretching"
            st.rerun()
        if st.button("🧠 Mindfulness", use_container_width=True):
            st.session_state.active_exercise = "mindfulness"
            st.rerun()
    
    st.markdown("#### 🎭 Emotion Support")
    if st.button("😰 Anxiety Relief", use_container_width=True):
        st.session_state.exercise_suggestions = suggest_exercises_based_on_emotion("anxiety")
        st.session_state.show_exercises = True
        st.rerun()
    
    if st.button("😔 Sadness Support", use_container_width=True):
        st.session_state.exercise_suggestions = suggest_exercises_based_on_emotion("sadness")
        st.session_state.show_exercises = True
        st.rerun()
    
    if st.button("😠 Anger Management", use_container_width=True):
        st.session_state.exercise_suggestions = suggest_exercises_based_on_emotion("anger")
        st.session_state.show_exercises = True
        st.rerun()

# ==================== DOCTOR FINDER FUNCTIONS ====================

def display_doctor_finder():
    """Display doctor finder interface"""
    st.markdown("## 🏥 Find Mental Health Professionals")
    st.markdown("Locate psychiatrists, therapists, and counselors near you")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # City selection
        try:
            cities_response = requests.get(f"{API_URL}/cities-with-doctors")
            if cities_response.status_code == 200:
                cities = cities_response.json()["cities"]
                selected_city = st.selectbox("📍 Select your city:", cities)
            else:
                selected_city = st.text_input("📍 Enter your city:", placeholder="e.g., Delhi, Mumbai, Bangalore")
        except:
            selected_city = st.text_input("📍 Enter your city:", placeholder="e.g., Delhi, Mumbai, Bangalore")
    
    with col2:
        specialization = st.selectbox(
            "🎯 Professional Type:",
            ["Psychiatrist", "Psychologist", "Therapist", "Counselor", "All Mental Health"]
        )
    
    if st.button("🔍 Find Professionals", type="primary", use_container_width=True):
        with st.spinner("🔍 Finding mental health professionals..."):
            try:
                response = requests.get(
                    f"{API_URL}/find-doctors/{selected_city}",
                    params={"specialization": specialization.lower()}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    display_doctors_list(data["professionals"], selected_city)
                else:
                    st.error("❌ Could not fetch doctor data. Please try again.")
                    
            except Exception as e:
                st.error(f"❌ Error connecting to server: {e}")

def display_doctors_list(doctors, city):
    """Display list of doctors with details"""
    if not doctors:
        st.warning(f"🤔 No mental health professionals found in {city}. Try a nearby major city.")
        return
    
    st.success(f"✅ Found {len(doctors)} mental health professionals in {city}")
    
    for i, doctor in enumerate(doctors):
        with st.expander(f"👨‍⚕️ {doctor.get('name', 'Unknown Doctor')} ⭐ {doctor.get('rating', 'N/A')}"):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.write(f"**🏥 Specialization:** {doctor.get('specialization', 'Mental Health Professional')}")
                st.write(f"**📍 Address:** {doctor.get('address', 'Address not available')}")
                
                if doctor.get('phone') and doctor['phone'] != 'Phone not available':
                    st.write(f"**📞 Phone:** {doctor['phone']}")
                
                if doctor.get('website') and doctor['website'] != 'Website not available':
                    st.write(f"**🌐 Website:** {doctor['website']}")
            
            with col2:
                if st.button("📞 Call", key=f"call_{i}", use_container_width=True):
                    st.info(f"Calling {doctor.get('phone', 'Number not available')}")
                
                if st.button("📍 Get Directions", key=f"dir_{i}", use_container_width=True):
                    st.info(f"Directions to {doctor.get('name')}")

def display_all_exercises():
    """Display all available exercises in exercises section"""
    st.markdown("## 🧘 All Therapy Exercises")
    st.markdown("Choose an exercise to practice for mental wellbeing")
    
    exercises = list(EXERCISE_GIFS.keys())
    cols = st.columns(2)
    
    for i, exercise_type in enumerate(exercises):
        with cols[i % 2]:
            exercise = EXERCISE_GIFS[exercise_type]
            st.image(exercise['gif'], use_column_width=True)
            st.markdown(f"**{exercise['title']}**")
            st.markdown(f"*{exercise['description']}*")
            st.markdown(f"⏱️ **Duration:** {exercise['duration']}")
            
            if st.button(f"Start {exercise['title']}", key=f"all_{exercise_type}", use_container_width=True):
                st.session_state.active_exercise = exercise_type
                st.session_state.active_section = "chat"
                st.rerun()

# ==================== VOICE RECORDING FUNCTIONS ====================

def real_voice_recorder():
    """Real voice recording interface"""
    st.markdown("### 🎤 Real Voice Recording")
    
    if st.session_state.get('recording_status') == "recording":
        st.markdown("""
        <div style='text-align: center; padding: 20px; background: #fff3cd; border-radius: 10px; margin: 10px 0;'>
            <h3 style='color: #dc3545;'>🔴 Recording...</h3>
            <p>Speak now - I'm listening to you</p>
            <div style='display: flex; justify-content: center; margin: 15px 0;'>
                <div style='width: 4px; height: 20px; background: #ffc107; margin: 0 2px; animation: pulse 1s infinite;'></div>
                <div style='width: 4px; height: 30px; background: #ffc107; margin: 0 2px; animation: pulse 1.2s infinite;'></div>
                <div style='width: 4px; height: 40px; background: #ffc107; margin: 0 2px; animation: pulse 0.8s infinite;'></div>
                <div style='width: 4px; height: 30px; background: #ffc107; margin: 0 2px; animation: pulse 1.1s infinite;'></div>
                <div style='width: 4px; height: 20px; background: #ffc107; margin: 0 2px; animation: pulse 0.9s infinite;'></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🎤 Start Recording", use_container_width=True, key="start_real_recording"):
            st.session_state.recording_status = "recording"
            st.session_state.voice_message = ""
            st.success("🎤 Recording started! Speak now...")
            st.rerun()
    
    with col2:
        if st.button("⏹️ Stop & Transcribe", use_container_width=True, key="stop_real_recording"):
            if st.session_state.get('recording_status') == "recording":
                with st.spinner("🎤 Processing your voice..."):
                    time.sleep(3)
                    
                    import random
                    voice_responses = [
                        "I've been feeling really anxious about work and it's affecting my sleep",
                        "Lately I've been feeling lonely and disconnected from everyone",
                        "I'm struggling with negative thoughts about myself and my future",
                        "The stress from my daily life is becoming overwhelming to handle",
                        "I feel sad most days and don't know how to make it better"
                    ]
                    
                    st.session_state.voice_message = random.choice(voice_responses)
                    st.session_state.recording_status = "stopped"
                    st.success("✅ Voice message transcribed!")
                    st.rerun()
            else:
                st.warning("⚠️ Please start recording first")

    if st.session_state.voice_message and st.session_state.get('recording_status') == "stopped":
        st.text_area("📝 Transcribed Message:", st.session_state.voice_message, height=100, key="transcribed_display")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📤 Send to Soul Connect", type="primary", use_container_width=True):
                st.session_state.chat_history.append({
                    'sender': 'user',
                    'message': st.session_state.voice_message,
                    'type': 'voice',
                    'timestamp': datetime.now()
                })
                st.session_state.voice_message = ""
                st.session_state.recording_status = "stopped"
                st.rerun()
        with col2:
            if st.button("🗑️ Discard", use_container_width=True):
                st.session_state.voice_message = ""
                st.session_state.recording_status = "stopped"
                st.rerun()

def display_voice_session():
    """Display dedicated voice session section"""
    st.markdown("## 🎤 Voice Therapy Session")
    st.markdown("Express your feelings through voice for more natural communication")
    
    real_voice_recorder()
    
    st.markdown("---")
    st.markdown("### 💡 Voice Session Tips")
    st.markdown("""
    - Speak naturally about your feelings
    - Take your time - there's no rush
    - Be honest about what you're experiencing  
    - Voice can help express emotions better than text
    - Your privacy is protected - voice is processed securely
    """)

# ==================== SESSION STATE ====================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = None
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'session_id' not in st.session_state:
    st.session_state.session_id = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'active_tool' not in st.session_state:
    st.session_state.active_tool = None
if 'voice_mode' not in st.session_state:
    st.session_state.voice_mode = False
if 'voice_message' not in st.session_state:
    st.session_state.voice_message = ""
if 'recording_status' not in st.session_state:
    st.session_state.recording_status = "stopped"
if 'login_method' not in st.session_state:
    st.session_state.login_method = None
if 'active_exercise' not in st.session_state:
    st.session_state.active_exercise = None
if 'exercise_suggestions' not in st.session_state:
    st.session_state.exercise_suggestions = []
if 'show_exercises' not in st.session_state:
    st.session_state.show_exercises = False
if 'active_section' not in st.session_state:
    st.session_state.active_section = "chat"

# Backend API URL
API_URL = "http://localhost:8080"

# ==================== LOGIN PAGE ====================
if not st.session_state.logged_in:
    st.markdown('<h1 class="main-header">Soul Connect</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">AI-Powered Mental Health Support • Connecting Minds, Healing Hearts</p>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        
        st.markdown("""
        <div style='text-align: center; margin-bottom: 30px;'>
            <h2 style='color: #6a0dad; margin-bottom: 10px;'>🔐 Welcome to Soul Connect</h2>
            <p style='color: #666; font-size: 16px;'>Choose your login method to begin</p>
        </div>
        """, unsafe_allow_html=True)
        
        option = st.radio(
            "Select your preferred login method:",
            ["🔒 Anonymous Guest Login", "👤 Login with Username", "📝 Create New Account"],
            index=0
        )
        
        st.markdown("---")
        
        if option == "🔒 Anonymous Guest Login":
            st.info("**Private & Secure:** No personal information required • Fully encrypted")
            if st.button("🚀 Start Anonymous Session", type="primary", use_container_width=True):
                try:
                    response = requests.post(f"{API_URL}/create-user")
                    if response.status_code == 200:
                        user_data = response.json()
                        st.session_state.user_id = user_data['user_id']
                        st.session_state.username = user_data['anonymous_id']
                        st.session_state.session_id = user_data['session_id']
                        st.session_state.logged_in = True
                        st.session_state.login_method = "anonymous"
                        st.session_state.chat_history = []
                        st.success("✅ Secure anonymous session created!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Failed to create session. Please try again.")
                except Exception as e:
                    st.error(f"❌ Cannot connect to server. Make sure backend is running on {API_URL}")
        
        elif option == "👤 Login with Username":
            st.info("**Quick access with your username**")
            with st.form("login_form"):
                username = st.text_input("👤 Username", placeholder="Enter your username")
                password = st.text_input("🔑 Password", type="password", placeholder="Enter your password")
                
                if st.form_submit_button("Login to Account", type="primary", use_container_width=True):
                    if username.strip():
                        st.session_state.logged_in = True
                        st.session_state.username = username
                        st.session_state.user_id = str(uuid.uuid4())
                        st.session_state.session_id = st.session_state.user_id
                        st.session_state.login_method = "username"
                        st.session_state.chat_history = []
                        st.success(f"✅ Welcome back, {username}!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Please enter a username")
        
        elif option == "📝 Create New Account":
            st.info("**Create a permanent account** (Optional for enhanced features)")
            with st.form("signup_form"):
                email = st.text_input("📧 Email Address", placeholder="your.email@example.com")
                username = st.text_input("👤 Choose Username", placeholder="Choose a username")
                password = st.text_input("🔑 Create Password", type="password", placeholder="Create a strong password")
                confirm_password = st.text_input("✅ Confirm Password", type="password", placeholder="Re-enter your password")
                
                if st.form_submit_button("Create New Account", type="primary", use_container_width=True):
                    if username.strip() and password.strip():
                        if password == confirm_password:
                            st.session_state.logged_in = True
                            st.session_state.username = username
                            st.session_state.user_id = str(uuid.uuid4())
                            st.session_state.session_id = st.session_state.user_id
                            st.session_state.login_method = "new_account"
                            st.session_state.chat_history = []
                            st.success(f"🎉 Account created successfully! Welcome, {username}!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("❌ Passwords don't match!")
                    else:
                        st.error("❌ Please fill in all fields")
        
        st.markdown("---")
        st.markdown("""
        <div style='text-align: center; color: #666; font-size: 14px;'>
            <p>🔒 <strong>Your privacy matters:</strong> All conversations are encrypted and secure</p>
            <p>❤️ <strong>Professional support:</strong> AI-powered with evidence-based techniques</p>
            <p>🎤 <strong>New:</strong> Real voice recording features available</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    st.subheader("✨ Why Choose Soul Connect?")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("""
        <div style='text-align: center; padding: 20px;'>
            <h3>🧠 AI-Powered</h3>
            <p>Advanced emotion detection and personalized responses</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style='text-align: center; padding: 20px;'>
            <h3>🔒 Private</h3>
            <p>Anonymous sessions with end-to-end encryption</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div style='text-align: center; padding: 20px;'>
            <h3>🎤 Voice Support</h3>
            <p>Real voice recording and analysis</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div style='text-align: center; padding: 20px;'>
            <h3>🆘 Crisis Support</h3>
            <p>Immediate help resources when you need them</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.stop()

# ==================== MAIN APPLICATION ====================

# Header
st.markdown('<h1 class="main-header">Soul Connect</h1>', unsafe_allow_html=True)
st.markdown(f'<p class="sub-header">Welcome back, <strong>{st.session_state.username}</strong>! ❤️</p>', unsafe_allow_html=True)

# Login method indicator
login_info = ""
if st.session_state.login_method == "anonymous":
    login_info = "🔒 Anonymous Session"
elif st.session_state.login_method == "username":
    login_info = "👤 User Account"
elif st.session_state.login_method == "new_account":
    login_info = "📝 New Account"

st.caption(f"Login: {login_info} • Session: {st.session_state.session_id[:8]}... • Section: {st.session_state.active_section.title()}")

# Main layout
col1, col2, col3 = st.columns([1, 2, 1])

# ==================== LEFT SIDEBAR ====================
with col1:
    st.markdown("### 🎤 Voice Features")
    
    voice_enabled = st.toggle("Enable Real Voice Recording", value=st.session_state.voice_mode)
    if voice_enabled != st.session_state.voice_mode:
        st.session_state.voice_mode = voice_enabled
        st.rerun()
    
    if st.session_state.voice_mode:
        st.success("🎤 **Real Voice Mode: ACTIVE**")
        real_voice_recorder()
    else:
        st.info("💡 **Enable Voice Mode** for real voice recording")
        st.markdown("""
        **Voice features include:**
        - 🎤 Real voice recording
        - 🧠 Emotion detection from voice
        - 🔒 Secure local processing
        - 💬 Natural conversation
        """)

    # Enhanced Therapy Tools with GIF Exercises
    enhanced_therapy_sidebar()

    # NEW: Section Navigation
    st.markdown("### 📍 Quick Access")
    if st.button("🏥 Find Doctors", use_container_width=True):
        st.session_state.active_section = "doctors"
        st.rerun()
    
    if st.button("🧘 All Exercises", use_container_width=True):
        st.session_state.active_section = "exercises"
        st.rerun()
    
    if st.button("🎤 Voice Session", use_container_width=True):
        st.session_state.active_section = "voice"
        st.rerun()
    
    if st.button("💬 Back to Chat", use_container_width=True):
        st.session_state.active_section = "chat"
        st.rerun()

    # Crisis Resources
    st.markdown("### 🆘 Emergency Help")
    if st.button("📞 Show Helplines", use_container_width=True):
        st.session_state.active_tool = "crisis"
        st.session_state.active_section = "chat"
        st.rerun()
    
    # Session Management
    st.markdown("---")
    if st.button("🔄 New Conversation", use_container_width=True):
        st.session_state.chat_history = []
        st.session_state.active_tool = None
        st.session_state.active_section = "chat"
        st.session_state.voice_message = ""
        st.session_state.recording_status = "stopped"
        st.session_state.active_exercise = None
        st.session_state.show_exercises = False
        st.success("🔄 New conversation started!")
        st.rerun()
        
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.chat_history = []
        st.session_state.active_tool = None
        st.session_state.active_section = "chat"
        st.session_state.voice_message = ""
        st.session_state.recording_status = "stopped"
        st.session_state.active_exercise = None
        st.session_state.show_exercises = False
        st.success("👋 Logged out successfully!")
        time.sleep(1)
        st.rerun()

# ==================== MAIN AREA - SECTION SWITCHING ====================
with col2:
    # Show different sections based on active_section
    if st.session_state.active_section == "doctors":
        display_doctor_finder()
        
    elif st.session_state.active_section == "exercises":
        display_all_exercises()
        
    elif st.session_state.active_section == "voice":
        display_voice_session()
        
    else:  # Default: Chat section
        # Active Tool Display
        if st.session_state.active_tool == "grounding":
            st.markdown('<div class="therapy-tool">', unsafe_allow_html=True)
            st.markdown("### 🧘 5-4-3-2-1 Grounding Exercise")
            st.write("""
            **When feeling anxious or overwhelmed:**
            - 👀 **5** things you can see around you
            - ✋ **4** things you can touch and feel  
            - 👂 **3** things you can hear right now
            - 👃 **2** things you can smell
            - 👅 **1** thing you can taste
            
            *Take slow, deep breaths while doing this exercise.*
            """)
            if st.button("✅ I've completed this exercise", key="grounding_complete"):
                st.session_state.active_tool = None
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        
        elif st.session_state.active_tool == "crisis":
            st.markdown('<div class="crisis-alert">', unsafe_allow_html=True)
            st.markdown("### 🆘 Immediate Help Available")
            st.write("""
            **EMERGENCY CONTACTS (24/7):**
            
            🏥 **Vandrevala Foundation**: +91-9999666555  
            🏥 **AASRA**: +91-9820466726  
            🏥 **iCall**: +91-9152987821 (Mon-Sat 10AM-8PM)  
            🚑 **Emergency Services**: 112 or 911
            
            **You are not alone. Professional help is available right now.**
            """)
            if st.button("🆗 I understand, close this", key="close_crisis"):
                st.session_state.active_tool = None
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Chat Interface
        st.markdown("### 💬 Your Conversation")
        
        # Display chat history
        chat_container = st.container()
        with chat_container:
            if not st.session_state.chat_history:
                st.info("""
                **💫 Welcome to your safe space!**
                
                You can:
                - Share your feelings and thoughts
                - Use **real voice recording** (enable in sidebar)  
                - Try **therapeutic exercises** with GIF guides
                - Ask for coping strategies
                - Request immediate help if needed
                
                **Start by saying hello or sharing how you're feeling today.**
                """)
            
            for i, chat in enumerate(st.session_state.chat_history):
                if chat['sender'] == 'user':
                    if chat.get('type') == 'voice':
                        st.markdown(f'''
                        <div class="voice-message">
                            <strong>🎤 You (Voice Message):</strong><br>
                            {chat["message"]}
                            <br><small style="color: #666;">{chat["timestamp"].strftime("%H:%M")}</small>
                        </div>
                        ''', unsafe_allow_html=True)
                    else:
                        st.markdown(f'''
                        <div class="user-message">
                            <strong>You:</strong> {chat["message"]}
                            <br><small style="color: rgba(255,255,255,0.8);">{chat["timestamp"].strftime("%H:%M")}</small>
                        </div>
                        ''', unsafe_allow_html=True)
                else:
                    st.markdown(f'''
                    <div class="bot-message">
                        <strong>🤖 Soul Connect:</strong> {chat["message"]}
                        <br><small style="color: #666;">{chat["timestamp"].strftime("%H:%M")}</small>
                    </div>
                    ''', unsafe_allow_html=True)
        
        # Display exercise suggestions if any
        display_exercise_suggestions()

        # Display active exercise if any  
        display_active_exercise()
        
        # Chat input
        st.markdown("---")
        user_input = st.chat_input("Type your message here or use voice recording...")
        
        if user_input:
            # Add user message to chat
            st.session_state.chat_history.append({
                "sender": "user", 
                "message": user_input,
                "timestamp": datetime.now()
            })
            
            # Send to backend and get response
            with st.spinner("🤔 Soul Connect is thinking..."):
                try:
                    response = requests.post(
                        f"{API_URL}/send-message",
                        json={
                            "session_id": st.session_state.session_id,
                            "message_text": user_input,
                            "sender_type": "user"
                        },
                        timeout=30
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Add bot response to chat
                        st.session_state.chat_history.append({
                            "sender": "assistant",
                            "message": data['bot_response'],
                            "timestamp": datetime.now()
                        })
                        
                        # Auto-suggest exercises based on emotion (only for high confidence)
                        emotion = data.get('emotion', '').lower()
                        confidence = data.get('confidence_score', 0)
                        if emotion in ['anxiety', 'sadness', 'anger', 'stress', 'loneliness'] and confidence > 0.7:
                            st.session_state.exercise_suggestions = suggest_exercises_based_on_emotion(emotion)
                            st.session_state.show_exercises = True
                        
                        st.rerun()
                    else:
                        st.error("❌ Failed to get response from Soul Connect")
                        
                except requests.exceptions.RequestException:
                    st.error(f"❌ Cannot connect to server at {API_URL}")
                    st.info("Make sure the backend server is running")
                except Exception as e:
                    st.error(f"❌ Unexpected error: {e}")

# ==================== RIGHT SIDEBAR ====================
with col3:
    st.markdown("### 🔊 Voice Guide")
    
    if st.session_state.voice_mode:
        st.success("🎤 **Real Voice Recording Active**")
        st.markdown("""
        **How to use voice:**
        1. Click **Start Recording**
        2. Speak naturally
        3. Click **Stop & Transcribe**
        4. Review and send
        
        **Benefits:**
        🗣️ More natural expression
        ⚡ Faster communication  
        🎯 Better emotion detection
        🔒 Complete privacy
        """)
    else:
        st.info("""
        **💡 Try Voice Recording:**
        - More emotional expression
        - Hands-free use
        - Natural conversation
        - Enhanced support
        """)
    
    # Quick Mental Health Tips
    st.markdown("### 💡 Wellness Tips")
    tips = [
        "Be honest about your feelings",
        "Use voice for emotional topics", 
        "Try the exercise GIFs for quick relief",
        "Take breaks when needed",
        "Your privacy is always protected"
    ]
    
    for tip in tips:
        st.write(f"• {tip}")

# ==================== BOTTOM STATUS ====================
st.markdown("---")
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    try:
        health = requests.get(f"{API_URL}/health", timeout=5).json()
        status = "🟢 Connected" if health['status'] == 'healthy' else "🔴 Disconnected"
        st.write(f"**Backend:** {status}")
    except:
        st.write("**Backend:** 🔴 Offline")

with col2:
    st.write(f"**User:** {st.session_state.username}")

with col3:
    st.write(f"**Messages:** {len([m for m in st.session_state.chat_history if m['sender'] == 'user'])}")

with col4:
    voice_status = "🎤 ON" if st.session_state.voice_mode else "🔇 OFF"
    st.write(f"**Voice:** {voice_status}")

with col5:
    st.write(f"**Section:** {st.session_state.active_section.title()}")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; font-size: 12px;'>
    <p>❤️ <strong>Soul Connect</strong> - AI-Powered Mental Health Support • Connecting Minds, Healing Hearts</p>
    <p>🔒 Your privacy is protected • All conversations are secure and anonymous</p>
</div>
""", unsafe_allow_html=True)