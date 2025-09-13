from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Dict
import logging
from contextlib import asynccontextmanager

# Assuming these are your custom modules
from rag_system import WikipediaRAGSystem
from data_loader import WikipediaLoader

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
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Wikipedia RAG Assistant</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            .container { margin: 20px 0; }
            input, textarea, button { width: 100%; padding: 10px; margin: 5px 0; border: 1px solid #ccc; border-radius: 4px; }
            button { background-color: #4CAF50; color: white; border: none; cursor: pointer; }
            button:hover { background-color: #45a049; }
            .result { background-color: #f9f9f9; padding: 15px; border-radius: 4px; margin: 10px 0; }
            .sources { background-color: #e8f4f8; padding: 10px; border-radius: 4px; margin: 10px 0; }
        </style>
    </head>
    <body>
        <h1>🤖 Wikipedia RAG Assistant</h1>
        <p>Ask questions and get AI-powered answers from Wikipedia!</p>
        
        <div class="container">
            <h3>1. First, Index Some Topics:</h3>
            <input type="text" id="topics" placeholder="Enter topics separated by commas (e.g., Python, Machine Learning, AI)" />
            <button onclick="indexTopics()">Index Topics</button>
            <div id="indexResult"></div>
        </div>
        
        <div class="container">
            <h3>2. Ask Questions:</h3>
            <textarea id="question" placeholder="Ask your question here..." rows="3"></textarea>
            <button onclick="askQuestion()">Ask Question</button>
            <div id="queryResult"></div>
        </div>
        <script>
            async function indexTopics() {
                const topics = document.getElementById('topics').value.split(',').map(t => t.trim());
                const resultDiv = document.getElementById('indexResult');
                
                if (topics.length === 0 || topics[0] === '') {
                    resultDiv.innerHTML = '<div class="result">Please enter at least one topic.</div>';
                    return;
                }
                
                resultDiv.innerHTML = '<div class="result">Indexing topics... This may take a while.</div>';
                
                try {
                    const response = await fetch('/index', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ topics: topics, max_articles_per_topic: 3 })
                    });
                    
                    if (!response.ok) {
                        const error = await response.json();
                        throw new Error(error.detail || 'Failed to index topics');
                    }
                    
                    const result = await response.json();
                    resultDiv.innerHTML = `<div class="result">Successfully indexed ${result.total_articles} articles for ${result.topics.length} topics!</div>`;
                } catch (error) {
                    resultDiv.innerHTML = `<div class="result">Error: ${error.message}</div>`;
                }
            }
            
            async function askQuestion() {
                const question = document.getElementById('question').value;
                const resultDiv = document.getElementById('queryResult');
                
                if (!question.trim()) {
                    resultDiv.innerHTML = '<div class="result">Please enter a question.</div>';
                    return;
                }
                
                resultDiv.innerHTML = '<div class="result">Searching for answer...</div>';
                
                try {
                    const response = await fetch('/query', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ question: question })
                    });
                    
                    if (!response.ok) {
                        const error = await response.json();
                        throw new Error(error.detail || 'Failed to get answer');
                    }
                    
                    const result = await response.json();
                    
                    let sourcesHtml = '';
                    if (result.sources && result.sources.length > 0) {
                        sourcesHtml = '<div class="sources"><h4>Sources:</h4><ul>';
                        result.sources.forEach(source => {
                            sourcesHtml += `<li><a href="${source.url}" target="_blank">${source.title}</a> (Topic: ${source.topic})</li>`;
                        });
                        sourcesHtml += '</ul></div>';
                    }
                    
                    resultDiv.innerHTML = `
                        <div class="result">
                            <h4>Answer:</h4>
                            <p>${result.answer.replace(/\\n/g, '<br>')}</p>
                            ${sourcesHtml}
                        </div>
                    `;
                } catch (error) {
                    resultDiv.innerHTML = `<div class="result">Error: ${error.message}</div>`;
                }
            }
        </script>
    </body>
    </html>
    """
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
