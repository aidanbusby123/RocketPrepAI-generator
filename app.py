from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ValidationError
from gen import generate_question, add_question, load_prompts
from typing import List
import os
import json
import random

app = FastAPI()

origins = [
    os.getenv("FRONTEND_ORIGIN", "http://localhost:3000"),
    "http://0.0.0.0:3000",
    "localhost:3000",
    "http://10.0.0.5:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # React frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QuestionRequest(BaseModel):
    section: str
    domains: list[str]
    skill_categories: list[str]
    difficulties: list[str]
    num_questions: int

    

class Question(BaseModel):
    question: str
    section: str
    domain: str
    skill_category: str
    choices: List[str]
    correct_answer: str
    difficulty: str
    difficulty_ranking: str

prompts = load_prompts()
main_prompt = prompts["main_prompt"]

base_user_prompt = "Please generate a question, where the correct answer is {random_choice} and the difficulty is {difficulty}, and try to make the question different from the previous one!"

skill_category_to_domain = {
    "words_in_context": "craft_and_structure",
    "text_structure_and_purpose": "craft_and_structure",
    "cross_text_connections": "craft_and_structure",
    "central_ideas_and_details": "information_and_ideas",
    "command_of_evidence": "information_and_ideas",
    "inferences": "information_and_ideas",
    "boundaries": "standard_english_conventions",
    "form_structure_and_sense": "standard_english_conventions",
    "rhetorical_synthesis": "expression_of_ideas",
    "transitions": "expression_of_ideas",
}

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
    section = request.section
    try:
        for skill_category in request.skill_categories:
            domain = skill_category_to_domain.get(skill_category)
            if not domain:
                raise HTTPException(status_code=400, detail=f"Invalid skill category: {skill_category}")
            for difficulty in request.difficulties:
                for _ in range(request.num_questions):
                    random_choice = random.choice(["A", "B", "C", "D"])
                    user_prompt = base_user_prompt.format(difficulty=difficulty, random_choice=random_choice)
                    system_prompt = main_prompt.format(section=section, domain=domain, skill_category=skill_category, formula=prompts[domain][skill_category], difficulty=difficulty)
                    question = generate_question(system_prompt, user_prompt, section, domain, skill_category, difficulty, generated_questions)
                    generated_questions.append(question)
        print(generated_questions)
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