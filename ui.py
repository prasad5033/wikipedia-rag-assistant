html_content = r"""
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