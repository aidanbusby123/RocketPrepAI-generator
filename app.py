from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from gen import generate_question, add_question, load_prompts
from typing import List
import os
import json
import random

app = FastAPI()

origins = [
    os.getenv("FRONTEND_ORIGIN", "http://localhost:3001"),
    "http://0.0.0.0:3001",
    "localhost:3001",
    "http://10.0.0.5:3001"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # React frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QuestionRequest(BaseModel):
    domains: list[str]
    skill_categories: list[str]
    difficulties: list[str]
    num_questions: int

    

class Question(BaseModel):
    question: str
    domain: str
    skill_category: str
    choices: List[str]
    correct_answer: str
    difficulty: str

prompts = load_prompts()
main_prompt = prompts["main_prompt"]

base_user_prompt = "Please generate a question, where the correct answer is {random_choice} and the difficulty is {difficulty}"

@app.middleware("http")
async def log_request_body(request: Request, call_next):
    if request.url.path == "/send-questions" or request.url.path == "/generate-questions":  # Only log for this endpoint
        body = await request.body()
        print("Raw request body:", body.decode("utf-8"))  # Log raw JSON data
    response = await call_next(request)
    return response

@app.post("/generate-questions")
async def generate_questions(request: QuestionRequest):
    generated_questions = []

    try:
        for domain in request.domains:
            for skill_category in request.skill_categories:
                for difficulty in request.difficulties:
                    for _ in range(request.num_questions):
                        random_choice = random.choice(["A", "B", "C", "D"])
                        user_prompt = base_user_prompt.format(difficulty=difficulty, random_choice=random_choice)
                        system_prompt = main_prompt.format(domain=domain, skill_category=skill_category, formula=prompts[domain][skill_category], difficulty=difficulty)
                        question = generate_question(system_prompt, user_prompt, domain, skill_category, difficulty, [])
                        generated_questions.append(question)
        return {"questions": generated_questions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/send-questions")
async def send_questions(request: Request):
    try:
        data = await request.json()
        questions_data = data.get("questions")

        questions: List[Question] = [Question(**q) for q in questions_data]
        print("Received questions:", questions)
        for question in questions:
            question_data = question.dict()
            add_question(question_data)  # Send each question to Firebase
        return {"message": "Questions successfully sent to Firebase"}
    except ValidationError as e:
        print("Validation error:", e.json())
        raise HTTPException(status_code=422, detail=e.errors())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))