from google import genai
from google.genai import errors

from .config import get_settings


def generate_nutrition_tip_with_flash(
    username: str,
    age: int,
    weight: float,
    goal: str,
) -> str:
    settings = get_settings()

    # Safe fallback if the API key is missing.
    if not settings.gemini_api_key:
        return (
            "Nutrition tip: Eat regular, balanced meals with a "
            "variety of fruits, vegetables, protein foods, and "
            "whole grains. Drink water regularly. Individual "
            "nutrition needs can vary."
        )

    client = genai.Client(api_key=settings.gemini_api_key)

    prompt = f"""
Give one short, safe, general wellness nutrition tip.

Name: {username}
Age: {age}
Weight in kg: {weight}
Fitness goal: {goal}

Focus on balanced meals, hydration, and sustainable habits.
Do not prescribe restrictive diets, promise weight changes,
or give medical advice. Keep the response friendly and simple.
"""

    try:
        response = client.models.generate_content(
            model=settings.nutrition_model,
            contents=prompt,
        )

        if not response.text:
            raise RuntimeError("Gemini returned an empty nutrition tip.")

        return response.text

    except errors.APIError as exc:
        if exc.code == 429:
            print("Nutrition API quota exceeded. Using fallback tip.")

            return (
                "General nutrition tip: Eat regular, balanced meals "
                "with a variety of fruits, vegetables, protein foods, "
                "and whole grains. Drink water regularly. Choose "
                "habits that support your general wellbeing."
            )

        raise
