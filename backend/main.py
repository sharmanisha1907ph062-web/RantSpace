import os
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq


# Load environment variables
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY is not set")


# Create Groq client
client = Groq(api_key=GROQ_API_KEY)


# Create FastAPI app
app = FastAPI(title="RantSpace API")


# Allow frontend to communicate with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RantRequest(BaseModel):
    rant: str
    mode: str


@app.get("/")
def home():
    return {"message": "RantSpace backend is running"}


@app.post("/api/rant")
def generate_response(request: RantRequest):

    if not request.rant.strip():
        raise HTTPException(
            status_code=400,
            detail="Please enter something first."
        )

    mode_prompts = {
        "listen": """
You are in Just Listen mode.

The user wants to be heard, not advised.

Respond with empathy and acknowledgement.
Do not give unsolicited advice.
Do not diagnose.
Do not judge.
Keep the response warm, natural and human.
""",

        "understand": """
You are in Help Me Understand mode.

Help the user make sense of what they wrote.
Identify emotions, thoughts, conflicts, concerns or patterns that are clearly present.

Do not diagnose mental health conditions.
Do not pretend to know things the user did not say.
Use phrases such as "It sounds like..." when appropriate.
Be clear and compassionate.
""",

        "figure_out": """
You are in Help Me Figure It Out mode.

Help the user think through their situation.
Offer practical options, possible next steps and trade-offs.
Do not make the decision for them.
Do not judge them.
Keep the advice realistic and actionable.
""",

        "put_into_words": """
You are in Put It Into Words mode.

Rewrite the user's thoughts clearly and naturally while preserving their original meaning and emotions.

Do not add facts or feelings that were not present.
Do not change what the user is trying to say.
Make the writing feel authentic rather than overly formal.
"""
    }

    system_prompt = mode_prompts.get(
        request.mode,
        mode_prompts["listen"]
    )

    # Basic safety check
    safety_words = [
        "kill myself",
        "suicide",
        "end my life",
        "want to die",
        "hurt myself"
    ]

    rant_lower = request.rant.lower()

    if any(word in rant_lower for word in safety_words):
        return {
            "response": (
                "I'm really sorry you're dealing with something this heavy. "
                "If you might hurt yourself or are in immediate danger, "
                "please contact local emergency services or reach out to "
                "someone you trust who can stay with you right now."
            )
        }

    try:
        completion = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": request.rant
                }
            ],
            temperature=0.7,
            max_tokens=500
        )

        response_text = completion.choices[0].message.content

        return {
            "response": response_text
        }

    except Exception as e:
        print("Groq API error:", e)

        raise HTTPException(
            status_code=500,
            detail="Unable to generate a response right now."
        )
