import requests
from bs4 import BeautifulSoup
import os
from urllib.parse import urljoin
from database import init_db, insert_document

COLLEGE_WEBSITE_URL = "https://www.example-college.edu/admissions"


def get_pdf_links(url):
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print("Failed to retrieve page:", e)
        return []

    soup = BeautifulSoup(resp.text, 'html.parser')
    pdf_links = set()
    for a in soup.find_all('a', href=True):
        href = a['href']
        if href.lower().endswith('.pdf'):
            full = urljoin(url, href)
            pdf_links.add(full)
    return list(pdf_links)


def download_pdf(url, target_folder='downloads'):
    os.makedirs(target_folder, exist_ok=True)
    local_name = os.path.join(target_folder, os.path.basename(url.split('?')[0]))
    try:
        r = requests.get(url, stream=True, timeout=30)
        r.raise_for_status()
        with open(local_name, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        return local_name
    except Exception as e:
        print("Failed to download PDF:", e)
        return None


def ingest_data():
    init_db()
    pdf_links = get_pdf_links(COLLEGE_WEBSITE_URL)
    for link in pdf_links:
        print("Processing:", link)
        local = download_pdf(link)
        if local:
            # Use the same process_and_save_pdf flow
            from bot_logic.data_processor import process_and_save_pdf
            success = process_and_save_pdf(local, os.path.basename(local))
            if success:
                print("Saved:", local)
            else:
                print("Failed processing:", local)
            try:
                os.remove(local)
            except Exception:
                pass


if __name__ == '__main__':
    ingest_data()
