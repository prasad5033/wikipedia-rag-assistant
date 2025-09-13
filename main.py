from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Dict
import logging
from contextlib import asynccontextmanager

# Assuming these are your custom modules
from rag_system import WikipediaRAGSystem
from data_loader import WikipediaLoader
from ui import html_content  # Import the HTML content from ui.py

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Pydantic Models ---
class QueryRequest(BaseModel):
    question: str
    max_results: int = 5

class QueryResponse(BaseModel):
    query: str
    answer: str
    sources: List[Dict]
    retrieved_chunks: int

class IndexRequest(BaseModel):
    topics: List[str]
    max_articles_per_topic: int = 3

# --- Lifespan Management ---
# Global RAG system instance, initialized during lifespan startup
rag_system = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles application startup and shutdown events.
    """
    global rag_system
    logger.info("Starting up Wikipedia RAG Assistant...")
    
    try:
        # Initialize RAG system on startup
        rag_system = WikipediaRAGSystem()
        logger.info("RAG system initialized successfully")
        
        # Check for existing data
        loader = WikipediaLoader()
        articles = loader.load_articles()
        
        if articles:
            logger.info(f"Found {len(articles)} existing articles")
        else:
            logger.info("No existing articles found. You'll need to index some topics first.")
            
    except Exception as e:
        logger.error(f"Failed to initialize RAG system during startup: {e}")
        # Raising the exception here will prevent the app from starting
        raise e

    yield  # The application runs here

    # --- Shutdown logic would go here ---
    logger.info("Shutting down Wikipedia RAG Assistant...")


# --- FastAPI App Initialization ---
app = FastAPI(
    title="Wikipedia RAG Assistant",
    description="AI Assistant powered by Wikipedia knowledge and RAG",
    version="1.0.0",
    lifespan=lifespan  # Use the lifespan context manager
)

# --- API Endpoints ---
@app.get("/", response_class=HTMLResponse)
async def root():
    return html_content

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "Wikipedia RAG Assistant is running"}

@app.post("/index")
async def index_topics(request: IndexRequest):
    try:
        logger.info(f"Indexing topics: {request.topics}")
        
        loader = WikipediaLoader()
        articles = loader.search_and_download(
            topics=request.topics, 
            max_articles=request.max_articles_per_topic
        )
        
        if not articles:
            raise HTTPException(status_code=404, detail="No articles found for the given topics")
        
        rag_system.add_documents(articles)
        
        return {
            "message": "Topics indexed successfully",
            "topics": request.topics,
            "total_articles": len(articles)
        }
        
    except Exception as e:
        logger.error(f"Error indexing topics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query", response_model=QueryResponse)
async def query_rag(request: QueryRequest):
    if not rag_system:
        raise HTTPException(status_code=503, detail="RAG system is not initialized. The application may be starting or encountered an error.")
    
    try:
        logger.info(f"Processing query: {request.question}")
        
        result = rag_system.retrieve_and_generate(
            query=request.question,
            n_results=request.max_results
        )
        
        return QueryResponse(**result)
        
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status")
async def get_status():
    if not rag_system:
        return {"status": "initializing", "message": "RAG system not yet available."}
        
    try:
        loader = WikipediaLoader()
        articles = loader.load_articles()
        collection_count = rag_system.collection.count()
        
        return {
            "status": "operational",
            "total_articles": len(articles),
            "total_chunks": collection_count,
            "rag_system_initialized": True
        }
        
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return {"status": "error", "message": str(e)}

# --- Main Execution ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
