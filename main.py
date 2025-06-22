import streamlit as st
import speech_recognition as sr
import requests
from gtts import gTTS
import pygame
import os
import string
from threading import Thread
import time

# Initialize pygame mixer
pygame.mixer.init()

# Initialize session state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Global variable for speech thread
speech_thread = None

# API Configuration
OPENROUTER_API_KEY = "Bearer "

# Helper functions
def listen_audio():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
    return audio

def transcribe_audio(audio):
    recognizer = sr.Recognizer()
    try:
        text = recognizer.recognize_google(audio)
        return text
    except sr.UnknownValueError:
        st.error("Could not understand audio.")
    except sr.RequestError as e:
        st.error(f"Speech recognition error: {e}")
    return None

def get_response_from_openrouter(prompt):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": OPENROUTER_API_KEY,
        "HTTP-Referer": "https://localhost:8501",  # Replace with your actual domain
        "X-Title": "Fardeen's J.A.R.V.I.S.",
        "Content-Type": "application/json"
    }
    data = {
        "model": "meta-llama/llama-3.3-70b-instruct:free",  # Updated to use GPT-4 model
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        if response.status_code == 401:
            st.error("Invalid API key. Please check your OpenRouter API key.")
            return None
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        st.error(f"API request failed: {str(e)}")
        return None

def speak_text(text):
    global speech_thread
    text = text.translate(str.maketrans('', '', string.punctuation))
    tts = gTTS(text=text, lang="en")
    filename = "response.mp3"
    tts.save(filename)
    
    def play_sound():
        sound = pygame.mixer.Sound(filename)
        sound.play()
        while pygame.mixer.get_busy():
            time.sleep(0.1)
        os.remove(filename)
    
    speech_thread = Thread(target=play_sound)
    speech_thread.start()

def stop_speech():
    pygame.mixer.stop()

# Streamlit UI
st.set_page_config(page_title="Voice Assistant", page_icon="🎙️", layout="wide")

# Custom CSS for buttons (avoiding interference with status text)
st.markdown("""
<style>
    .stButton>button {
        width: 100%;
        padding: 0.5rem;
        border-radius: 0.5rem;
        font-size: 1.1rem;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: scale(1.05);
    }
    .speak-btn {
        background-color: #4CAF50 !important;
        color: white !important;
    }
    .stop-btn {
        background-color: #f44336 !important;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# Main layout
st.title("🎙️ Fardeen's J.A.R.V.I.S.")
st.markdown("Experience seamless voice interaction with our AI-powered assistant")

# Chat history container
chat_container = st.container()
with chat_container:
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# Control buttons
col1, col2 = st.columns(2)
with col1:
    speak_button = st.button("🎤 Speak", key="speak", help="Click to start speaking", 
                            use_container_width=True, type="primary", 
                            kwargs={"class": "speak-btn"})
with col2:
    stop_button = st.button("⏹️ Stop", key="stop", help="Click to stop speaking", 
                           use_container_width=True, type="secondary", 
                           kwargs={"class": "stop-btn"})

# Status container
status_container = st.empty()

# Main logic
if speak_button:
    # Listening phase
    status_container.markdown(
        "<h3 style='text-align: center; color: #4CAF50;'>🎙️ Listening...</h3>",
        unsafe_allow_html=True
    )
    audio = listen_audio()
    
    # Transcribing phase
    status_container.markdown(
        "<h3 style='text-align: center; color: #FFA500;'>✍️ Transcribing...</h3>",
        unsafe_allow_html=True
    )
    user_input = transcribe_audio(audio)
    
    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        
        # Processing phase
        status_container.markdown(
            "<h3 style='text-align: center; color: #1E90FF;'>🤖 Processing...</h3>",
            unsafe_allow_html=True
        )
        assistant_response = get_response_from_openrouter(user_input)
        
        # Clear status and update UI
        status_container.empty()
        if assistant_response:
            st.session_state.chat_history.append({"role": "assistant", "content": assistant_response})
            speak_text(assistant_response)
            st.rerun()

if stop_button:
    stop_speech()
