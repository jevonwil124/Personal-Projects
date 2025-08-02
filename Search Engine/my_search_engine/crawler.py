import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import json
import os
import re
import time # Import the time module

class WebCrawler:
    def __init__(self, start_urls, max_pages=50, max_depth=1, delay_seconds=1): # Added delay_seconds parameter
        self.start_urls = start_urls
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.delay_seconds = delay_seconds # Store the delay
        self.visited_urls = set()
        self.documents = []
        self.session = requests.Session()
        # Updated User-Agent to a more recent Chrome version
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
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
        # Note: self.headers['User-Agent'] might include full string, we need to handle this
        # For simplicity, let's just check for '*' or a substring match
        user_agent_short = self.headers['User-Agent'].split('/')[0].lower() # e.g., 'mozilla' or 'chrome'

        disallow_rules = []
        user_agent_block = False

        for line in robots_content.splitlines():
            line = line.strip()
            if line.lower().startswith("user-agent:"):
                current_agent = line.split(':')[1].strip().lower()
                # Check if the current user-agent block applies to us
                if current_agent == '*' or user_agent_short in current_agent:
                    user_agent_block = True
                else:
                    user_agent_block = False
                disallow_rules = [] # Reset rules for new user-agent block
            elif user_agent_block and line.lower().startswith("disallow:"):
                disallowed_path = line.split(':')[1].strip()
                disallow_rules.append(disallowed_path)
            elif user_agent_block and line.lower().startswith("allow:"): # Handle allow rules, which override disallow
                allowed_path = line.split(':')[1].strip()
                # If an allow rule specifically allows a path that was previously disallowed, it overrides
                # This simple parsing doesn't fully implement specificity, but it's a start
                if allowed_path in disallow_rules:
                    disallow_rules.remove(allowed_path) # Remove from disallow if explicitly allowed

        path = urlparse(url).path
        for disallowed_path in disallow_rules:
            if disallowed_path and path.startswith(disallowed_path):
                print(f"Skipping {url} due to robots.txt Disallow: {disallowed_path}")
                return False
        return True


    def crawl(self):
        queue = [(url, 0) for url in self.start_urls] # (url, depth)

        while queue and len(self.documents) < self.max_pages:
            current_url, depth = queue.pop(0)

            if current_url in self.visited_urls:
                continue

            # Ensure we respect robots.txt
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
                    # Simplified check for common video embeds. More robust regex might be needed for full coverage.
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
            finally:
                # --- NEW: Introduce a delay after each request (whether successful or not) ---
                time.sleep(self.delay_seconds) 

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
        "https://www.nasa.gov/",
        "https://www.wikipedia.org/",
        "https://www.bbc.com/news",
        "https://stockx.com/", # This site is very aggressive with anti-bot measures.
        "https://www.nbcnews.com/",
        "https://www.reuters.com/",
        "https://www.nytimes.com/",
        "https://www.theguardian.com/",
        "https://www.wired.com/",
        "https://docs.python.org/3/",
        "https://developer.mozilla.org/en-US/",
        "https://github.com/",
        "https://www.nationalgeographic.com/",
        "https://www.smithsonianmag.com/",
        "https://www.khanacademy.org/",
        "https://www.allrecipes.com/",
        "https://www.gutenberg.org/",

    ]
    # Increased max_pages and max_depth as per previous discussions
    # Added delay_seconds to make the crawler more polite and potentially avoid 403 errors
    crawler = WebCrawler(start_urls=start_urls, max_pages=1000, max_depth=5, delay_seconds=2) # Increased delay to 2 seconds
    crawler.crawl()