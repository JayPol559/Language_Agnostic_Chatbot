import requests
from bs4 import BeautifulSoup
import PyPDF2
from database import init_db, DATABASE_NAME
import sqlite3
import re
import os

COLLEGE_WEBSITE_URL = "https://www.example-college.edu/admissions" # Replace with actual URL

def get_pdf_links(url):
    print(f"Scraping for PDFs on {url}...")
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    pdf_links = set()
    for a_tag in soup.find_all('a', href=True):
        link = a_tag['href']
        if link.lower().endswith('.pdf'):
            if not link.startswith('http'):
                link = requests.compat.urljoin(url, link)
            pdf_links.add(link)
    return list(pdf_links)

def download_and_read_pdf(url):
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        reader = PyPDF2.PdfReader(response.raw)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        print(f"Error processing PDF from {url}: {e}")
        return None

def ingest_data():
    init_db()
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    pdf_links = get_pdf_links(COLLEGE_WEBSITE_URL)
    
    for url in pdf_links:
        print(f"Processing {url}...")
        text_content = download_and_read_pdf(url)
        
        if text_content:
            title = os.path.basename(url)
            cursor.execute(
                "INSERT OR IGNORE INTO Documents (title, url, content, status) VALUES (?, ?, ?, ?)",
                (title, url, text_content, 'scraped')
            )
            print(f"Successfully added {title} to database.")
    
    conn.commit()
    conn.close()
    print("Data ingestion complete!")

if __name__ == '__main__':
    ingest_data()
