import json
import os
import re
from collections import defaultdict

class SearchEngine:
    def __init__(self, inverted_index_file="output/inverted_index.json", document_map_file="output/inverted_index_doc_map.json"):
        self.inverted_index = self._load_json(inverted_index_file)
        self.document_map = self._load_json(document_map_file)
        print("Loaded inverted index from inverted_index.json")
        print("Loaded document map from inverted_index_doc_map.json")

    def _load_json(self, filepath):
        if not os.path.exists(filepath):
            return {} # Return empty if file doesn't exist
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _tokenize(self, text):
        return re.findall(r'\b\w+\b', text.lower())

    def search(self, query):
        query_words = self._tokenize(query)
        
        # Calculate TF-IDF like scores (simplified for demonstration)
        # This is a very basic scoring, can be improved with actual TF-IDF,
        # cosine similarity, PageRank, etc.
        doc_scores = defaultdict(float)
        
        for word in query_words:
            if word in self.inverted_index:
                doc_ids = self.inverted_index[word]
                for doc_id in doc_ids:
                    # Simple scoring: just count word occurrences in documents
                    # In a real system, you'd calculate actual TF-IDF weights
                    doc_scores[doc_id] += 1 # Increment score for each word match

        # Sort results by score in descending order
        # Convert doc_id to int for sorting purposes if needed, but keep string for map lookup
        sorted_results = sorted(doc_scores.items(), key=lambda item: item[1], reverse=True)
        
        # Format for output: (score, doc_id)
        # Ensure score is a float or int, not a string here.
        # It should already be a float/int from doc_scores defaultdict.
        return [(score, doc_id) for doc_id, score in sorted_results]