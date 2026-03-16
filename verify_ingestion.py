#!/usr/bin/env python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'backend'))

from document_processor import list_ingested_files, get_collection, ingest_document
from config import CHROMA_COLLECTION_INTERNAL

print("=" * 60)
print("CHECKING KNOWLEDGE BASE STATUS")
print("=" * 60)

collection = get_collection(CHROMA_COLLECTION_INTERNAL)
print(f"Total chunks in bank_circulars: {collection.count()}")

files = list_ingested_files(CHROMA_COLLECTION_INTERNAL)
print(f"\nIngested documents ({len(files)}):")
for f in files:
    print(f"  - {f['filename']} ({f['total_chunks']} chunks)")

# Try to ingest test_with_text.pdf
print("\n" + "=" * 60)
test_file = Path(__file__) .parent / 'circulars' / 'test_with_text.pdf'
print(f"Attempting to ingest: {test_file.name}")
print("=" * 60)

result = ingest_document(test_file)
print(f"Result: {result}")

# Verify it was added
print("\n" + "=" * 60)
print("VERIFICATION")
print("=" * 60)
collection = get_collection(CHROMA_COLLECTION_INTERNAL)
new_count = collection.count()
print(f"Total chunks now: {new_count}")

files = list_ingested_files(CHROMA_COLLECTION_INTERNAL)
print(f"Total files: {len(files)}")
found_test = any(f['filename'] == 'test_with_text.pdf' for f in files)
if found_test:
    print("✓ test_with_text.pdf IS in the knowledge base")
else:
    print("✗ test_with_text.pdf NOT in the knowledge base")
