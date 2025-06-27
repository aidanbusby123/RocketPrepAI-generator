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

'''parser = argparse.ArgumentParser(description="tool to generate questions for RocketPrepAI")
parser.add_argument("--domains", nargs="+", choices=["all", "craft_and_structure", "information_and_ideas", "standard_english_conventions", "expression_of_ideas"], default="all")
parser.add_argument("--difficulty", nargs="+", choices=["easy", "medium", "hard"], default="all")
parser.add_argument("--batch_number", default=1)
parser.add_argument("--epochs", default=1)

args = parser.parse_args()
'''
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)

db = firestore.client()

base_user_prompt = "Please generate a question, where the correct answer is {random_choice} and the difficulty is {difficulty}"



def load_sources():
    cross_text_connections_samples = gemini_client.files.upload(file="sources/reading_and_writing/craft_and_structure/cross_text_connections.pdf")
    text_structure_and_purpose_samples = gemini_client.files.upload(file="sources/reading_and_writing/craft_and_structure/text_structure_and_purpose.pdf")
    words_in_context_samples = gemini_client.files.upload(file="sources/reading_and_writing/craft_and_structure/words_in_context.pdf")

    rhetorical_synthesis_samples = gemini_client.files.upload(file="sources/reading_and_writing/expression_of_ideas/rhetorical_synthesis.pdf")
    transitions_samples = gemini_client.files.upload(file="sources/reading_and_writing/expression_of_ideas/transitions.pdf")

    central_ideas_and_details_samples = gemini_client.files.upload(file="sources/reading_and_writing/information_and_ideas/central_ideas_and_details.pdf")
    command_of_evidence_samples = gemini_client.files.upload(file="sources/reading_and_writing/information_and_ideas/command_of_evidence.pdf")
    inferences_samples = gemini_client.files.upload(file="sources/reading_and_writing/information_and_ideas/inferences.pdf")

    boundaries_samples = gemini_client.files.upload(file="sources/reading_and_writing/standard_english_conventions/boundaries.pdf")
    form_structure_and_sense_samples = gemini_client.files.upload(file="sources/reading_and_writing/standard_english_conventions/form_structure_and_sense.pdf")


    return {"craft_and_structure": {"cross_text_connections": cross_text_connections_samples, "text_structure_and_purpose": text_structure_and_purpose_samples, "words_in_context": words_in_context_samples}, "expression_of_ideas": {"rhetorical_synthesis": rhetorical_synthesis_samples, "transitions": transitions_samples}, "information_and_ideas": {"central_ideas_and_details": central_ideas_and_details_samples, "command_of_evidence": command_of_evidence_samples, "inferences": inferences_samples}, "standard_english_conventions": {"boundaries": boundaries_samples, "form_structure_and_sense": form_structure_and_sense_samples}}
def load_prompts():

    # Craft and Structure
    with open ("prompts/reading_and_writing/craft_and_structure/words_in_context.txt", "r") as f:
        words_in_context_prompt = f.read()

    with open ("prompts/reading_and_writing/craft_and_structure/text_structure_and_purpose.txt", "r") as f:
        text_structure_and_purpose_prompt = f.read()

    with open ("prompts/reading_and_writing/craft_and_structure/cross_text_connections.txt", "r") as f:
        cross_text_connections_prompt = f.read()

    
    # Information and Ideas
    with open ("prompts/reading_and_writing/information_and_ideas/central_ideas_and_details.txt", "r") as f:
        central_ideas_and_details_prompt = f.read()

    with open ("prompts/reading_and_writing/information_and_ideas/command_of_evidence.txt" , "r") as f:
        command_of_evidence_prompt = f.read()

    with open ("prompts/reading_and_writing/information_and_ideas/inferences.txt", "r") as f:
        inferences_prompt = f.read()


    # Standard English Conventions

    with open ("prompts/reading_and_writing/standard_english_conventions/boundaries.txt", "r") as f:
        boundaries_prompt = f.read()

    with open ("prompts/reading_and_writing/standard_english_conventions/form_structure_and_sense.txt", "r") as f:
        form_structure_and_sense_prompt = f.read()

    # Expression of Ideas

    with open ("prompts/reading_and_writing/expression_of_ideas/rhetorical_synthesis.txt", "r") as f:
        rhetorical_synthesis_prompt = f.read()

    with open("prompts/reading_and_writing/expression_of_ideas/transitions.txt", "r") as f:
        transitions_prompt = f.read()

    with open ("prompts/mainprompt.txt", "r") as f:
        main_prompt = f.read()
    
    with open ("prompts/formatprompt.txt", "r") as f:
        format_prompt = f.read()

    with open ("prompts/explanationprompt.txt", "r") as f:
        explanation_prompt = f.read()
    

    return {"craft_and_structure": {"words_in_context": words_in_context_prompt, "text_structure_and_purpose": text_structure_and_purpose_prompt, "cross_text_connections": cross_text_connections_prompt}, "information_and_ideas":{"central_ideas_and_details": central_ideas_and_details_prompt, "command_of_evidence": command_of_evidence_prompt, "inferences": inferences_prompt}, "standard_english_conventions": {"boundaries": boundaries_prompt, "form_structure_and_sense": form_structure_and_sense_prompt}, "expression_of_ideas": {"rhetorical_synthesis": rhetorical_synthesis_prompt, "transitions": transitions_prompt}, "main_prompt": main_prompt, "format_prompt": format_prompt, "explanation_prompt": explanation_prompt}

prompts = load_prompts()

sources = load_sources()

def format_question(raw_data, section, domain, skill_category, explanations, difficulty, difficulty_ranking):
    format_prompt = prompts["format_prompt"]
    format_prompt = format_prompt.format(section=section, domain=domain, skill_category=skill_category, explanations=explanations, difficulty=difficulty, difficulty_ranking=difficulty_ranking)
    format_messages = [{"role": "system", "content": format_prompt}]
    format_messages.append({"role": "user", "content": f"Please format this for me: {raw_data}"})
    '''response = chatgpt_client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=format_messages
    )'''

    gemini_response = gemini_client.models.generate_content(
        model="gemini-2.5-pro-preview-06-05",
        contents=f"Please format this for me: {raw_data}",
        config=GenerateContentConfig(
            system_instruction=[format_prompt]
        ),
    )

    #response = response.choices[0].message.content
    gemini_response = gemini_response.text
    print(gemini_response)
    return gemini_response

def generate_question(system_prompt, user_prompt, section, domain, skill_category, difficulty, messages):
    #messages.append({"role": "system", "content": system_prompt})
    #messages.append({"role": "user", "parts": [user_prompt]})

    ''' response = chatgpt_client.chat.completions.create(
        model="o4-mini",
        messages=messages,
        temperature=1,
    )
    '''
    generated_questions = f"Here are the existing questions. Make your next one different than these to ensure question diversity: {str(messages)}"

    print ("Generating questions!")
    print(generated_questions)

    gemini_response = gemini_client.models.generate_content(
        model="gemini-2.5-pro-preview-06-05",
        #messages = str(messages)
        #print(generated_questions)
        contents=[generated_questions, sources[section][domain][skill_category], user_prompt],
        config=GenerateContentConfig(
            system_instruction=[system_prompt],
            temperature=1.05
        ),
    )

    explanation_prompt = f"Please generate the answer explanations for the following question: {gemini_response}. "

    explanations_response = gemini_client.models.generate_content(
        model="gemini-2.5-pro-preview-06-05",
        contents=[explanation_prompt],
        config=GenerateContentConfig(
            system_instruction=[prompts["explanation_prompt"]]
        )
    )
    explanations = explanations_response.text
    #response = response.choices[0].message.content
    #messages.append({"role": "assistant", "content": response})

    formatted_response = format_question(gemini_response, section=section, domain=domain, skill_category=skill_category, explanations=explanations, difficulty=difficulty, difficulty_ranking=0.5)
    
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

args = None

def generate():
    chatgpt_messages = []

    q_num = 0

    difficulties = ["easy", "medium", "hard"]
    main_prompt = prompts["main_prompt"] # main prompt for SAT questions

    print(main_prompt)

    if args.difficulty == "all":
        difficulties = ["easy", "medium", "hard"]
    else:
        difficulties = args.difficulty

    #print (args.topics)
    for epoch in range (0, args.epochs):
        print(f"Epoch: {epoch}")
        for batch in range (0, int(args.batch_number)):
            for domain, skills in prompts.items():
                #print (skills)
                for dif in difficulties:
                    if domain != "main_prompt" and domain != "format_prompt" and domain != "gen_prompt" and ((args.domains == "all") or  (domain in args.domains)):
                        print(f"Domain: {domain}") 
                        dif = str(dif)
                        
                        for skill_key, skill_value in skills.items():
                           # print(skill_key)
                                print(f"Skill: {skill_key}")
                                skill_prompt = skill_value
                                system_prompt = main_prompt.format(domain=domain, skill_category=skill_key, formula=skill_prompt, difficulty=dif)
                                #print(system_prompt)
                                random_choice = random.choice(["A", "B", "C", "D"])
                                user_prompt = base_user_prompt.format(difficulty=dif, random_choice=random_choice)
                                question = generate_question(system_prompt, user_prompt, chatgpt_messages, domain=domain, skill_category=skill_key, difficulty=dif)
                                question_id = add_question(question)
                                print(f"Question #{q_num} , id {question_id} generated!")
                                q_num+=1
                                #print(question)



#generate()