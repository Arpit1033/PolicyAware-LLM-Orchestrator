from django.conf import settings
from langchain_google_genai import ChatGoogleGenerativeAI

def get_google_api_key():
    return settings.GOOGLE_API_KEY

def get_llm_model(model=None):
    if model is None:
        model = "gemini-3.1-flash-lite-preview"
    return ChatGoogleGenerativeAI(
        model=model,
        temperature=0,
        max_retries=3,
        google_api_key=get_google_api_key(), 
    )