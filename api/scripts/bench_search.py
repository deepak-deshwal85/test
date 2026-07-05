import time

import httpx

queries = [
    "How many people does Reliance employ?",
    "What is Reliance Industries revenue?",
]

for run in ("cold", "cached"):
    print(f"--- {run} ---")
    for query in queries:
        started = time.perf_counter()
        response = httpx.post(
            "http://127.0.0.1:8090/v1/search",
            json={
                "phone_number": "911171366880",
                "query": query,
                "max_results": 5,
            },
            timeout=60.0,
        )
        elapsed_ms = (time.perf_counter() - started) * 1000
        hits = len(response.json().get("hits", []))
        print(f"{elapsed_ms:6.0f}ms hits={hits} query={query[:50]!r}")
