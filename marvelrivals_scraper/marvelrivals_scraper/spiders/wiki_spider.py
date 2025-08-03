import scrapy
from urllib.parse import urljoin
import logging

class WikiSpider(scrapy.Spider):
    name = "wiki_spider"
    # only crawl pages from this domain
    allowed_domains = ["marvelrivals.fandom.com"]
    start_urls = [
        "https://marvelrivals.fandom.com/wiki/Maps",
        "https://marvelrivals.fandom.com/wiki/Category:Lore",
        "https://marvelrivals.fandom.com/wiki/Heroes"
    ]
    # track to avoid duplicates
    visited_urls = set()
    
    # to avoid getting blocked by the website
    custom_settings = {
        'DOWNLOAD_DELAY': 1,  
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,  
        'ROBOTSTXT_OBEY': True,  
    }
    # this function finds all the wiki links on a page
    def parse(self, response):
        # Check if this is a category page
        if "/Category:" in response.url:
            category_links = response.css('#mw-pages a::attr(href), .category-page__members a::attr(href)').getall()
            for href in category_links:
                if href.startswith("/wiki/") and not any(href.startswith(f"/wiki/{prefix}") for prefix in [
                    "Category:", "Talk:", "File:", "Help:", "Template:", "Special:", "User:"
                ]):
                    full_url = urljoin(response.url, href.split("#")[0])
                    if full_url not in self.visited_urls:
                        self.visited_urls.add(full_url)
                        yield response.follow(full_url, self.parse_article)
        
        # Look for all links on the page (for regular pages and additional links)
        for href in response.css('a::attr(href)').getall():
            # Only follow links that go to wiki articles
            if href.startswith("/wiki/") and not any(href.startswith(f"/wiki/{prefix}") for prefix in [
                "Category:", "Talk:", "File:", "Help:", "Template:", "Special:", "User:"
            ]):
                # Convert relative URL to full URL and remove any # anchors
                full_url = urljoin(response.url, href.split("#")[0])
                if full_url not in self.visited_urls:
                    self.visited_urls.add(full_url)
                    # extract its content
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
            # Only get text from important elements 
            if block.root.tag in ["p", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6", "div", "table"]:
                text = " ".join(block.css("::text").getall()).strip()
                if text and text not in [item for item in full_text]:
                    full_text.append(text)

        # Return all the extracted data as a dictionary
        yield {
            "title": response.css("h1::text").get(), 
            "url": response.url,  
            "content": "\n\n".join(full_text), 
            "content_length": len("\n\n".join(full_text)),  
            "sections_count": len(full_text)  
        }

        # Log what we just scraped for debugging
        self.logger.info(f"Scraped: {response.css('h1::text').get()} - {len(full_text)} sections")

        # Look for more wiki links on this page to continue crawling
        for href in response.css('a::attr(href)').getall():
            if href.startswith("/wiki/") and not any(href.startswith(f"/wiki/{prefix}") for prefix in [
                "Category:", "Talk:", "File:", "Help:", "Template:", "Special:", "User:"
            ]):
                full_url = urljoin(response.url, href.split("#")[0])
                if full_url not in self.visited_urls:
                    self.visited_urls.add(full_url)
                    yield response.follow(full_url, self.parse_article)