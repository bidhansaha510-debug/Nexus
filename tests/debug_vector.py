"""Debug script for vector memory"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import chromadb
from config import DATA_DIR
from memory.embeddings import embedding_service
from memory.vector_store import vector_memory_store

# Direct ChromaDB test
print("=== ChromaDB Direct Test ===")
client = chromadb.PersistentClient(path=str(DATA_DIR / 'vector_store'))

# List collections
collections = client.list_collections()
print(f'Collections: {[c.name for c in collections]}')

for c in collections:
    count = c.count()
    print(f'\n  {c.name}: {count} items')
    if count > 0:
        # Get a sample
        results = c.get(limit=2, include=['documents', 'embeddings'])
        print(f'    Sample doc: {results["documents"][0][:80] if results["documents"] else "None"}...')
        if results.get('embeddings') is not None and len(results['embeddings']) > 0:
            print(f'    Embedding dim: {len(results["embeddings"][0])}')

# Test semantic search directly
print("\n=== Semantic Search Test ===")

# Get the episodic collection
episodic = client.get_collection("nexus_memory_episodic")
print(f"Episodic collection has {episodic.count()} items")

# Get all items to see what we have
all_items = episodic.get(limit=10, include=['documents'])
print(f"Sample documents:")
for i, doc in enumerate(all_items['documents'][:5]):
    print(f"  {i}: {doc[:80]}...")

# Generate embedding for query
print("\nGenerating query embedding...")
query = "France vacation"
query_embedding = embedding_service.encode(query).tolist()
print(f"Query embedding dim: {len(query_embedding)}")

# Query the collection
print(f"\nQuerying for: '{query}'")
results = episodic.query(
    query_embeddings=[query_embedding],
    n_results=5,
    include=['documents', 'distances']
)

print(f"Results: {len(results['ids'][0])} items")
for i, (id_, doc, dist) in enumerate(zip(results['ids'][0], results['documents'][0], results['distances'][0])):
    similarity = 1 - dist
    print(f"  {i}: similarity={similarity:.3f} dist={dist:.3f}")
    print(f"     {doc[:80]}...")

# Now test using vector_memory_store
print("\n=== VectorMemoryStore Test ===")
search_results = vector_memory_store.search(query="France vacation", n_results=5)
print(f"Found {len(search_results)} results")
for mem, sim in search_results:
    print(f"  sim={sim:.3f}: {mem.content[:60]}...")