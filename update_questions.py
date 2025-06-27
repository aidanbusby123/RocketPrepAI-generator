import firebase_admin
from firebase_admin import credentials, firestore
from google import genai
from google.genai.types import GenerateContentConfig
import os
import json
import re
from google.api_core.retry import Retry
# Initialize Firebase Admin SDK
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)

db = firestore.client()

gemini_api_key = os.environ["GEMINI_API_KEY"]
gemini_client = genai.Client(api_key=gemini_api_key)

with open ("prompts/explanationprompt.txt") as f:
    explanation_system_prompt = f.read()

def add_section_field():
    """Adds the 'section' field to all existing questions in Firebase."""

    questions_ref = db.collection("questions")
    docs = questions_ref.stream(retry=Retry())

    for doc in docs:
        try:
            question_data = doc.to_dict()
            if "section" not in question_data:
                # Add the "section" field with a default value
                question_data["section"] = "reading_and_writing"  # Set your desired default section
                doc_ref = questions_ref.document(doc.id)
                doc_ref.set(question_data)
                print(f"Added 'section' field to question with ID: {doc.id}")
            else:
                print(f"Question with ID: {doc.id} already has a 'section' field.")

            if "explanations" not in question_data:
                question = question_data["question"]
                explanation_prompt = f"Please generate the answer explanations for the following question: {question}. "

                explanations_response = gemini_client.models.generate_content(
                model="gemini-2.5-pro-preview-06-05",
                contents=[explanation_prompt],
                    config=GenerateContentConfig(
                        system_instruction=[explanation_system_prompt]
                    )
                )
                explanations = re.search(r'\{.*\}', explanations_response.text, re.DOTALL)
                if explanations:
                    explanations = explanations.group(0)
                    explanations = json.loads(explanations)
                else:
                    raise ValueError("No valid JSON found in response")
                

                question_data["explanations"] = explanations
                doc_ref = questions_ref.document(doc.id)
                doc_ref.set(question_data)

        except Exception as e:
            print(f"Error processing document {doc.id}: {e}")

if __name__ == "__main__":
    add_section_field()
    print("Script completed.")