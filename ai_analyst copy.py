import chromadb
import json

# --- CONFIGURATION ---
# 1. IMPORTANT: Set the path to your ChromaDB folder.
db_path = "chroma_store"

# 2. IMPORTANT: Set the name for your output text file.
output_file_name = "chroma_export_ALL.txt"
# ---------------------

print(f"Connecting to ChromaDB at: {db_path}")
try:
    # Connect to the persistent ChromaDB client
    client = chromadb.PersistentClient(path=db_path)
except Exception as e:
    print(f"Error connecting to ChromaDB: {e}")
    exit()

# Get a list of all collections
try:
    all_collections = client.list_collections()
    if not all_collections:
        print("No collections found in the database. Nothing to export.")
        exit()

    collection_names = [c.name for c in all_collections]
    print(f"Found {len(collection_names)} collections to export: {collection_names}")

except Exception as e:
    print(f"Error listing collections: {e}")
    exit()


# Open the file once to write all data
try:
    with open(output_file_name, 'w', encoding='utf-8') as f:
        print(f"\nStarting export process. Writing all data to '{output_file_name}'...")
        
        # Loop through each collection object
        for collection_obj in all_collections:
            collection_name = collection_obj.name
            
            # Write a main header for the current collection in the text file
            f.write("\n" + "#"*35 + f" START OF COLLECTION: {collection_name} " + "#"*35 + "\n\n")
            print(f"\nProcessing collection: '{collection_name}'...")

            # Get the actual collection and retrieve all its data
            collection = client.get_collection(name=collection_name)
            results = collection.get()

            # Extract the data
            ids = results.get('ids', [])
            documents = results.get('documents', [])
            metadatas = results.get('metadatas', [])
            item_count = len(ids)
            
            print(f"-> Found {item_count} items in this collection.")

            if item_count == 0:
                f.write("This collection is empty.\n")
                continue # Skip to the next collection

            # Loop through each document in the current collection
            for i in range(item_count):
                doc_id = ids[i]
                metadata = metadatas[i] if metadatas and i < len(metadatas) else {}
                document_content = documents[i] if documents and i < len(documents) else "N/A"

                # Write formatted output to the file
                f.write("="*80 + "\n")
                f.write(f"DOCUMENT ID: {doc_id}\n")
                f.write("-" * 20 + "\n")
                f.write(f"METADATA: {json.dumps(metadata, indent=2)}\n")
                f.write("-" * 20 + "\n")
                f.write("CONTENT:\n")
                f.write(document_content + "\n\n")

            f.write("#"*35 + f" END OF COLLECTION: {collection_name} " + "#"*35 + "\n\n")

    print("\n✅ Export complete!")
    print(f"All data from all collections has been successfully saved to '{output_file_name}'.")

except Exception as e:
    print(f"\nAn error occurred during the export process: {e}")