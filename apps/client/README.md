# 📈 Stock Agents Dashboard (Pro)

> **A Multi-Agent Financial Intelligence System based on the "TradingAgents" Framework.**

[![Powered by Gemini](https://img.shields.io/badge/Powered%20by-Gemini%203%20Pro-4E8BF5?style=for-the-badge&logo=google-gemini)](https://deepmind.google/technologies/gemini/)
[![React 19](https://img.shields.io/badge/Frontend-React%2019-61DAFB?style=for-the-badge&logo=react)](https://react.dev/)
[![Status](https://img.shields.io/badge/Status-Alpha-orange?style=for-the-badge)]()

This project is a **Sophisticated Financial Dashboard** designed to simulate an institutional trading floor. Instead of a single AI trying to do everything, it orchestrates a **Squad of Specialized Agents** (Analyst, Researcher, Risk Manager, Fund Manager) to debate, deliberate, and decide on stock trades in real-time.

Based on the principles of the [TradingAgents Paper](https://arxiv.org/abs/2412.20138), this system leverages **Google Gemini 3 Pro's** reasoning capabilities to reduce hallucinations and improve decision quality through adversarial debate.

---

## 🧠 The "TradingAgents" Architecture

We mimic a real-world asset management firm's workflow within a structured AI pipeline:

### 1. 🕵️ The Scout (Discovery Agent)
*   **Role:** Scans the market for opportunities based on natural language themes (e.g., "Undervalued AI supply chain stocks").
*   **Model:** `gemini-3-pro-preview`
*   **Capabilities:** Semantic search, trend identification, sector filtering.

### 2. 🔍 The Analyst Team (Data Mining)
*   **Role:** Gathers raw intelligence.
*   **Sub-Agents:**
    *   *Technical Analyst:* RS, MACD, Bollinger Bands, Key Levels.
    *   *Sentiment Analyst:* News sentiment, Social volume.
    *   *Fundamental Analyst:* Earnings, P/E ratios, Catalysts.

### 3. ⚔️ The Researcher Debate (Adversarial Reasoning)
*   **Role:** Prevents "Echo Chamber" bias.
*   **Mechanism:**
    *   🐮 **Bull Agent:** Forced to find the strongest arguments *FOR* the trade.
    *   🐻 **Bear Agent:** Forced to find the strongest arguments *AGAINST* the trade.
    *   **Outcome:** A synthesized debate log showing the clash of perspectives.

### 4. 🛡️ The Risk Manager (The Guardian)
*   **Role:** Pure downside protection. Ignores FOMO.
*   **Output:** A 0-10 Risk Score, Volatility Assessment, and Max Drawdown estimation.
*   **Authority:** Can veto a "Buy" signal if liquidity or volatility risks are too high.

### 5. 👨‍💼 The Fund Manager (Decision Maker)
*   **Role:** Synthesizes all inputs into a final actionable signal.
*   **Output:** Signal (Strong Buy/Hold/Sell), Entry Zone, Targets, and Confidence Score.

---

## ✨ Dashboard Features

*   **⚡ Real-Time "Watchdog" Ticker**: A scrolling ticker at the top that monitors breaking news (simulated/live) relevant to your watchlist.
*   **📊 Interactive Visualization**:
    *   **Workflow Timeline**: Watch the agents step through their tasks in real-time.
    *   **Debate Meter**: Visual balance bar showing Bull vs. Bear strength.
    *   **Risk Gauge**: Dynamic gauge showing the safety level of the trade.
*   **🗣️ AI Audio Briefing**: Uses `gemini-2.5-flash-tts` to generate a broadcast-quality "Morning Briefing" summary of the analysis.
*   **💬 Interrogate the Agent**: Don't just read the report—chat with the Fund Manager to ask specific questions like "What happens if interest rates rise?"

---

## 🛠️ Technical Stack

- **Core**: React 19, TypeScript, Vite.
- **Styling**: Tailwind CSS (Optimized for Dark Mode / Large Screens).
- **AI Engine**: Google GenAI SDK (`@google/genai`).
    - **Reasoning**: `gemini-3-pro-preview` (Configured with high `thinkingBudget`).
    - **Speed/Chat**: `gemini-3-flash-preview`.
    - **Speech**: `gemini-2.5-flash-preview-tts`.
- **Charting**: Recharts.
- **Icons**: Lucide React.

---

## 🚀 Setup & Usage

### Prerequisites
*   Node.js v18+
*   A Google Cloud Project with **Gemini API** enabled (Billing required for Search Grounding & Pro models).

### Installation

1.  **Clone the Repo**
    ```bash
    git clone https://github.com/yourusername/stock-agents-dashboard.git
    cd stock-agents-dashboard
    ```

2.  **Install Packages**
    ```bash
    npm install
    ```

3.  **Set API Key**
    *   Create a `.env` file in the root.
    *   Add your key:
        ```env
        API_KEY=AIzaSy...YourKeyHere
        ```

4.  **Run Development Server**
    ```bash
    npm run dev
    ```

### Usage Tips
*   **Add Stocks**: Use the Sidebar to add US (AAPL), HK (00700.HK), or CN (600276.SH) stocks.
*   **AI Scout**: Click "AI Market Scout" in the sidebar and type "High dividend stocks in HK" to let the agent find tickers for you.
*   **Deep Analysis**: Click "Run Agent" on any card. Wait for the 4-step pipeline to complete.
*   **Audio Mode**: Open the modal and click "Briefing" to hear the report while you multi-task.

---

## 🔮 Future Roadmap (Experiments)

*   [ ] **Portfolio Level Agent**: An agent that analyzes the correlation *between* your watchlist stocks to suggest diversification.
*   [ ] **Memory Module**: Using a vector database to let agents remember past predictions and "learn" from mistakes.
*   [ ] **Macro-Economic Overlay**: A dedicated agent tracking Fed rates and GDP to bias the entire dashboard's sentiment.

---

## ⚠️ Disclaimer

**Simulated Environment**: This application is a technical demonstration of AI Agent capabilities.
**Not Financial Advice**: The signals generated are probabilistic outputs from a Language Model. Do not trade real money based solely on this dashboard.

---

*Built with ❤️ by [Your Name] for the AI Trading Community.*
