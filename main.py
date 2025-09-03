from fastapi import FastAPI
from src.articles.controller import router as article_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(article_router)

@app.get("/")
def read_root():
    return {"APi_CHECK": "UP and Running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, port=7626)