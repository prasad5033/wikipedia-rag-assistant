import os
from typing import List, Dict, Tuple
import chromadb
from sentence_transformers import SentenceTransformer
import numpy as np
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

class WikipediaRAGSystem:
    def __init__(self, 
                 model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
                 vector_store_path: str = "./vector_store"):
        
        self.model_name = model_name
        self.vector_store_path = vector_store_path
        
        # Initialize embedding model
        logger.info(f"Loading embedding model: {model_name}")
        self.embedding_model = SentenceTransformer(model_name)
        
        # Initialize vector store
        os.makedirs(vector_store_path, exist_ok=True)
        self.client = chromadb.PersistentClient(path=vector_store_path)
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="wikipedia_articles",
            metadata={"hnsw:space": "cosine"}
        )
        
        logger.info("RAG System initialized successfully")
    
    def add_documents(self, articles: List[Dict]):
        """Add Wikipedia articles to vector store"""
        from data_loader import WikipediaLoader
        loader = WikipediaLoader()
        
        documents = []
        metadatas = []
        ids = []
        
        doc_id = 0
        
        for article in articles:
            # Chunk the article content
            chunks = loader.chunk_text(article['content'])
            
            for chunk_idx, chunk in enumerate(chunks):
                documents.append(chunk)
                metadatas.append({
                    "title": article['title'],
                    "url": article['url'],
                    "topic": article['topic'],
                    "chunk_id": chunk_idx,
                    "total_chunks": len(chunks)
                })
                ids.append(f"{doc_id}_{chunk_idx}")
            
            doc_id += 1
        
        # Generate embeddings and add to collection
        logger.info(f"Adding {len(documents)} document chunks to vector store...")
        
        # Process in batches to avoid memory issues
        batch_size = 100
        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i:i+batch_size]
            batch_metadatas = metadatas[i:i+batch_size]
            batch_ids = ids[i:i+batch_size]
            
            # Generate embeddings
            embeddings = self.embedding_model.encode(batch_docs).tolist()
            
            # Add to collection
            self.collection.add(
                documents=batch_docs,
                metadatas=batch_metadatas,
                embeddings=embeddings,
                ids=batch_ids
            )
        
        logger.info(f"Successfully added {len(documents)} chunks to vector store")
    
    def search_similar_documents(self, query: str, n_results: int = 5) -> Dict:
        """Search for similar documents using vector similarity"""
        # Generate query embedding
        query_embedding = self.embedding_model.encode([query]).tolist()
        
        # Search in vector store
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=n_results,
            include=['documents', 'metadatas', 'distances']
        )
        
        return results
    
    def generate_answer(self, query: str, context_docs: List[str]) -> str:
        """Generate answer using retrieved context (simple concatenation for now)"""
        # Combine context documents
        context = "\n\n".join(context_docs[:3])  # Use top 3 docs
        
        # Simple template-based answer (you can replace with LLM later)
        answer = f"""Based on the Wikipedia articles, here's what I found about your query: "{query}"

Context from Wikipedia:
{context[:1500]}...

This information comes from Wikipedia articles. For more detailed information, please refer to the original sources."""

        return answer
    
    def retrieve_and_generate(self, query: str, n_results: int = 5) -> Dict:
        """Complete RAG pipeline: retrieve and generate"""
        # Step 1: Retrieve similar documents
        search_results = self.search_similar_documents(query, n_results)
        
        # Step 2: Extract documents and metadata
        documents = search_results['documents'][0]
        metadatas = search_results['metadatas'][0]
        distances = search_results['distances'][0]
        
        # Step 3: Generate answer
        answer = self.generate_answer(query, documents)
        
        # Step 4: Prepare sources
        sources = []
        seen_titles = set()
        
        for meta, distance in zip(metadatas, distances):
            if meta['title'] not in seen_titles:
                sources.append({
                    "title": meta['title'],
                    "url": meta['url'],
                    "topic": meta['topic'],
                    "relevance_score": 1 - distance  # Convert distance to similarity
                })
                seen_titles.add(meta['title'])
        
        return {
            "query": query,
            "answer": answer,
            "sources": sources[:3],  # Top 3 unique sources
            "retrieved_chunks": len(documents)
        }

# Test the RAG system
if __name__ == "__main__":
    from data_loader import WikipediaLoader
    
    # Load articles
    loader = WikipediaLoader()
    articles = loader.load_articles()
    
    if not articles:
        print("No articles found. Run data_loader.py first!")
    else:
        # Initialize RAG system
        rag = WikipediaRAGSystem()
        
        # Add documents to vector store
        rag.add_documents(articles)
        
        # Test query
        result = rag.retrieve_and_generate("What is artificial intelligence?")
        print("Query:", result['query'])
        print("Answer:", result['answer'][:500] + "...")
        print("Sources:", [s['title'] for s in result['sources']])