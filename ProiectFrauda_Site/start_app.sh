#!/bin/bash

# --- Funcție de curățenie (Oprește tot la ieșire) ---
cleanup() {
    echo ""
    echo "🛑 Opresc serverele și eliberez porturile..."
    # Omoară procesele copil (Python & Node)
    kill 0
    exit
}
trap cleanup SIGINT

echo "=================================================="
echo "🛡️  AI GUARD - ULTIMATE INSTALLER (WSL/LINUX)"
echo "=================================================="

# --- PASUL 0: VERIFICĂ DACĂ AI UNELTELE DE BAZĂ ---
echo "🔍 [0/4] Verific uneltele de sistem..."

# 1. Verificăm Python
if ! command -v python3 &> /dev/null; then
    echo "⚠️  Python3 lipsește! Încerc să îl instalez (îți va cere parola)..."
    sudo apt update
    sudo apt install -y python3 python3-venv python3-pip
else
    echo "✅ Python3 este instalat."
fi

# 2. Verificăm Node.js / NPM
if ! command -v npm &> /dev/null; then
    echo "⚠️  Node.js/NPM lipsește! Încerc să îl instalez..."
    # Instalăm o versiune compatibilă
    sudo apt install -y nodejs npm
else
    echo "✅ Node.js este instalat."
fi

echo "--------------------------------------------------"

# --- PASUL 1: SETUP BACKEND ---
echo "🔧 [1/4] Configurare Backend..."
cd backend

# Dacă nu există venv, îl creăm
if [ ! -d "venv" ]; then
    echo "📦 Prima rulare detectată! Se creează mediul virtual..."
    python3 -m venv venv
    source venv/bin/activate
    
    echo "⬇️  Se descarcă librăriile AI (poate dura 2-3 minute)..."
    
    # Update pip pentru siguranță
    pip install --upgrade pip

    # Instalăm varianta light (CPU)
    pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
    
    # Instalăm restul
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
    else
        pip install flask flask-cors pandas numpy scikit-learn joblib cloudscraper beautifulsoup4 requests pillow python-dateutil
    fi
    echo "✅ Backend instalat cu succes!"
else
    source venv/bin/activate
fi

# Pornim Serverul Python
echo "🐍 [2/4] Pornesc serverul Python..."
python3 app.py &
cd ..

# --- PASUL 2: PAUZĂ DE ÎNCĂRCARE ---
echo ""
echo "⏳ [3/4] Se încarcă modelele AI în memorie..."
echo "    Așteptăm 20 de secunde pentru stabilitate..."
echo "--------------------------------------------------"

# Bara de progres vizuală
for i in {20..1}; do
    echo -ne "⏱️  Lansare în $i secunde... \r"
    sleep 1
done
echo ""
echo "✅ Backend-ul este gata de acțiune!"
echo ""

# --- PASUL 3: SETUP FRONTEND ---
echo "⚛️  [4/4] Pornesc Interfața Grafică..."
cd frontend

if [ ! -d "node_modules" ]; then
    echo "📦 Prima rulare Frontend! Se instalează modulele (1-2 min)..."
    npm install
fi

# Pornim React
npm start &

echo "=================================================="
echo "🎉 APLICAȚIA RULEAZĂ!"
echo "👉 Apasă Ctrl+C în acest terminal pentru a închide."
echo "=================================================="

wait