import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import json
import os
import re

class WebCrawler:
    def __init__(self, start_urls, max_pages=50, max_depth=1):
        self.start_urls = start_urls
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.visited_urls = set()
        self.documents = []
        self.session = requests.Session()
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        self.output_dir = "crawled_data"
        os.makedirs(self.output_dir, exist_ok=True)
        self.documents_file = os.path.join(self.output_dir, "documents.json")
        self.robots_txt_cache = {} # Cache for robots.txt rules

    def _get_robots_txt(self, base_url):
        if base_url in self.robots_txt_cache:
            return self.robots_txt_cache[base_url]

        robots_url = urljoin(base_url, "/robots.txt")
        try:
            response = self.session.get(robots_url, headers=self.headers, timeout=5)
            if response.status_code == 200:
                self.robots_txt_cache[base_url] = response.text
                return response.text
        except requests.exceptions.RequestException:
            pass # Ignore if robots.txt cannot be fetched
        self.robots_txt_cache[base_url] = "" # Cache empty string if not found or error
        return ""

    def _can_fetch(self, url):
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        robots_content = self._get_robots_txt(base_url)
        if not robots_content:
            return True # No robots.txt or couldn't fetch, assume allowed

        # Simple robots.txt parsing: check for Disallow rules for any user-agent or our user-agent
        for line in robots_content.splitlines():
            line = line.strip()
            if line.lower().startswith("user-agent:"):
                current_agent = line.split(':')[1].strip().lower()
                if current_agent == '*' or current_agent == 'mozilla/5.0': # Check for generic or our specific UA
                    pass # Continue to check Disallow rules for this agent
                else:
                    continue # Skip rules for other agents

            if line.lower().startswith("disallow:"):
                disallowed_path = line.split(':')[1].strip()
                if disallowed_path and urlparse(url).path.startswith(disallowed_path):
                    print(f"Skipping {url} due to robots.txt")
                    return False
        return True


    def crawl(self):
        queue = [(url, 0) for url in self.start_urls] # (url, depth)

        while queue and len(self.documents) < self.max_pages:
            current_url, depth = queue.pop(0)

            if current_url in self.visited_urls:
                continue

            if not self._can_fetch(current_url):
                continue

            self.visited_urls.add(current_url)
            print(f"Crawling ({len(self.documents) + 1}/{self.max_pages}, Depth: {depth}): {current_url}")

            try:
                response = self.session.get(current_url, headers=self.headers, timeout=10)
                response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
                
                # Check for content type before parsing
                if 'content-type' not in response.headers or 'text/html' not in response.headers['content-type']:
                    # print(f"Skipping {current_url}: Not HTML content")
                    continue

                soup = BeautifulSoup(response.text, 'html.parser')

                # Extract text content
                text_content = ' '.join(soup.stripped_strings)

                # Extract images
                images = []
                for img in soup.find_all('img', src=True):
                    img_src = urljoin(current_url, img['src'])
                    if img_src and urlparse(img_src).scheme in ['http', 'https']:
                        images.append({'src': img_src, 'alt': img.get('alt', '')})

                # Extract videos (simple approach for <video> and YouTube/Vimeo iframes)
                videos = []
                for video_tag in soup.find_all('video', src=True):
                    video_src = urljoin(current_url, video_tag['src'])
                    if video_src and urlparse(video_src).scheme in ['http', 'https']:
                        videos.append({'src': video_src, 'type': 'direct'})
                
                for iframe in soup.find_all('iframe', src=True):
                    iframe_src = iframe['src']
                    if 'youtube.com/embed/' in iframe_src or 'player.vimeo.com/video/' in iframe_src:
                        if urlparse(iframe_src).scheme in ['http', 'https']:
                            videos.append({'src': iframe_src, 'type': 'embed'})

                self.documents.append({
                    'url': current_url,
                    'text_content': text_content,
                    'images': images,
                    'videos': videos
                })

                if len(self.documents) >= self.max_pages:
                    break # Stop if max pages reached

                # Find new links to crawl
                if depth < self.max_depth:
                    for link in soup.find_all('a', href=True):
                        href = link['href']
                        new_url = urljoin(current_url, href)
                        
                        # Basic URL cleaning and validation
                        parsed_new_url = urlparse(new_url)
                        if parsed_new_url.scheme not in ['http', 'https']:
                            continue
                        
                        # Avoid fragment identifiers
                        new_url = parsed_new_url._replace(fragment="").geturl()

                        # Only add to queue if not visited and within same domain (optional, depends on crawl scope)
                        if new_url not in self.visited_urls and len(self.documents) + len(queue) < self.max_pages * 2: # Heuristic to limit queue size
                            # Add simple domain check to stay somewhat focused
                            if parsed_new_url.netloc == urlparse(current_url).netloc:
                                queue.append((new_url, depth + 1))

            except requests.exceptions.RequestException as e:
                print(f"Error crawling {current_url}: {e}")
            except Exception as e:
                print(f"An unexpected error occurred with {current_url}: {e}")

        self._save_documents()
        print(f"\nCrawl finished.")
        print(f"Total pages crawled: {len(self.documents)}")

    def _save_documents(self):
        with open(self.documents_file, 'w', encoding='utf-8') as f:
            json.dump(self.documents, f, ensure_ascii=False, indent=2)
        print(f"Saved {len(self.documents)} structured documents to {self.documents_file}")

if __name__ == "__main__":
    # You can customize these starting URLs
    start_urls = [
        "https://www.python.org/",
        "https://quotes.toscrape.com/",
        "https://www.nasa.gov/",
        "https://www.wikipedia.org/",
        "https://www.bbc.com/news"
    ]
    crawler = WebCrawler(start_urls=start_urls, max_pages=150, max_depth=2)
    crawler.crawl()