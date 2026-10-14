from datetime import datetime, timezone
from pathlib import Path
import traceback
from google.genai import errors
from fastapi import (
    APIRouter,
    Depends,
    Form,
    HTTPException,
    Request,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_db, User, Plan
from .schemas import UserInput, FeedbackRequest, Goal,Intensity
from .gemini_generator import generate_workout_gemini
from .gemini_flash_generator import generate_nutrition_tip_with_flash
from .updated_plan import update_workout_plan


# --------------------------------------------------
# Configuration
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"

templates = Jinja2Templates(
    directory=str(TEMPLATE_DIR)
)
router = APIRouter()


# --------------------------------------------------
# Helper functions
# --------------------------------------------------

def render(request: Request, template: str, **context):
    return templates.TemplateResponse(
        request=request,
        name=template,
        context=context,
    )


def latest_plan(db: Session, user_id: str):
    return db.scalar(
        select(Plan)
        .where(Plan.user_id == user_id)
        .order_by(Plan.id.desc())
        .limit(1)
    )


def get_user_or_404(db: Session, user_id: str):
    user = db.scalar(
        select(User).where(User.user_id == user_id)
    )

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User ID was not found.",
        )

    return user


def save_or_update_user(db: Session, data: UserInput):
    user = db.scalar(
        select(User).where(User.user_id == data.user_id)
    )

    if user is None:
        user = User(
            user_id=data.user_id,
            username=data.username,
            age=data.age,
            weight=data.weight,
            goal=data.goal,
            intensity=data.intensity,
        )
        db.add(user)
    else:
        user.username = data.username
        user.age = data.age
        user.weight = data.weight
        user.goal = data.goal
        user.intensity = data.intensity

    return user


def create_plan(db: Session, data: UserInput):
    user = save_or_update_user(db, data)

    workout = generate_workout_gemini(
        username=data.username,
        age=data.age,
        weight=data.weight,
        goal=data.goal,
        intensity=data.intensity,
    )

    nutrition_tip = generate_nutrition_tip_with_flash(
        username=data.username,
        age=data.age,
        weight=data.weight,
        goal=data.goal,
    )

    plan = Plan(
        user_id=data.user_id,
        original_plan=workout,
        nutrition_tip=nutrition_tip,
    )

    db.add(plan)
    db.commit()
    db.refresh(plan)

    return user, plan


def save_feedback_update(
    db: Session,
    user: User,
    plan: Plan,
    feedback: str,
):
    revised_plan = update_workout_plan(
        original_plan=plan.updated_plan or plan.original_plan,
        feedback=feedback,
        goal=user.goal,
        intensity=user.intensity,
    )

    plan.updated_plan = revised_plan
    plan.last_feedback = feedback
    plan.updated_at = datetime.now(
        timezone.utc
    ).replace(tzinfo=None)

    db.commit()
    db.refresh(plan)

    return revised_plan


# --------------------------------------------------
# Home page
# --------------------------------------------------

@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    return render(
        request,
        "index.html",
        error=None,
    )


# --------------------------------------------------
# Generate workout plan from HTML form
# --------------------------------------------------

@router.post(
    "/generate-workout",
    response_class=HTMLResponse,
)
def generate_workout(
    request: Request,
    username: str = Form(...),
    user_id: str = Form(...),
    age: int = Form(...),
    weight: float = Form(...),
    goal: Goal = Form(...),
    intensity: Intensity = Form(...),
    db: Session = Depends(get_db),
):
    try:
        data = UserInput(
            username=username.strip(),
            user_id=user_id.strip(),
            age=age,
            weight=weight,
            goal=goal,
            intensity=intensity,
        )
    except ValidationError as exc:
        print("FORM VALIDATION ERROR:", exc.errors())

        return render(
            request,
            "index.html",
            error="Please check your entries and try again.",
        )

    try:
        user, plan = create_plan(db, data)

        return render(
            request,
            "result.html",
            user=user,
            plan=plan,
            message=None,
        )
    except errors.APIError as exc:
        print("FITBUDDY API ERROR:", repr(exc))
        traceback.print_exc()
        db.rollback()

        if exc.code == 429:
            message = (
                "Gemini AI quota exceeded. Please try again "
                "after the quota resets."
            )
        else:
            message = (
                "The AI service is temporarily unavailable. "
                "Please try again later."
            )

        return render(
            request,
            "index.html",
            error=message,

         ) 
    
    except Exception as exc:
        print("FITBUDDY GENERATION ERROR:", repr(exc))
        traceback.print_exc()
        db.rollback()

        return render(
            request,
            "index.html",
            error=(
                "The plan could not be generated or saved. "
                "Check the VS Code Terminal for details."
            ),
        )


# --------------------------------------------------
# Feedback page
# --------------------------------------------------

@router.get("/feedback", response_class=HTMLResponse)
def feedback_page(request: Request):
    return render(
        request,
        "feedback.html",
        error=None,
        message=None,
        user_id="",
        feedback="",
    )


# --------------------------------------------------
# Submit feedback from HTML form
# --------------------------------------------------

@router.post(
    "/submit-feedback",
    response_class=HTMLResponse,
)
def submit_feedback(
    request: Request,
    user_id: str = Form(...),
    feedback: str = Form(...),
    db: Session = Depends(get_db),
):
    try:
        data = FeedbackRequest(
            user_id=user_id.strip(),
            feedback=feedback.strip(),
        )
    except ValidationError as exc:
        print("FEEDBACK VALIDATION ERROR:", exc.errors())

        return render(
            request,
            "feedback.html",
            error="Enter a valid user ID and feedback.",
            message=None,
            user_id=user_id,
            feedback=feedback,
        )

    try:
        user = db.scalar(
            select(User).where(User.user_id == data.user_id)
        )
        plan = latest_plan(db, data.user_id)

        if user is None or plan is None:
            return render(
                request,
                "feedback.html",
                error="No saved workout plan was found for that user ID.",
                message=None,
                user_id=data.user_id,
                feedback=data.feedback,
            )

        save_feedback_update(
            db=db,
            user=user,
            plan=plan,
            feedback=data.feedback,
        )

        return render(
            request,
            "result.html",
            user=user,
            plan=plan,
            message="Your workout plan has been updated.",
        )

    except Exception as exc:
        print("FITBUDDY UPDATE ERROR:", repr(exc))
        traceback.print_exc()
        db.rollback()

        return render(
            request,
            "feedback.html",
            error="Unable to update the plan. Check the terminal.",
            message=None,
            user_id=user_id,
            feedback=feedback,
        )


# --------------------------------------------------
# View all users
# --------------------------------------------------

@router.get("/view-all-users", response_class=HTMLResponse)
def view_all_users(
    request: Request,
    db: Session = Depends(get_db),
):
    users = db.scalars(
        select(User).order_by(User.id.desc())
    ).all()

    records = [
        {
            "user": user,
            "plan": latest_plan(db, user.user_id),
        }
        for user in users
    ]

    return render(
        request,
        "all_users.html",
        records=records,
    )


# --------------------------------------------------
# Delete user
# --------------------------------------------------

@router.post("/delete-user/{user_id}")
def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
):
    user = db.scalar(
        select(User).where(User.user_id == user_id)
    )

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found.",
        )

    try:
        db.delete(user)
        db.commit()

    except Exception as exc:
        print("DELETE USER ERROR:", repr(exc))
        traceback.print_exc()
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to delete user. "
                "Check whether saved plans reference this user."
            ),
        )

    return RedirectResponse(
        url="/view-all-users",
        status_code=303,
    )


# --------------------------------------------------
# Health check API
# --------------------------------------------------

@router.get("/api/health")
def health():
    return {
        "status": "ok",
        "application": "FitBuddy",
    }


# --------------------------------------------------
# Generate workout through JSON API
# --------------------------------------------------

@router.post("/api/generate-workout")
def api_generate_workout(
    data: UserInput,
    db: Session = Depends(get_db),
):
    try:
        user, plan = create_plan(db, data)

        return {
            "user_id": user.user_id,
            "plan_id": plan.id,
            "workout_plan": plan.original_plan,
            "nutrition_tip": plan.nutrition_tip,
        }

    except Exception as exc:
        print("API GENERATION ERROR:", repr(exc))
        traceback.print_exc()
        db.rollback()

        raise HTTPException(
            status_code=503,
            detail="Plan generation or database saving failed.",
        )


# --------------------------------------------------
# Update workout through JSON API
# --------------------------------------------------

@router.post("/api/submit-feedback")
def api_submit_feedback(
    data: FeedbackRequest,
    db: Session = Depends(get_db),
):
    try:
        user = db.scalar(
            select(User).where(User.user_id == data.user_id)
        )
        plan = latest_plan(db, data.user_id)

        if user is None or plan is None:
            raise HTTPException(
                status_code=404,
                detail="User or saved plan not found.",
            )

        revised = save_feedback_update(
            db=db,
            user=user,
            plan=plan,
            feedback=data.feedback,
        )

        return {
            "user_id": data.user_id,
            "updated_plan": revised,
        }

    except HTTPException:
        raise

    except Exception as exc:
        print("API FEEDBACK UPDATE ERROR:", repr(exc))
        traceback.print_exc()
        db.rollback()

        raise HTTPException(
            status_code=503,
            detail="Plan update failed.",
        )


# --------------------------------------------------
# List users through JSON API
# --------------------------------------------------

@router.get("/api/users")
def api_users(
    db: Session = Depends(get_db),
):
    users = db.scalars(
        select(User).order_by(User.id.desc())
    ).all()

    return [
        {
            "user_id": user.user_id,
            "username": user.username,
            "age": user.age,
            "weight": user.weight,
            "goal": user.goal,
            "intensity": user.intensity,
        }
        for user in users
    ]
