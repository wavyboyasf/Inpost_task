from fastapi import FastAPI
import httpx
import json
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    url = "https://api-global-points.easypack24.net/v1/points"
    print("Fetching data from InPost API...", flush=True)

    async with httpx.AsyncClient() as client:
        response = await client.get(url)

        if response.status_code == 200:
            data = response.json()
            items = data.get("items", [])

            if items:
                print("\n" + "=" * 70, flush=True)
                print("STRUKTURA KILKU PUNKTÓW INPOST:", flush=True)
                print("=" * 70, flush=True)

                for i, point in enumerate(items[:5], start=1):
                    print(f"\nLOCKER #{i}", flush=True)
                    print("-" * 70, flush=True)

                    # tutaj wypisujesz CAŁY JSON
                    print(
                        json.dumps(
                            point,
                            indent=2,
                            ensure_ascii=False
                        ),
                        flush=True
                    )

                print("\n" + "=" * 70 + "\n", flush=True)

            else:
                print("Brak punktów w odpowiedzi.", flush=True)

        else:
            print(f"Błąd API: {response.status_code}", flush=True)

    yield


app = FastAPI(
    title="InPost Points App",
    lifespan=lifespan
)


@app.get("/")
def read_root():
    return {"status": "FastAPI is running!"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000)