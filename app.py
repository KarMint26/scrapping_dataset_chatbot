import requests
from bs4 import BeautifulSoup
from fpdf import FPDF
import os
import re
from urllib.parse import urlparse
from time import sleep
import random

# Fungsi untuk mencari URL menggunakan Google (tanpa API key)
def search_google(keyword, num_results=10):
    search_url = f"https://www.google.com/search?q={keyword}"
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.85 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36",
        "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0) Gecko/20100101 Firefox/40.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.129 Safari/537.36"
    ]

    headers = {
        "User-Agent": random.choice(user_agents)
    }
    response = requests.get(search_url, headers=headers)
    
    # Cetak status dan URL
    print(f"Response status code: {response.status_code}")
    
    soup = BeautifulSoup(response.text, "html.parser")

    links = []
    for a_tag in soup.find_all("a", href=True):
        href = a_tag['href']
        if href.startswith('http'):
            if len(links) >= num_results:
                break
            print(f"Found link: {href}")  # Menampilkan link yang ditemukan
            links.append(href)

    return links

# Fungsi untuk mengecek apakah URL mengarah ke halaman PDF
def is_pdf(url):
    return url.lower().endswith('.pdf')

# Fungsi untuk mengunduh PDF dan mengekstrak teks dari file lokal
def download_pdf(pdf_url):
    try:
        response = requests.get(pdf_url, stream=True)
        if response.status_code == 200:
            filename = os.path.join('downloads', os.path.basename(urlparse(pdf_url).path))
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
            return filename
    except Exception as e:
        print(f"Error downloading PDF {pdf_url}: {e}")
    return None

# Fungsi untuk mengekstrak teks dari file PDF lokal
def extract_pdf_content(pdf_file_path):
    try:
        from pdfminer.high_level import extract_text
        text = extract_text(pdf_file_path)
        return text
    except Exception as e:
        print(f"Error extracting PDF content from {pdf_file_path}: {e}")
        return None

# Fungsi untuk mengekstrak artikel dari halaman HTML
def scrape_website(url, num_articles=5):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=15, verify=False)
        print(f"Fetching {url}, status code: {response.status_code}")  # Cetak status kode
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return []

    if is_pdf(url):
        # Jika URL mengarah ke PDF, unduh dan ekstrak teks dari PDF
        print(f"Downloading PDF: {url}")
        pdf_file_path = download_pdf(url)
        if pdf_file_path:
            pdf_content = extract_pdf_content(pdf_file_path)
            if pdf_content:
                return [{"content": pdf_content}]
            else:
                print(f"Skipping PDF content at {url}")
        return []

    try:
        soup = BeautifulSoup(response.content, "html.parser")
    except Exception as e:
        print(f"Error parsing content from {url}: {e}")
        return []

    articles = []
    count = 0

    # Ambil konten paragraf saja (mengabaikan judul)
    for p_tag in soup.find_all("p"):
        if count >= num_articles:
            break
        content = p_tag.get_text(strip=True)
        if content:  # Pastikan konten tidak kosong
            articles.append({"content": content})
            count += 1

    # Cek apakah artikel ditemukan
    if not articles:
        print(f"No articles found in {url}")

    return articles


# Fungsi untuk membersihkan teks
def sanitize_text(text):
    # Hapus tanda kutip melengkung dan simbol tidak diinginkan
    text = text.replace('“', '"').replace('”', '"').replace('‘', "'").replace('’', "'")

    # Hapus angka dalam tanda kurung kotak (citation) seperti [1], [2], dll.
    text = re.sub(r'\[\d+\]', '', text)

    # Hapus simbol atau karakter khusus yang mungkin muncul
    text = re.sub(r'[^\w\s.,;!?-]', '', text)  # Menjaga teks tetap bersih tetapi mempertahankan tanda baca umum

    # Menghapus spasi berlebih
    text = re.sub(r'\s+', ' ', text).strip()

    return text

# Fungsi untuk menyimpan hasil dalam PDF
def save_to_pdf(data, output_file="dataset.pdf"):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Menambahkan font yang mendukung UTF-8 (DejaVu)
    pdf.add_font('DejaVu', '', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', uni=True)
    pdf.set_font("DejaVu", size=12)

    content_combined = ""

    # Gabungkan semua konten menjadi satu string tanpa spasi tambahan antar paragraf
    for item in data:
        content = sanitize_text(item["content"])
        content_combined += content + "\n"  # Gabungkan dengan satu spasi antar konten

    pdf.multi_cell(0, 10, content_combined)

    pdf.output(output_file)

# Disable SSL warnings
requests.packages.urllib3.disable_warnings()

# Keyword untuk pencarian
keyword = "Tanaman komoditas pertanian"

# Cari URL di Google
print("Searching Google...")
urls = search_google(keyword, num_results=50)
all_articles = []

for url in urls:
    print(f"Scraping {url}...")
    articles = scrape_website(url, num_articles=50)
    all_articles.extend(articles)
    sleep(2)  # Hindari request berlebihan dengan delay

if all_articles:
    # Simpan ke PDF
    print("Saving data to PDF...")
    save_to_pdf(all_articles, output_file="file_pdf/agriculture_dataset.pdf")
    print("Dataset saved as agriculture_dataset.pdf")
else:
    print("No articles found or unable to scrape data.")
