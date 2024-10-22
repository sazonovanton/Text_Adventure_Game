# 🎮 AI-Powered Text Adventure Game

Welcome to an immersive, AI-driven text adventure game that adapts to your choices and creates a unique story every time you play!  

Enjoy your unique, AI-crafted adventure! 🌟🗺️🐉

## 🌟 Features

- 🗨️ **Interactive Storytelling**: Engage with a dynamic narrative that evolves based on your decisions.
- 🎨 **Colored Text**: Enjoy visually enhanced storytelling with colorful highlights.
- 🧠 **AI Memory**: The game remembers key events and adapts the story accordingly.
- 📜 **Action History**: Recent choices influence the narrative flow.
- 🎒 **Inventory System**: Manage items that affect your journey.
- ⌨️ **Custom Actions**: Input your own creative choices beyond predefined options.
- 📊 **Player Status Tracking**: Monitor your progress and character development.
- 📝 **Detailed Logging**: Review your adventure with comprehensive session logs.

## 🚀 Getting Started

1. **Prerequisites**: Ensure you have Python 3 installed on your system.

2. **Clone the Repository**:
   ```
   git clone https://your-repository-url.git
   cd your-project-directory
   ```

3. **Install Dependencies**:
   ```
   pip install -r requirements.txt
   ```

4. **Configuration**:
   Create a `.env` file in the root directory with the following:
   ```
   OPENAI_API_KEY=your_api_key
   BASE_URL=https://openrouter.ai/api/v1
   MODEL_NAME=openai/gpt-4o-mini
   DEBUG=False
   GAME_DATA_FILE=game_data.json
   ```
   - Set `DEBUG=True` to enable detailed API response logging.
   - `BASE_URL` can be set to use OpenAI-compatible APIs (optional, game uses OpenAI by default).
   - `GAME_DATA_FILE` can be set to use a custom JSON file for game data (optional, default: `game_data.json`).

5. **Launch the Game**:
   ```
   python text_game.py
   ```

## 🕹️ How to Play

- 🔼🔽 Use **arrow keys** to navigate options
- ↩️ Press **Enter** to confirm your choice
- ⇥ Hit **Tab** to input a custom action
- 🛑 Press **Ctrl+C** to exit the game safely  

![Example](https://i.imgur.com/bhBCcjV.gif)

## 📊 Game Data and Logs

- **Session Logs**: Find detailed game progress in `logs/session_YYYYMMDD_HHMMSS.md`
- **Player Status**: Review game state in `logs/player_status_YYYYMMDD_HHMMSS.json`
- **Game Configuration**: Customize initial game state in `game_data.json` or your custom JSON file

## 🧠 AI "Memory" System

The game utilizes an advanced AI memory system to create a coherent and evolving narrative:

- 📚 Maintains a summary of key plot points and character development
- 🔄 Updates after each player action to influence future story generation
- 🎭 Enhances narrative consistency and depth

## 🛠️ Customization

- Modify `game_data.json` or create your own custom JSON file to define:
  - Initial player information
  - Starting inventory
  - Character background
  - Custom game scenarios
- Set the `GAME_DATA_FILE` environment variable to use your custom JSON file

## 🔐 Security Note

- Keep your `.env` file secure and never commit it to version control
- The `.gitignore` file is set up to exclude sensitive data and logs

## ⚠️ Important

This game is compatible with the OpenAI API and similar OpenAI-compatible APIs (like [openrouter.ai](openrouter.ai)). Ensure you have the necessary API key and credits to use your chosen service.


---

_This project was created with a help of [Cline](https://cline.bot/) to test it's capabilities._

