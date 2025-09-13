import wikipedia
import json
import os
from typing import List, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WikipediaLoader:
    def __init__(self, data_path: str = "./data"):
        self.data_path = data_path
        os.makedirs(data_path, exist_ok=True)
    
    def search_and_download(self, topics: List[str], max_articles: int = 5) -> List[Dict]:
        """Search and download Wikipedia articles for given topics"""
        articles = []
        
        for topic in topics:
            try:
                logger.info(f"Searching for: {topic}")
                # Search for articles
                search_results = wikipedia.search(topic, results=max_articles)
                
                for title in search_results[:max_articles]:
                    try:
                        # Get article content
                        page = wikipedia.page(title)
                        
                        article = {
                            "title": page.title,
                            "content": page.content,
                            "url": page.url,
                            "summary": page.summary,
                            "topic": topic
                        }
                        
                        articles.append(article)
                        logger.info(f"Downloaded: {page.title}")
                        
                    except wikipedia.exceptions.DisambiguationError as e:
                        # Handle disambiguation by taking first option
                        try:
                            page = wikipedia.page(e.options[0])
                            article = {
                                "title": page.title,
                                "content": page.content,
                                "url": page.url,
                                "summary": page.summary,
                                "topic": topic
                            }
                            articles.append(article)
                            logger.info(f"Downloaded (disambiguated): {page.title}")
                        except:
                            continue
                            
                    except Exception as e:
                        logger.warning(f"Error downloading {title}: {e}")
                        continue
                        
            except Exception as e:
                logger.error(f"Error searching for {topic}: {e}")
                continue
        
        # Save articles
        self.save_articles(articles)
        return articles
    
    def save_articles(self, articles: List[Dict]):
        """Save articles to JSON file"""
        file_path = os.path.join(self.data_path, "wikipedia_articles.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(articles, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved {len(articles)} articles to {file_path}")
    
    def load_articles(self) -> List[Dict]:
        """Load articles from JSON file"""
        file_path = os.path.join(self.data_path, "wikipedia_articles.json")
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                articles = json.load(f)
            logger.info(f"Loaded {len(articles)} articles from {file_path}")
            return articles
        return []
    
    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """Split text into overlapping chunks"""
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), chunk_size - overlap):
            chunk = ' '.join(words[i:i + chunk_size])
            chunks.append(chunk)
            
            if i + chunk_size >= len(words):
                break
        
        return chunks

# Test the loader
if __name__ == "__main__":
    loader = WikipediaLoader()
    
    # Example topics - you can change these
    topics = [
        "Artificial Intelligence",
        "Machine Learning", 
        "Python Programming",
        "FastAPI",
        "Natural Language Processing"
    ]
    
    articles = loader.search_and_download(topics, max_articles=3)
    print(f"Downloaded {len(articles)} articles")