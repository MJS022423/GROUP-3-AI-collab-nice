# standalone_qa_generator.py
"""
A standalone tool to automatically generate a JSON file of question-and-answer pairs
based on a student's profile from the database.
This script is completely independent of ai_analyst.py.
"""
import json
import os
import requests
import chromadb
from typing import Dict, Any, List

# --- CONFIGURATION ---
# THIS IS WHERE YOU WILL CHANGE THE VALUE, FEED NIYO YUNG PDM ID HERE DAPAT STRING, EDIT NIYO NALANG NUMBER OF QUESTIONS IF GUSTO NIYO
STUDENT_ID_TO_TEST = "PDM-2025-0001" 
NUMBER_OF_QUESTIONS = 5
OUTPUT_FILENAME = "generated_qa.json"
CHROMA_DB_PATH = "./chroma_store" # The path to your ChromaDB database folder


class SimpleLLMService:
    """A simplified client for interacting with the Mistral API."""
    def __init__(self, api_key: str, api_url: str, model: str):
        self.api_key = api_key
        self.api_url = api_url
        self.model = model

    def execute(self, system_prompt: str, user_prompt: str) -> str:
        """Executes a request to the Mistral API with retry logic."""
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        payload = {
            "model": self.model,
            "messages": messages,
            "response_format": {"type": "json_object"}
        }

        for attempt in range(3): 
            try:
                resp = requests.post(self.api_url, headers=headers, data=json.dumps(payload), timeout=120)
                resp.raise_for_status()
                rj = resp.json()
                return rj['choices'][0]['message']['content'].strip()
            except Exception as e:
                print(f"LLM attempt {attempt+1} failed: {e}")
                if attempt == 2:
                    return f'{{"error": "Failed to connect to AI service: {e}"}}'
        return '{"error": "LLM execution failed after retries."}'


def get_profile_from_db(pdm_id: str, db_path: str) -> List[dict]:
    """Connects to ChromaDB and retrieves a student profile by their ID."""
    try:
        client = chromadb.PersistentClient(path=db_path)
        all_collections = client.list_collections()
        student_collections = [c for c in all_collections if 'students' in c.name]
        
        all_docs = []
        for collection in student_collections:
            results = collection.get(
                where={"student_id": pdm_id},
                include=["metadatas", "documents"]
            )
            for i, doc_content in enumerate(results['documents']):
                all_docs.append({
                    "source_collection": collection.name,
                    "content": doc_content,
                    "metadata": results['metadatas'][i]
                })
        return all_docs
    except Exception as e:
        print(f"❌ Database error: Could not connect or query ChromaDB at path '{db_path}'. Error: {e}")
        return []


class QAGenerator:
    """Encapsulates the logic for the Q&A generation process."""

    def __init__(self, generator_llm: SimpleLLMService):
        self.llm = generator_llm

    def generate_and_save(self, pdm_id: str, count: int):
        print("="*50)
        print(f"🚀 Starting Q&A Generation for PDM ID: {pdm_id}")
        print("="*50)

        # Step 1: Retrieve the student's profile from the database
        print(f"1. Retrieving profile for {pdm_id} from ChromaDB...")
        profile_docs = get_profile_from_db(pdm_id=pdm_id, db_path=CHROMA_DB_PATH)

        if not profile_docs:
            print(f"❌ Could not retrieve a valid profile for {pdm_id}. Aborting.")
            return

        context_str = "\n\n".join([f"Source: {doc.get('source_collection')}\nContent:\n{doc.get('content')}" for doc in profile_docs])
        print("   ✅ Profile retrieved successfully.")

        # Step 2: Call the AI to generate the Q&A pairs
        print(f"2. Asking AI to generate {count} question-answer pairs...")
        system_prompt = "You are an expert in creating training data. Your job is to generate a list of question-and-answer pairs based ONLY on the provided text."
        user_prompt = f"""
        Here is a student's profile text:
        ---
        {context_str}
        ---
        Based ONLY on the text above, act as an interviewer and generate a JSON object with a single key "qa_pairs".
        The value of "qa_pairs" should be a list containing exactly {count} unique JSON objects.
        Each object must have two keys:
        1. "question": A question phrased in the SECOND PERSON, as if you are speaking directly to the student (e.g., "What is YOUR student ID?"). Focus on less obvious or more specific details from the profile.
        2. "answer": The precise, factual answer to that question, taken directly from the text.
        """

        response_str = self.llm.execute(system_prompt, user_prompt)
        print("   ✅ AI response received.")
        
        # Step 3: Save the final JSON to a file
        print(f"3. Saving the output to '{OUTPUT_FILENAME}'...")
        try:
            # --- ✨ FIX: Add these two lines to delete the old file first ---
            if os.path.exists(OUTPUT_FILENAME):
                os.remove(OUTPUT_FILENAME)

            # The rest of the code is the same
            qa_json = json.loads(response_str)
            with open(OUTPUT_FILENAME, "w", encoding="utf-8") as f:
                json.dump(qa_json, f, indent=2, ensure_ascii=False)
            print(f"   ✅ Successfully saved the Q&A pairs.")
            print("\n--- FILE CONTENT ---")
            print(json.dumps(qa_json, indent=2))
            print("--------------------")
        except json.JSONDecodeError:
            print(f"❌ Failed to decode JSON from the AI. The response was: {response_str}")
        
        print("\n="*50)
        print("🎉 Process Complete.")
        print("="*50)

# ==============================
# Main Execution Block
# ==============================
def main():
    """Main function to set up and run the Q&A generation tool."""
    print("Initializing Standalone Q&A Generator...")
    
    # Load configuration from config.json
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            full_config = json.load(f)
            online_config = full_config['online']
    except (FileNotFoundError, KeyError) as e:
        print(f"❌ FATAL: Could not load 'online' configuration from config.json. Error: {e}")
        return

    # Initialize the simplified LLM service for the generator
    generator_llm_service = SimpleLLMService(
        api_key=online_config.get("mistral_api_key"),
        api_url=online_config.get("mistral_api_url"),
        model=online_config.get("synth_model")
    )

    # Create and run the generator
    generator = QAGenerator(generator_llm=generator_llm_service)
    generator.generate_and_save(STUDENT_ID_TO_TEST, NUMBER_OF_QUESTIONS)

if __name__ == "__main__":
    main()