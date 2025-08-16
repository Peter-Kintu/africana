# learnflow_ai/django_backend/api/ai_integration.py
import openai
import os
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')

def get_quiz_feedback(question, user_answer, correct_answer):
    prompt = f"""
    You are an AI assistant providing feedback on a quiz answer.
    The user's question was: "{question}"
    The user's answer was: "{user_answer}"
    The correct answer is: "{correct_answer}"

    Please provide concise, encouraging, and helpful feedback.
    If the answer is correct, congratulate the user.
    If the answer is incorrect, gently explain why and guide them toward the correct answer without simply giving it away.
    The feedback should be no more than 3-4 sentences.
    """
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful and encouraging AI quiz assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"An error occurred while generating feedback: {e}"

def get_recommendations(student_progress, lessons):
    progress_summary = "Student Progress Summary:\n"
    if student_progress:
        for sp in student_progress:
            progress_summary += f"- Lesson: {sp.lesson.title}, Score: {sp.score}, Attempts: {sp.attempts}\n"
    else:
        progress_summary += "No progress data available.\n"

    available_lessons = "Available Lessons:\n"
    if lessons:
        for lesson in lessons:
            available_lessons += f"- Title: {lesson.title}, Topic: {lesson.topic}\n"
    else:
        available_lessons += "No lessons available.\n"

    prompt = f"""
    Based on the student's progress, recommend the top 3 most relevant lessons for them to take next.
    Use the following information to make your recommendations.
    {progress_summary}
    {available_lessons}
    Provide a brief reason for each recommendation.
    """
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an AI tutor recommending lessons."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=250
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"An error occurred while generating recommendations: {e}"