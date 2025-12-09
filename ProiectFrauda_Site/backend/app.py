import os
import re
import json
import joblib
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import cloudscraper
from flask import Flask, request, jsonify
from flask_cors import CORS
from bs4 import BeautifulSoup
from datetime import datetime
from dateutil import parser
from PIL import Image
from io import BytesIO
from torchvision import transforms
from scipy.sparse import hstack
from urllib.parse import urljoin

app = Flask(__name__)
CORS(app)

# ==========================================
# 1. MODEL PREȚ (CNN)
# ==========================================
class SimpleCNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(12, 32, 3, stride=2, padding=1), nn.ReLU(),
            nn.Conv2d(32, 64, 3, stride=2, padding=1), nn.ReLU(),
            nn.Conv2d(64, 128, 3, stride=2, padding=1), nn.ReLU(),
            nn.Conv2d(128, 256, 3, stride=2, padding=1), nn.ReLU(),
            nn.AdaptiveAvgPool2d((1,1))
        )
    def forward(self, x):
        return self.features(x).view(x.size(0), -1)

class HousePriceModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.cnn = SimpleCNN()
        self.mlp = nn.Sequential(nn.Linear(2, 32), nn.ReLU(), nn.Linear(32, 32), nn.ReLU())
        self.fc = nn.Sequential(nn.Linear(256 + 32, 64), nn.ReLU(), nn.Linear(64, 1))
    def forward(self, img, features):
        img_feat = self.cnn(img)
        num_feat = self.mlp(features)
        return self.fc(torch.cat([img_feat, num_feat], dim=1))

DEVICE = torch.device('cpu')
price_model = HousePriceModel().to(DEVICE)
img_transform = transforms.Compose([transforms.ToTensor()])

try:
    path_pt = 'house_price_cnn_model.pt'
    if os.path.exists(path_pt):
        checkpoint = torch.load(path_pt, map_location=DEVICE)
        state_dict = checkpoint['model_state_dict'] if isinstance(checkpoint, dict) and 'model_state_dict' in checkpoint else checkpoint
        price_model.load_state_dict(state_dict)
        price_model.eval()
        print("✅ Model PREȚ (CNN) activ!")
    else:
        print("⚠️ Modelul de preț lipsește!")
        price_model = None
except: price_model = None

# ==========================================
# 2. MODEL FRAUDĂ
# ==========================================
scam_model = None
tfidf_vectorizer = None
try:
    path_pkl = 'scam_model_logreg.pkl'
    if os.path.exists(path_pkl) and os.path.exists('tfidf_descriere.pkl'):
        scam_model = joblib.load(path_pkl)
        tfidf_vectorizer = joblib.load('tfidf_descriere.pkl')
        print("✅ Model FRAUDĂ activ!")
except: pass

# ==========================================
# 3. SCRAPING NUCLEAR (FIX POZE)
# ==========================================
scraper = cloudscraper.create_scraper()
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36"}

def clean_price_string(text):
    if not text: return 0.0
    text = text.replace('\xa0', '').replace(' ', '')
    if '.' in text and ',' in text: text = text.replace('.', '').replace(',', '.')
    elif '.' in text and len(text.split('.')[-1]) == 3: text = text.replace('.', '')
    else: text = text.replace(',', '.')
    match = re.search(r"(\d+(\.\d+)?)", text)
    return float(match.group(1)) if match else 0.0

def detect_listing_type(soup, titlu):
    t = titlu.lower()
    if any(kw in t for kw in ['vand', 'vând', 'vanzare', 'vânzare', 'de vanzare']): return "sale"
    if any(kw in t for kw in ['inchiriez', 'închiriez', 'chirie', 'inchiriere']): return "rent"
    
    bread = soup.find(class_=re.compile("breadcrumb", re.I))
    if bread:
        bt = bread.get_text().lower()
        # Dacă titlul nu e explicit, ne luăm după breadcrumbs
        if not any(kw in t for kw in ['vand', 'vanzare']):
            if "inchiriat" in bt or "chirie" in bt: return "rent"
    
    return "sale"

def calculate_market_price(suprafata, locatie):
    AVG_MP = 1600 
    if any(x in locatie.lower() for x in ['bucuresti', 'cluj', 'cismigiu', 'primaverii']): AVG_MP = 2500
    elif any(x in locatie.lower() for x in ['timisoara', 'iasi', 'constanta']): AVG_MP = 1800
    return suprafata * AVG_MP

def extract_images_nuclear(soup, html_text):
    """ Metoda supremă de extragere a imaginilor """
    imgs = []

    # 1. Încercăm JSON-LD (Date structurate Google) - Cea mai sigură metodă
    try:
        script = soup.find('script', type='application/ld+json')
        if script:
            data = json.loads(script.string)
            # Uneori e o listă, alteori un obiect
            if isinstance(data, list):
                for item in data:
                    if 'image' in item:
                        imgs.extend(item['image'] if isinstance(item['image'], list) else [item['image']])
            elif isinstance(data, dict) and 'image' in data:
                imgs.extend(data['image'] if isinstance(data['image'], list) else [data['image']])
    except: pass

    # 2. Dacă JSON a eșuat, căutăm link-uri de galerie (A tags)
    if not imgs:
        for a in soup.find_all('a', href=True):
            href = a['href']
            # Link-urile de imagini mari de obicei se termină în jpg/webp și NU sunt thumbnail-uri
            if re.search(r'\.(jpg|jpeg|png|webp)$', href, re.I):
                if 'thumb' not in href.lower() and 'icon' not in href.lower():
                    imgs.append(href)

    # 3. Fallback: Regex pe tot HTML-ul (găsește orice link de poză)
    if len(imgs) < 2:
        # Caută URL-uri de imagini tipice Publi24/Romimo
        matches = re.findall(r'(https?://[^\s"\']+\.(?:jpg|jpeg|png|webp))', html_text)
        for m in matches:
            if 'logo' not in m and 'icon' not in m and 'thumb' not in m:
                imgs.append(m)

    # Curățare și limitare la 4
    unique_imgs = []
    for img in imgs:
        if img not in unique_imgs:
            unique_imgs.append(img)
    
    return unique_imgs[:4]

def extract_all(soup, html_text):
    titlu = soup.find('h1').get_text(strip=True) if soup.find('h1') else "Anunț"
    desc_elem = soup.find("div", class_=re.compile(r"description|content|body", re.I))
    descriere = desc_elem.get_text(strip=True) if desc_elem else ""
    
    tip_anunt = detect_listing_type(soup, titlu)

    # Preț
    pret = 0.0
    price_tags = soup.find_all(class_=re.compile("price|detail-price|money", re.I))
    for tag in price_tags:
        txt = tag.get_text(strip=True)
        if any(c.isdigit() for c in txt):
            val = clean_price_string(txt)
            if val > 100:
                pret = val
                if "RON" in txt.upper() or "LEI" in txt.upper(): pret = pret / 5.0
                break
    if pret == 0:
        m_brut = re.search(r"(\d[\d\s\.]*)\s*(EUR|€)", html_text)
        if m_brut: pret = clean_price_string(m_brut.group(1))

    # Detalii
    text_page = soup.get_text(" ", strip=True)
    m_sup = re.search(r"(\d+)\s*(?:mp|m²)", text_page, re.I)
    suprafata = float(m_sup.group(1)) if m_sup else 50.0
    m_cam = re.search(r"(\d+)\s*camere", text_page, re.I)
    camere = float(m_cam.group(1)) if m_cam else 1.0

    # User
    vanzator = {"vechime_zile": 30, "nr_postari": 0}
    profil = soup.find("a", href=re.compile(r"public-user-profile|anunturi-utilizator"))
    if profil:
        try:
            p_url = urljoin("https://www.publi24.ro", profil["href"])
            r_prof = scraper.get(p_url, headers=HEADERS, timeout=5)
            sp_prof = BeautifulSoup(r_prof.text, "html.parser")
            txt_p = sp_prof.get_text(" ", strip=True)
            
            m_dt = re.search(r"Pe site din\s+(\w+\s+\d{4}|\d{2}\.\d{2}\.\d{4})", txt_p)
            if m_dt:
                dt = parser.parse(m_dt.group(1), dayfirst=True, fuzzy=True)
                vanzator["vechime_zile"] = (datetime.now() - dt).days
            m_ad = re.search(r"Anunțuri\s+(\d+)", txt_p)
            if m_ad: vanzator["nr_postari"] = int(m_ad.group(1))
        except: pass

    # IMAGINI (Folosim funcția nouă)
    imgs = extract_images_nuclear(soup, html_text)

    return {
        "titlu": titlu, "descriere": descriere, "pret": pret, "tip": tip_anunt,
        "suprafata": suprafata, "camere": camere, "user": vanzator, "imgs": imgs
    }

@app.route('/api/analyze', methods=['POST'])
def analyze():
    url = request.json.get('url', '')
    if "publi24" not in url: return jsonify({"error": "Link invalid"}), 400

    try:
        r = scraper.get(url, headers=HEADERS, timeout=10)
        html_text = r.text
        soup = BeautifulSoup(html_text, "html.parser")
        d = extract_all(soup, html_text)
        
        # Filtru strict Chirie
        if d['tip'] == 'rent' or (d['pret'] > 0 and d['pret'] < 2000):
            return jsonify({
                "error_type": "WRONG_TYPE",
                "message": "⚠️ STOP! Acest anunț este de ÎNCHIRIERE. Aplicația verifică doar VÂNZĂRI."
            }), 200

        # AI Price
        ai_price = d['pret']
        if price_model and d['imgs']:
            try:
                img_tensors = []
                for i in range(4):
                    if i < len(d['imgs']):
                        try:
                            resp = scraper.get(d['imgs'][i], timeout=2)
                            img = Image.open(BytesIO(resp.content)).convert('RGB').resize((224, 224))
                            img_tensors.append(img_transform(img))
                        except: img_tensors.append(torch.zeros(3, 224, 224))
                    else: img_tensors.append(torch.zeros(3, 224, 224))
                inp_img = torch.cat(img_tensors, dim=0).unsqueeze(0).to(DEVICE)
                inp_feat = torch.tensor([[d['camere'], d['suprafata']]], dtype=torch.float32).to(DEVICE)
                with torch.no_grad(): ai_price = float(price_model(inp_img, inp_feat).item())
            except: pass

        # Stabilizare
        market_ref = calculate_market_price(d['suprafata'], d['titlu'])
        if abs(ai_price - market_ref) > (market_ref * 0.5):
            final_ai = (ai_price * 0.3) + (market_ref * 0.7)
        else:
            final_ai = (ai_price * 0.6) + (market_ref * 0.4)
        
        final_ai = round(final_ai, 0)

        # Fraudă
        fraud_prob = 30
        if scam_model and tfidf_vectorizer:
            try:
                delta = d['pret'] - final_ai
                X_text = tfidf_vectorizer.transform([d['descriere']])
                X_num = np.array([[d['user']['vechime_zile'], d['user']['nr_postari'], delta]])
                X_final = hstack([X_text, X_num])
                is_fraud = int(scam_model.predict(X_final)[0])
                fraud_prob = round(scam_model.predict_proba(X_final)[0][1] * 100, 2)
            except: pass
        
        if d['pret'] < (final_ai * 0.5): fraud_prob = max(fraud_prob, 85)
        if not d['imgs']: fraud_prob += 25

        return jsonify({
            "success": True,
            "is_fraud": 1 if fraud_prob > 50 else 0,
            "confidence": min(fraud_prob, 99),
            "ai_price": final_ai,
            "details": {
                "Titlu": d['titlu'],
                "Pret": round(d['pret'], 0),
                "Suprafata": d['suprafata'],
                "Camere": int(d['camere']),
                "SellerDays": d['user']['vechime_zile'],
                "SellerPosts": d['user']['nr_postari'],
                "Images": d['imgs']
            },
            "message": "RISC MARE" if fraud_prob > 50 else "VERIFICAT"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)