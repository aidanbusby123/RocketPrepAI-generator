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
import logging
import atexit
import random

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
        questions_ref = db.collection("questions").document("SAT")
        questions_collections = questions_ref.collections()

        questions_docs = {}

        all_questions = {}
        for questions_collection in questions_collections:
            questions_docs = questions_collection.stream()
            for question_doc in questions_docs:
                question_data = question_doc.to_dict()
                print(question_data["id"])
                all_questions.setdefault("SAT", {}).setdefault(questions_collection.id, []).append(question_data)


        # Save the questions to a JSON file
        with open(json_file, "w") as f:
            json.dump(all_questions, f, indent=4)

        print(f"Successfully loaded {len(all_questions)} questions from Firebase and saved to {json_file}")
        return all_questions

    except Exception as e:
        print(f"Error loading questions from Firebase: {e}")
        return None
def load_feedback_from_firebase(json_file="feedback.json"):
    """
    Loads all feedback entries from Firebase and saves them to a JSON file,
    organized by section and question_id.
    """
    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate("serviceAccountKey.json")
            firebase_admin.initialize_app(cred)

        db = firestore.client()

        feedback_ref = db.collection("feedback").document("SAT")

        all_feedback = {}

        # List all section-level subcollections (e.g., "reading_and_writing")
        section_collections = feedback_ref.collections()

        for section_collection in section_collections:
            section_id = section_collection.id
            print(f"Processing section: {section_id}")
            all_feedback[section_id] = {}

            # Each document here represents a question_id
            question_docs = section_collection.stream()
            for question_doc in question_docs:
                question_id = question_doc.id
                print(f"Processing question ID: {question_id}")
                entries_ref = section_collection.document(question_id).collection("entries")
                entries = entries_ref.stream()

                all_feedback[section_id][question_id] = []
                for entry in entries:
                    entry_data = entry.to_dict()
                    all_feedback[section_id][question_id].append(entry_data)

        # Save to file
        with open(json_file, "w") as f:
            json.dump(all_feedback, f, indent=4)

        print(f"Successfully loaded feedback from Firebase and saved to {json_file}")
        return all_feedback

    except Exception as e:
        print(f"Error loading feedback from Firebase: {e}")
        return None


def update_local_questions_data(new_question, json_file="pending_questions.json"):
    """
    Updates the local JSON file with a new question.
    """
    questions = [] # Initialize as an empty list to start
    try:
        # Load existing questions from the JSON file
        if os.path.exists(json_file):
            with open(json_file, "r") as f:
                # Corrected line: Assign the loaded JSON data to 'questions'
                loaded_data = json.load(f)
                # Add a check to ensure the loaded data is actually a list,
                # as discussed in the previous turn. This makes it more robust.
                if isinstance(loaded_data, list):
                    questions = loaded_data
                else:
                    print(f"Warning: {json_file} contains non-list data. Initializing questions as empty list.")
                    questions = [] # Re-initialize if the file content is not a list

        # Add the new question to the list
        questions.append(new_question)

        # Save the updated list to the JSON file
        with open(json_file, "w") as f:
            json.dump(questions, f, indent=4)

        print(f"Successfully updated {json_file} with new question.")

        return questions # Return the updated list of questions

    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {json_file}: {e}. File might be corrupted. Initializing with new question.")
        # If the file is corrupted, start fresh with the new question
        questions = [new_question]
        with open(json_file, "w") as f:
            json.dump(questions, f, indent=4)
        return questions
    except Exception as e:
        print(f"An unexpected error occurred updating local questions data: {e}")
        # In case of other errors, try to load and return existing or empty list
        try:
            if os.path.exists(json_file):
                with open(json_file, "r") as f:
                    return json.load(f) # Try to load what's there
        except:
            return [] # Return empty list if even recovery fails
        return []

all_questions = load_questions_from_firebase()

all_feedback = load_feedback_from_firebase()


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
        Uses full file path as the unique key since filenames may be duplicated.
        """
        if filepath in sources_data:
            try:
                # Check if the file still exists in Gemini
                gemini_client.files.get(name=sources_data[filepath])
                print(f"Reusing existing file at path: {filepath} with ID {sources_data[filepath]}")
                return sources_data[filepath]
            except Exception as e:
                print(f"File at path {filepath} with ID {sources_data[filepath]} not found in Gemini, re-uploading...")
                del sources_data[filepath]
        
        try:
            uploaded_file = gemini_client.files.upload(file=filepath)
            sources_data[filepath] = uploaded_file.name
            print(f"Uploaded new file from path: {filepath} with ID {uploaded_file.name}")
            return uploaded_file.name
        except Exception as e:
            print(f"Error uploading {filepath}: {e}")
            return None

    subjects = {
        "reading_and_writing": {
            "craft_and_structure": [
                "cross_text_connections",
                "text_structure_and_purpose",
                "words_in_context",
            ],
            "expression_of_ideas": [
                "rhetorical_synthesis",
                "transitions",
            ],
            "information_and_ideas": [
                "central_ideas_and_details",
                "command_of_evidence",
                "inferences",
            ],
            "standard_english_conventions": [
                "boundaries",
                "form_structure_and_sense",
            ],
        },
        "math": {
            "algebra": [
                "linear_equations_in_one_variable",
                "linear_equations_in_two_variables",
                "linear_functions",
                "systems_of_two_linear_equations_in_two_variables",
                "linear_inequalities_in_one_or_two_variables",
            ],
            "advanced_math": [
                "equivalent_expressions",
                "nonlinear_equations_in_one_variable_and_systems_of_equations_in_two_variables",
                "nonlinear_functions",
            ],
            "problem_solving_and_data_analysis": [
                "ratios_rates_proportional_relationships_and_units",
                "percentages",
                "one_variable_data_distributions_and_measures_of_center_and_spread",
                "two_variable_data_models_and_scatterplots",
                "probability_and_conditional_probability",
                "inference_from_sample_statistics_and_margin_of_error",
                "evaluating_statistical_claims_observational_studies_and_experiments",
            ],
            "geometry_and_trigonometry": [
                "area_and_volume",
                "lines_angles_and_triangles",
                "right_triangles_and_trigonometry",
                "circles",
            ],
        },
    }

    difficulties = ["easy", "medium", "hard"]

    sources_nested = {}

    for subject, domains in subjects.items():
        sources_nested[subject] = {}
        for domain, skills in domains.items():
            sources_nested[subject][domain] = {}
            for skill in skills:
                sources_nested[subject][domain][skill] = {}
                for difficulty in difficulties:
                    path = f"sources/{subject}/{domain}/{skill}/{difficulty}/{skill}.pdf"
                    sources_nested[subject][domain][skill][difficulty] = upload_or_reuse(path)

    # Save updated sources metadata
    with open(SOURCES_FILE, "w") as f:
        json.dump(sources_data, f, indent=4)

    return sources_nested

                    
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


    with open("prompts/math/algebra/linear_equations_in_one_variable.txt", "r") as f:
        linear_equations_in_one_variable_prompt = f.read()
    with open("prompts/math/algebra/linear_equations_in_two_variables.txt", "r") as f:
        linear_equations_in_two_variables_prompt = f.read()
    with open("prompts/math/algebra/linear_functions.txt", "r") as f:
        linear_functions_prompt = f.read()
    with open("prompts/math/algebra/systems_of_two_linear_equations_in_two_variables.txt", "r") as f:
        systems_of_two_linear_equations_in_two_variables_prompt = f.read()
    with open("prompts/math/algebra/linear_inequalities_in_one_or_two_variables.txt", "r") as f:
        linear_inequalities_in_one_or_two_variables_prompt = f.read()
    '''
    # Advanced Math
    with open("prompts/math/advanced_math/equivalent_expressions.txt", "r") as f:
        equivalent_expressions_prompt = f.read()
    with open("prompts/math/advanced_math/nonlinear_equations_in_one_variable_and_systems_of_equations_in_two_variables.txt", "r") as f:
        nonlinear_equations_in_one_variable_and_systems_of_equations_in_two_variables_prompt = f.read()
    with open("prompts/math/advanced_math/nonlinear_functions.txt", "r") as f:
        nonlinear_functions_prompt = f.read()

    # Problem-Solving and Data Analysis
    with open("prompts/math/problem_solving_and_data_analysis/ratios_rates_proportional_relationships_and_units.txt", "r") as f:
        ratios_rates_proportional_relationships_and_units_prompt = f.read()
    with open("prompts/math/problem_solving_and_data_analysis/percentages.txt", "r") as f:
        percentages_prompt = f.read()
    with open("prompts/math/problem_solving_and_data_analysis/one_variable_data_distributions_and_measures_of_center_and_spread.txt", "r") as f:
        one_variable_data_distributions_and_measures_of_center_and_spread_prompt = f.read()
    with open("prompts/math/problem_solving_and_data_analysis/two_variable_data_models_and_scatterplots.txt", "r") as f:
        two_variable_data_models_and_scatterplots_prompt = f.read()
    with open("prompts/math/problem_solving_and_data_analysis/probability_and_conditional_probability.txt", "r") as f:
        probability_and_conditional_probability_prompt = f.read()
    with open("prompts/math/problem_solving_and_data_analysis/inference_from_sample_statistics_and_margin_of_error.txt", "r") as f:
        inference_from_sample_statistics_and_margin_of_error_prompt = f.read()
    with open("prompts/math/problem_solving_and_data_analysis/evaluating_statistical_claims_observational_studies_and_experiments.txt", "r") as f:
        evaluating_statistical_claims_observational_studies_and_experiments_prompt = f.read()

    # Geometry and Trigonometry
    with open("prompts/math/geometry_and_trigonometry/area_and_volume.txt", "r") as f:
        area_and_volume_prompt = f.read()
    with open("prompts/math/geometry_and_trigonometry/lines_angles_and_triangles.txt", "r") as f:
        lines_angles_and_triangles_prompt = f.read()
    with open("prompts/math/geometry_and_trigonometry/right_triangles_and_trigonometry.txt", "r") as f:
        right_triangles_and_trigonometry_prompt = f.read()
    with open("prompts/math/geometry_and_trigonometry/circles.txt", "r") as f:
        circles_prompt = f.read()

    '''

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

    with open ("prompts/humanfeedbackprompt.txt", "r") as f:
        human_feedback_prompt = f.read()

    with open ("prompts/aifeedbackprompt.txt", "r") as f:
        ai_feedback_prompt = f.read()

    return {
        "reading_and_writing": {
            "craft_and_structure": {
                "words_in_context": words_in_context_prompt,
                "text_structure_and_purpose": text_structure_and_purpose_prompt,
                "cross_text_connections": cross_text_connections_prompt
            },
            "information_and_ideas": {
                "central_ideas_and_details": central_ideas_and_details_prompt,
                "command_of_evidence": command_of_evidence_prompt,
                "inferences": inferences_prompt
            },
            "standard_english_conventions": {
                "boundaries": boundaries_prompt,
                "form_structure_and_sense": form_structure_and_sense_prompt
            },
            "expression_of_ideas": {
                "rhetorical_synthesis": rhetorical_synthesis_prompt,
                "transitions": transitions_prompt
            },
        },
        "math": { # NEW MATH SUPERSTRUCTURE
            "algebra": {
                "linear_equations_in_one_variable": linear_equations_in_one_variable_prompt,
                "linear_equations_in_two_variables": linear_equations_in_two_variables_prompt,
                "linear_functions": linear_functions_prompt,
                "systems_of_two_linear_equations_in_two_variables": systems_of_two_linear_equations_in_two_variables_prompt,
                "linear_inequalities_in_one_or_two_variables": linear_inequalities_in_one_or_two_variables_prompt,
            },

        },
        # Miscellaneous Prompts (kept at the same top level)
        "main_prompt": main_prompt,
        "format_prompt": format_prompt,
        "explanation_prompt": explanation_prompt,
        "evaluation_prompt": evaluation_prompt,
        "refine_prompt": refine_prompt,
        "human_feedback_prompt": human_feedback_prompt,
        "ai_feedback_prompt": ai_feedback_prompt
    }





prompts = load_prompts()

sources = load_sources()
def get_questions_by_difficulty(questions_data, section, skill_category, target_difficulty, limit=10):
    """
    Retrieves a list of questions filtered by a specific difficulty level
    from the loaded questions data.
    
    Args:
        questions_data (dict): The dictionary containing all loaded questions
            (e.g., from load_questions_from_firebase).
        section (str): The section of the SAT (e.g., "reading_and_writing", "math").
        skill_category (str): The skill category within the section (e.g., "craft_and_structure", "algebra").
        target_difficulty (str): The desired difficulty level ("easy", "medium", "hard").
        limit (int, optional): Maximum number of questions to return. If None, returns all matching questions.
            If the number of matching questions exceeds this limit, randomly selects up to this many questions.
    
    Returns:
        list: A list of question dictionaries that match the specified difficulty.
            Returns an empty list if no questions are found for the criteria.
            If limit is specified and exceeded, returns a random sample of questions up to the limit.
    """
    if "SAT" not in questions_data:
        return []
    
    section_data = questions_data["SAT"].get(section, {})
    domain_questions = []
    
    # Iterate through all questions within the section
    for question in section_data:
        if (question.get("difficulty", "").lower() == target_difficulty.lower() and 
            question.get("skill_category", "").lower() == skill_category.lower()):
            domain_questions.append(question)
    
    # Apply limit with random selection if specified and exceeded
    if limit is not None and len(domain_questions) > limit:
        domain_questions = random.sample(domain_questions, limit)
    
    return domain_questions


def get_feedback_by_difficulty(feedback_data, section, difficulty, limit=15):
    """
    Retrieves feedback entries filtered by difficulty level.
    
    Args:
        feedback_data (dict): The dictionary containing all feedback data.
        section (str): The section to filter by.
        difficulty (str): The difficulty level to filter by.
        limit (int, optional): Maximum number of feedback entries to return. If None, returns all matching entries.
            If the number of matching entries exceeds this limit, randomly selects up to this many entries.
    
    Returns:
        list: A list of feedback entries that match the specified difficulty.
            If limit is specified and exceeded, returns a random sample of entries up to the limit.
    """
    section_data = feedback_data.get(section, {})
    difficulty_feedback = []
    
    for question_id, entries in section_data.items():
        for feedback in entries:
            # Check if feedback contains a difficulty key (inside .get("feedback") if saved that way)
            feedback_info = feedback.get("feedback", feedback)  # handles both nested and flat formats
            feedback_difficulty = feedback_info.get("original_question", {}).get("difficulty", "").lower()
            
            if feedback_difficulty == difficulty.lower():
                difficulty_feedback.append(feedback)
    
    # Apply limit with random selection if specified and exceeded
    if limit is not None and len(difficulty_feedback) > limit:
        difficulty_feedback = random.sample(difficulty_feedback, limit)
    
    return difficulty_feedback


def evaluate_question_difficulty(raw_question_data, section, domain, skill_category, difficulty, ref_system_prompt):
    print("# Evaluating difficulty\n")
    evaluation_system_prompt = prompts["evaluation_prompt"]
    evaluation_prompt = f"Please evaluate the difficulty of the following question: {raw_question_data}.\nThe question is from the section {section}, domain {domain}, skill category {skill_category}, and is of difficulty {difficulty}.\n"
    reference_prompt = f"Original system prompt, for reference: {ref_system_prompt}"
    print("evaluating difficulty")
    all_questions_text = json.dumps(all_questions)
    difficulty_questions = str(get_questions_by_difficulty(all_questions, str(section), skill_category, str(difficulty), 25))
    response = gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[evaluation_prompt, difficulty_questions, reference_prompt],
        config=GenerateContentConfig(
            system_instruction=[evaluation_system_prompt]
        )
    )
    print(f"metadata: {response.usage_metadata}")
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
    print(f"metadata: {response.usage_metadata}")
    return response.text

def format_question(raw_question_data, section, domain, skill_category, difficulty):
    format_prompt = prompts["format_prompt"]
    format_prompt = format_prompt.format(section=section, domain=domain, skill_category=skill_category, difficulty=difficulty)
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
    print(f"format question response: {gemini_response.text}")
    print(f"metadata: {gemini_response.usage_metadata}")
    #response = response.choices[0].message.content
    gemini_response = gemini_response.text

    question = re.search(r'\{.*\}', gemini_response, re.DOTALL)
    if question:
        question_json = question.group(0) # changed from question.group(0)
        print (f"Question json generated: {json.loads(question_json)}")
        update_local_questions_data(json.loads(question_json))
        return json.loads(question_json)
        return question
    else:
        raise ValueError("No valid JSON found in response")



def generate_ai_feedback(question, section, domain, skill_category, difficulty, ref_system_prompt):
    ai_feedback_system_prompt = prompts["ai_feedback_prompt"]
    section_questions = str(all_questions["SAT"].get(section, []))

    difficulty_questions = str(get_questions_by_difficulty(all_questions, str(section),  skill_category, str(difficulty)))

    difficulty_feedback = str(get_feedback_by_difficulty(all_feedback, str(section), str(difficulty)))

    ref_system_prompt = f"reference system prompt: {ref_system_prompt}. This question should be of difficulty {difficulty}. Do not take an easy question and make it a hard, or vice versa, for example."
    feedback_response = gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[str(question), "feedback:", difficulty_feedback, "other questions that have been generated of this difficulty: ", difficulty_questions, "source questions", sources[section][domain][skill_category][difficulty], ref_system_prompt],
        config=GenerateContentConfig(
            system_instruction=[ai_feedback_system_prompt],
            temperature=1.0
        ),
    )
    print(f"feedback metadata: {feedback_response.usage_metadata}")
    feedback_response = feedback_response.text

    print(feedback_response)
    
    return feedback_response


def get_ai_feedback(question, section, domain, skill_category, difficulty, feedback, ref_system_prompt):
    human_feedback_system_prompt = prompts["human_feedback_prompt"]
    section_questions = str(all_questions["SAT"].get(section, []))
    difficulty_questions = str(get_questions_by_difficulty(all_questions, str(section), skill_category, str(difficulty)))
    ref_system_prompt = f"reference system prompt: {ref_system_prompt}"
    feedback_prompt=f"section: {section}, domain: {domain}, skill_category: {skill_category}, difficulty:{difficulty}. Please ensure that the question remains in the target difficulty {difficulty}. Please ensure response is in proper markdown for formatting, and that you only test concepts that appear in the source questions. You do have more freedom for readining and writing questions however, those should be more diverse"
    feedback_response = gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[feedback_prompt, str(question), str(feedback), difficulty_questions, "source questions: ", sources[section][domain][skill_category][difficulty], ref_system_prompt],
        config=GenerateContentConfig(
            system_instruction=[human_feedback_system_prompt],
            temperature=1.0
        ),
    )

    feedback_response = feedback_response.text
   

    return feedback_response

    

def generate_question(system_prompt, user_prompt, section, domain, skill_category, difficulty, messages):
    print("# Generating Question\n")
    #messages.append({"role": "system", "content": system_prompt})
    #messages.append({"role": "user", "parts": [user_prompt]})

    ''' response = chatgpt_client.chat.completions.create(
        model="o4-mini",
        messages=messages,
        temperature=1,
    )
    '''
    section_questions = all_questions["SAT"].get(section, [])
    difficulty_questions = str(get_questions_by_difficulty(all_questions, section, skill_category, difficulty))
    difficulty_session_questions = str(get_questions_by_difficulty(messages, section, skill_category, difficulty))

    if domain == "reading_and_writing":
        generated_questions = f"Here are the existing questions, including the questions generated during this session and those that are already in the database. Make your next one different than these to ensure question diversity (no copycats!)THis session: {difficulty_session_questions} from database: \n{difficulty_questions}. THESE ARE NOT SOURCE QUESTIONS, THEY ARE PROVIDED ONLY SO YOU CAN ENSURE QUESTION DIVERSITY"
    else:
        generated_questions = ""
    #print ("Generating questions!")
# print(generated_questions)

    gemini_response = gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        #messages = str(messages)
        #print(generated_questions)
        contents=["source questions from CollegeBoard: ", sources[section][domain][skill_category][difficulty], str(generated_questions), user_prompt],
        config=GenerateContentConfig(
            system_instruction=[system_prompt],
            temperature=1.0
        ),
    )

    question = gemini_response.text
    print(f"question draft: {question}")
# print(f"# Question: {question}")
    print(f"metadata: {gemini_response.usage_metadata}")

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

    #question = refine_question(question, evaluation, section=section, domain=domain, skill_category=skill_category, difficulty=difficulty, target_difficulty_ranking=target_difficulty_ranking, ref_system_prompt=system_prompt)
    #evaluation, difficulty_ranking = evaluate_question_difficulty(question, section=section, domain=domain, skill_category=skill_category, difficulty=difficulty, target_difficulty_ranking=target_difficulty_ranking, ref_system_prompt=system_prompt)
    ai_feedback = generate_ai_feedback(question, section, domain, skill_category, difficulty, system_prompt)

    question = get_ai_feedback(question, section, domain, skill_category, difficulty, ai_feedback, system_prompt)

    

    formatted_response = format_question(raw_question_data=question, section=section, domain=domain, skill_category=skill_category, difficulty=difficulty)
    question = formatted_response
    #question = re.search(r'\{.*\}', formatted_response, re.DOTALL)

    if question:
        question_json = question # changed from question.group(0)
        #print (f"Question json generated: {json.loads(question_json)}")
        #update_local_questions_data(json.loads(question_json))
        #return json.loads(question_json)
        return question
    else:
        raise ValueError("No valid JSON found in response")

def load_feedback_log():
    if not os.path.exists("feedback_log.json"):
        return []  # Return empty list if file doesn't exist

    try:
        with open("feedback_log.json", "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        # Handle corrupt file
        return []

def append_to_feedback_log(feedback_entry, log_file="feedback_log.json"):
    """
    Appends a feedback entry to the local feedback log.
    If the file does not exist, it will create it.
    """
    try:
        feedback_log = []
        if os.path.exists(log_file):
            with open(log_file, "r") as f:
                feedback_log = json.load(f)
                if not isinstance(feedback_log, list):
                    print("Feedback log is corrupted. Resetting to empty list.")
                    feedback_log = []

        feedback_log.append(feedback_entry)

        with open(log_file, "w") as f:
            json.dump(feedback_log, f, indent=4)

        print("Feedback successfully appended to feedback_log.json")

    except Exception as e:
        print(f"Error appending to feedback log: {e}")
def save_human_feedback(feedback, question_id):
    try:
        original_question = feedback["original_question"]

        if not isinstance(original_question, dict):
            raise ValueError("original_question must be a dict.")

        section = original_question.get("section")
        if not isinstance(section, str):
            raise ValueError("Missing or invalid 'section' in original_question.")

        timestamp = datetime.utcnow().isoformat()

        feedback_data = {
            "feedback": feedback,
            "timestamp": timestamp,
            "id": question_id,
        }

        # Path: feedback/SAT/{section}/{question_id}
        question_doc_ref = db.collection("feedback") \
                            .document("SAT") \
                            .collection(section) \
                            .document(question_id)

        # Ensure the question document exists (you can also save metadata here)
        question_doc_ref.set({
            "question_id": question_id,
            "timestamp": timestamp
        }, merge=True)  # merge=True ensures existing data isn't overwritten

        # Add feedback entry to the "entries" subcollection
        print(f"Writing feedback to: feedback/SAT/{section}/{question_id}/entries")
        question_doc_ref.collection("entries").add(feedback_data)

        print("✅ Feedback successfully added.")

    except Exception as e:
        logging.error(f"❌ Failed to add feedback: {e}")
        return None



def get_human_feedback(question, section, skill_category, difficulty, question_index, feedback: str, ref_system_prompt):
    human_feedback_system_prompt = prompts["human_feedback_prompt"]
    section_questions = str(all_questions["SAT"].get(section, []))
    difficulty_questions = str(get_questions_by_difficulty(all_questions, str(section), str(skill_category), str(difficulty)))

    feedback_response = gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[str(question), str(feedback), str(difficulty_questions), sources[question["section"]][question["domain"]][question["skill_category"]][question["difficulty"]], ref_system_prompt],
        config=GenerateContentConfig(
            system_instruction=[human_feedback_system_prompt],
            temperature=1.0
        ),
    )

    feedback_response = feedback_response.text
    updated_question = re.search(r'\{.*\}', feedback_response, re.DOTALL)



    if updated_question:
        updated_question_json = updated_question.group(0)
        #print (f"Question json generated: {json.loads(updated_question_json)}")
        update_local_questions_data(json.loads(updated_question_json))
        append_to_feedback_log({
        "original_question": question,
        "updated_question": feedback_response,
        "feedback": feedback,
        "original_difficulty_rating": question.get("difficulty_rating", "unknown"),
        "question_index": question_index,
        "timestamp": datetime.utcnow().isoformat()
        })
        return json.loads(updated_question_json)
    else:
        raise ValueError("No valid JSON found in response")



def add_question(question):
    try:
        # Validate input
        if not isinstance(question, dict):
            raise ValueError("Input must be a dictionary.")

        required_fields = ["section"]
        for field in required_fields:
            if field not in question or not isinstance(question[field], str):
                raise ValueError(f"Missing or invalid field: {field}")

        # Add metadata
        question["timestamp"] = datetime.utcnow().isoformat()
        question["id"] = question_id = str(uuid.uuid4())
        question["test"] = "SAT"

        # Save to Firestore
        db.collection("questions") \
        .document(question["test"]) \
        .collection(question["section"]) \
        .document(question_id) \
        .set(question)

        return question_id

    except Exception as e:
        logging.error(f"Failed to add question: {e}")
        return None  # or raise if you want the caller to handle it
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