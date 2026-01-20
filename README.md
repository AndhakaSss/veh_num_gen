# Vehicle Number Generator Telegram Bot

A Telegram bot that generates vehicle numbers based on user input and sends them as a .txt file.

## Features

- Interactive conversation flow to collect vehicle number components
- Generates all numbers in a specified range
- Saves results to a .txt file
- Sends the file directly to the user via Telegram

## Setup

### 1. Create a Telegram Bot

1. Open Telegram and search for [@BotFather](https://t.me/botfather)
2. Send `/newbot` command
3. Follow the instructions to create your bot
4. Copy the bot token you receive

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Set Bot Token

**Option 1: Environment Variable (Windows PowerShell)**
```powershell
$env:TELEGRAM_BOT_TOKEN="your_bot_token_here"
```

**Option 2: Environment Variable (Windows CMD)**
```cmd
set TELEGRAM_BOT_TOKEN=your_bot_token_here
```

**Option 3: Create .env file** (requires python-dotenv)
Create a `.env` file in the project directory:
```
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

### 4. Run the Bot

```bash
python bot.py
```

## Usage

1. Start a conversation with your bot on Telegram
2. Send `/start` command
3. Follow the prompts:
   - **First 2 letters** (e.g., AB)
   - **Second 2 numbers** (e.g., 12)
   - **Third 2 letters (series)** (e.g., CD)
   - **Starting 4 digits** (e.g., 0001)
   - **Ending 4 digits** (e.g., 1000)

4. The bot will generate all vehicle numbers in the format: `AB12CD0001` to `AB12CD1000`
5. You'll receive a .txt file with all generated numbers

## Example

Input:
- First letters: `AB`
- Second numbers: `12`
- Series letters: `CD`
- Start digits: `0001`
- End digits: `0050`

Output: A file containing:
```
AB12CD0001
AB12CD0002
AB12CD0003
...
AB12CD0050
```

## Commands

- `/start` - Start generating vehicle numbers
- `/cancel` - Cancel the current operation

## Notes

- All letters are automatically converted to uppercase
- Numbers are zero-padded to 4 digits
- The generated file is automatically deleted after sending
- Make sure the start digits are less than or equal to end digits

