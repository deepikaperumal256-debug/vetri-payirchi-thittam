from google import genai

from .config import get_settings


def demo_updated_plan(
    original_plan: str,
    feedback: str,
    goal: str | None = None,
    intensity: str | None = None,
) -> str:
    """Create a basic revised plan when Gemini is unavailable."""

    return (
        "UPDATED WORKOUT PLAN\n\n"
        "Your feedback:\n"
        f"{feedback.strip()}\n\n"
        f"Fitness goal: {goal or 'General wellness'}\n"
        f"Preferred intensity: {intensity or 'Comfortable'}\n\n"
        "Suggested adjustments:\n"
        "- Choose activities suitable for your abilities.\n"
        "- Start gently and increase activity gradually.\n"
        "- Include warm-up and cool-down activities.\n"
        "- Allow time for rest and recovery.\n"
        "- Stop if an activity causes pain or dizziness.\n\n"
        "Previous workout plan:\n"
        f"{original_plan}\n\n"
        "Note: This is a basic fallback plan, not an AI-generated revision."
    )


def update_workout_plan(
    original_plan: str,
    feedback: str,
    goal: str | None = None,
    intensity: str | None = None,
) -> str:
    """Revise an existing workout plan using feedback."""

    settings = get_settings()

    if not original_plan or not original_plan.strip():
        raise ValueError("Original workout plan cannot be empty.")

    if not feedback or not feedback.strip():
        raise ValueError("Feedback cannot be empty.")

    # Use demo mode if no API key is configured.
    if not settings.gemini_api_key:
        if settings.use_demo_fallback:
            print("FitBuddy: Using demo update because no API key is configured.")
            return demo_updated_plan(
                original_plan, feedback, goal, intensity
            )
        raise RuntimeError("Gemini API key is missing.")

    prompt = f"""
You are FitBuddy, a general fitness and wellness assistant.

Revise the existing workout plan using the user's feedback.

EXISTING WORKOUT PLAN:
{original_plan}

USER FEEDBACK:
{feedback.strip()}

FITNESS GOAL:
{goal or "General wellness"}

PREFERRED INTENSITY:
{intensity or "Comfortable"}

Requirements:
- Provide a clear, practical revised plan.
- Respect the user's abilities and preferences.
- Include warm-up, cool-down, and recovery guidance.
- Avoid extreme exercise challenges and unrealistic promises.
- Do not provide medical diagnosis or treatment.
- Return plain text only.
"""

    try:
        client = genai.Client(api_key=settings.gemini_api_key)

        response = client.models.generate_content(
            model=settings.workout_model,
            contents=prompt,
        )

        updated_plan = response.text

        if not updated_plan or not updated_plan.strip():
            raise RuntimeError("Gemini returned an empty updated plan.")

        return updated_plan.strip()

    except Exception as exc:
        print("FITBUDDY UPDATE ERROR:", repr(exc))

        # Keep the feedback workflow testable during Gemini outages.
        if settings.use_demo_fallback:
            print("FitBuddy: Gemini failed; using demo update.")
            return demo_updated_plan(
                original_plan, feedback, goal, intensity
            )

        raise RuntimeError(
            "Unable to update the workout plan using Gemini."
        ) from exc