from fastapi import FastAPI
from src.articles.controller import router as article_router
from src.addresse.controller import router as address_router
from src.command.controller import router as command_router
from src.clients.controller import router as clients_router
from src.taxe.controller import router as taxe_router
from src.currency.controller import router as currency_router
from src.livraison.controller import router as livraison_router
from src.facturation.controller import router as facture_router
from src.pricing.controller import router as pricing_router
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
app.include_router(address_router)
app.include_router(command_router)
app.include_router(clients_router)
app.include_router(taxe_router)
app.include_router(currency_router)
app.include_router(livraison_router)
app.include_router(facture_router)
app.include_router(pricing_router)

@app.get("/")
def read_root():
    return {"API_CHECK": "UP and Running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, port=7626)