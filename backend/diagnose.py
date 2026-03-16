import requests
import json

BASE = "http://localhost:8000"

# 1. Check documents
print("=" * 60)
print("DOCUMENTS IN KNOWLEDGE BASE")
print("=" * 60)
r = requests.get(f"{BASE}/api/documents")
data = r.json()

print("\n--- Internal Circulars ---")
for d in data.get("internal_circulars", []):
    print(f"  {d['filename']} | ref={d.get('ref_no','?')} | chunks={d.get('total_chunks','?')}")
print(f"  Total: {len(data.get('internal_circulars', []))}")

print("\n--- Regulatory (Web) Docs ---")
for d in data.get("regulatory_docs", []):
    print(f"  {d['filename']}")
print(f"  Total: {len(data.get('regulatory_docs', []))}")

# 2. Check status
print("\n" + "=" * 60)
print("SERVER STATUS")
print("=" * 60)
r = requests.get(f"{BASE}/api/status")
status = r.json()
print(json.dumps(status, indent=2))

# 3. Test a query
print("\n" + "=" * 60)
print("TEST QUERY")
print("=" * 60)
query = "What is the interest rate for KCC loans?"
print(f"Query: {query}")
r = requests.post(f"{BASE}/api/chat", json={"query": query})
result = r.json()
print(f"\nAnswer: {result.get('answer', 'NO ANSWER')[:500]}")
print(f"\nChunks found: {result.get('chunks_found', 0)}")
print(f"Sources: {len(result.get('sources', []))}")
for s in result.get("sources", []):
    print(f"  - {s['filename']} | ref={s.get('ref_no')} | match={s.get('relevance')}%")

# 4. Check recent query logs
print("\n" + "=" * 60)
print("RECENT QUERY LOGS")
print("=" * 60)
r = requests.get(f"{BASE}/api/logs")
logs = r.json().get("logs", [])
for log in logs[-10:]:
    print(f"  Q: {log['query'][:60]}... | sources: {log.get('sources_count', 0)}")
