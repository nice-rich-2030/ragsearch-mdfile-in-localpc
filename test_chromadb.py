#!/usr/bin/env python3
"""
Basic ChromaDB test to verify installation and functionality.
"""

import chromadb
from pathlib import Path

print("=" * 70)
print("ChromaDB Basic Test")
print("=" * 70)

# Test path
test_path = Path(__file__).parent / "test-chroma"
print(f"Test directory: {test_path}")

try:
    # Initialize client
    print("\n1. Initializing ChromaDB client...")
    client = chromadb.PersistentClient(path=str(test_path))
    print("   ✓ Client initialized")

    # Create collection
    print("\n2. Creating collection...")
    collection = client.get_or_create_collection(name="test_collection")
    print("   ✓ Collection created")

    # Add documents
    print("\n3. Adding documents...")
    collection.add(
        ids=["id1", "id2","id3", "id4", "id5", "id6"],
        documents=[
            "This is a document about pineapple",
            "This is a document about oranges"
            "That is a document about pineapple",
            "This was a document about oranges"
            "This is two document about pineapple",
            "This is a book about oranges"
        ]
    )
    print("   ✓ Documents added")

    # Query
    print("\n4. Querying collection...")
    results = collection.query(
        query_texts=["This is a query document about hawaii"],
        n_results=2
    )
    print("   ✓ Query completed")

    # Display results
    print("\n5. Results:")
    print(f"   IDs: {results['ids']}")
    print(f"   Documents: {results['documents']}")
    print(f"   Distances: {results['distances']}")

    print("\n" + "=" * 70)
    print("Test completed successfully!")
    print("=" * 70)

except Exception as e:
    print(f"\n✗ Error occurred: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
