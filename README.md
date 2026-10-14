
# FitBuddy - AI Fitness Plan Generator

## Project Overview

FitBuddy is a web application that generates personalized seven-day
workout plans and general nutrition or recovery tips.

## Technologies

- Python
- FastAPI
- Google Gemini API
- SQLAlchemy
- SQLite
- HTML, CSS and Jinja2
- Pytest

## Features

1. User registration through a fitness information form.
2. Seven-day workout plan generation.
3. Nutrition and recovery tips.
4. Feedback-based plan updates.
5. SQLite database persistence.
6. Admin dashboard for viewing user records.
7. JSON API endpoints.
8. Swagger API documentation.
9. Demo fallback when Gemini is not configured.

## Installation

Install Python 3.11 or a compatible newer version.

Create a virtual environment:

    py -m venv .venv

Activate on Windows PowerShell:

    .\.venv\Scripts\Activate.ps1

Install dependencies:

    pip install -r requirements.txt

Copy `.env.example` to `.env`.

Configure the Gemini API key and supported model IDs
if AI generation is required.

## Run the application

    python -m uvicorn app.main:app --reload

Open:

- Homepage: http://127.0.0.1:8000/
- Feedback: http://127.0.0.1:8000/feedback
- Admin: http://127.0.0.1:8000/view-all-users
- API docs: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/api/health

## Run tests

    python -m pytest -q

## Database

SQLite tables are created automatically when the application starts.

The database stores users and workout plan versions.

## Safety and deployment

FitBuddy provides general wellness information, not medical advice.
The admin and deletion routes require authentication and CSRF protection
before the application is deployed publicly.
Never commit your `.env` file or expose your Gemini API key.
