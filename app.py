from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ValidationError
from gen import generate_question, add_question, load_prompts, load_questions_from_firebase, get_human_feedback, save_human_feedback, load_feedback_log
from typing import List, Dict
import os
import json
import random
import threading
import queue


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
    explanations: Dict[str, str]

class FeedbackRequest(BaseModel):
    index: int
    content: str

prompts = load_prompts()
main_prompt = prompts["main_prompt"]

base_user_prompt = "Please generate a question, where the correct answer is {random_choice} and the difficulty is {difficulty}, and try to make the question different from the previous one!"

skill_category_to_domain = {
    # Reading and Writing Skills
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

    # Math Skills
    "linear_equations_in_one_variable": "algebra",
    "linear_equations_in_two_variables": "algebra",
    "linear_functions": "algebra",
    "systems_of_two_linear_equations_in_two_variables": "algebra",
    "linear_inequalities_in_one_or_two_variables": "algebra",

    "equivalent_expressions": "advanced_math",
    "nonlinear_equations_in_one_variable_and_systems_of_equations_in_two_variables": "advanced_math",
    "nonlinear_functions": "advanced_math",

    "ratios_rates_proportional_relationships_and_units": "problem_solving_and_data_analysis",
    "percentages": "problem_solving_and_data_analysis",
    "one_variable_data_distributions_and_measures_of_center_and_spread": "problem_solving_and_data_analysis",
    "two_variable_data_models_and_scatterplots": "problem_solving_and_data_analysis",
    "probability_and_conditional_probability": "problem_solving_and_data_analysis",
    "inference_from_sample_statistics_and_margin_of_error": "problem_solving_and_data_analysis",
    "evaluating_statistical_claims_observational_studies_and_experiments": "problem_solving_and_data_analysis",

    "area_and_volume": "geometry_and_trigonometry",
    "lines_angles_and_triangles": "geometry_and_trigonometry",
    "right_triangles_and_trigonometry": "geometry_and_trigonometry",
    "circles": "geometry_and_trigonometry",
}

generated_questions = []


@app.middleware("http")
async def log_request_body(request: Request, call_next):
    if request.url.path == "/send-questions" or request.url.path == "/generate-questions":  # Only log for this endpoint
        body = await request.body()
        print("Raw request body:", body.decode("utf-8"))  # Log raw JSON data
    response = await call_next(request)
    return response

def generate_questions_for_skill_category(section: str, skill_category: str, difficulties: List[str], num_questions: int, generated_questions: List[Dict], question_queue: queue.Queue):
    domain = skill_category_to_domain.get(skill_category)
    if not domain:
        raise HTTPException(status_code=400, detail=f"Invalid skill category: {skill_category}")
    for difficulty in difficulties:
                for _ in range(num_questions):
                    random_choice = random.choice(["A", "B", "C", "D"])
                    if difficulty == "easy":
                        target_difficulty_ranking = random.uniform(0, 0.33)
                    elif difficulty == "medium":
                        target_difficulty_ranking = random.uniform(0.33, 0.67)
                    elif difficulty == "hard":
                        target_difficulty_ranking = random.uniform(0.67, 1.0)
                    else:
                        raise ValueError("Invalid difficulty level. Must be 'easy', 'medium', or 'hard'.")
                    

                    user_prompt = base_user_prompt.format(difficulty=difficulty, random_choice=random_choice)
                    print(f"domain: {domain}, section: {section}")
                    system_prompt = f"Using the sources as a guide, generate an authentic and unique question of the given difficulty level.\
                    # For RW Questions \
                    Make questions harder than you think they should be always, \
                    and ensure that the tone and style does not differ drastically from those of the examples. The only way in which your question should differ \
is that it is allowed to be harder than the others. Realistically, your easiest questions for each difficulty should be as hard as the harder ones in the provided sources. (the files). To ensure question diversity, use the sources as reference to decide when you need to switch gears and  \
generate questions of a different style, for example expository vs fictional (for reading and writing questions), based off of how many questions of different styles there are. For now, any math questions should be multiple choice and that are numerical or use a clearly formatted table. For the reading and writing questions, unlike the math do NOT make each question an image of one of the source questions. Your reading and writing questions should be original and they should not be copies, but should take inspiration. Ensure to make your distractors harder too for reading and writing questions. (if its a math question, obviously, otherwise ignore this). Make them HARDER! \
# For math questions\
      please use the relevant sources as inspiration when generating your question, only testing topics that are covered in those questions. DO NOT USE ANY CONCEPTS/STRATEGIES THAT DO NOT APPEAR IN THE SOURCE QUESTIONS. The questions should only contain mathematical concepts that you can find in the source questions (CollegeBoard questions), and should be indestinguishable from real SAT math question, besides the fact they should be a litte bit harder. Harder does not mean using concepts that are not covered in the source questions, however. You should basically be taking the provided source questions and making a replica of them for the math questions (but not for RW) to avoid creating questions that don't look exactly like SAT questions, because these math questions need to be of the *exact same format and style*  as the example ones. You are given less creative leeway with the math questions, as they should be made in the image of one of the source questions. NOTHING SUPER CREATIVE OR OFF TOPIC OR NOT IN THE EXACT FORMAT OF ONE OF THE EXAMPLES! THIS MEANS YOUR QUESTIONS SHOULD BE SOLVABLE ALMOST EXACTLY LIKE ONE OF THE SOURCE QUESTIONS. You should really take one of the source questions and just modify it to have different equations/whatever instead of just writing the question from scratch.\
                   Using the prompt above, here is a new, generated question of difficulty {difficulty}, domain {domain}, and section {section}. Please ensure you achieve the correct difficulty level. \
"
                    system_prompt = str(system_prompt)
                    #system_prompt = main_prompt.format(section=section, domain=domain, skill_category=skill_category, formula=prompts[section][domain][skill_category], difficulty=difficulty, evaluation_formula=prompts["evaluation_prompt"], refine_formula=prompts["refine_prompt"])
                    question = generate_question(system_prompt, user_prompt, section, domain, skill_category, difficulty, generated_questions)
                    print(f"question JSON: {question}")
                    question_queue.put(question)

def save_pending_questions(questions: List[Dict]):
    with open ("pending_questions.json", "w") as f:
        json.dump(questions, f, indent=4)

def load_pending_questions() -> List[Dict] : 
    try:
        with open ("pending_questions.json", "r") as f:
            return json.load(f)
        
    except FileNotFoundError:
        return []
    
generated_questions = load_pending_questions()

@app.post("/generate-questions")
async def generate_questions(request: QuestionRequest):

    section = request.section
    question_queue = queue.Queue()
    threads = []
    try:
        for skill_category in request.skill_categories:
            thread = threading.Thread(target=generate_questions_for_skill_category, args=(section, skill_category, request.difficulties, request.num_questions, generated_questions, question_queue))
            threads.append(thread)
            thread.start()
        for thread in threads:
            thread.join()

        while not question_queue.empty():
            generated_questions.append(question_queue.get())
        #print(generated_questions)
        save_pending_questions(generated_questions)
        return {"questions": generated_questions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/remove-question")
async def remove_question(request: Request):
    try:
        data = await request.json()
        index_to_remove = data.get("index")

        if index_to_remove is None:
            raise HTTPException(status_code=400, detail="Missing question index")

        global generated_questions

        if not (0 <= index_to_remove < len(generated_questions)):
            raise HTTPException(status_code=404, detail=f"No question at index {index_to_remove}")

        # Actually remove by index
        removed_question = generated_questions.pop(index_to_remove)

        save_pending_questions(generated_questions)

        return {
            "questions": generated_questions
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/human-feedback")
async def human_feedback(request: FeedbackRequest):
    question_index = request.index
    feedback_content = request.content

    if not (0 <= question_index < len(generated_questions)):
        raise HTTPException(status_code=404, detail=f"No question at index {question_index}")

    original_question = generated_questions[question_index]
    old_difficulty_rating = original_question.get("difficulty_ranking", "unknown")

    section = original_question.get("section", "unknown")
    difficulty = original_question.get("difficulty", "unknown")
    skill_category = original_question.get("skill_category", "unknown")

    revised_question = get_human_feedback(original_question, section, skill_category, difficulty, question_index, feedback_content, prompts["main_prompt"])
    generated_questions[question_index] = revised_question  # Update in place



    save_pending_questions(generated_questions)

    return {"questions": generated_questions}

@app.post("/send-questions")
async def send_questions(request: Request):
    try:
        data = await request.json()
        questions_data = data.get("questions")

        questions: List[Question] = [Question(**q) for q in questions_data]
        print("Received questions:", questions)

        feedback_log = load_feedback_log()
        for idx, question in enumerate(questions):
            question_data = question.dict()
            question_id = add_question(question_data)  # Get unique ID from Firebase

            # Find matching feedback by index
            for entry in feedback_log:
                print(entry)
                if entry["question_index"] == idx:
                    entry["question_id"] = question_id  # Add the unique ID here
                    print("saving feedback")
                    save_human_feedback(
                        feedback=entry,
                        question_id=question_id,
                    )
                    

        load_questions_from_firebase()
        global generated_questions
        generated_questions = []
        with open("pending_questions.json", "w") as f:
            json.dump([], f)

# Clear feedback log
        with open("feedback_log.json", "w") as f:
            json.dump([], f)
        return {"message": "Questions successfully sent to Firebase"}
    except ValidationError as e:
        print("Validation error:", e.json())
        raise HTTPException(status_code=422, detail=e.errors())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@app.get('/load-pending-questions')
def load_pending_questions_from_file():
    pending_questions = load_pending_questions()
    return {"questions": pending_questions}