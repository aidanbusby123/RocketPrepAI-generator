from openai import OpenAI
from google import genai
from google.genai.types import GenerateContentConfig
import sys
import argparse
import random
import os
import re
import json
from datetime import datetime
import uuid
import firebase_admin
from firebase_admin import credentials, firestore

questions = []

openai_api_key = os.environ["OPENAI_API_KEY"]
chatgpt_client = OpenAI(api_key=openai_api_key)

gemini_api_key = os.environ["GEMINI_API_KEY"]
gemini_client = genai.Client(api_key=gemini_api_key)

parser = argparse.ArgumentParser(description="tool to generate questions for RocketPrepAI")
parser.add_argument("outputfile", help="Name of output file")
parser.add_argument("--topics", nargs="+", choices=["all", "words_in_context", "text_structure_and_purpose"], default="all")
parser.add_argument("--difficulty", nargs="+", choices=["easy", "medium", "hard"], default="all")
parser.add_argument("--batch_number", default=4)
parser.add_argument("--epochs", default=1)

args = parser.parse_args()

cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)

db = firestore.client()

base_user_prompt = "Please generate a question, where the correct answer is {random_choice} and the difficulty is {difficulty}"

def load_prompts():
    with open ("prompts/craft_and_structure/words_in_context.txt", "r") as f:
        words_in_context_prompt = f.read()

    with open ("prompts/craft_and_structure/text_structure_and_purpose.txt", "r") as f:
        text_structure_and_purpose_prompt = f.read()

    with open ("prompts/mainprompt.txt", "r") as f:
        main_prompt = f.read()
    
    with open ("prompts/formatprompt.txt", "r") as f:
        format_prompt = f.read()
    

    return {"craft_and_structure_prompts": {"words_in_context": words_in_context_prompt, "text_structure_and_purpose": text_structure_and_purpose_prompt}, "main_prompt": main_prompt, "format_prompt": format_prompt}

prompts = load_prompts()

def format_question(raw_data):
    format_prompt = prompts["format_prompt"]
    format_messages = [{"role": "system", "content": format_prompt}]
    format_messages.append({"role": "user", "content": f"Please format this for me: {raw_data}"})
    response = chatgpt_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=format_messages
    )

    response = response.choices[0].message.content

    return response

def generate_question(system_prompt, user_prompt, messages):
    messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})

    response = chatgpt_client.chat.completions.create(
        model="o4-mini",
        messages=messages,
        temperature=1,
    )

    gemini_response = gemini_client.models.generate_content(
        model="gemini-2.5-pro-preview-06-05",
        contents=user_prompt,
        config=GenerateContentConfig(
            system_instruction=[system_prompt]
        ),
    )

    response = response.choices[0].message.content
    messages.append({"role": "assistant", "content": response})

    formatted_response = format_question(gemini_response)
    
    question = re.search(r'\{.*\}', formatted_response, re.DOTALL)

    if question:
        question_json = question.group(0)
        return json.loads(question_json)
    else:
        raise ValueError("No valid JSON found in response")


def add_question(question):
    question["timestamp"] = datetime.utcnow().isoformat()
    question["id"] = question_id = str(uuid.uuid4())
    question["test"] = "SAT"

    db.collection("questions").document(question_id).set(question)
    return question_id

def generate():
    chatgpt_messages = []


    main_prompt = prompts["main_prompt"] # main prompt for SAT questions

    if args.difficulty == "all":
        difficulties = ["easy", "medium", "hard"]
    else:
        difficulties = args.difficulty

    #print (args.topics)
    for epoch in range (0, args.epochs):
        print(f"Epoch: {epoch}")
        for batch in range (0, args.batch_number):
            for domain, skills in prompts.items():
                #print (skills)
                for dif in difficulties:
                    if domain != "main_prompt":
                        print(f"Domain: {domain}") 
                        
                        for skill_key, skill_value in skills.items():
                           # print(skill_key)
                            if (args.topics == "all" or skill_key in args.topics):
                                print(f"Skill: {skill_key}")
                                skill_prompt = skill_value.format(difficulty=dif)
                                system_prompt = main_prompt.format(domain=domain, skill_category=skill_key, formula=skill_prompt)
                                random_choice = random.choice(["A", "B", "C", "D"])
                                user_prompt = base_user_prompt.format(difficulty=dif, random_choice=random_choice)
                                question = generate_question(system_prompt, user_prompt, chatgpt_messages)
                                add_question(question)
                                #print(question)



generate()