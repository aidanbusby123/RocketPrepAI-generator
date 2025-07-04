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

all_questions = []

openai_api_key = os.environ["OPENAI_API_KEY"]
chatgpt_client = OpenAI(api_key=openai_api_key)

gemini_api_key = os.environ["GEMINI_API_KEY"]
gemini_client = genai.Client(api_key=gemini_api_key)

GEMINI_MODEL = "gemini-2.5-pro"

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

def load_questions_from_firebase(json_file="questions_data.json"):
    """
    Loads all questions from Firebase, saves them to a JSON file,
    and returns the questions as a list of dictionaries.
    """
    try:
        # Initialize Firebase Admin SDK (if not already initialized)
        if not firebase_admin._apps:
            cred = credentials.Certificate("serviceAccountKey.json")
            firebase_admin.initialize_app(cred)

        db = firestore.client()
        questions_ref = db.collection("questions")
        docs = questions_ref.stream()

        all_questions = []
        for doc in docs:
            question_data = doc.to_dict()
            all_questions.append(question_data)

        # Save the questions to a JSON file
        with open(json_file, "w") as f:
            json.dump(all_questions, f, indent=4)

        print(f"Successfully loaded {len(all_questions)} questions from Firebase and saved to {json_file}")
        return all_questions

    except Exception as e:
        print(f"Error loading questions from Firebase: {e}")
        return None

def update_local_questions_data(new_question, json_file="questions_data.json"):
    """
    Updates the local JSON file with a new question.
    """
    try:
        # Load existing questions from the JSON file
        if os.path.exists(json_file):
            with open(json_file, "r") as f:
                questions = json.load(f)
        else:
            questions = []

        # Add the new question to the list
        questions.append(new_question)

        # Save the updated list to the JSON file
        with open(json_file, "w") as f:
            json.dump(questions, f, indent=4)

        print(f"Successfully updated {json_file} with new question.")

        return questions

    except Exception as e:
        print(f"Error updating local questions data: {e}")

all_questions = load_questions_from_firebase()


SOURCES_FILE = "sources_data.json"

def load_sources():
    """
    Loads sources from local storage or uploads them to Gemini if they don't exist.
    """
    sources = {}

    # Load existing sources data from file, if it exists
    try:
        with open(SOURCES_FILE, "r") as f:
            sources_data = json.load(f)
    except FileNotFoundError:
        sources_data = {}

    def upload_or_reuse(filepath):
        """
        Uploads a file to Gemini if it doesn't exist, otherwise reuses the existing file ID.
        """
        filename = os.path.basename(filepath)
        if filename in sources_data:
            try:
                # Check if the file still exists in Gemini
                gemini_client.files.get(name=sources_data[filename])
                print(f"Reusing existing file: {filename} with ID {sources_data[filename]}")
                return sources_data[filename]
            except Exception as e:
                print(f"File {filename} with ID {sources_data[filename]} not found in Gemini, re-uploading...")
                # File not found, remove from sources_data and re-upload
                del sources_data[filename]
        
        # Upload the file
        try:
            uploaded_file = gemini_client.files.upload(file=filepath)
            sources_data[filename] = uploaded_file.name
            print(f"Uploaded new file: {filename} with ID {uploaded_file.name}")
            return uploaded_file.name
        except Exception as e:
            print(f"Error uploading {filename}: {e}")
            return None

    # Craft and Structure
    cross_text_connections_samples = upload_or_reuse("sources/reading_and_writing/craft_and_structure/cross_text_connections.pdf")
    text_structure_and_purpose_samples = upload_or_reuse("sources/reading_and_writing/craft_and_structure/text_structure_and_purpose.pdf")
    words_in_context_samples = upload_or_reuse("sources/reading_and_writing/craft_and_structure/words_in_context.pdf")

    # Expression of Ideas
    rhetorical_synthesis_samples = upload_or_reuse("sources/reading_and_writing/expression_of_ideas/rhetorical_synthesis.pdf")
    transitions_samples = upload_or_reuse("sources/reading_and_writing/expression_of_ideas/transitions.pdf")

    # Information and Ideas
    central_ideas_and_details_samples = upload_or_reuse("sources/reading_and_writing/information_and_ideas/central_ideas_and_details.pdf")
    command_of_evidence_samples = upload_or_reuse("sources/reading_and_writing/information_and_ideas/command_of_evidence.pdf")
    inferences_samples = upload_or_reuse("sources/reading_and_writing/information_and_ideas/inferences.pdf")

    # Standard English Conventions
    boundaries_samples = upload_or_reuse("sources/reading_and_writing/standard_english_conventions/boundaries.pdf")
    form_structure_and_sense_samples = upload_or_reuse("sources/reading_and_writing/standard_english_conventions/form_structure_and_sense.pdf")

    # Save the updated sources data to file
    with open(SOURCES_FILE, "w") as f:
        json.dump(sources_data, f, indent=4)

    return {
        "reading_and_writing": {
            "craft_and_structure": {
                "cross_text_connections": cross_text_connections_samples,
                "text_structure_and_purpose": text_structure_and_purpose_samples,
                "words_in_context": words_in_context_samples,
            },
            "expression_of_ideas": {
                "rhetorical_synthesis": rhetorical_synthesis_samples,
                "transitions": transitions_samples,
            },
            "information_and_ideas": {
                "central_ideas_and_details": central_ideas_and_details_samples,
                "command_of_evidence": command_of_evidence_samples,
                "inferences": inferences_samples,
            },
            "standard_english_conventions": {
                "boundaries": boundaries_samples,
                "form_structure_and_sense": form_structure_and_sense_samples,
            },
        }
    }
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

    with open ("prompts/evaluationprompt.txt", "r") as f:
        evaluation_prompt = f.read()
    
    with open ("prompts/refineprompt.txt", "r") as f:
        refine_prompt = f.read()

    return {"craft_and_structure": {"words_in_context": words_in_context_prompt, "text_structure_and_purpose": text_structure_and_purpose_prompt, "cross_text_connections": cross_text_connections_prompt}, "information_and_ideas":{"central_ideas_and_details": central_ideas_and_details_prompt, "command_of_evidence": command_of_evidence_prompt, "inferences": inferences_prompt}, "standard_english_conventions": {"boundaries": boundaries_prompt, "form_structure_and_sense": form_structure_and_sense_prompt}, "expression_of_ideas": {"rhetorical_synthesis": rhetorical_synthesis_prompt, "transitions": transitions_prompt}, "main_prompt": main_prompt, "format_prompt": format_prompt, "explanation_prompt": explanation_prompt, "evaluation_prompt": evaluation_prompt, "refine_prompt": refine_prompt}

prompts = load_prompts()

sources = load_sources()

def evaluate_question_difficulty(raw_question_data, section, domain, skill_category, difficulty, target_difficulty_ranking, ref_system_prompt):
    print("# Evaluating difficulty\n")
    evaluation_system_prompt = prompts["evaluation_prompt"]
    evaluation_prompt = f"Please evaluate the difficulty of the following question: {raw_question_data}.\nThe question is from the section {section}, domain {domain}, skill category {skill_category}, and is of difficulty {difficulty}.\n"
    reference_prompt = f"Original system prompt, for reference: {ref_system_prompt}"
    print("evaluating difficulty")
    all_questions_text = json.dumps(all_questions)
    response = gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[evaluation_prompt, all_questions_text, reference_prompt],
        config=GenerateContentConfig(
            system_instruction=[evaluation_system_prompt]
        )
    )

    evaluation = response.text

    print(evaluation)
    evaluation = re.search(r'\{.*\}', evaluation, re.DOTALL)

    print(evaluation)
    evaluation_data = json.loads(evaluation.group(0))
    print(evaluation)
    evaluation = str(evaluation_data["evaluation"])
    difficulty_ranking = str(evaluation_data["difficulty_ranking"])
    
    print(f"# Difficulty Evaluation: {evaluation}\n")
    return (evaluation, difficulty_ranking)

def refine_question(raw_question_data, question_evaluation, section, domain, skill_category, difficulty, target_difficulty_ranking, ref_system_prompt):
    print ("#Refining question \n")
    refine_system_prompt = prompts["refine_prompt"]
    refine_system_prompt = refine_system_prompt.format(section=section, domain=domain, skill_category=skill_category, difficulty=difficulty, evaluation=question_evaluation)

    response = gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[f"Please refine the following question: {raw_question_data}", f"Reference generation prompt: {ref_system_prompt}"],
        config=GenerateContentConfig(
            system_instruction=[refine_system_prompt]
        )
    )
    print(f"# Refine notes: {response} ")
    return response

def format_question(raw_question_data, section, domain, skill_category, difficulty, difficulty_ranking):
    format_prompt = prompts["format_prompt"]
    format_prompt = format_prompt.format(section=section, domain=domain, skill_category=skill_category, difficulty=difficulty, difficulty_ranking=difficulty_ranking)
    print("format prompt formatted")
    format_messages = [{"role": "system", "content": format_prompt}]
    format_messages.append({"role": "user", "content": f"Please format this for me: {raw_question_data}."})
    '''response = chatgpt_client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=format_messages
    )'''

    gemini_response = gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=f"Please format this for me: {raw_question_data}.",
        config=GenerateContentConfig(
            system_instruction=[format_prompt]
        ),
    )

    #response = response.choices[0].message.content
    gemini_response = gemini_response.text
    
    print(gemini_response)
    return gemini_response

def generate_question(system_prompt, user_prompt, section, domain, skill_category, difficulty, target_difficulty_ranking, messages):
    print("# Generating Question\n")
    #messages.append({"role": "system", "content": system_prompt})
    #messages.append({"role": "user", "parts": [user_prompt]})

    ''' response = chatgpt_client.chat.completions.create(
        model="o4-mini",
        messages=messages,
        temperature=1,
    )
    '''
    generated_questions = f"Here are the existing questions, including the questions generated during this session and those that are already in the database. Make your next one different than these to ensure question diversity (no copycats!)\n Questions from this session: {str(messages)}\n Questions from database: {all_questions}"

    #print ("Generating questions!")
    #print(generated_questions)

    gemini_response = gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        #messages = str(messages)
        #print(generated_questions)
        contents=[generated_questions, sources[section][domain][skill_category], user_prompt],
        config=GenerateContentConfig(
            system_instruction=[system_prompt],
            temperature=1.05
        ),
    )

    question = gemini_response.text
    print(f"# Question: {question}")

   # explanations = re.search(r'\{.*\}', explanations_response.text, re.DOTALL)
    '''
    if explanations:
        explanations = explanations.group(0)
        explanations = json.loads(explanations)
    else:
        raise ValueError("No valid JSON found in response")
    '''
    #response = response.choices[0].message.content
    #messages.append({"role": "assistant", "content": response})

    evaluation, difficulty_ranking = evaluate_question_difficulty(question, section=section, domain=domain, skill_category=skill_category, difficulty=difficulty, target_difficulty_ranking=target_difficulty_ranking, ref_system_prompt=system_prompt)
    evaluation = evaluation + f"\n current difficulty ranking: {difficulty_ranking}"
    question = refine_question(question, evaluation, section=section, domain=domain, skill_category=skill_category, difficulty=difficulty, target_difficulty_ranking=target_difficulty_ranking, ref_system_prompt=system_prompt)
    evaluation, difficulty_ranking = evaluate_question_difficulty(question, section=section, domain=domain, skill_category=skill_category, difficulty=difficulty, target_difficulty_ranking=target_difficulty_ranking, ref_system_prompt=system_prompt)

    formatted_response = format_question(raw_question_data=question, section=section, domain=domain, skill_category=skill_category, difficulty=difficulty, difficulty_ranking=difficulty_ranking)
    
    question = re.search(r'\{.*\}', formatted_response, re.DOTALL)

    if question:
        question_json = question.group(0)
        print (f"Question json generated: {json.loads(question_json)}")
        update_local_questions_data(json.loads(question_json))
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