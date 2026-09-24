"""The FastAPI backend for RantSpace.

Run locally with:
    pip install fastapi "uvicorn[standard]" anthropic python-dotenv
    uvicorn backend.main:app --reload

This backend calls Anthropic's Claude API to generate real, mode-specific
responses to a user's rant. TEMPORARY_MOCK_AI_MODE can be enabled while the
app is being developed without making API requests.
"""

import os
from enum import Enum
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from anthropic import (
    AsyncAnthropic,
    APIConnectionError,
    APIStatusError,
    AuthenticationError,
    RateLimitError,
)
from pydantic import BaseModel, Field
from dotenv import load_dotenv


# This file lives in <project root>/backend/, so its parent directory is the
# project root. Using an explicit path means the .env file works no matter
# which directory is used to start the server.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Load local environment variables before anything reads ANTHROPIC_API_KEY.
# The key remains in the server process and is never printed or returned.
load_dotenv(PROJECT_ROOT / ".env")


app = FastAPI(
    title="RantSpace API",
    description="A small API for responding to a user's rant.",
    version="0.1.0",
)

# Allow a separately served local frontend to call this local API. This exposes
# only the endpoint; the Anthropic API key remains in the backend environment.
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
    PUT_INTO_WORDS = "put_into_words"


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


# Set this to True to temporarily use local responses without calling Claude.
TEMPORARY_MOCK_AI_MODE = False

# The Claude model used for real responses. Not a secret; only
# ANTHROPIC_API_KEY is sensitive and it stays in the environment.
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")
ANTHROPIC_MAX_TOKENS = 500


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
    ResponseMode.PUT_INTO_WORDS: (
        "Help turn the person's thoughts into clear, compassionate words. Offer "
        "a polished version they could use to describe how they feel."
    ),
}


def create_mock_response(rant: str, mode: ResponseMode) -> str:
    """Return a local, mode-specific response without contacting Claude."""

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

    # The Enum validates mode values, so reaching this point means PUT_INTO_WORDS.
    return f"Here is a clearer version of what you are saying:\n\n{rant}"


async def create_response(rant: str, mode: ResponseMode) -> str:
    """Return mock text now, or ask Claude when mock mode is disabled."""

    if TEMPORARY_MOCK_AI_MODE:
        return create_mock_response(rant, mode)

    # os.getenv reads only from the server's environment. It never exposes the
    # value to the frontend or includes it in the API response.
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="The AI service is not configured. Set ANTHROPIC_API_KEY on the server.",
        )

    system_prompt = (
        "You are RantSpace, a supportive space for people to express themselves. "
        f"{MODE_INSTRUCTIONS[mode]} "
        "Respond directly to the rant in plain language. Keep it under 180 words. "
        "If the person may be in immediate danger or mentions self-harm, encourage "
        "them to contact local emergency services or a crisis line right away."
    )

    try:
        # AsyncAnthropic keeps this network request from blocking FastAPI's event loop.
        async with AsyncAnthropic(api_key=api_key) as client:
            result = await client.messages.create(
                model=ANTHROPIC_MODEL,
                max_tokens=ANTHROPIC_MAX_TOKENS,
                system=system_prompt,
                messages=[{"role": "user", "content": rant}],
            )
    except AuthenticationError:
        # Do not reveal the key or provider details to the person using the app.
        raise HTTPException(status_code=503, detail="The Claude service is unavailable.")
    except RateLimitError:
        raise HTTPException(
            status_code=429,
            detail="The Claude service is busy. Please try again in a moment.",
        )
    except APIConnectionError:
        raise HTTPException(
            status_code=503,
            detail="Could not reach the Claude service. Please try again shortly.",
        )
    except APIStatusError:
        raise HTTPException(
            status_code=502,
            detail="The Claude service could not complete the request. Please try again.",
        )

    # Concatenate the text blocks in the reply. This is the safe, convenient
    # way to get the model's text out of the Messages API response.
    response_text = "".join(
        block.text for block in result.content if block.type == "text"
    ).strip()

    if not response_text:
        raise HTTPException(
            status_code=502,
            detail="The Claude service returned an empty response. Please try again.",
        )

    return response_text


@app.post("/api/rant", response_model=RantResponse)
@app.post("/api/respond", response_model=RantResponse, include_in_schema=False)
async def respond_to_rant(request: RantRequest) -> RantResponse:
    """Accept a rant and return an AI response in the requested mode."""

    # Reject messages that contain only spaces, even though they have length.
    clean_rant = request.rant.strip()
    if not clean_rant:
        raise HTTPException(status_code=422, detail="The rant cannot be blank.")

    # This function's local variables are the only place the rant text lives
    # during a request; nothing here writes it to a file, log, or database.
    response = await create_response(clean_rant, request.mode)
    return RantResponse(response=response, mode=request.mode)
