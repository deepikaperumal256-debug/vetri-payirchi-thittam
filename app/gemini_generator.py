from google import genai
from google.genai import errors

from .config import get_settings

settings = get_settings()


def _generate(prompt: str, model: str) -> str:
    if not settings.gemini_api_key:
        raise RuntimeError("Gemini API key is not configured.")

    client = genai.Client(api_key=settings.gemini_api_key)

    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
        )
        if not response.text:
            raise RuntimeError("Gemini returned an empty response.")
        return response.text.strip()
    finally:
        client.close()


def demo_workout(goal: str, intensity: str) -> str:
    return f"""
7-DAY FITBUDDY WORKOUT PLAN
Goal: {goal}
Intensity: {intensity}

Day 1 — Full Body
Warm-up: 5 minutes of easy movement.
Workout: Bodyweight squats, wall push-ups, and gentle marching.
Cooldown: Gentle stretching.

Day 2 — Cardio
Warm-up: Easy walking.
Workout: Comfortable walking or cycling for 10–20 minutes.
Cooldown: Slow walking and stretching.

Day 3 — Mobility
Warm-up: Gentle shoulder and ankle movements.
Workout: Beginner mobility exercises and comfortable yoga poses.
Cooldown: Relaxed breathing.

Day 4 — Active Recovery
Workout: Easy walking and gentle stretching.
Recovery: Rest if tired or uncomfortable.

Day 5 — Strength
Warm-up: Easy movement.
Workout: Supported squats, wall push-ups, and glute bridges.
Cooldown: Gentle stretching.

Day 6 — Cardio and Core
Workout: Comfortable walking and beginner core exercises.
Cooldown: Gentle stretching.

Day 7 — Rest and Reflection
Workout: Rest or gentle movement as comfortable.
Recovery: Reflect on what felt manageable.

Safety: This is a general beginner example, not medical advice.
Adjust activity to your ability, take breaks, and stop if you
experience pain, dizziness, or unusual discomfort.
"""


def generate_workout_gemini(
    username: str,
    age: int,
    weight: float,
    goal: str,
    intensity: str,
) -> str:
    prompt = f"""
Create a safe, general seven-day beginner-friendly wellness plan.

Name: {username}
Age: {age}
Weight in kg: {weight}
Goal: {goal}
Preferred intensity: {intensity}

For every day include:
1. Day and focus
2. Gentle warm-up
3. Main activity with duration or repetitions
4. Cooldown or recovery advice

Include rest days and accessible alternatives.
Do not promise medical outcomes or rapid weight changes.
Do not prescribe restrictive diets or diagnose conditions.
Tell users to adapt activities to their abilities.
Use clear headings and plain English.
"""

    try:
        return _generate(prompt, settings.workout_model)
    except Exception:
        if settings.use_demo_fallback:
            return demo_workout(goal, intensity)
        raise
