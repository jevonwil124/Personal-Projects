import json
import os
import re
from collections import defaultdict

class Indexer:
    def __init__(self, documents_file="crawled_data/documents.json", output_dir="output"):
        self.documents_file = documents_file
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.inverted_index = defaultdict(list)
        self.document_map = {} # Maps doc_id to {url, images, videos}

    def build_index(self):
        documents = self._load_documents()
        if not documents:
            print("No documents to index. Exiting.")
            return

        print(f"Loaded {len(documents)} documents from {self.documents_file}")

        for doc_id, doc in enumerate(documents):
            url = doc['url']
            text_content = doc.get('text_content', '')
            images = doc.get('images', [])
            videos = doc.get('videos', [])

            # Store document info in document_map
            self.document_map[str(doc_id + 1)] = { # Use 1-based indexing for doc_id
                'url': url,
                'images': images,
                'videos': videos
            }

            # Process text content for inverted index
            words = self._tokenize(text_content)
            for word in words:
                self.inverted_index[word].append(str(doc_id + 1)) # Store doc_id as string

        self._save_index()
        print("Inverted index and document map built.")
        print(f"Saved inverted index to {os.path.join(self.output_dir, 'inverted_index.json')}")
        print(f"Saved document map (with media info) to {os.path.join(self.output_dir, 'inverted_index_doc_map.json')}")
        print("Indexing complete.")

    def _load_documents(self):
        if not os.path.exists(self.documents_file):
            print(f"Error: {self.documents_file} not found.")
            return None
        with open(self.documents_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _tokenize(self, text):
        # Convert to lowercase and remove non-alphanumeric characters, then split
        text = text.lower()
        words = re.findall(r'\b\w+\b', text)
        return words

    def _save_index(self):
        # Convert defaultdict to dict for JSON serialization
        inverted_index_dict = {k: sorted(list(set(v))) for k, v in self.inverted_index.items()}
        
        with open(os.path.join(self.output_dir, "inverted_index.json"), 'w', encoding='utf-8') as f:
            json.dump(inverted_index_dict, f, ensure_ascii=False, indent=2)

        with open(os.path.join(self.output_dir, "inverted_index_doc_map.json"), 'w', encoding='utf-8') as f:
            json.dump(self.document_map, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    indexer = Indexer()
    indexer.build_index()