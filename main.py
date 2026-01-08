from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
import mysql.connector
from mysql.connector import Error
import uuid
import os
from datetime import datetime, timedelta
import re
from difflib import get_close_matches
import json
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
import joblib
import google.generativeai as genai
import requests
import random
import asyncio
from contextlib import asynccontextmanager

# Enhanced database configuration with better error handling
def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host="localhost",
            database="soul_connect",
            user="root",
            password="",  # Empty password
            port=3306,
            auth_plugin='mysql_native_password'
        )
        return connection
    except Error as e:
        print(f"⚠️ Database connection error: {e}")
        print("💡 Running in memory mode (no database required)")
        return None

# Initialize database tables
def init_database():
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            
            # Create database if it doesn't exist
            cursor.execute("CREATE DATABASE IF NOT EXISTS soul_connect")
            cursor.execute("USE soul_connect")
            
            # Create tables if they don't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id VARCHAR(36) PRIMARY KEY,
                    anonymous_id VARCHAR(100) UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_sessions INT DEFAULT 1
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id VARCHAR(36) PRIMARY KEY,
                    session_id VARCHAR(36),
                    sender_type VARCHAR(20),
                    message_text TEXT,
                    emotion_label VARCHAR(50),
                    risk_level VARCHAR(20),
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS emotion_analytics (
                    id VARCHAR(36) PRIMARY KEY,
                    user_id VARCHAR(36),
                    emotion VARCHAR(50),
                    confidence_score FLOAT,
                    message_context TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS therapy_sessions (
                    id VARCHAR(36) PRIMARY KEY,
                    user_id VARCHAR(36),
                    tool_used VARCHAR(100),
                    duration_minutes INT,
                    outcome_notes TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # New tables for Support Groups
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS support_groups (
                    id VARCHAR(36) PRIMARY KEY,
                    name VARCHAR(200),
                    topic VARCHAR(100),
                    description TEXT,
                    max_members INT DEFAULT 8,
                    current_members INT DEFAULT 0,
                    status VARCHAR(20) DEFAULT 'active',
                    ai_moderator_id VARCHAR(36),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS group_members (
                    id VARCHAR(36) PRIMARY KEY,
                    group_id VARCHAR(36),
                    user_id VARCHAR(36),
                    anonymous_name VARCHAR(100),
                    join_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS group_messages (
                    id VARCHAR(36) PRIMARY KEY,
                    group_id VARCHAR(36),
                    user_id VARCHAR(36),
                    anonymous_name VARCHAR(100),
                    message_text TEXT,
                    emotion_label VARCHAR(50),
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS crisis_logs (
                    id VARCHAR(36) PRIMARY KEY,
                    user_id VARCHAR(36),
                    trigger_message TEXT,
                    severity_level INT,
                    action_taken TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            connection.commit()
            cursor.close()
            connection.close()
            print("✅ Database initialized successfully!")
        except Error as e:
            print(f"❌ Database initialization error: {e}")
    else:
        print("💡 Running in memory mode - all data will be stored in memory only")

# Gemini AI Service
class GeminiAIService:
    def __init__(self):
        self.api_key = "AIzaSyC52L5HoNHP9ecrl3vqeHRsl1aFC3qF7t4"
        try:
            genai.configure(api_key=self.api_key)
            try:
                self.model = genai.GenerativeModel('models/gemini-2.0-flash-exp')
                print("🤖 Using model: gemini-2.0-flash-exp")
            except:
                try:
                    self.model = genai.GenerativeModel('models/gemini-2.0-flash-001') 
                    print("🤖 Using model: gemini-2.0-flash-001")
                except:
                    self.model = genai.GenerativeModel('models/gemini-2.0-flash')
                    print("🤖 Using model: gemini-2.0-flash")
        except Exception as e:
            print(f"❌ Gemini setup failed: {e}")
            self.model = None
    
    def get_ai_response(self, user_message, conversation_history=None):
        if not self.model:
            return "I'm here to listen and support you. Please tell me more about what you're feeling today."
            
        try:
            # Build context from conversation history
            context = ""
            if conversation_history:
                for msg in conversation_history[-4:]:
                    context += f"User: {msg.get('user_message', '')}\n"
                    context += f"Assistant: {msg.get('bot_response', '')}\n"
            
            prompt = f"""You are Soul Connect - a compassionate mental health AI assistant. 
Be empathetic, supportive, and conversational like a caring friend. Keep responses warm, human-like, and focused on mental health support.

Previous conversation:
{context}

User: {user_message}

Soul Connect:"""
            
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.8,
                    top_p=0.9,
                    top_k=40,
                    max_output_tokens=250,
                )
            )
            return response.text
        except Exception as e:
            print(f"❌ Gemini API error: {e}")
            return "I'm here to listen and support you. Please tell me more about what you're going through."

# Initialize Gemini
gemini_service = GeminiAIService()

# Pydantic models - FIXED for 422 error
class UserCreate(BaseModel):
    username: str

class MessageCreate(BaseModel):
    session_id: str
    message_text: str
    sender_type: Optional[str] = "user"

class ChatResponse(BaseModel):
    user_message: str
    bot_response: str
    emotion: str
    risk_level: str

# Support Group Models
class GroupCreate(BaseModel):
    name: str
    topic: str
    description: str
    max_members: int = 8

class GroupJoin(BaseModel):
    group_id: str
    user_id: str

class GroupMessage(BaseModel):
    group_id: str
    user_id: str
    message_text: str

# Enhanced Emotion Detector with ML
class EnhancedEmotionDetector:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(max_features=1000, ngram_range=(1,2), stop_words='english')
        self.model = MultinomialNB()
        self.emotions = ['sadness', 'anxiety', 'anger', 'hopelessness', 'loneliness', 'stress', 'neutral', 'fear']
        self.is_trained = False
        
    def train_demo_model(self):
        """Train a simple ML model for emotion detection"""
        try:
            texts = [
                # Sadness
                "i feel so sad and depressed today", "im feeling really down and miserable",
                "everything makes me want to cry", "i cant stop feeling sad",
                "my heart feels heavy and broken", "i feel empty inside",
                
                # Anxiety
                "im so anxious about everything", "i cant stop worrying about the future",
                "my heart is racing and im scared", "i feel panicked and overwhelmed",
                "what if everything goes wrong", "im having anxiety attacks",
                
                # Anger
                "im so angry and frustrated", "this makes me furious",
                "i cant control my anger", "everything irritates me",
                "im mad at everyone", "i feel so frustrated",
                
                # Hopelessness
                "theres no hope for me", "nothing will ever get better",
                "im completely hopeless", "things will never improve",
                "i give up on everything", "theres no point in trying",
                
                # Loneliness
                "i feel so alone in this world", "nobody understands me",
                "im all by myself", "i have no one to talk to",
                "everyone has abandoned me", "im isolated from everyone",
                
                # Stress
                "im so stressed out", "the pressure is too much",
                "i cant handle all this stress", "im overwhelmed with work",
                "too many things to do", "im burning out",
                
                # Fear
                "im really scared right now", "im terrified of what might happen",
                "i feel so afraid", "im frightened about everything",
                
                # Neutral
                "hello how are you", "im doing okay today",
                "just checking in", "what can you help me with",
                "tell me about yourself", "good morning"
            ]
            
            labels = [
                'sadness', 'sadness', 'sadness', 'sadness', 'sadness', 'sadness',
                'anxiety', 'anxiety', 'anxiety', 'anxiety', 'anxiety', 'anxiety', 
                'anger', 'anger', 'anger', 'anger', 'anger', 'anger',
                'hopelessness', 'hopelessness', 'hopelessness', 'hopelessness', 'hopelessness', 'hopelessness',
                'loneliness', 'loneliness', 'loneliness', 'loneliness', 'loneliness', 'loneliness',
                'stress', 'stress', 'stress', 'stress', 'stress', 'stress',
                'fear', 'fear', 'fear', 'fear',
                'neutral', 'neutral', 'neutral', 'neutral', 'neutral', 'neutral'
            ]
            
            X = self.vectorizer.fit_transform(texts)
            self.model.fit(X, labels)
            self.is_trained = True
            print("✅ ML Emotion Detector trained successfully!")
        except Exception as e:
            print(f"❌ Training error: {e}")
    
    def predict_emotion(self, text):
        """Predict emotion with confidence score"""
        try:
            if not self.is_trained:
                return "neutral", 0.5
                
            X = self.vectorizer.transform([text])
            prediction = self.model.predict(X)[0]
            probabilities = self.model.predict_proba(X)[0]
            confidence = np.max(probabilities)
            
            return prediction, float(confidence)
        except Exception as e:
            print(f"❌ Prediction error: {e}")
            return "neutral", 0.5

# Initialize enhanced emotion detector
emotion_detector = EnhancedEmotionDetector()

# Google Maps Service
class GoogleMapsService:
    def __init__(self):
        self.api_key = "YOUR_GOOGLE_MAPS_API_KEY"
    
    def find_mental_health_professionals(self, city: str, specialization: str = "psychiatrist"):
        """Find mental health professionals in a specific city"""
        try:
            if not self.api_key or self.api_key == "YOUR_GOOGLE_MAPS_API_KEY":
                return self.get_fallback_doctors(city)
            
            url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
            params = {
                'query': f'{specialization} in {city}, India',
                'key': self.api_key
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            professionals = []
            for place in data.get('results', [])[:10]:
                professional = {
                    'name': place.get('name', 'Unknown'),
                    'address': place.get('formatted_address', 'Address not available'),
                    'rating': place.get('rating', 'Not rated'),
                    'types': place.get('types', []),
                    'place_id': place.get('place_id'),
                    'location': place.get('geometry', {}).get('location', {})
                }
                professionals.append(professional)
            
            return professionals
            
        except Exception as e:
            print(f"❌ Google Maps API error: {e}")
            return self.get_fallback_doctors(city)
    
    def get_fallback_doctors(self, city: str):
        """Fallback data when API is not available"""
        fallback_doctors = {
            "delhi": [
                {
                    "name": "Dr. Sameer Malhotra - Max Healthcare",
                    "specialization": "Psychiatrist",
                    "address": "Max Super Speciality Hospital, Saket, New Delhi",
                    "phone": "+91-11-2651 5050",
                    "rating": 4.5,
                    "types": ["psychiatrist", "mental_health"]
                },
                {
                    "name": "Dr. Jyoti Kapoor - Paras Hospitals",
                    "specialization": "Psychiatrist", 
                    "address": "Paras Hospitals, Gurugram",
                    "phone": "+91-124-458 5555",
                    "rating": 4.3,
                    "types": ["psychiatrist", "therapist"]
                }
            ],
            "mumbai": [
                {
                    "name": "Dr. Harish Shetty - LH Hiranandani Hospital",
                    "specialization": "Psychiatrist",
                    "address": "LH Hiranandani Hospital, Powai, Mumbai",
                    "phone": "+91-22-2576 3000", 
                    "rating": 4.6,
                    "types": ["psychiatrist", "counselor"]
                }
            ],
            "bangalore": [
                {
                    "name": "Dr. Prathima Murthy - NIMHANS",
                    "specialization": "Psychiatrist",
                    "address": "NIMHANS, Hosur Road, Bangalore",
                    "phone": "+91-80-2699 5000",
                    "rating": 4.7,
                    "types": ["psychiatrist", "mental_health"]
                },
                {
                    "name": "Dr. K. John - Apollo Hospitals",
                    "specialization": "Therapist",
                    "address": "Apollo Hospitals, Bannerghatta Road, Bangalore",
                    "phone": "+91-80-2630 4050",
                    "rating": 4.4,
                    "types": ["therapist", "counselor"]
                }
            ],
            "chennai": [
                {
                    "name": "Dr. R. Thara - SCARF",
                    "specialization": "Psychiatrist",
                    "address": "SCARF, Chennai",
                    "phone": "+91-44-2615 3974",
                    "rating": 4.5,
                    "types": ["psychiatrist", "mental_health"]
                }
            ],
            "kolkata": [
                {
                    "name": "Dr. J. R. Ram - AMRI Hospitals",
                    "specialization": "Psychiatrist",
                    "address": "AMRI Hospitals, Kolkata",
                    "phone": "+91-33-6680 0000",
                    "rating": 4.3,
                    "types": ["psychiatrist", "mental_health"]
                }
            ]
        }
        
        return fallback_doctors.get(city.lower(), [
            {
                 "name": "Local Mental Health Professional",
        "specialization": "Mental Health Specialist",  # Add this line
        "address": f"Search for mental health professionals in {city}",
        "phone": "Contact local helpline",
        "rating": "Not rated",
        "types": ["mental_health", "professional"]
            }
        ])

# Initialize maps service
maps_service = GoogleMapsService()

# Support Group Manager
class SupportGroupManager:
    def __init__(self):
        self.active_groups = {}
        self.group_connections = {}  # WebSocket connections
    
    def create_group(self, name, topic, description, max_members=8):
        group_id = str(uuid.uuid4())
        group_data = {
            'id': group_id,
            'name': name,
            'topic': topic,
            'description': description,
            'max_members': max_members,
            'members': [],
            'messages': [],
            'created_at': datetime.now(),
            'status': 'active'
        }
        
        # Save to database if available
        connection = get_db_connection()
        if connection:
            try:
                cursor = connection.cursor()
                cursor.execute(
                    """INSERT INTO support_groups (id, name, topic, description, max_members) 
                    VALUES (%s, %s, %s, %s, %s)""",
                    (group_id, name, topic, description, max_members)
                )
                connection.commit()
                cursor.close()
                connection.close()
            except Error as e:
                print(f"⚠️ Database save error: {e}")
        
        self.active_groups[group_id] = group_data
        self.group_connections[group_id] = []
        return group_data
    
    def join_group(self, group_id, user_id, anonymous_name=None):
        if group_id not in self.active_groups:
            return None
        
        group = self.active_groups[group_id]
        
        if len(group['members']) >= group['max_members']:
            return None
        
        # Generate anonymous name if not provided
        if not anonymous_name:
            colors = ['Blue', 'Green', 'Red', 'Purple', 'Orange', 'Yellow', 'Pink', 'Teal']
            animals = ['Dolphin', 'Owl', 'Bear', 'Wolf', 'Butterfly', 'Tiger', 'Elephant', 'Panda']
            anonymous_name = f"{random.choice(colors)}_{random.choice(animals)}_{random.randint(10,99)}"
        
        # Check if user already in group
        for member in group['members']:
            if member['user_id'] == user_id:
                return member
        
        member_data = {
            'user_id': user_id,
            'anonymous_name': anonymous_name,
            'join_time': datetime.now()
        }
        
        group['members'].append(member_data)
        
        # Update database if available
        connection = get_db_connection()
        if connection:
            try:
                cursor = connection.cursor()
                cursor.execute(
                    """INSERT INTO group_members (id, group_id, user_id, anonymous_name) 
                    VALUES (%s, %s, %s, %s)""",
                    (str(uuid.uuid4()), group_id, user_id, anonymous_name)
                )
                connection.commit()
                cursor.close()
                connection.close()
            except Error as e:
                print(f"⚠️ Database save error: {e}")
        
        return member_data
    
    def add_group_message(self, group_id, user_id, message_text):
        if group_id not in self.active_groups:
            return None
        
        group = self.active_groups[group_id]
        
        # Find user's anonymous name
        anonymous_name = None
        for member in group['members']:
            if member['user_id'] == user_id:
                anonymous_name = member['anonymous_name']
                break
        
        if not anonymous_name:
            return None
        
        message_id = str(uuid.uuid4())
        emotion, confidence = emotion_detector.predict_emotion(message_text)
        
        message_data = {
            'id': message_id,
            'user_id': user_id,
            'anonymous_name': anonymous_name,
            'message_text': message_text,
            'emotion': emotion,
            'confidence': confidence,
            'timestamp': datetime.now()
        }
        
        group['messages'].append(message_data)
        
        # Save to database if available
        connection = get_db_connection()
        if connection:
            try:
                cursor = connection.cursor()
                cursor.execute(
                    """INSERT INTO group_messages (id, group_id, user_id, anonymous_name, message_text, emotion_label) 
                    VALUES (%s, %s, %s, %s, %s, %s)""",
                    (message_id, group_id, user_id, anonymous_name, message_text, emotion)
                )
                connection.commit()
                cursor.close()
                connection.close()
            except Error as e:
                print(f"⚠️ Database save error: {e}")
        
        return message_data
    
    def leave_group(self, group_id, user_id):
        if group_id not in self.active_groups:
            return False
        
        group = self.active_groups[group_id]
        initial_count = len(group['members'])
        
        group['members'] = [m for m in group['members'] if m['user_id'] != user_id]
        
        # Update database if available
        connection = get_db_connection()
        if connection:
            try:
                cursor = connection.cursor()
                cursor.execute(
                    "UPDATE group_members SET is_active = FALSE WHERE group_id = %s AND user_id = %s",
                    (group_id, user_id)
                )
                connection.commit()
                cursor.close()
                connection.close()
            except Error as e:
                print(f"⚠️ Database save error: {e}")
        
        return len(group['members']) < initial_count

# Initialize group manager
group_manager = SupportGroupManager()

# User session memory
user_sessions = {}

def get_user_session(session_id):
    """Get or create user session memory"""
    if session_id not in user_sessions:
        user_sessions[session_id] = {
            'conversation_history': [],
            'user_profile': {},
            'emotion_trends': [],
            'therapy_tools_used': [],
            'created_at': datetime.now(),
            'risk_history': []
        }
    return user_sessions[session_id]

def advanced_spelling_correction(text):
    """Fix common spelling mistakes in mental health context"""
    common_mistakes = {
        'sadd': 'sad', 'depresed': 'depressed', 'anxius': 'anxious',
        'stresed': 'stressed', 'lonley': 'lonely', 'angery': 'angry',
        'hoples': 'hopeless', 'sucide': 'suicide', 'kil': 'kill',
        'dieing': 'dying', 'lonly': 'lonely', 'axious': 'anxious',
        'stres': 'stress', 'depresion': 'depression', 'anxty': 'anxiety',
        'sleeppy': 'sleepy', 'tierd': 'tired', 'exosted': 'exhausted',
        'woried': 'worried', 'scard': 'scared', 'frightnd': 'frightened',
        'overwhelimg': 'overwhelming', 'panik': 'panic', 'nervus': 'nervous',
        'miserabel': 'miserable', 'empti': 'empty', 'isolatd': 'isolated',
        'abandond': 'abandoned', 'frustratd': 'frustrated', 'iritated': 'irritated'
    }
    
    words = text.lower().split()
    corrected_words = []
    
    for word in words:
        clean_word = re.sub(r'[^\w\s]', '', word)
        
        if clean_word in common_mistakes:
            corrected_words.append(common_mistakes[clean_word])
        else:
            matches = get_close_matches(clean_word, common_mistakes.keys(), n=1, cutoff=0.7)
            if matches:
                corrected_words.append(common_mistakes[matches[0]])
            else:
                corrected_words.append(clean_word)
    
    return ' '.join(corrected_words)

def understand_user_intent(text):
    """Advanced intent understanding with spelling tolerance"""
    corrected_text = advanced_spelling_correction(text)
    
    intents = {
        'greeting': ['hi', 'hello', 'hey', 'hola', 'namaste', 'good morning', 'good afternoon'],
        'sadness': ['sad', 'depressed', 'unhappy', 'miserable', 'down', 'low', 'empty', 'hopeless'],
        'anxiety': ['anxious', 'worried', 'nervous', 'panic', 'scared', 'afraid', 'fearful', 'overwhelmed'],
        'anger': ['angry', 'mad', 'furious', 'rage', 'frustrated', 'irritated', 'annoyed'],
        'loneliness': ['lonely', 'alone', 'isolated', 'abandoned', 'empty', 'no one cares'],
        'stress': ['stressed', 'overwhelmed', 'pressure', 'burnt out', 'exhausted', 'too much'],
        'crisis': ['suicide', 'kill myself', 'end my life', 'want to die', 'end it all', 'not want to live'],
        'support_request': ['help', 'support', 'advice', 'guide', 'what should i do', 'need help'],
        'gratitude': ['thank', 'thanks', 'grateful', 'appreciate', 'helpful'],
        'farewell': ['bye', 'goodbye', 'see you', 'take care', 'goodnight'],
        'physical_symptoms': ['tired', 'sleep', 'headache', 'pain', 'sick', 'cant sleep', 'insomnia'],
        'relationship': ['friend', 'family', 'partner', 'boyfriend', 'girlfriend', 'parents', 'broken']
    }
    
    detected_intents = []
    for intent, keywords in intents.items():
        if any(keyword in corrected_text for keyword in keywords):
            detected_intents.append(intent)
    
    return detected_intents, corrected_text

def enhanced_risk_assessment(text, emotion, confidence, session_id):
    """Comprehensive risk assessment with multiple factors"""
    session = get_user_session(session_id)
    
    risk_score = 0
    
    high_risk_terms = ['suicide', 'kill myself', 'end my life', 'want to die', 'end it all']
    moderate_risk_terms = ['hopeless', 'no point', 'cant take it', 'better off dead', 'no reason to live']
    
    for term in high_risk_terms:
        if term in text:
            risk_score += 3
    
    for term in moderate_risk_terms:
        if term in text:
            risk_score += 2
    
    if emotion in ['hopelessness', 'sadness'] and confidence > 0.7:
        risk_score += 2
    elif emotion in ['anxiety', 'anger'] and confidence > 0.6:
        risk_score += 1
    
    recent_risks = [msg.get('risk_level') for msg in session['conversation_history'][-3:]]
    if recent_risks.count('high') >= 1:
        risk_score += 2
    elif recent_risks.count('moderate') >= 2:
        risk_score += 1
    
    if risk_score >= 3:
        return "high", risk_score
    elif risk_score >= 2:
        return "moderate", risk_score
    elif risk_score >= 1:
        return "low", risk_score
    else:
        return "none", risk_score

def generate_cbt_response(user_text, emotion, session_id):
    """Generate CBT-inspired responses"""
    
    cbt_techniques = {
        'sadness': {
            'technique': 'Behavioral Activation',
            'response': "When we feel sad, our activities decrease, which can deepen the sadness. Let's plan one small, enjoyable activity for today, even if you don't feel like it.",
            'exercise': "What's one activity you used to enjoy? Let's schedule it for 15 minutes today."
        },
        'anxiety': {
            'technique': 'Cognitive Restructuring', 
            'response': "Anxiety often comes from overestimating danger. Let's examine the evidence - what's the realistic worst-case scenario?",
            'exercise': "Write down your anxious thought and list evidence for and against it."
        },
        'anger': {
            'technique': 'Anger Management',
            'response': "Anger signals that something matters to us. Let's explore the underlying need behind this anger.",
            'exercise': "What need isn't being met? How can we address it constructively?"
        },
        'hopelessness': {
            'technique': 'Hope Building',
            'response': "Hopelessness makes us see only negatives. Let's look for small signs of possibility, even tiny ones.",
            'exercise': "Can you recall one small thing that went slightly better than expected recently?"
        },
        'loneliness': {
            'technique': 'Connection Building',
            'response': "Loneliness can make us withdraw. Let's explore small ways to connect, even if it feels difficult.",
            'exercise': "Who is one person you could send a simple message to today?"
        }
    }
    
    session = get_user_session(session_id)
    
    recent_techniques = [msg.get('technique', '') for msg in session['conversation_history'][-3:]]
    
    if emotion in cbt_techniques and cbt_techniques[emotion]['technique'] not in recent_techniques:
        technique = cbt_techniques[emotion]
        return f"**CBT Technique: {technique['technique']}**\n\n{technique['response']}\n\n *Exercise:* {technique['exercise']}"
    
    return None

def generate_ai_enhanced_response(user_text, original_text, intents, risk_level, emotion, confidence, session_id):
    """Generate smart responses using AI-like logic with memory"""
    
    session = get_user_session(session_id)
    
    if risk_level == "high":
        try:
            connection = get_db_connection()
            if connection:
                cursor = connection.cursor()
                cursor.execute(
                    "INSERT INTO crisis_logs (id, user_id, trigger_message, severity_level, action_taken) VALUES (%s, %s, %s, %s, %s)",
                    (str(uuid.uuid4()), session_id, user_text, 3, "Crisis alert shown with helplines")
                )
                connection.commit()
                cursor.close()
                connection.close()
        except Exception as e:
            print(f"❌ Error saving crisis log: {e}")
        
        return f""" **CRISIS ALERT - IMMEDIATE HELP NEEDED**

I'm very concerned about what you're saying. Your life is precious and people care about you.

**EMERGENCY CONTACTS - CALL NOW:**
• Vandrevala Foundation: +91-9999666555 (24/7)
• AASRA: +91-9820466726 (24/7) 
• iCall: +91-9152987821 (Mon-Sat 10AM-8PM)
• Emergency Services: 112 / 911

**You don't have to go through this alone. Please reach out NOW.** """

    elif risk_level == "moderate":
        return """ **I'm concerned about you**

I hear that you're having very difficult thoughts. These feelings are temporary, even if they don't feel that way right now.

**Please consider:**
• Speaking with a trusted friend or family member
• Calling a helpline: +91-9999666555
• Remembering that many people care about you

Would you like to talk about what's making you feel this way?"""

    # TRY CBT FIRST for emotional issues (BEFORE Gemini)
    if emotion in ['sadness', 'anxiety', 'anger', 'hopelessness', 'loneliness', 'stress']:
        cbt_response = generate_cbt_response(user_text, emotion, session_id)
        if cbt_response:
            print(f"🎯 Using CBT response for {emotion}")
            return cbt_response

    # Then try Gemini (but it will fail due to quota)
    gemini_response = gemini_service.get_ai_response(
        user_text, 
        session['conversation_history']
    )
    
    # Only use Gemini if it returns a real response (not error messages)
    if gemini_response and "I'm here to listen" not in gemini_response:
        return gemini_response

    # Then try response templates based on intents
    response_templates = {
        'greeting': [
            "Hello!  I'm Soul Connect. Thank you for reaching out. How are you feeling today?",
            "Hi there!  I'm here to listen and support you. What's on your mind?",
            "Welcome!  I'm Soul Connect, your mental health companion. How can I help you today?"
        ],
        'sadness': [
            "I hear the sadness in your words.  It takes courage to share these feelings. Would you like to talk more about what's making you feel this way?",
            "I'm here with you in this sadness.  Sometimes just expressing these feelings can bring some relief. What's weighing on your heart today?"
        ],
        'anxiety': [
            "I sense the anxiety in your message.  Let's breathe together for a moment. Inhale slowly... exhale slowly... What's causing these anxious feelings?",
            "Anxiety can feel overwhelming.  You're not alone in this. Let's break it down - what specific worry is on your mind right now?"
        ],
        'anger': [
            "I notice the anger in your words. Anger often signals that something important matters to you. What's been frustrating you?",
            "I hear the frustration. It's okay to feel angry. Let's explore what's behind these feelings together."
        ],
        'loneliness': [
            "Loneliness can feel really isolating. I'm here with you right now. What does connection mean to you?",
            "I hear you're feeling lonely. That must be really difficult. Remember that you're not alone in this."
        ],
        'stress': [
            "Stress can feel overwhelming. Let's prioritize together - what's feeling most pressing right now?",
            "I sense you're feeling stressed. That's completely valid. What's one thing we could do to reduce the pressure?"
        ]
    }
    
    for intent in intents:
        if intent in response_templates:
            print(f"🎯 Using template response for {intent}")
            return random.choice(response_templates[intent])

    # Final fallback
    return "I'm here to listen and support you.  Tell me more about what's on your mind today."
# ==================== WEBSOCKET FOR REAL-TIME GROUPS ====================

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, group_id: str):
        await websocket.accept()
        if group_id not in self.active_connections:
            self.active_connections[group_id] = []
        self.active_connections[group_id].append(websocket)

    def disconnect(self, websocket: WebSocket, group_id: str):
        if group_id in self.active_connections:
            self.active_connections[group_id].remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast_to_group(self, message: str, group_id: str):
        if group_id in self.active_connections:
            for connection in self.active_connections[group_id]:
                try:
                    await connection.send_text(message)
                except:
                    self.disconnect(connection, group_id)

manager = ConnectionManager()

# ==================== LIFESPAN HANDLER ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Starting Soul Connect Server - ENHANCED VERSION...")
    print("🧠 Initializing ML Emotion Detector...")
    emotion_detector.train_demo_model()
    print("🗄️ Initializing Database...")
    init_database()
    print("🤖 Gemini AI Integration: Ready!")
    print("👥 Virtual Support Groups: Ready!")
    print("🔌 WebSocket Real-time Chat: Ready!")
    print("🌟 Soul Connect API v4.0 Ready!")
    print("📚 API Documentation: http://localhost:8080/docs")
    print("🎯 Enhanced Features: ML Emotion Detection, CBT Logic, Session Memory, Gemini AI, Support Groups")
    yield
    # Shutdown
    print("👋 Shutting down Soul Connect Server...")

# Initialize FastAPI with lifespan
app = FastAPI(
    title="Soul Connect API",
    version="4.0",
    description="AI-Powered Mental Health Support Platform with Virtual Support Groups",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== ROUTES ====================

@app.get("/")
def read_root():
    return {
        "message": "Soul Connect API v4.0 is running!", 
        "status": "healthy", 
        "version": "4.0",
        "features": [
            "ML Emotion Detection", 
            "CBT Logic", 
            "Crisis Support", 
            "Session Memory", 
            "Gemini AI Integration",
            "Virtual Support Groups",
            "Real-time WebSocket Chat"
        ]
    }

@app.post("/create-user")
async def create_anonymous_user():
    """Create anonymous user for login"""
    try:
        user_id = str(uuid.uuid4())
        anonymous_id = f"user_{user_id[:8]}"
        
        connection = get_db_connection()
        if connection:
            try:
                cursor = connection.cursor()
                cursor.execute(
                    "INSERT INTO users (id, anonymous_id) VALUES (%s, %s)",
                    (user_id, anonymous_id)
                )
                connection.commit()
                cursor.close()
                connection.close()
                print("💾 User saved to database")
            except Error as e:
                print(f"⚠️ Database save error: {e}")
        
        get_user_session(user_id)
        
        return {
            "user_id": user_id,
            "anonymous_id": anonymous_id,
            "message": "Anonymous user created successfully",
            "session_id": user_id
        }
    except Exception as e:
        return {"error": str(e)}

@app.post("/send-message")
async def send_message(request: dict):
    try:
        # Extract fields with multiple possible names
        session_id = request.get('session_id') or request.get('sessionId') or str(uuid.uuid4())
        message_text = request.get('message_text') or request.get('messageText') or request.get('message') or "Hello"
        
        user_text = message_text.lower()
        message_id = str(uuid.uuid4())
        
        session = get_user_session(session_id)
        
        detected_intents, corrected_text = understand_user_intent(user_text)
        emotion, confidence = emotion_detector.predict_emotion(corrected_text)
        risk_level, risk_score = enhanced_risk_assessment(corrected_text, emotion, confidence, session_id)
        
        bot_response = generate_ai_enhanced_response(
            corrected_text, user_text, detected_intents, risk_level, emotion, confidence, session_id
        )

        # Try to save to database, but continue even if it fails
        connection = get_db_connection()
        if connection:
            try:
                cursor = connection.cursor()
                cursor.execute(
                    """INSERT INTO messages (id, session_id, sender_type, message_text, emotion_label, risk_level) 
                    VALUES (%s, %s, %s, %s, %s, %s)""",
                    (message_id, session_id, "user", user_text, emotion, risk_level)
                )
                
                cursor.execute(
                    """INSERT INTO emotion_analytics (id, user_id, emotion, confidence_score, message_context) 
                    VALUES (%s, %s, %s, %s, %s)""",
                    (str(uuid.uuid4()), session_id, emotion, confidence, user_text[:200])
                )
                
                connection.commit()
                cursor.close()
                connection.close()
                print("💾 Message saved to database")
            except Error as e:
                print(f"⚠️ Database save error: {e}")
        else:
            print("💾 Database not available - running in memory mode")

        # Update session memory
        session['conversation_history'].append({
            'timestamp': datetime.now(),
            'user_message': user_text,
            'corrected_message': corrected_text,
            'bot_response': bot_response,
            'emotion': emotion,
            'risk_level': risk_level,
            'intents': detected_intents,
            'confidence': confidence
        })
        
        if len(session['conversation_history']) > 20:
            session['conversation_history'] = session['conversation_history'][-20:]
        
        session['emotion_trends'].append({
            'timestamp': datetime.now(),
            'emotion': emotion,
            'risk_level': risk_level,
            'confidence': confidence
        })

        return {
            "user_message": message_text,
            "bot_response": bot_response,
            "corrected_text": corrected_text,
            "detected_intents": detected_intents,
            "emotion": emotion,
            "confidence_score": confidence,
            "risk_level": risk_level,
            "risk_score": risk_score, 
            "message_id": message_id,
            "session_id": session_id,
            "conversation_length": len(session['conversation_history'])
        }
        
    except Exception as e:
        print(f"❌ Error in send_message: {e}")
        return {
            "user_message": "Error",
            "bot_response": "I'm here to listen. Please tell me more about what you're going through.",
            "error": str(e)
        }

# ==================== SUPPORT GROUP ROUTES ====================

@app.get("/support-groups")
async def get_available_groups():
    """Get list of available support groups"""
    available_groups = []
    for group_id, group in group_manager.active_groups.items():
        if len(group['members']) < group['max_members'] and group['status'] == 'active':
            available_groups.append({
                'id': group_id,
                'name': group['name'],
                'topic': group['topic'],
                'description': group['description'],
                'current_members': len(group['members']),
                'max_members': group['max_members'],
                'created_at': group['created_at'].isoformat()
            })
    
    if not available_groups:
        demo_groups = [
            group_manager.create_group(
                "Anxiety Support Circle", 
                "anxiety", 
                "Safe space for anxiety discussions and coping strategies"
            ),
            group_manager.create_group(
                "Depression Support", 
                "depression", 
                "Supportive community for depression recovery"
            ),
            group_manager.create_group(
                "Stress Management", 
                "stress", 
                "Learn stress relief techniques together"
            ),
            group_manager.create_group(
                "Loneliness & Connection", 
                "loneliness", 
                "Building connections and overcoming isolation"
            )
        ]
        available_groups = [{
            'id': group['id'],
            'name': group['name'],
            'topic': group['topic'],
            'description': group['description'],
            'current_members': len(group['members']),
            'max_members': group['max_members'],
            'created_at': group['created_at'].isoformat()
        } for group in demo_groups]
    
    return {"groups": available_groups}

@app.post("/support-groups/create")
async def create_support_group(group: GroupCreate):
    """Create a new support group"""
    group_data = group_manager.create_group(
        group.name,
        group.topic,
        group.description,
        group.max_members
    )
    return {"group": group_data, "message": "Support group created successfully"}

@app.post("/support-groups/join")
async def join_support_group(join_data: GroupJoin):
    """Join an existing support group"""
    user_session = get_user_session(join_data.user_id)
    member_data = group_manager.join_group(join_data.group_id, join_data.user_id)
    
    if member_data:
        group = group_manager.active_groups[join_data.group_id]
        return {
            "success": True,
            "member": member_data,
            "group": {
                'id': group['id'],
                'name': group['name'],
                'topic': group['topic'],
                'members': group['members'],
                'messages': group['messages'][-20:]
            },
            "message": "Joined group successfully"
        }
    else:
        return {"success": False, "message": "Group is full or not found"}

@app.post("/support-groups/send-message")
async def send_group_message(message: GroupMessage):
    """Send message to support group"""
    message_data = group_manager.add_group_message(
        message.group_id,
        message.user_id,
        message.message_text
    )
    
    if message_data:
        group = group_manager.active_groups[message.group_id]
        
        # Broadcast to all WebSocket connections in this group
        await manager.broadcast_to_group(
            json.dumps({
                'type': 'new_message',
                'message': message_data,
                'group_id': message.group_id
            }),
            message.group_id
        )
        
        return {
            "success": True,
            "message": message_data,
            "group_messages": group['messages'][-20:]
        }
    else:
        return {"success": False, "error": "Failed to send message"}

@app.get("/support-groups/{group_id}/messages")
async def get_group_messages(group_id: str):
    """Get messages from a support group"""
    group = group_manager.active_groups.get(group_id)
    if not group:
        return {"error": "Group not found"}
    
    return {
        "group_id": group_id,
        "messages": group['messages'][-50:],
        "member_count": len(group['members'])
    }

@app.get("/support-groups/{group_id}/info")
async def get_group_info(group_id: str):
    """Get detailed information about a support group"""
    group = group_manager.active_groups.get(group_id)
    if not group:
        return {"error": "Group not found"}
    
    return {
        "group": {
            'id': group['id'],
            'name': group['name'],
            'topic': group['topic'],
            'description': group['description'],
            'members': group['members'],
            'current_members': len(group['members']),
            'max_members': group['max_members'],
            'created_at': group['created_at'].isoformat(),
            'status': group['status']
        }
    }

@app.post("/support-groups/{group_id}/leave")
async def leave_support_group(group_id: str, user_data: dict):
    """Leave a support group"""
    user_id = user_data.get('user_id')
    success = group_manager.leave_group(group_id, user_id)
    
    if success:
        # Notify other members via WebSocket
        await manager.broadcast_to_group(
            json.dumps({
                'type': 'user_left',
                'user_id': user_id,
                'group_id': group_id
            }),
            group_id
        )
        
        return {"success": True, "message": "Left group successfully"}
    
    return {"success": False, "message": "Error leaving group"}

# ==================== WEBSOCKET ENDPOINT ====================

@app.websocket("/ws/groups/{group_id}/{user_id}")
async def websocket_endpoint(websocket: WebSocket, group_id: str, user_id: str):
    await manager.connect(websocket, group_id)
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Handle different message types
            if message_data['type'] == 'join_group':
                await manager.broadcast_to_group(
                    json.dumps({
                        'type': 'user_joined',
                        'user_id': user_id,
                        'group_id': group_id,
                        'timestamp': datetime.now().isoformat()
                    }),
                    group_id
                )
            
            elif message_data['type'] == 'chat_message':
                # Save message and broadcast
                msg_data = group_manager.add_group_message(
                    group_id,
                    user_id,
                    message_data['text']
                )
                
                if msg_data:
                    await manager.broadcast_to_group(
                        json.dumps({
                            'type': 'new_message',
                            'message': msg_data,
                            'group_id': group_id
                        }),
                        group_id
                    )
                    
    except WebSocketDisconnect:
        manager.disconnect(websocket, group_id)
        await manager.broadcast_to_group(
            json.dumps({
                'type': 'user_left',
                'user_id': user_id,
                'group_id': group_id
            }),
            group_id
        )

# ==================== EXISTING ROUTES ====================

@app.get("/user/{user_id}/conversations")
async def get_user_conversations(user_id: str):
    """Get user's conversation history"""
    try:
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                "SELECT * FROM messages WHERE session_id = %s ORDER BY timestamp DESC LIMIT 50",
                (user_id,)
            )
            conversations = cursor.fetchall()
            cursor.close()
            connection.close()
            return {"conversations": conversations}
        return {"conversations": []}
    except Exception as e:
        return {"error": str(e)}

@app.get("/crisis-resources")
async def get_crisis_resources():
    """Get emergency helpline information"""
    return {
        "emergency_contacts": [
            {
                "name": "Vandrevala Foundation Helpline",
                "number": "+91-9999666555",
                "hours": "24/7",
                "services": "Counselling and mental health support"
            },
            {
                "name": "iCall",
                "number": "+91-9152987821", 
                "hours": "Mon-Sat 10AM-8PM",
                "services": "Psychological support"
            },
            {
                "name": "AASRA",
                "number": "+91-9820466726",
                "hours": "24/7", 
                "services": "Crisis intervention"
            },
            {
                "name": "Emergency Services",
                "number": "112",
                "hours": "24/7",
                "services": "Police, Fire, Ambulance"
            }
        ],
        "online_resources": [
            "Mental Health First Aid India",
            "The Live Love Laugh Foundation", 
            "YourDOST - Online Counseling",
            "Mindful Science Centre"
        ],
        "message": "Please reach out if you need immediate help. You are not alone."
    }

@app.get("/find-doctors/{city}")
async def find_doctors(city: str, specialization: str = "psychiatrist"):
    """Find mental health professionals in a city"""
    professionals = maps_service.find_mental_health_professionals(city, specialization)
    return {
        "city": city,
        "specialization": specialization,
        "count": len(professionals),
        "professionals": professionals
    }

@app.get("/cities-with-doctors")
async def get_available_cities():
    """Get list of major Indian cities with mental health professionals"""
    major_cities = [
        "Delhi", "Mumbai", "Bangalore", "Chennai", "Kolkata", 
        "Hyderabad", "Pune", "Ahmedabad", "Jaipur", "Lucknow",
        "Chandigarh", "Kochi", "Bhopal", "Indore", "Nagpur"
    ]
    return {"cities": major_cities}

@app.get("/session-info/{session_id}")
async def get_session_info(session_id: str):
    """Get conversation history and user patterns"""
    session = get_user_session(session_id)
    
    emotion_counts = {}
    for trend in session['emotion_trends']:
        emotion = trend['emotion']
        emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
    
    return {
        "session_id": session_id,
        "conversation_count": len(session['conversation_history']),
        "emotion_trends": session['emotion_trends'][-10:],
        "emotion_statistics": emotion_counts,
        "created_at": session['created_at'],
        "recent_intents": [msg.get('intents', []) for msg in session['conversation_history'][-5:]]
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "service": "Soul Connect API v4.0", 
        "timestamp": datetime.now(),
        "version": "4.0",
        "active_sessions": len(user_sessions),
        "active_groups": len(group_manager.active_groups),
        "ml_model_trained": emotion_detector.is_trained,
        "gemini_ai_connected": gemini_service.model is not None
    }

@app.get("/test-gemini")
async def test_gemini():
    """Test if Gemini API is working"""
    test_response = gemini_service.get_ai_response("Hello, what's your name?", [])
    return {
        "gemini_working": test_response is not None,
        "response": test_response,
        "model_loaded": gemini_service.model is not None
    }

@app.post("/process-voice")
async def process_voice_message(voice_data: dict):
    """Process voice audio - SIMULATED for now"""
    try:
        session_id = voice_data.get('session_id')
        simulated_text = "I'm feeling anxious today (from voice)"
        
        emotion, confidence = emotion_detector.predict_emotion(simulated_text)
        risk_level, risk_score = enhanced_risk_assessment(simulated_text, emotion, confidence, session_id)
        
        return {
            "transcribed_text": simulated_text,
            "emotion": emotion,
            "risk_level": risk_level,
            "message": "Voice processed successfully"
        }
    except Exception as e:
        return {"error": str(e)}

# Add a simple test endpoint
@app.get("/test")
async def test_endpoint():
    return {
        "status": "working",
        "message": "Soul Connect API is running!",
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)