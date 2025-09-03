from articles.model import ArticleRequest
from fastapi import APIRouter


router = APIRouter(
    prefix="/articles",
   tags=["articles"]
)


@router.post("/", response_model=ArticleRequest)
def create_article(article: ArticleRequest):
    return article
