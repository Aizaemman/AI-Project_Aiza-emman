from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import joblib
import pandas as pd
import google.generativeai as genai
from dotenv import load_dotenv
import os

app = FastAPI()
load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
chat_model = genai.GenerativeModel("gemini-2.5-flash")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load the newly trained AQI Predictor
try:
    aqi_predictor = joblib.load("model/aqi_predictor.pkl")
except Exception as e:
    print("Warning: aqi_predictor.pkl not found, future predictions will fail.")
    aqi_predictor = None


class FuturePredictionInput(BaseModel):
    current_aqi: float
    pm25: float
    pm10: float
    temp: float
    humidity: float
    wind_speed: float

class PersonalRiskInput(BaseModel):
    age: int
    has_asthma: bool
    has_copd: bool
    is_smoker: bool
    has_heart_disease: bool
    outdoor_job: bool
    current_pm25: float
    city: str

class ChatRequest(BaseModel):
    message: str


@app.get("/")
def home():
    return {"message": "AirSense Pakistan AI Backend is running"}


@app.post("/predict_future")
def predict_future_aqi(data: FuturePredictionInput):
    if aqi_predictor is None:
        return {"error": "Model not loaded"}
    
    input_df = pd.DataFrame([{
        "current_aqi": data.current_aqi,
        "pm25": data.pm25,
        "pm10": data.pm10,
        "temp": data.temp,
        "humidity": data.humidity,
        "wind_speed": data.wind_speed
    }])
    
    predictions = aqi_predictor.predict(input_df)[0]
    
    return {
        "aqi_6h": float(predictions[0]),
        "aqi_24h": float(predictions[1])
    }


@app.post("/predict")
def predict_personal_risk(data: PersonalRiskInput):
    try:
        risk_score = 0

        # PM2.5 Risk
        if data.current_pm25 <= 12:
            risk_score += 0
        elif data.current_pm25 <= 35:
            risk_score += 1
        elif data.current_pm25 <= 55:
            risk_score += 2
        elif data.current_pm25 <= 150:
            risk_score += 3
        else:
            risk_score += 5

        # Age Risk
        if data.age < 5:
            risk_score += 2
        elif data.age >= 65:
            risk_score += 2
        elif data.age >= 50:
            risk_score += 1

        # Medical Conditions
        if data.has_asthma:
            risk_score += 2

        if data.has_copd:
            risk_score += 3

        if data.has_heart_disease:
            risk_score += 3

        if data.is_smoker:
            risk_score += 1

        # Outdoor Work Risk
        if data.outdoor_job and data.current_pm25 > 55:
            risk_score += 1

        # Final Classification
        if risk_score <= 2:
            risk = "Low Risk"
            recommendation = (
                f"Air quality in {data.city} is generally acceptable for your profile. "
                "You may continue normal outdoor activities."
            )

        elif risk_score <= 5:
            risk = "Moderate Risk"
            recommendation = (
                f"Air quality in {data.city} may cause mild discomfort during long outdoor exposure. "
                "Consider reducing prolonged outdoor activity and stay hydrated."
            )

        elif risk_score <= 8:
            risk = "High Risk"
            recommendation = (
                f"Air quality in {data.city} may affect your health. "
                "Limit outdoor exposure and wear an N95 mask when outdoors."
            )

        else:
            risk = "Severe Risk"
            recommendation = (
                f"Air quality in {data.city} is unhealthy for your profile. "
                "Avoid outdoor exposure whenever possible and use respiratory protection."
            )

        return {
            "predicted_risk": risk,
            "recommendation": recommendation,
            "risk_score": risk_score
        }

    except Exception as e:
        print(f"Risk Calculation Error: {e}")

        return {
            "predicted_risk": "Moderate Risk",
            "recommendation": "Unable to calculate exact risk. Please monitor air quality conditions."
        }
@app.post("/chat")
def chatbot(request: ChatRequest):
    try:
        response = chat_model.generate_content(
            f"""
            You are "AirSense Pakistan AI Health Assistant", an intelligent and professional AI assistant.
            You can answer questions related to:
            - Air quality, PM2.5, smog, pollution comparisons between cities like Lahore and Karachi
            - Health risks, asthma, outdoor activity safety, mask recommendations (like N95)
            - Environmental alerts
            
            Keep answers short (2-3 sentences max), empathetic, and professional.
            User: {request.message}
            """
        )
        return {"reply": response.text}
    except Exception as e:
        return {"reply": "I am experiencing network issues right now. Please monitor your local AQI and stay safe."}