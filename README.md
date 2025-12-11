# Fraud-detection-on-marketplace
A machine learning project that detects fraudulent posts on online marketplaces.
# 🛡️ Marketplace Fraud Guard

<div align="center">

![Python](https://img.shields.io/badge/Python-3.9%2B-blue?style=for-the-badge&logo=python)
![PyTorch](https://img.shields.io/badge/PyTorch-Deep%20Learning-EE4C2C?style=for-the-badge&logo=pytorch)
![Scikit-Learn](https://img.shields.io/badge/Sklearn-NLP-F7931E?style=for-the-badge&logo=scikit-learn)
![Status](https://img.shields.io/badge/Maintenance-Active-success?style=for-the-badge)

**Un sistem inteligent hibrid pentru securitatea tranzacțiilor imobiliare.** Detectează automat anunțurile frauduloase folosind Deep Learning pentru prețuri și NLP pentru text.

[View Demo](#) • [Report Bug](https://github.com/I-Robert-A/Fraud-detection-on-marketplace/issues) • [Request Feature](https://github.com/I-Robert-A/Fraud-detection-on-marketplace/issues)

</div>

---

## ⚡ Overview
Platformele de imobiliare sunt vulnerabile la fraude de tip "Price Trap" sau "Advance Fee Scam". Acest proiect rezolvă problema printr-o abordare **multi-modală**:

1.  **Valuare Obiectivă:** Un model Neural Network (PyTorch) estimează prețul real al pieței. Dacă prețul listat este suspect de mic, se ridică un flag.
2.  **Analiză Lingvistică:** Un clasificator NLP (TF-IDF + Logistic Regression) scanează descrierea pentru tipare semantice de înșelăciune.

## 🧠 Arhitectura Sistemului

```mermaid
graph LR
    A[🌍 Web Scraper] -->|Raw Data| B(Data Processing)
    B --> C{⚔️ Dual AI Core}
    C -->|Numerical Data| D[📉 Price Estimator Model]
    C -->|Text Data| E[📝 Scam Classifier Model]
    D & E --> F[🚨 FINAL RISK SCORE]
    style F fill:#f96,stroke:#333,stroke-width:2px
