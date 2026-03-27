import os
import itertools
from cliniq.rag.icd10_loader import load_icd10_codes
from pinecone import Pinecone
from cliniq_v2.api_client import OpenAIClient
from cliniq_v2.config import PINECONE_INDEX_NAME, PINECONE_NAMESPACE

def chunks(iterable, batch_size=100):
    it = iter(iterable)
    chunk = tuple(itertools.islice(it, batch_size))
    while chunk:
        yield chunk
        chunk = tuple(itertools.islice(it, batch_size))

def main():
    print("Loading local ICD-10 data...")
    codes = load_icd10_codes()
    descriptions = [code["description"] for code in codes]

    print("Authenticating with OpenAI...")
    client = OpenAIClient().client

    print("Authenticating with Pinecone...")
    pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))
    index = pc.Index(name=PINECONE_INDEX_NAME)

    print(f"Generating embeddings and uploading to Pinecone '{PINECONE_INDEX_NAME}'...")
    batch_size = 2048 # Using OpenAI max batch size for embeddings
    
    for i in range(0, len(descriptions), batch_size):
        batch_codes = codes[i : i + batch_size]
        batch_desc = descriptions[i : i + batch_size]
        
        # Get embeddings
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=batch_desc,
        )
        
        # Prepare for Pinecone
        vectors_to_upsert = []
        for j, code_entry in enumerate(batch_codes):
            vec_id = f"icd-{i + j}"
            vec_values = response.data[j].embedding
            vectors_to_upsert.append({
                "id": vec_id,
                "values": vec_values,
                "metadata": {
                    "code": code_entry["code"],
                    "description": code_entry["description"]
                }
            })
            
        print(f"Upserting {len(vectors_to_upsert)} vectors to Pinecone...")
        # Upsert in chunks of 100
        for sub_batch in chunks(vectors_to_upsert, batch_size=100):
            index.upsert(vectors=sub_batch, namespace=PINECONE_NAMESPACE)
            
    print("Population complete! Your application is ready to run live without FAISS.")

if __name__ == "__main__":
    if not os.environ.get("OPENAI_API_KEY") or not os.environ.get("PINECONE_API_KEY"):
        print("Please set your OPENAI_API_KEY and PINECONE_API_KEY environment variables first.")
        exit(1)
    main()
