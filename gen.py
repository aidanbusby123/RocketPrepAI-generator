from openai import OpenAI
import sys
import argparse
import random
import os
import re
import json


questions = []

openai_api_key = os.environ["OPENAI_API_KEY"]
chatgpt_client = OpenAI(api_key=openai_api_key)

parser = argparse.ArgumentParser(description="tool to generate questions for RocketPrepAI")
parser.add_argument("outputfile", help="Name of output file")
parser.add_argument("--topics", nargs="+", choices=["all", "words_in_context"], default="all")
parser.add_argument("--difficulty", nargs="+", choices=["easy", "medium", "hard"], default="all")
parser.add_argument("--batch_number", default=10)
parser.add_argument("--epochs", default=1)

args = parser.parse_args()

base_user_prompt = "Please generate a question, where the correct answer is {random_choice} and the difficulty is {difficulty}"

def load_prompts():
    with open ("prompts/craft_and_structure/words_in_context.txt", "r") as f:
        words_in_context_prompt = f.read()

    with open ("prompts/mainprompt.txt", "r") as f:
        main_prompt = f.read()

    return {"craft_and_structure_prompts": {"words_in_context_prompt": words_in_context_prompt}, "main_prompt": main_prompt}

def generate_question(system_prompt, user_prompt, messages):
    messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})

    response = chatgpt_client.chat.completions.create(
        model="o4-mini",
        messages=messages,
        temperature=1,
    )

    response = response.choices[0].message.content
    messages.append({"role": "assistant", "content": response})
    
    question = re.search(r'\{.*\}', response, re.DOTALL)

    if question:
        question_json = question.group(0)
        return json.loads(question_json)
    else:
        raise ValueError("No valid JSON found in response")




def generate():
    chatgpt_messages = []
    
    prompts = load_prompts() # prompts for generating questions

    main_prompt = prompts["main_prompt"] # main prompt for SAT questions

    if args.difficulty == "all":
        difficulties = ["easy", "medium", "hard"]
    else:
        difficulties = args.difficulty

    for epoch in range (0, args.epochs):
        print(f"Epoch: {epoch}")
        for batch in range (0, args.batch_number):
            for domain, skills in prompts.items():
                for dif in difficulties:
                    if domain != "main_prompt":
                        print(f"Domain: {domain}")
                        for skill_key, skill_value in skills.items():
                            skill_prompt = skill_value.format(difficulty=dif)
                            system_prompt = main_prompt.format(domain=domain, skill_category=skill_key, formula=skill_prompt)
                            random_choice = random.choice(["A", "B", "C", "D"])
                            user_prompt = base_user_prompt.format(difficulty=dif, random_choice=random_choice)
                            question = generate_question(system_prompt, user_prompt, chatgpt_messages)
                            print(question)


generate()