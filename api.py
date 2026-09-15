import sys
from fastapi import FastAPI
from database.session import Base, engine
from src.articles.controller import router as article_router
from src.addresse.controller import router as address_router
from src.command.controller import router as command_router
from src.clients.controller import router as clients_router
from src.taxe.controller import router as taxe_router
from src.currency.controller import router as currency_router
from src.livraison.controller import router as livraison_router
from src.facturation.controller import router as facture_router
from src.pricing.controller import router as pricing_router
from src.settings.controller import router as settings_router
from src.payments.controller import router as payment_router
from src.users.controller import router as users_router
from src.cash.controller import router as cash_router
from src.site.controller import router as site_router
from src.reports.controller import router as reports_router
from src.export.controller import router as export_router
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import logging


from database.get_data_email import sync_emails  # Import the new sync function

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s - %(name)s - %(funcName)s - %(lineno)d - %(threadName)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('fastapi.log')
    ]
)

logger = logging.getLogger(__name__)

from database.migrate import upgrade as upgrade_local_db
upgrade_local_db()


sync_lock = asyncio.Lock()

async def periodic_sync():
    """Run sync_email immediately at startup and then every 15 minutes."""
    while True:
        try:
            async with sync_lock:
                logger.info("Running sync_emails() ...")
                await asyncio.to_thread(sync_emails)  # run blocking code safely
                logger.info("sync_emails completed.")
        except Exception as e:
            logger.error(f" Error in periodic sync: {e}")
        await asyncio.sleep(60 * 15)  # wait 15 minutes before next run

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create background task
    task = asyncio.create_task(periodic_sync())
    logger.info("Background sync started.")
    yield
    # Shutdown: cancel background task
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        logger.error(" Background sync stopped gracefully.")


app = FastAPI(
    lifespan=lifespan
    )

# sync_data()



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
app.include_router(settings_router)
app.include_router(payment_router)
app.include_router(users_router)
app.include_router(cash_router)
app.include_router(site_router)
app.include_router(reports_router)
app.include_router(export_router)

@app.get("/")
def read_root():
    return {"API_CHECK": "UP and Running"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/synchronize")
async def sync_endpoint():
    """Run the email sync now (same job as the 15-minute background task)."""
    async with sync_lock:
        await asyncio.to_thread(sync_emails)
    return {"status": "ok"}
    

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, port=7626)