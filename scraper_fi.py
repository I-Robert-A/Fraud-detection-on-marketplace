import cloudscraper
from bs4 import BeautifulSoup
import os
import re
import time
import random
import pandas as pd
from urllib.parse import urljoin

# ==============================================
# CONFIG
# ==============================================

CSV_PATH = "case_cu_pret_estim.csv"
IMAGES_FOLDER = "images_case"

START_PAGE = 50          # pagina de start
MAX_NEWS = 1000          # cate anunturi NOI vrem maxim
MAX_PAGES = 500          # limita superioara

os.makedirs(IMAGES_FOLDER, exist_ok=True)

# ==============================================
# CLOUDSCRAPER
# ==============================================

scraper = cloudscraper.create_scraper()

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:110.0) "
        "Gecko/20100101 Firefox/110.0"
    ),
    "Accept-Language": "ro-RO,ro;q=0.9,en-US;q=0.8"
}

def get_page(url, tries=3):
    for i in range(tries):
        try:
            r = scraper.get(url, headers=HEADERS, timeout=15)
            if r.status_code == 200 and len(r.text) > 500:
                return r.text
        except:
            pass

        # delay sigur anti-ban
        time.sleep(random.uniform(3, 6))

    return None

# ==============================================
# CSV EXISTENT
# ==============================================

df_old = pd.read_csv(CSV_PATH)
existing_links = set(df_old["link"].astype(str))

start_id = int(df_old["id"].max()) + 1
print(f"CSV are {len(df_old)} anunțuri. Începem de la ID = {start_id}\n")

# ==============================================
# DESCRIERE + VANZATOR
# ==============================================

def extract_descriere(soup):
    h = soup.find(string=re.compile(r"Descriere", re.I))
    if not h:
        return ""
    container = h.find_parent().find_next_sibling()

    while container and len(container.get_text(strip=True)) < 10:
        container = container.find_next_sibling()

    if not container:
        return ""

    desc = container.get_text(" ", strip=True)
    desc = re.sub(r"Vezi detalii.*", "", desc, flags=re.I).strip()
    return desc


def extract_vanzator(soup):
    vanzator = {"data_cont": "", "nr_postari": 0}

    profile_link = soup.find("a", href=re.compile(
        r"(public-user-profile|anunturi-utilizator|anunturi-[a-z0-9-]+)",
        re.I
    ))
    if not profile_link:
        return vanzator

    def parse_profile(url):
        if url.startswith("/"):
            url = "https://www.publi24.ro" + url

        for _ in range(3):
            try:
                r = scraper.get(url, headers=HEADERS, timeout=10)
                sp = BeautifulSoup(r.text, "html.parser")
                text = sp.get_text(" ", strip=True)

                m_date = re.search(r"Pe site din\s+(\d{2}\.\d{2}\.\d{4})", text)
                m_ads = re.search(r"Anunțuri\s+(\d+)", text)

                if m_date or m_ads:
                    return (
                        m_date.group(1) if m_date else "",
                        int(m_ads.group(1)) if m_ads else 0
                    )
            except:
                pass

            time.sleep(random.uniform(2, 4))

        return "", 0

    d, n = parse_profile(profile_link["href"])
    vanzator["data_cont"] = d
    vanzator["nr_postari"] = n
    return vanzator

# ==============================================
# POZE
# ==============================================

def download_image(url, anunt_id, index):
    try:
        ext = "webp"
        fname = f"{IMAGES_FOLDER}/anunt_{anunt_id}_img_{index}.{ext}"

        r = scraper.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            with open(fname, "wb") as f:
                f.write(r.content)
            return fname
    except:
        pass
    return None


def extract_images(soup, base_url, anunt_id):
    images = []
    seen = set()
    count_valid = 0
    ignore = ["logo", "icon", "avatar", "profile", "banner", "svg"]

    for img in soup.find_all("img"):
        if len(images) >= 4:
            break

        raw = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
        if not raw:
            continue

        full = urljoin(base_url, raw)
        name = full.split("/")[-1].split("?")[0].lower()
        if name in seen:
            continue
        seen.add(name)

        low = full.lower()
        if any(x in low for x in ignore):
            continue
        if not any(ext in low for ext in [".jpg", ".jpeg", ".png", ".webp"]):
            continue

        count_valid += 1
        if count_valid == 1:
            continue  # skip thumbnail

        saved = download_image(full, anunt_id, len(images) + 1)
        if saved:
            images.append(saved)

    return images

# ==============================================
# PRET, CAMERE, MP
# ==============================================

def extract_fields(text):
    pret = moneda = camere = suprafata = None

    m = re.search(r"(\d[\d\s.,]*)\s*(EUR|RON|lei|€)", text, re.I)
    if m:
        pret = m.group(1).replace(" ", "").replace(",", "").replace(".", "")
        moneda = m.group(2).upper().replace("€", "EUR")

    mc = re.search(r"(\d+)\s*camere", text, re.I)
    if mc:
        camere = int(mc.group(1))

    mp = re.search(r"(\d+)\s*(mp|m²|m2)", text, re.I)
    if mp:
        suprafata = int(mp.group(1))

    return pret, moneda, camere, suprafata

# ==============================================
# SCRAPE ANUNT COMPLET
# ==============================================

def scrape_anunt(url, anunt_id):
    html = get_page(url)
    if not html:
        print("   ⚠ Nu pot încărca anunțul.")
        return None

    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)

    pret, moneda, camere, suprafata = extract_fields(text)
    imagini = extract_images(soup, url, anunt_id)
    descriere = extract_descriere(soup)
    vanz = extract_vanzator(soup)

    print(f"   → {len(imagini)} poze, vanzator {vanz['nr_postari']} anunturi")

    return {
        "id": anunt_id,
        "titlu": f"Anunț {anunt_id}",
        "pret": pret,
        "moneda": moneda,
        "nr_camere": camere,
        "suprafata": suprafata,
        "link": url,
        "imagini_paths": "|".join(imagini),
        "numar_imagini": len(imagini),
        "observatii": "",
        "descriere": descriere,
        "data_cont": vanz["data_cont"],
        "nr_postari": vanz["nr_postari"],
        "pret_estim": "",
        "data_cont_parsed": "",
        "vechime_zile": "",
        "scam": "",
        "delta_pret": "",
        "nr_imagini": len(imagini)
    }

# ==============================================
# LINKURI DIN PAGINA DE LISTA
# ==============================================

def extract_listing_links(soup, page_url):
    raw = []

    raw += [a.get("href") for a in soup.select('a[href*="/anunt/"]')]
    raw += [a.get("data-href") for a in soup.select('[data-href*="/anunt/"]')]

    # onclick='/anunt/...'
    for tag in soup.select('[onclick]'):
        onclick = tag.get("onclick") or ""
        if "/anunt/" in onclick:
            m = re.search(r"'(/anunt/[^']+)'", onclick)
            if m:
                raw.append(m.group(1))

    clean = []
    for h in raw:
        if not h:
            continue
        full = urljoin(page_url, h)
        if "/anunt/" in full and full not in clean:
            clean.append(full)

    return clean

# ==============================================
# MAIN
# ==============================================

def main():
    base = "https://www.publi24.ro/anunturi/imobiliare/de-vanzare/case/?withpictures=true"

    df_new_rows = []
    new_count = 0
    anunt_id = start_id
    page = START_PAGE

    while new_count < MAX_NEWS and page <= MAX_PAGES:

        page_url = f"{base}&page={page}"
        print(f"\n📄 PAGINA {page}: {page_url}")

        html = get_page(page_url)
        if not html:
            print("⚠ Nu pot încărca pagina.")
            page += 1
            continue

        soup = BeautifulSoup(html, "html.parser")
        links = extract_listing_links(soup, page_url)

        new_links = [l for l in links if l not in existing_links]
        print(f" → {len(new_links)} linkuri noi.")

        if not new_links:
            page += 1
            continue

        # procesam linkurile de pe pagina asta
        for link in new_links:
            if new_count >= MAX_NEWS:
                break

            print(f"[ID {anunt_id}] {link}")
            data = scrape_anunt(link, anunt_id)

            if data:
                df_new_rows.append(data)
                existing_links.add(link)
                new_count += 1
                anunt_id += 1

            # delay sigur între anunțuri
            time.sleep(random.uniform(1.4, 2.7))

        # salvam dupa fiecare pagina
        if df_new_rows:
            df_new = pd.DataFrame(df_new_rows)
            df_new = df_new.reindex(columns=df_old.columns)
            df_final = pd.concat([df_old, df_new], ignore_index=True)
            df_final.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")

        # cooldown între pagini
        print("   ⏳ Cooldown 6–10 secunde...")
        time.sleep(random.uniform(6, 10))

        page += 1

    print(f"\n🎉 GATA! Adăugat {new_count} anunțuri noi.")
    print(f"📁 Imaginile sunt în {IMAGES_FOLDER}")

if __name__ == "__main__":
    main()
