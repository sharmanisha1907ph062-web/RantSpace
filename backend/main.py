<<<<<<< HEAD
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
=======
"""The FastAPI backend for RantSpace.

Run locally with:
    pip install fastapi "uvicorn[standard]" openai
    uvicorn backend.main:app --reload

Groq integration remains below, and TEMPORARY_MOCK_AI_MODE can be enabled
while the app is being developed without making API requests.
"""

import os
from enum import Enum
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import APIConnectionError, APIStatusError, AsyncOpenAI, AuthenticationError, RateLimitError
from pydantic import BaseModel, Field
from dotenv import load_dotenv


# This file lives in <project root>/backend/, so its parent directory is the
# project root. Using an explicit path means the .env file works no matter
# which directory is used to start the server.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Load local environment variables before anything reads GROQ_API_KEY.
# The key remains in the server process and is never printed or returned.
load_dotenv(PROJECT_ROOT / ".env")


app = FastAPI(
    title="RantSpace API",
    description="A small API for responding to a user's rant.",
    version="0.1.0",
)

# Allow a separately served local frontend to call this local API. This exposes
# only the endpoint; the Groq API key remains in the backend environment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["null"],  # Supports opening index.html directly during local development.
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=False,
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)


class ResponseMode(str, Enum):
    """The four ways RantSpace can respond to a rant."""

    LISTEN = "listen"
    UNDERSTAND = "understand"
    FIGURE_OUT = "figure_out"
    WORDS = "words"


class RantRequest(BaseModel):
    """The data the frontend sends to POST /api/rant."""

    rant: str = Field(
        ...,
        min_length=1,
        max_length=10_000,
        description="The user's rant or thought.",
    )
    mode: ResponseMode = Field(
        ...,
        description="How RantSpace should respond.",
    )


class RantResponse(BaseModel):
    """The data the backend sends back to the frontend."""

    response: str
    mode: ResponseMode


# Set this to True to temporarily use local responses without calling Groq.
TEMPORARY_MOCK_AI_MODE = False

# Groq supports the OpenAI-compatible API at this server-side URL. This is not
# a secret; only GROQ_API_KEY is sensitive and it stays in the environment.
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = "openai/gpt-oss-120b"


# Each mode gives the AI a distinct role when real AI mode is enabled.
MODE_INSTRUCTIONS = {
    # Just Listen
    ResponseMode.LISTEN: (
        "You are a warm, non-judgmental listener. Acknowledge the person's "
        "feelings without trying to solve the problem or giving advice."
    ),
    # Help Me Understand
    ResponseMode.UNDERSTAND: (
        "Help the person understand what they may be feeling and what matters "
        "to them. Reflect patterns gently, without making assumptions or diagnoses."
    ),
    # Advice
    ResponseMode.FIGURE_OUT: (
        "Help the person think through the situation. Offer a small number of "
        "practical, low-pressure next steps or questions they can consider."
    ),
    # Rewrite
    ResponseMode.WORDS: (
        "Help turn the person's thoughts into clear, compassionate words. Offer "
        "a polished version they could use to describe how they feel."
    ),
}


def create_mock_response(rant: str, mode: ResponseMode) -> str:
    """Return a local, mode-specific response without contacting OpenAI."""

    if mode is ResponseMode.LISTEN:
        return f"I hear you. {rant} That sounds important, and you do not have to solve it right now."

    if mode is ResponseMode.UNDERSTAND:
        return (
            "Here is one way to organize what you shared:\n"
            f"- What happened or is bothering you: {rant}\n"
            "- What may be underneath it: there may be frustration, hurt, or pressure involved.\n"
            "- What seems to matter: feeling heard and having clarity about what happens next."
        )

    if mode is ResponseMode.FIGURE_OUT:
        return (
            f"Based on what you shared — \"{rant}\" — here are a few practical options:\n"
            "1. Pause and name the one part that feels most urgent.\n"
            "2. Write down the outcome you would like, even if it is small.\n"
            "3. Choose one low-pressure next step, such as taking a break, asking a question, or talking to someone you trust."
        )

    # The Enum validates mode values, so reaching this point means WORDS.
    return f"Here is a clearer version of what you are saying:\n\n{rant}"


async def create_response(rant: str, mode: ResponseMode) -> str:
    """Return mock text now, or ask Groq when mock mode is disabled."""

    if TEMPORARY_MOCK_AI_MODE:
        return create_mock_response(rant, mode)

    # AsyncOpenAI is the OpenAI-compatible Python client used to call Groq.
    # os.getenv reads only from the server's environment. It never exposes the
    # value to the frontend or includes it in the API response.
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="The AI service is not configured. Set GROQ_API_KEY on the server.",
        )

    instructions = (
        "You are RantSpace, a supportive space for people to express themselves. "
        f"{MODE_INSTRUCTIONS[mode]} "
        "Respond directly to the rant in plain language. Keep it under 180 words. "
        "If the person may be in immediate danger or mentions self-harm, encourage "
        "them to contact local emergency services or a crisis line right away."
    )

    try:
        # AsyncOpenAI keeps this network request from blocking FastAPI's event loop.
        async with AsyncOpenAI(api_key=api_key, base_url=GROQ_BASE_URL) as client:
            result = await client.responses.create(
                model=GROQ_MODEL,
                instructions=instructions,
                input=rant,
                # Rants can be personal, so do not store Responses API data by default.
                store=False,
            )
    except AuthenticationError:
        # Do not reveal the key or provider details to the person using the app.
        raise HTTPException(status_code=503, detail="The Groq service is unavailable.")
    except RateLimitError:
        raise HTTPException(
            status_code=429,
            detail="The Groq service is busy. Please try again in a moment.",
        )
    except APIConnectionError:
        raise HTTPException(
            status_code=503,
            detail="Could not reach the Groq service. Please try again shortly.",
        )
    except APIStatusError:
        raise HTTPException(
            status_code=502,
            detail="The Groq service could not complete the request. Please try again.",
        )

    # output_text is the SDK's safe, convenient way to get the model's text.
    if not result.output_text:
        raise HTTPException(
            status_code=502,
            detail="The Groq service returned an empty response. Please try again.",
        )

    return result.output_text


@app.post("/api/rant", response_model=RantResponse)
@app.post("/api/respond", response_model=RantResponse, include_in_schema=False)
async def respond_to_rant(request: RantRequest) -> RantResponse:
    """Accept a rant and return an AI response in the requested mode."""

    # Reject messages that contain only spaces, even though they have length.
    clean_rant = request.rant.strip()
    if not clean_rant:
        raise HTTPException(status_code=422, detail="The rant cannot be blank.")

    response = await create_response(clean_rant, request.mode)
    return RantResponse(response=response, mode=request.mode)
>>>>>>> master
