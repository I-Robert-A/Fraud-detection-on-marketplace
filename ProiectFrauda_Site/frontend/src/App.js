import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import './App.css';

// Componenta Modernă: Bară de Progres
const ProgressBar = ({ label, value, color }) => (
  <div className="progress-item">
    <div className="progress-label">
      <span>{label}</span>
      <span>{value}%</span>
    </div>
    <div className="progress-track">
      <motion.div 
        className={`progress-fill ${color}`}
        initial={{ width: 0 }}
        animate={{ width: `${value}%` }}
        transition={{ duration: 1, delay: 0.2 }}
      />
    </div>
  </div>
);

// Componenta NOUĂ: Checklist Inteligent (Umple spațiul din dreapta)
const SafetyChecklist = ({ riskLevel }) => {
  const tips = riskLevel > 50 ? [
    { icon: "🚫", text: "NU trimite niciun avans prin transfer!" },
    { icon: "📹", text: "Cere un apel video din apartament." },
    { icon: "🕵️", text: "Verifică imaginile pe Google Images." },
    { icon: "❓", text: "Întreabă de ce prețul e așa mic." }
  ] : [
    { icon: "📄", text: "Solicită extrasul de carte funciară." },
    { icon: "🤝", text: "Programează o vizionare fizică." },
    { icon: "💡", text: "Verifică instalațiile sanitare." },
    { icon: "🗣️", text: "Negociază prețul final." }
  ];

  return (
    <div className="checklist-container">
      {tips.map((tip, i) => (
        <motion.div 
          key={i} 
          className="checklist-item"
          initial={{ x: 20, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          transition={{ delay: 0.5 + (i * 0.1) }}
        >
          <span className="check-icon">{tip.icon}</span>
          <span>{tip.text}</span>
        </motion.div>
      ))}
    </div>
  );
};

function App() {
  const [url, setUrl] = useState('');
  const [data, setData] = useState(null);
  const [errorMsg, setErrorMsg] = useState('');
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState([]);
  const [activeImg, setActiveImg] = useState(null);

  // Încărcare istoric
  useEffect(() => {
    const saved = localStorage.getItem('scanHistorySales');
    if (saved) setHistory(JSON.parse(saved));
  }, []);

  // Funcție ȘTERGERE (NOUĂ)
  const deleteItem = (e, indexToDelete) => {
    e.stopPropagation(); // Oprește click-ul să nu declanșeze încărcarea scanării
    const newHistory = history.filter((_, i) => i !== indexToDelete);
    setHistory(newHistory);
    localStorage.setItem('scanHistorySales', JSON.stringify(newHistory));
  };

  const scan = async (scanUrl = url) => {
    if (!scanUrl) return;
    setLoading(true);
    setData(null);
    setErrorMsg('');
    setActiveImg(null);
    
    try {
      const res = await axios.post('http://localhost:5000/api/analyze', { url: scanUrl });
      
      if (res.data.error_type === "WRONG_TYPE") {
        setErrorMsg(res.data.message);
        setLoading(false);
        return;
      }

      const result = res.data;
      setData(result);
      if (result.details.Images.length > 0) setActiveImg(result.details.Images[0]);
      
      setHistory(prev => {
        // Evităm duplicatele
        if (prev.find(item => item.url === scanUrl)) return prev;
        const newH = [{
          url: scanUrl, 
          title: result.details.Titlu, 
          fraud: result.is_fraud, 
          date: new Date().toLocaleTimeString(), 
          data: result
        }, ...prev].slice(0, 15); // Păstrăm ultimele 15
        localStorage.setItem('scanHistorySales', JSON.stringify(newH));
        return newH;
      });

    } catch (e) {
      alert("Eroare server: " + (e.response?.data?.error || e.message));
    }
    setLoading(false);
  };

  const loadFromHistory = (item) => {
    setUrl(item.url);
    setData(item.data);
    setErrorMsg('');
    if (item.data.details.Images.length > 0) setActiveImg(item.data.details.Images[0]);
  };

  const reset = () => {
    setUrl('');
    setData(null);
    setErrorMsg('');
    setActiveImg(null);
  };

  // Scoruri vizuale
  const getScores = (d) => {
    const priceScore = d.details.Pret < d.ai_price * 0.6 ? 30 : 95;
    const sellerScore = d.details.SellerDays > 365 ? 98 : (d.details.SellerDays > 30 ? 80 : 40);
    const trustScore = 100 - d.confidence; 
    return { priceScore, sellerScore, trustScore };
  };

  return (
    <div className="app-container">
      
      {/* SIDEBAR */}
      <div className="sidebar">
        <div className="logo-box">
          <span className="logo-icon">🏢</span> 
          <div className="logo-text">
            <span className="main-title">FRAUD DETECTION</span>
            <span className="sub-title">ON MARKETPLACE</span>
          </div>
        </div>
        
        <button className="new-btn" onClick={reset}>SCANARE NOUĂ</button>

        <div className="history-list">
          <p className="section-title">ISTORIC ({history.length})</p>
          <AnimatePresence>
            {history.map((h, i) => (
              <motion.div 
                key={i} 
                className="history-item" 
                onClick={() => loadFromHistory(h)}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
              >
                <div className="h-left">
                  <div className={`dot ${h.fraud ? 'red' : 'green'}`}></div>
                  <div className="h-text">
                    <span className="h-tit">{h.title.substring(0, 15)}...</span>
                    <span className="h-date">{h.date}</span>
                  </div>
                </div>
                {/* BUTON STERGERE */}
                <button className="delete-btn" onClick={(e) => deleteItem(e, i)}>×</button>
              </motion.div>
            ))}
          </AnimatePresence>
          {history.length === 0 && <p className="empty-msg">Nicio scanare recentă</p>}
        </div>
      </div>

      {/* MAIN CONTENT */}
      <div className="main">
        {/* LIGHTBOX */}
        {activeImg && (
          <div className="lightbox-overlay" onClick={() => setActiveImg(null)}></div>
        )}

        {!data && !errorMsg && (
          <div className="search-state">
            <motion.div initial={{ y: 20, opacity: 0 }} animate={{ y: 0, opacity: 1 }}>
              <h2>Verifică un Anunț de Vânzare</h2>
              <p>Analiză preț, imagini și fraudă în timp real.</p>
              <div className="search-input">
                <input placeholder="Lipește link-ul Publi24..." value={url} onChange={e => setUrl(e.target.value)} />
                <button onClick={() => scan(url)} disabled={loading}>
                  {loading ? "..." : "VERIFICĂ"}
                </button>
              </div>
            </motion.div>
          </div>
        )}

        {errorMsg && (
          <div className="error-state">
            <div className="error-card"><span className="error-icon">⛔</span><h3>Eroare</h3><p>{errorMsg}</p><button onClick={reset}>Reîncearcă</button></div>
          </div>
        )}

        {data && (
          <motion.div className="dashboard" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            
            {/* 1. GALERIE SLIDER */}
            <div className="card gallery-section">
              <div className="hero-image" 
                   style={{backgroundImage: `url(${activeImg})`}}>
              </div>
              <div className="thumbnails-row">
                {data.details.Images.map((src, i) => (
                  <div 
                    key={i} 
                    className={`thumb-item ${activeImg === src ? 'active' : ''}`}
                    style={{backgroundImage: `url(${src})`}}
                    onClick={() => setActiveImg(src)}
                  ></div>
                ))}
              </div>
            </div>

            {/* 2. VERDICT & SCORURI */}
            <div className="verdict-container">
              <div className={`card verdict ${data.is_fraud ? 'bad' : 'good'}`}>
                <h3>VERDICT SCANARE</h3>
                <div className="verdict-txt">{data.message}</div>
                <div className="score">Risc: {data.confidence}%</div>
              </div>

              <motion.div 
                className="card security-breakdown"
                initial={{ y: 20, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ delay: 0.3 }}
              >
                <h3><span className="glow-icon">🛡️</span> Analiză Scoruri</h3>
                <div className="breakdown-grid">
                  <ProgressBar label="Validitate Preț" value={getScores(data).priceScore} color="blue" />
                  <ProgressBar label="Încredere Vânzător" value={getScores(data).sellerScore} color="purple" />
                  <ProgressBar label="Analiză Generală" value={getScores(data).trustScore} color={data.is_fraud ? 'red' : 'green'} />
                </div>
              </motion.div>
            </div>

            {/* 3. PREȚ */}
            <div className="card price">
              <h3>ANALIZĂ PREȚ PIAȚĂ</h3>
              <div className="price-compare">
                <div className="p-box">
                  <span className="lbl">Preț Cerut</span>
                  <span className="val">{data.details.Pret} €</span>
                  <span className="sub-val">{(data.details.Pret / data.details.Suprafata).toFixed(0)} €/mp</span>
                </div>
                <div className="vs">vs</div>
                <div className="p-box">
                  <span className="lbl">Estimare</span>
                  <span className="val ai">{data.ai_price} €</span>
                  <span className="sub-val">{(data.ai_price / data.details.Suprafata).toFixed(0)} €/mp</span>
                </div>
              </div>
            </div>

            {/* 4. RECOMANDĂRI SMART (NOU!) - Umple dreapta jos */}
            <div className="card tips-card">
              <h3>💡 Recomandări</h3>
              <SafetyChecklist riskLevel={data.confidence} />
            </div>

            {/* 5. DETALII */}
            <div className="card info">
              <h3>DETALII PROPRIETATE & VANZATOR</h3>
              <div className="row"><span>📐 Suprafață</span><strong>{data.details.Suprafata} mp</strong></div>
              <div className="row"><span>🚪 Camere</span><strong>{data.details.Camere}</strong></div>
              <hr/>
              <div className="row"><span>👤 Vechime</span><strong>{data.details.SellerDays} zile</strong></div>
              <div className="row"><span>📝 Postări</span><strong>{data.details.SellerPosts} active</strong></div>
            </div>

          </motion.div>
        )}
      </div>
      
    </div>
  );
}

export default App;