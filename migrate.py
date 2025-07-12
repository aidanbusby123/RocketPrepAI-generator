import os
import asyncio
from firebase_admin import firestore, credentials, exceptions as firebase_exceptions
import firebase_admin

# --- Firebase Admin SDK Initialization for the script ---
def initialize_firebase_for_migration():
    if not firebase_admin._apps:
        try:
            if os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY_PATH"):
                cred = credentials.Certificate(os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY_PATH"))
            else:
                # IMPORTANT: Replace with the actual path to your service account key file
                # This path should be accessible from where your script is run.
                # For production, always use environment variables!
                print("WARNING: 'FIREBASE_SERVICE_ACCOUNT_KEY_PATH' not set. Using default local path.")
                cred = credentials.Certificate("serviceAccountKey.json") # <<< UPDATE THIS PATH
            firebase_admin.initialize_app(cred)
            print("Firebase Admin SDK initialized successfully for migration script.")
        except Exception as e:
            print(f"ERROR: Failed to initialize Firebase Admin SDK: {e}")
            raise

# --- Constants for the new nested structure ---
# These should be consistent across your application
OLD_QUESTIONS_COLLECTION = "questions"
SAT_PARENT_COLLECTION = "questions"
SAT_DOCUMENT_ID = "SAT"
RW_SUBCOLLECTION_NAME = "reading_and_writing"
MATH_SUBCOLLECTION_NAME = "math" # Defined for completeness, though not used in this specific R&W migration

def run_migration():
    """
    PERFORMS ACTUAL MIGRATION: Moves questions from the top-level 'questions' collection
    to the new nested structure: questions/sat/reading_and_writing.
    Assumes all existing questions are Reading & Writing.
    This function initializes Firebase itself for standalone execution.
    """
    initialize_firebase_for_migration()
    db = firestore.client()

    print("\n--- Starting ACTUAL question migration ---")
    old_collection_ref = db.collection(OLD_QUESTIONS_COLLECTION)

    # Reference to the SAT document which will contain the subcollections
    sat_doc_ref = db.collection(SAT_PARENT_COLLECTION).document(SAT_DOCUMENT_ID)

    migrated_count = 0
    errors = []

    batch_size = 499 # Max 500 operations per batch, keep it safe
    current_batch = db.batch()
    batch_operations_count = 0

    # Ensure the 'sat' document exists or will be created implicitly.
    # Explicitly setting it here for metadata or to ensure its existence.
    try:
        sat_doc_ref.set({"_last_migration_timestamp": firestore.SERVER_TIMESTAMP}, merge=True)
        print(f"Ensured '{sat_doc_ref.path}' document exists.")
    except firebase_exceptions.FirebaseError as e:
        print(f"CRITICAL ERROR: Could not ensure 'sat' document exists: {e}")
        raise RuntimeError(f"Migration failed at setup: {e}")


    # Fetch all documents from the old collection
    try:
        docs_stream = old_collection_ref.stream()
        docs_list = list(docs_stream) # Convert stream to a list to get count and iterate
        if not docs_list:
            print("No questions found in the old collection to migrate.")
            return {"message": "No questions found to migrate.", "migrated_count": 0}
        print(f"Found {len(docs_list)} questions in '{OLD_QUESTIONS_COLLECTION}'.")
    except firebase_exceptions.FirebaseError as e:
        print(f"CRITICAL ERROR: Firebase error fetching documents from '{OLD_QUESTIONS_COLLECTION}': {e}")
        raise RuntimeError(f"Migration failed during data fetch: {e}")

    # Process each document
    for doc in docs_list:
        question_data = doc.to_dict()
        original_doc_id = doc.id

        # Assume all are Reading & Writing as per user's request
        target_subcollection_name = RW_SUBCOLLECTION_NAME

        # Construct the new document reference in the nested structure
        new_doc_ref = sat_doc_ref.collection(target_subcollection_name).document(original_doc_id)
        
        # Add to batch for writing to the new location
        current_batch.set(new_doc_ref, question_data)

        # Add to batch for deleting from the old top-level collection
        current_batch.delete(old_collection_ref.document(original_doc_id))
        
        batch_operations_count += 2 # 1 set + 1 delete
        migrated_count += 1

        # Commit batch if it reaches size limit
        if batch_operations_count >= batch_size:
            try:
                current_batch.commit()
                print(f"Committed a batch of {batch_operations_count} operations.")
            except firebase_exceptions.FirebaseError as e:
                errors.append(f"Error committing batch for documents (up to {original_doc_id}): {e}")
                print(f"ERROR: Batch commit failed: {e}")
                # For critical migrations, you might want to stop on the first error:
                raise RuntimeError(f"Migration batch failed unexpectedly: {e}")
            finally:
                current_batch = db.batch() # Start a new batch
                batch_operations_count = 0

    # Commit any remaining operations in the last batch
    if batch_operations_count > 0:
        try:
            current_batch.commit()
            print(f"Committed final batch of {batch_operations_count} operations.")
        except firebase_exceptions.FirebaseError as e:
            errors.append(f"Error committing final batch: {e}")
            print(f"ERROR: Final batch commit failed: {e}")
            raise RuntimeError(f"Migration final batch failed unexpectedly: {e}")

    if errors:
        print(f"Migration completed with {migrated_count} documents processed, but with errors.")
        print("Errors:", errors)
        return {"message": "Migration completed with errors.", "migrated_count": migrated_count, "errors": errors}
    else:
        print(f"Migration completed successfully. {migrated_count} documents moved.")
        return {"message": "Migration completed successfully.", "migrated_count": migrated_count}

# This allows the script to be run directly from the command line
if __name__ == "__main__":
    # You can uncomment and set this if you want to test against the emulator directly from the script
    # os.environ["FIRESTORE_EMULATOR_HOST"] = "localhost:8080"
    
    # Run the asynchronous migration function
    run_migration()
