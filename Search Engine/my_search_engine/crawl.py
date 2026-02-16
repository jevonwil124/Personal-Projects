import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import os
import time
from urllib.robotparser import RobotFileParser

class MiniCrawler:
    def __init__(self, start_urls, output_dir="crawled_pages", max_depth=2, crawl_limit=50):
        self.start_urls = start_urls
        self.output_dir = output_dir
        self.max_depth = max_depth
        self.crawl_limit = crawl_limit # Max number of pages to crawl
        self.visited = set()
        self.queue = [] # (url, depth)
        self.robot_parsers = {} # Cache for RobotFileParser objects
        self.crawled_count = 0

        # Initialize queue with start URLs at depth 0
        for url in start_urls:
            self.queue.append((url, 0))

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

    def _can_fetch(self, url):
        """Checks robots.txt for the given URL."""
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        robots_txt_url = urljoin(base_url, "/robots.txt")

        if base_url not in self.robot_parsers:
            rp = RobotFileParser()
            try:
                rp.set_url(robots_txt_url)
                rp.read()
                self.robot_parsers[base_url] = rp
                print(f"Fetched robots.txt for {base_url}")
            except Exception as e:
                print(f"Could not fetch or parse robots.txt for {base_url}: {e}")
                self.robot_parsers[base_url] = None # Mark as failed
                return True # Assume we can fetch if robots.txt is unavailable

        rp = self.robot_parsers[base_url]
        if rp:
            # Check if our "user agent" is allowed to fetch this URL
            # A good practice for a real crawler would be to define a specific user agent
            return rp.can_fetch("*", url) # "*" represents any user-agent
        return True # If no robots.txt or failed to parse, assume allowed

    def _save_content(self, url, content):
        """Saves the content of a page to a file."""
        parsed_url = urlparse(url)
        # Create a unique filename from the URL path
        filename = parsed_url.netloc + parsed_url.path.replace('/', '_').replace('.', '_')
        if not filename.strip(): # Handle empty paths for root URLs
            filename = parsed_url.netloc + "_root"
        filename = f"{filename}.html" # Save as HTML
        filepath = os.path.join(self.output_dir, filename)

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Saved: {filepath}")
        except Exception as e:
            print(f"Error saving {url}: {e}")

    def crawl(self):
        """Starts the crawling process."""
        while self.queue and self.crawled_count < self.crawl_limit:
            current_url, depth = self.queue.pop(0) # Get URL and depth from queue

            if current_url in self.visited:
                continue # Skip if already visited

            if depth > self.max_depth:
                print(f"Skipping {current_url} (max depth reached)")
                continue

            # Basic politeness delay
            time.sleep(0.1) # Be nice to servers

            print(f"Crawling ({self.crawled_count+1}/{self.crawl_limit}, Depth: {depth}): {current_url}")

            if not self._can_fetch(current_url):
                print(f"Skipping {current_url} due to robots.txt")
                self.visited.add(current_url)
                continue

            try:
                response = requests.get(current_url, timeout=5)
                response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
                self.crawled_count += 1
                self.visited.add(current_url)
                self._save_content(current_url, response.text)

                soup = BeautifulSoup(response.text, 'html.parser')
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    absolute_url = urljoin(current_url, href)
                    parsed_link = urlparse(absolute_url)

                    # Only queue HTTP/HTTPS links and not external file links or anchor links
                    if parsed_link.scheme in ['http', 'https'] and parsed_link.netloc:
                        # Normalize URL (remove fragments like #section)
                        normalized_url = parsed_link._replace(fragment="").geturl()

                        if normalized_url not in self.visited:
                            self.queue.append((normalized_url, depth + 1))

            except requests.exceptions.RequestException as e:
                print(f"Error crawling {current_url}: {e}")
                self.visited.add(current_url) # Mark as visited even on error to avoid retrying immediately
            except Exception as e:
                print(f"An unexpected error occurred with {current_url}: {e}")
                self.visited.add(current_url)

        print("\nCrawl finished.")
        print(f"Total pages crawled: {self.crawled_count}")
        print(f"Pages stored in: {self.output_dir}")


if __name__ == "__main__":
    # Define your starting URLs here.
    # IMPORTANT: Start with a small, manageable set of URLs for testing.
    # Avoid extremely large sites or sites that might block crawlers quickly.
    # For a true "Google-like" experience, you'd start with highly linked public domains.

    # Example: Using a small collection of well-behaved sites for demonstration
    # You can change these to your own blog, a specific project site, etc.
    seed_urls = [
        "https://www.scrapingbee.com/blog/",
        "https://www.iana.org/domains/example/",
        "https://quotes.toscrape.com/", # A site specifically designed for scraping examples
    ]

    # Initialize and run the crawler
    # Adjust max_depth and crawl_limit as needed.
    # max_depth=1 means it will only crawl the start URLs and links directly on them.
    # crawl_limit controls the total number of pages it will save.
    crawler = MiniCrawler(
        start_urls=seed_urls,
        output_dir="crawled_data",
        max_depth=1,         # Go 1 level deep from initial links
        crawl_limit=20       # Crawl a maximum of 20 pages
    )
    crawler.crawl()