import scrapy
from urllib.parse import urljoin
import logging

class WikiSpider(scrapy.Spider):
    # Spider name used to run it: scrapy crawl wiki_spider
    name = "wiki_spider"
    # Only crawl pages from this domain
    allowed_domains = ["marvelrivals.fandom.com"]
    # Start crawling from the main Marvel Rivals wiki page
    start_urls = ["https://marvelrivals.fandom.com/wiki/Marvel_Rivals_Wiki"]
    # Keep track of pages we've already visited to avoid duplicates
    visited_urls = set()
    
    # Settings to be polite and avoid getting blocked by the website
    custom_settings = {
        'DOWNLOAD_DELAY': 1,  # Wait 1 second between requests
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,  # Only 1 request at a time
        'ROBOTSTXT_OBEY': True,  # Respect the website's robots.txt file
    }
    # This function finds all the wiki links on a page
    def parse(self, response):
        # Look for all links on the page
        for href in response.css('a::attr(href)').getall():
            # Only follow links that go to wiki articles
            if href.startswith("/wiki/") and not any(href.startswith(f"/wiki/{prefix}") for prefix in [
                "Category:", "Talk:", "File:", "Help:", "Template:", "Special:", "User:"
            ]):
                # Convert relative URL to full URL and remove any # anchors
                full_url = urljoin(response.url, href.split("#")[0])
                # Only visit if we haven't been to this page before
                if full_url not in self.visited_urls:
                    self.visited_urls.add(full_url)
                    # Go to that page and extract its content
                    yield response.follow(full_url, self.parse_article)
    
    # This function extracts all the text content from a wiki article
    def parse_article(self, response):
        # Get all the main content blocks from the page
        content_blocks = response.css(".mw-parser-output > *")
        full_text = []

        # First, look for infoboxes (those boxes with character stats, etc.)
        infobox = response.css('.portable-infobox, .infobox')
        if infobox:
            infobox_text = " ".join(infobox.css("::text").getall()).strip()
            if infobox_text:
                full_text.append(f"INFOBOX: {infobox_text}")

        # Go through each content block and extract text
        for block in content_blocks:
            # Only get text from important elements (paragraphs, lists, headers, tables)
            if block.root.tag in ["p", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6", "div", "table"]:
                text = " ".join(block.css("::text").getall()).strip()
                # Only add if there's actual text and it's not a duplicate
                if text and text not in [item for item in full_text]:
                    full_text.append(text)

        # Return all the extracted data as a dictionary
        yield {
            "title": response.css("h1::text").get(),  # Page title
            "url": response.url,  # Page URL
            "content": "\n\n".join(full_text),  # All text content joined together
            "content_length": len("\n\n".join(full_text)),  # How much text we got
            "sections_count": len(full_text)  # How many sections we found
        }

        # Log what we just scraped for debugging
        self.logger.info(f"Scraped: {response.css('h1::text').get()} - {len(full_text)} sections")

        # Look for more wiki links on this page to continue crawling
        for href in response.css('a::attr(href)').getall():
            # Same filtering as above - only follow wiki article links
            if href.startswith("/wiki/") and not any(href.startswith(f"/wiki/{prefix}") for prefix in [
                "Category:", "Talk:", "File:", "Help:", "Template:", "Special:", "User:"
            ]):
                full_url = urljoin(response.url, href.split("#")[0])
                # Only visit if we haven't been there before
                if full_url not in self.visited_urls:
                    self.visited_urls.add(full_url)
                    # Go scrape that page too
                    yield response.follow(full_url, self.parse_article)
