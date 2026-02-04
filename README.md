# One More Run 👁‍🗨

> "A zero-sum game of trust, deception, and calculated risk."

**One More Run** is a psychological strategy game based on Game Theory concepts (The Inspection Game, Signaling Theory, Mixed Strategy Nash Equilibrium). You play as a Smuggler against an AI Inspector.

<img width="2588" height="1552" alt="image" src="https://github.com/user-attachments/assets/c34672e8-9b91-4c11-8a2e-be37765939a6" />


## 🎮 The Mission

You have **20 Rounds** to maximize your score.
The Inspector learns from your patterns. If you become predictable, you get caught.

### Moves

| Action | Cost/Gain | Effect | Game Theory Concept |
| :--- | :--- | :--- | :--- |
| **Smuggle** | +10 / -5 | High risk, high reward. Fails if Inspected. | *Risk Reward* |
| **Lay Low** | +1 | Safe play. Gain small profit. | *Passive Strategy* |
| **Bribe** | -3 | **Grants 2 Turns of Immunity**. Inspector looks away. | *Costly Signaling* |
| **Signal Truce** | 0 | Attempts to build Trust without cost. | *Cheap Talk* |

---

## ⚡ Features

*   **Adaptive AI**: The Inspector tracks your Smuggle Rate and "Trust Level" to decide whether to Inspect or Trap you.
*   **Tactical Debriefing**: At the end of the game, get a "Game Theory Report" analyzing your playstyle (e.g., *Mixed Strategy Equilibrium*, *Greedy Algorithm*).
*   **Variable Stakes**: Choose cargo size (x1, x2, x3) to scale your risk and reward.
*   **Social Sharing**: Generate a high-res scorecard image to share your run.
*   **Cyberpunk UI**: Full CRT terminal aesthetic with scanlines and typewriter effects.
*   **LLM Integration (Optional)**: Connect OpenAI or Anthropic API keys for dynamic, trash-talking Inspector dialogue.

---

## 🛠️ Installation & Setup

### Prerequisites
*   Python 3.8+
*   `pip`

### Local Development

1.  **Clone the repository**
    ```bash
    git clone https://github.com/aadithya1996/OneMoreRun.git
    cd OneMoreRun
    ```

2.  **Install dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run the Web App**
    ```bash
    python3 web_app.py
    ```
    Open `http://localhost:5000` in your browser.

4.  **(Optional) Run CLI Version**
    For the hardcore terminal experience:
    ```bash
    python3 inspection_game.py
    ```

---

## 🚀 Deployment (Vercel)

This project is configured for one-click deployment on Vercel.

1.  Push your code to GitHub.
2.  Import the project in Vercel.
3.  Ensure `vercel.json` and `requirements.txt` are present (they are included).
4.  **Environment Variables**:
    *   `OPENAI_API_KEY` (Optional): Enable GPT-4o dialogue.
    *   `ANTHROPIC_API_KEY` (Optional): Enable Claude 3 dialogue.
5.  Deploy!

---

## 🧠 Strategic Tips

*   **Don't be greedy**: If you smuggle every turn, the Inspector will inspect every turn (Nash Equilibrium).
*   **Use Bribes wisely**: A bribe costs points but guarantees safety. Use it to set up a massive x3 Smuggle on the next turn.
*   **Watch the Trust Meter**: If Trust is high, the Inspector *might* let you go... or they might be baiting a trap.

---

## 📄 License

MIT License. Free to play, hack, and distribute.
