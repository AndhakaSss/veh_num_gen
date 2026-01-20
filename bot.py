import os
import logging
import asyncio
import csv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from telegram.constants import ParseMode
from telegram.error import TimedOut, NetworkError

# ============================================================================
# CONFIGURATION
# ============================================================================

# Bot Token - Set here or use environment variable TELEGRAM_BOT_TOKEN
# For Railway/Cloud: Use environment variable
# For local: Set BOT_TOKEN here or use environment variable
BOT_TOKEN = ""  # Leave empty to use environment variable only

# ============================================================================

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============================================================================
# VEHICLE NUMBER GENERATION FUNCTIONS
# ============================================================================

def generate_vehicle_numbers(first_letters, second_numbers, third_letters, start_digits, end_digits):
    """Generate vehicle numbers and save to file"""
    numbers = []
    
    # Validate inputs
    if len(first_letters) != 2 or not first_letters.isalpha():
        return None, "First part must be exactly 2 letters"
    if len(second_numbers) != 2 or not second_numbers.isdigit():
        return None, "Second part must be exactly 2 digits"
    if len(third_letters) != 2 or not third_letters.isalpha():
        return None, "Third part (series) must be exactly 2 letters"
    if len(start_digits) != 4 or not start_digits.isdigit():
        return None, "Start digits must be exactly 4 digits"
    if len(end_digits) != 4 or not end_digits.isdigit():
        return None, "End digits must be exactly 4 digits"
    
    start_num = int(start_digits)
    end_num = int(end_digits)
    
    if start_num > end_num:
        return None, "Start digits must be less than or equal to end digits"
    
    # Generate all numbers in range
    for num in range(start_num, end_num + 1):
        number_str = f"{first_letters.upper()}{second_numbers}{third_letters.upper()}{num:04d}"
        numbers.append(number_str)
    
    # Save to file
    filename = f"vehicle_numbers_{first_letters.upper()}{second_numbers}{third_letters.upper()}.txt"
    with open(filename, 'w', encoding='utf-8') as f:
        for number in numbers:
            f.write(number + '\n')
    
    return filename, None

def generate_batch_vehicle_numbers(first_letters, second_numbers, series_list, start_digits, end_digits):
    """Generate vehicle numbers for multiple series and save to file"""
    all_numbers = []
    
    # Validate inputs
    if len(first_letters) != 2 or not first_letters.isalpha():
        return None, "First part must be exactly 2 letters"
    if len(second_numbers) != 2 or not second_numbers.isdigit():
        return None, "Second part must be exactly 2 digits"
    if len(start_digits) != 4 or not start_digits.isdigit():
        return None, "Start digits must be exactly 4 digits"
    if len(end_digits) != 4 or not end_digits.isdigit():
        return None, "End digits must be exactly 4 digits"
    
    if not series_list:
        return None, "No series provided"
    
    start_num = int(start_digits)
    end_num = int(end_digits)
    
    if start_num > end_num:
        return None, "Start digits must be less than or equal to end digits"
    
    # Generate numbers for each series
    for series in series_list:
        series = series.strip().upper()
        if len(series) != 2 or not series.isalpha():
            return None, f"Invalid series: {series}. Each series must be exactly 2 letters"
        
        for num in range(start_num, end_num + 1):
            number_str = f"{first_letters.upper()}{second_numbers}{series}{num:04d}"
            all_numbers.append(number_str)
    
    # Save to file
    filename = f"vehicle_numbers_batch_{first_letters.upper()}{second_numbers}.txt"
    with open(filename, 'w', encoding='utf-8') as f:
        for number in all_numbers:
            f.write(number + '\n')
    
    return filename, None

def convert_txt_to_csv(txt_file_path, csv_file_path):
    """Convert TXT file to CSV format - handles VEHICLE_NUMBER - PHONE_NUMBER or VEHICLE_NUMBER - PHONE_NUMBER - OTHER format"""
    try:
        with open(txt_file_path, 'r', encoding='utf-8') as txt_file:
            lines = txt_file.readlines()
        
        if not lines:
            return False, "The TXT file is empty"
        
        # Write to CSV
        with open(csv_file_path, 'w', encoding='utf-8', newline='') as csv_file:
            writer = csv.writer(csv_file, delimiter=',')
            
            # Write header: Number,Vehicle Number
            writer.writerow(['Number', 'Vehicle Number'])
            
            # Process each line
            processed_count = 0
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Check if line matches format: VEHICLE_NUMBER - PHONE_NUMBER or VEHICLE_NUMBER - PHONE_NUMBER - OTHER
                if ' - ' in line:
                    # Split by ' - ' and take first 2 parts (ignore third part if present)
                    parts = line.split(' - ', 2)
                    if len(parts) >= 2:
                        vehicle_number = parts[0].strip()
                        phone_number = parts[1].strip()
                        # Only write if both parts are not empty
                        if vehicle_number and phone_number:
                            writer.writerow([phone_number, vehicle_number])
                            processed_count += 1
            
            if processed_count == 0:
                return False, "No valid data found. Expected format: VEHICLE_NUMBER - PHONE_NUMBER"
        
        return True, None
    except Exception as e:
        return False, str(e)

# ============================================================================
# COMMAND HANDLERS
# ============================================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start command - begin vehicle number generation"""
    context.user_data.clear()  # Clear any previous state
    context.user_data['mode'] = 'single'
    context.user_data['step'] = 'first_letters'
    
    welcome_msg = (
        "🚗 *Vehicle Number Generator Bot*\n\n"
        "I'll help you generate vehicle numbers in the format:\n"
        "`XX##YY####`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📋 *Step 1 of 5*\n"
        "Enter the *first 2 letters*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "💡 *Example:* `AB`\n"
        "Use /cancel to stop anytime"
    )
    await update.message.reply_text(
        welcome_msg,
        parse_mode=ParseMode.MARKDOWN
    )

async def batch_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Batch command - generate multiple series"""
    context.user_data.clear()
    context.user_data['mode'] = 'batch'
    context.user_data['step'] = 'first_letters'
    
    welcome_msg = (
        "📦 *Batch Number Generator*\n\n"
        "Generate numbers for *multiple series* at once!\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📋 *Step 1 of 5*\n"
        "Enter the *first 2 letters*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "💡 *Example:* `AB`\n"
        "Use /cancel to stop anytime"
    )
    await update.message.reply_text(
        welcome_msg,
        parse_mode=ParseMode.MARKDOWN
    )

async def txt2csv_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """TXT to CSV converter command"""
    context.user_data.clear()
    context.user_data['mode'] = 'txt2csv'
    context.user_data['step'] = 'waiting_file'
    
    welcome_msg = (
        "📄 *TXT to CSV Converter*\n\n"
        "Convert your .txt files to CSV format!\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📤 *How to use:*\n\n"
        "1. Send me a .txt file\n"
        "2. I'll convert it to CSV format\n"
        "3. You can rename the file if needed\n"
        "4. Output: `Number,Vehicle Number`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "💡 *Supported format:*\n"
        "• Format: `VEHICLE_NUMBER - PHONE_NUMBER`\n"
        "• Example: `CG13AA0010 - 7389247318`\n"
        "• Output CSV: `Number,Vehicle Number`\n\n"
        "📤 *Please upload your .txt file now:*\n"
        "Use /cancel to stop"
    )
    await update.message.reply_text(
        welcome_msg,
        parse_mode=ParseMode.MARKDOWN
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Help command"""
    help_text = (
        "📖 *Help - Vehicle Number Generator Bot*\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🚗 *Vehicle Number Generation*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Format: `[2 Letters][2 Numbers][2 Letters][4 Digits]`\n\n"
        "📝 *Example:*\n"
        "• First 2 letters: `AB`\n"
        "• Second 2 numbers: `12`\n"
        "• Series (2 letters): `CD`\n"
        "• Start digits: `0001`\n"
        "• End digits: `0100`\n\n"
        "Result: `AB12CD0001` to `AB12CD0100`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📄 *TXT to CSV Converter*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Convert your .txt files to CSV format\n"
        "Each line becomes a row in the CSV\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🔹 `/start` - Generate single series\n"
        "🔹 `/batch` - Generate multiple series at once\n"
        "🔹 `/txt2csv` - Convert TXT file to CSV\n"
        "🔹 `/help` - Show this help message\n"
        "🔹 `/cancel` - Cancel current operation"
    )
    await update.message.reply_text(
        help_text,
        parse_mode=ParseMode.MARKDOWN
    )

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Cancel command"""
    context.user_data.clear()
    await update.message.reply_text(
        "❌ *Operation Cancelled*\n\n"
        "All progress has been cleared.\n\n"
        "Use /start, /batch, or /txt2csv to begin again.",
        parse_mode=ParseMode.MARKDOWN
    )

# ============================================================================
# MESSAGE HANDLERS (State-based processing)
# ============================================================================

async def safe_reply(update: Update, message: str, parse_mode=None, reply_markup=None, max_retries=2):
    """Safely send a reply with retry logic for timeouts"""
    for attempt in range(max_retries):
        try:
            await update.message.reply_text(message, parse_mode=parse_mode, reply_markup=reply_markup)
            return True
        except (TimedOut, NetworkError):
            if attempt < max_retries - 1:
                await asyncio.sleep(1)
                continue
            else:
                logger.warning(f"Failed to send message after {max_retries} attempts (timeout)")
                return False
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False
    return False

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle all text messages based on current state"""
    if not update.message or not update.message.text:
        return
    
    try:
        user_data = context.user_data
        mode = user_data.get('mode')
        step = user_data.get('step')
        
        # If no active mode, ignore
        if not mode:
            return
        
        text = update.message.text.strip()
        
        # Handle txt2csv rename step
        if mode == 'txt2csv' and step == 'waiting_rename':
            await handle_csv_rename(update, context, text)
            return
        
        # Handle single generation mode
        if mode == 'single':
            await handle_single_generation(update, context, text, step)
        
        # Handle batch generation mode
        elif mode == 'batch':
            await handle_batch_generation(update, context, text, step)
        
        # txt2csv mode is handled by document handler
    except Exception as e:
        logger.error(f"Error in handle_message: {e}", exc_info=True)
        try:
            await safe_reply(update, "❌ An error occurred. Please try again or use /cancel to restart.")
        except:
            pass

async def handle_csv_rename(update: Update, context: ContextTypes.DEFAULT_TYPE, new_filename: str) -> None:
    """Handle CSV file rename"""
    user_data = context.user_data
    csv_file_path = user_data.get('csv_file_path')
    txt_file_path = user_data.get('txt_file_path')
    line_count = user_data.get('line_count', 0)
    file_size_mb = user_data.get('file_size_mb', 0)
    
    if not csv_file_path:
        await safe_reply(update, "❌ Error: File not found. Please start over with /txt2csv", parse_mode=ParseMode.MARKDOWN)
        context.user_data.clear()
        return
    
    # Clean filename - remove invalid characters and ensure .csv extension
    new_filename = new_filename.strip()
    if not new_filename:
        await safe_reply(update, "❌ *Invalid filename!*\n\nPlease enter a valid filename:", parse_mode=ParseMode.MARKDOWN)
        return
    
    # Remove invalid characters for filenames
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        new_filename = new_filename.replace(char, '_')
    
    # Ensure .csv extension
    if not new_filename.lower().endswith('.csv'):
        new_filename = new_filename + '.csv'
    
    # Send file with new name
    await send_csv_file(update.message, context, csv_file_path, new_filename, line_count, file_size_mb, txt_file_path)

async def handle_single_generation(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, step: str) -> None:
    """Handle single generation steps"""
    user_data = context.user_data
    
    if step == 'first_letters':
        text = text.upper()
        if len(text) != 2 or not text.isalpha():
            await safe_reply(update,
                "❌ *Invalid Input!*\n\nPlease enter exactly 2 letters (e.g., AB):",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        user_data['first_letters'] = text
        user_data['step'] = 'second_numbers'
        await safe_reply(update,
            f"✅ *Step 1 Complete!*\nFirst letters: `{text}`\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "📋 *Step 2 of 5*\nEnter the *second 2 numbers*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "💡 *Example:* `12`",
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif step == 'second_numbers':
        if len(text) != 2 or not text.isdigit():
            await update.message.reply_text(
                "❌ *Invalid Input!*\n\nPlease enter exactly 2 digits (e.g., 12):",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        user_data['second_numbers'] = text
        user_data['step'] = 'third_letters'
        first_letters = user_data.get('first_letters', '')
        await update.message.reply_text(
            f"✅ *Step 2 Complete!*\nSecond numbers: `{text}`\n\n"
            f"📝 Current format: `{first_letters}{text}XX####`\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "📋 *Step 3 of 5*\nEnter the *series (2 letters)*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "💡 *Example:* `CD`",
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif step == 'third_letters':
        text = text.upper()
        if len(text) != 2 or not text.isalpha():
            await update.message.reply_text(
                "❌ *Invalid Input!*\n\nPlease enter exactly 2 letters (e.g., CD):",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        user_data['third_letters'] = text
        user_data['step'] = 'start_digits'
        first_letters = user_data.get('first_letters', '')
        second_numbers = user_data.get('second_numbers', '')
        await update.message.reply_text(
            f"✅ *Step 3 Complete!*\nSeries letters: `{text}`\n\n"
            f"📝 Current format: `{first_letters}{second_numbers}{text}####`\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "📋 *Step 4 of 5*\nEnter the *starting 4 digits*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "💡 *Example:* `0001`",
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif step == 'start_digits':
        if len(text) != 4 or not text.isdigit():
            await update.message.reply_text(
                "❌ *Invalid Input!*\n\nPlease enter exactly 4 digits (e.g., 0001):",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        user_data['start_digits'] = text
        user_data['step'] = 'end_digits'
        first_letters = user_data.get('first_letters', '')
        second_numbers = user_data.get('second_numbers', '')
        third_letters = user_data.get('third_letters', '')
        await update.message.reply_text(
            f"✅ *Step 4 Complete!*\nStart digits: `{text}`\n\n"
            f"📝 Current format: `{first_letters}{second_numbers}{third_letters}{text}` to `{first_letters}{second_numbers}{third_letters}XXXX`\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "📋 *Step 5 of 5*\nEnter the *ending 4 digits*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "💡 *Example:* `1000`\n⚠️ Must be ≥ start digits",
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif step == 'end_digits':
        if len(text) != 4 or not text.isdigit():
            await update.message.reply_text(
                "❌ *Invalid Input!*\n\nPlease enter exactly 4 digits (e.g., 1000):",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Get all data
        first_letters = user_data.get('first_letters')
        second_numbers = user_data.get('second_numbers')
        third_letters = user_data.get('third_letters')
        start_digits = user_data.get('start_digits')
        end_digits = text
        
        # Validate range
        if int(start_digits) > int(end_digits):
            await update.message.reply_text(
                f"❌ *Invalid Range!*\n\nStart digits (`{start_digits}`) must be ≤ End digits (`{end_digits}`)\n\nPlease enter a valid ending 4 digits:",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Calculate count
        count = int(end_digits) - int(start_digits) + 1
        
        # Show confirmation
        preview_msg = (
            "✅ *All Information Collected!*\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "📋 *Summary:*\n\n"
            f"🔹 Format: `{first_letters}{second_numbers}{third_letters}####`\n"
            f"🔹 Range: `{start_digits}` to `{end_digits}`\n"
            f"🔹 Total numbers: *{count:,}*\n\n"
            f"📝 Example: `{first_letters}{second_numbers}{third_letters}{start_digits}`\n"
            f"📝 Example: `{first_letters}{second_numbers}{third_letters}{end_digits}`\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Ready to generate? Click the button below!"
        )
        
        keyboard = [[InlineKeyboardButton("✅ Generate Numbers", callback_data="generate")],
                   [InlineKeyboardButton("❌ Cancel", callback_data="cancel_gen")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            preview_msg,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        
        user_data['step'] = 'confirm'
        user_data['end_digits'] = end_digits

async def handle_batch_generation(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, step: str) -> None:
    """Handle batch generation steps"""
    user_data = context.user_data
    
    if step == 'first_letters':
        text = text.upper()
        if len(text) != 2 or not text.isalpha():
            await update.message.reply_text("❌ Invalid! Enter exactly 2 letters (e.g., AB):", parse_mode=ParseMode.MARKDOWN)
            return
        user_data['first_letters'] = text
        user_data['step'] = 'second_numbers'
        await update.message.reply_text(f"✅ Step 1 Complete! First letters: `{text}`\n\n📋 Step 2 of 5\nEnter the *second 2 numbers*\n💡 Example: `12`", parse_mode=ParseMode.MARKDOWN)
    
    elif step == 'second_numbers':
        if len(text) != 2 or not text.isdigit():
            await update.message.reply_text("❌ Invalid! Enter exactly 2 digits (e.g., 12):", parse_mode=ParseMode.MARKDOWN)
            return
        user_data['second_numbers'] = text
        user_data['step'] = 'series_list'
        await update.message.reply_text(f"✅ Step 2 Complete! Second numbers: `{text}`\n\n📋 Step 3 of 5\nEnter *multiple series* (2 letters each)\n💡 Format: `CD,EF,GH` or `CD EF GH`", parse_mode=ParseMode.MARKDOWN)
    
    elif step == 'series_list':
        text = text.upper()
        if ',' in text:
            series_list = [s.strip() for s in text.split(',')]
        else:
            series_list = text.split()
        
        valid_series = []
        for series in series_list:
            series = series.strip()
            if len(series) == 2 and series.isalpha():
                valid_series.append(series)
        
        if not valid_series:
            await update.message.reply_text("❌ Invalid! Enter at least one valid 2-letter series.\n💡 Example: `CD,EF,GH`", parse_mode=ParseMode.MARKDOWN)
            return
        
        user_data['series_list'] = valid_series
        user_data['step'] = 'start_digits'
        await update.message.reply_text(f"✅ Step 3 Complete! Series: `{', '.join(valid_series)}`\nTotal: *{len(valid_series)}*\n\n📋 Step 4 of 5\nEnter the *starting 4 digits*\n💡 Example: `0001`", parse_mode=ParseMode.MARKDOWN)
    
    elif step == 'start_digits':
        if len(text) != 4 or not text.isdigit():
            await update.message.reply_text("❌ Invalid! Enter exactly 4 digits (e.g., 0001):", parse_mode=ParseMode.MARKDOWN)
            return
        user_data['start_digits'] = text
        user_data['step'] = 'end_digits'
        await update.message.reply_text(f"✅ Step 4 Complete! Start digits: `{text}`\n\n📋 Step 5 of 5\nEnter the *ending 4 digits*\n💡 Example: `1000`\n⚠️ Must be ≥ start digits", parse_mode=ParseMode.MARKDOWN)
    
    elif step == 'end_digits':
        if len(text) != 4 or not text.isdigit():
            await update.message.reply_text("❌ Invalid! Enter exactly 4 digits (e.g., 1000):", parse_mode=ParseMode.MARKDOWN)
            return
        
        first_letters = user_data.get('first_letters')
        second_numbers = user_data.get('second_numbers')
        series_list = user_data.get('series_list', [])
        start_digits = user_data.get('start_digits')
        end_digits = text
        
        if int(start_digits) > int(end_digits):
            await update.message.reply_text(f"❌ Invalid Range! Start (`{start_digits}`) must be ≤ End (`{end_digits}`)", parse_mode=ParseMode.MARKDOWN)
            return
        
        numbers_per_series = int(end_digits) - int(start_digits) + 1
        total_count = numbers_per_series * len(series_list)
        series_display = ', '.join(series_list)
        
        preview_msg = (
            "✅ *All Information Collected!*\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "📋 *Batch Summary:*\n\n"
            f"🔹 Format: `{first_letters}{second_numbers}[SERIES]####`\n"
            f"🔹 Series: `{series_display}`\n"
            f"🔹 Series count: *{len(series_list)}*\n"
            f"🔹 Range: `{start_digits}` to `{end_digits}`\n"
            f"🔹 Numbers per series: *{numbers_per_series:,}*\n"
            f"🔹 Total numbers: *{total_count:,}*\n\n"
            "Ready to generate? Click the button below!"
        )
        
        keyboard = [[InlineKeyboardButton("✅ Generate Batch", callback_data="batch_generate")],
                   [InlineKeyboardButton("❌ Cancel", callback_data="cancel_gen")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(preview_msg, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
        user_data['step'] = 'confirm'
        user_data['end_digits'] = end_digits

# ============================================================================
# CALLBACK HANDLERS
# ============================================================================

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "cancel_gen":
        await query.edit_message_text("❌ *Generation Cancelled*\n\nUse /start or /batch to begin again.", parse_mode=ParseMode.MARKDOWN)
        context.user_data.clear()
        return
    
    user_data = context.user_data
    mode = user_data.get('mode')
    
    if query.data == "generate" and mode == 'single':
        first_letters = user_data.get('first_letters')
        second_numbers = user_data.get('second_numbers')
        third_letters = user_data.get('third_letters')
        start_digits = user_data.get('start_digits')
        end_digits = user_data.get('end_digits')
        
        await query.edit_message_text("⏳ *Generating vehicle numbers...*\n\nPlease wait...", parse_mode=ParseMode.MARKDOWN)
        
        filename, error = generate_vehicle_numbers(first_letters, second_numbers, third_letters, start_digits, end_digits)
        
        if error:
            await query.edit_message_text(f"❌ *Error:*\n\n`{error}`\n\nUse /start to try again.", parse_mode=ParseMode.MARKDOWN)
            context.user_data.clear()
            return
        
        with open(filename, 'r', encoding='utf-8') as f:
            count = len(f.readlines())
        
        file_size = os.path.getsize(filename)
        file_size_mb = file_size / (1024 * 1024)
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with open(filename, 'rb') as f:
                    caption = (
                        f"✅ *Successfully Generated!*\n\n"
                        f"📊 *Statistics:*\n"
                        f"• Total numbers: *{count:,}*\n"
                        f"• Format: `{first_letters}{second_numbers}{third_letters}####`\n"
                        f"• Range: `{start_digits}` to `{end_digits}`\n"
                        f"• File size: *{file_size_mb:.2f} MB*\n\n"
                        f"📁 File ready for download!"
                    )
                    await query.message.reply_document(document=f, filename=filename, caption=caption, parse_mode=ParseMode.MARKDOWN)
                break
            except (TimedOut, NetworkError):
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)
                    continue
                else:
                    await query.edit_message_text(f"⚠️ *File too large to send*\n\nTotal numbers: *{count:,}*\n\nPlease reduce the range.", parse_mode=ParseMode.MARKDOWN)
                    try:
                        os.remove(filename)
                    except:
                        pass
                    context.user_data.clear()
                    return
        
        try:
            os.remove(filename)
        except:
            pass
        
        await query.message.reply_text(f"🎉 *Generation Complete!*\n\n✅ {count:,} vehicle numbers generated!\n\nUse /start to generate more", parse_mode=ParseMode.MARKDOWN)
        context.user_data.clear()
    
    elif query.data == "csv_use_default":
        user_data = context.user_data
        csv_file_path = user_data.get('csv_file_path')
        txt_file_path = user_data.get('txt_file_path')
        default_filename = user_data.get('default_filename', 'converted.csv')
        line_count = user_data.get('line_count', 0)
        file_size_mb = user_data.get('file_size_mb', 0)
        
        if csv_file_path:
            await query.edit_message_text("📤 *Sending file with default name...*", parse_mode=ParseMode.MARKDOWN)
            await send_csv_file(query.message, context, csv_file_path, default_filename, line_count, file_size_mb, txt_file_path)
        else:
            await query.edit_message_text("❌ Error: File not found. Please start over with /txt2csv", parse_mode=ParseMode.MARKDOWN)
            context.user_data.clear()
    
    elif query.data == "csv_rename":
        context.user_data['step'] = 'waiting_rename'
        await query.edit_message_text(
            "✏️ *Rename File*\n\n"
            "Please enter the new filename (without extension):\n\n"
            "💡 *Example:* `my_vehicle_data`\n"
            "Will become: `my_vehicle_data.csv`\n\n"
            "Use /cancel to cancel",
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif query.data == "csv_cancel":
        user_data = context.user_data
        csv_file_path = user_data.get('csv_file_path')
        txt_file_path = user_data.get('txt_file_path')
        try:
            if csv_file_path and os.path.exists(csv_file_path):
                os.remove(csv_file_path)
            if txt_file_path and os.path.exists(txt_file_path):
                os.remove(txt_file_path)
        except:
            pass
        await query.edit_message_text("❌ *Cancelled*\n\nUse /txt2csv to convert another file", parse_mode=ParseMode.MARKDOWN)
        context.user_data.clear()
    
    elif query.data == "batch_generate" and mode == 'batch':
        first_letters = user_data.get('first_letters')
        second_numbers = user_data.get('second_numbers')
        series_list = user_data.get('series_list', [])
        start_digits = user_data.get('start_digits')
        end_digits = user_data.get('end_digits')
        
        await query.edit_message_text(f"⏳ *Generating batch...*\n\nProcessing {len(series_list)} series...", parse_mode=ParseMode.MARKDOWN)
        
        filename, error = generate_batch_vehicle_numbers(first_letters, second_numbers, series_list, start_digits, end_digits)
        
        if error:
            await query.edit_message_text(f"❌ *Error:*\n\n`{error}`\n\nUse /batch to try again.", parse_mode=ParseMode.MARKDOWN)
            context.user_data.clear()
            return
        
        with open(filename, 'r', encoding='utf-8') as f:
            count = len(f.readlines())
        
        file_size = os.path.getsize(filename)
        file_size_mb = file_size / (1024 * 1024)
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with open(filename, 'rb') as f:
                    series_display = ', '.join(series_list)
                    caption = (
                        f"✅ *Batch Generation Complete!*\n\n"
                        f"📊 *Statistics:*\n"
                        f"• Total numbers: *{count:,}*\n"
                        f"• Series: `{series_display}`\n"
                        f"• Series count: *{len(series_list)}*\n"
                        f"• File size: *{file_size_mb:.2f} MB*\n\n"
                        f"📁 File ready for download!"
                    )
                    await query.message.reply_document(document=f, filename=filename, caption=caption, parse_mode=ParseMode.MARKDOWN)
                break
            except (TimedOut, NetworkError):
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)
                    continue
                else:
                    await query.edit_message_text(f"⚠️ *File too large*\n\nTotal: *{count:,}*\n\nPlease reduce range or series count.", parse_mode=ParseMode.MARKDOWN)
                    try:
                        os.remove(filename)
                    except:
                        pass
                    context.user_data.clear()
                    return
        
        try:
            os.remove(filename)
        except:
            pass
        
        await query.message.reply_text(f"🎉 *Batch Complete!*\n\n✅ {count:,} numbers across {len(series_list)} series!\n\nUse /batch to generate more", parse_mode=ParseMode.MARKDOWN)
        context.user_data.clear()

# ============================================================================
# DOCUMENT HANDLER (for TXT to CSV)
# ============================================================================

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle document uploads for TXT to CSV conversion"""
    if context.user_data.get('mode') != 'txt2csv' or context.user_data.get('step') != 'waiting_file':
        return
    
    if not update.message.document:
        await update.message.reply_text("❌ *No file detected!*\n\nPlease send a .txt file.", parse_mode=ParseMode.MARKDOWN)
        return
    
    document = update.message.document
    file_name = document.file_name or "document.txt"
    
    if not file_name.lower().endswith('.txt'):
        await update.message.reply_text("❌ *Invalid file type!*\n\nPlease send a .txt file.", parse_mode=ParseMode.MARKDOWN)
        return
    
    try:
        await update.message.reply_text("⏳ *Downloading file...*", parse_mode=ParseMode.MARKDOWN)
        
        file = await context.bot.get_file(document.file_id)
        txt_file_path = f"temp_{document.file_id}.txt"
        await file.download_to_drive(txt_file_path)
        
        file_size = os.path.getsize(txt_file_path)
        if file_size > 50 * 1024 * 1024:
            os.remove(txt_file_path)
            await update.message.reply_text("❌ *File too large!*\n\nMaximum: 50 MB", parse_mode=ParseMode.MARKDOWN)
            return
        
        await update.message.reply_text("⏳ *Converting to CSV...*", parse_mode=ParseMode.MARKDOWN)
        
        csv_file_path = f"converted_{document.file_id}.csv"
        success, error = convert_txt_to_csv(txt_file_path, csv_file_path)
        
        if not success:
            os.remove(txt_file_path)
            await update.message.reply_text(f"❌ *Conversion failed!*\n\nError: `{error}`", parse_mode=ParseMode.MARKDOWN)
            return
        
        csv_file_size = os.path.getsize(csv_file_path)
        csv_file_size_mb = csv_file_size / (1024 * 1024)
        
        with open(csv_file_path, 'r', encoding='utf-8') as f:
            line_count = sum(1 for line in f) - 1
        
        # Store file info for rename step
        context.user_data['csv_file_path'] = csv_file_path
        context.user_data['txt_file_path'] = txt_file_path
        context.user_data['default_filename'] = file_name.replace('.txt', '.csv')
        context.user_data['line_count'] = line_count
        context.user_data['file_size_mb'] = csv_file_size_mb
        context.user_data['step'] = 'ask_rename'
        
        # Ask if user wants to rename
        rename_msg = (
            f"✅ *Conversion Complete!*\n\n"
            f"📊 *Statistics:*\n"
            f"• Records: *{line_count:,}*\n"
            f"• Format: `Number,Vehicle Number`\n"
            f"• File size: *{csv_file_size_mb:.2f} MB*\n\n"
            f"📁 Default filename: `{file_name.replace('.txt', '.csv')}`\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Would you like to rename the file?"
        )
        
        keyboard = [
            [InlineKeyboardButton("✅ Use Default Name", callback_data="csv_use_default")],
            [InlineKeyboardButton("✏️ Rename File", callback_data="csv_rename")],
            [InlineKeyboardButton("❌ Cancel", callback_data="csv_cancel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(rename_msg, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error processing file: {e}", exc_info=True)
        await update.message.reply_text(f"❌ *Error processing file!*\n\nError: `{str(e)}`", parse_mode=ParseMode.MARKDOWN)
        try:
            if 'txt_file_path' in locals():
                os.remove(txt_file_path)
            if 'csv_file_path' in locals():
                os.remove(csv_file_path)
        except:
            pass
        context.user_data.clear()

async def send_csv_file(message, context: ContextTypes.DEFAULT_TYPE, csv_file_path: str, filename: str, line_count: int, file_size_mb: float, txt_file_path: str = None) -> None:
    """Send CSV file to user"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with open(csv_file_path, 'rb') as f:
                caption = (
                    f"✅ *Conversion Complete!*\n\n"
                    f"📊 *Statistics:*\n"
                    f"• Records: *{line_count:,}*\n"
                    f"• Format: `Number,Vehicle Number`\n"
                    f"• File size: *{file_size_mb:.2f} MB*\n"
                    f"• Filename: `{filename}`\n\n"
                    f"📁 File ready for download!"
                )
                await message.reply_document(document=f, filename=filename, caption=caption, parse_mode=ParseMode.MARKDOWN)
            break
        except (TimedOut, NetworkError):
            if attempt < max_retries - 1:
                await asyncio.sleep(2)
                continue
            else:
                await message.reply_text(f"⚠️ *File too large*\n\nSize: *{file_size_mb:.2f} MB*\n\nPlease use a smaller file.", parse_mode=ParseMode.MARKDOWN)
                try:
                    if txt_file_path and os.path.exists(txt_file_path):
                        os.remove(txt_file_path)
                    if os.path.exists(csv_file_path):
                        os.remove(csv_file_path)
                except:
                    pass
                context.user_data.clear()
                return
    
    # Clean up files
    try:
        if txt_file_path and os.path.exists(txt_file_path):
            os.remove(txt_file_path)
        if os.path.exists(csv_file_path):
            os.remove(csv_file_path)
    except:
        pass
    
    await message.reply_text(f"🎉 *Conversion Successful!*\n\n✅ Converted {line_count:,} records to CSV\n📋 Format: `Number,Vehicle Number`\n📁 Filename: `{filename}`\n\nUse /txt2csv to convert another file", parse_mode=ParseMode.MARKDOWN)
    context.user_data.clear()

# ============================================================================
# MAIN FUNCTION
# ============================================================================

def main() -> None:
    """Start the bot"""
    # Try to get token from environment variable first (for Railway/cloud deployments)
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    # If not in environment, try the BOT_TOKEN variable in file
    if not token:
        token = BOT_TOKEN
    
    # If still no token, show error
    if not token:
        logger.error("Bot token not found!")
        print("\n❌ Error: Bot token not found!")
        print("\nPlease set the token in one of these ways:")
        print("1. Environment variable (for Railway/cloud):")
        print("   export TELEGRAM_BOT_TOKEN='your_token_here'")
        print("   Or in Railway: Add TELEGRAM_BOT_TOKEN in Variables")
        print("\n2. In the file itself (for local use):")
        print("   Edit bot.py and set BOT_TOKEN = 'your_token_here'")
        print("\n3. Windows PowerShell:")
        print("   $env:TELEGRAM_BOT_TOKEN='your_token_here'")
        return
    
    # Create application
    application = Application.builder().token(token).build()
    
    # Add error handler
    async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        error = context.error
        # Don't log timeouts as errors - they're network issues
        if isinstance(error, (TimedOut, NetworkError)):
            logger.warning(f"Network timeout/error: {error}")
        else:
            logger.error(f"Exception: {error}", exc_info=error)
        
        if isinstance(update, Update) and update.effective_message:
            try:
                # Only send error message for non-timeout errors
                if not isinstance(error, (TimedOut, NetworkError)):
                    await update.effective_message.reply_text("❌ An error occurred. Please try again or use /help")
            except:
                pass
    
    application.add_error_handler(error_handler)
    
    # Add command handlers
    application.add_handler(CommandHandler('start', start_command))
    application.add_handler(CommandHandler('batch', batch_command))
    application.add_handler(CommandHandler('txt2csv', txt2csv_command))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('cancel', cancel_command))
    
    # Add message handler (for state-based processing)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Add document handler (for TXT to CSV)
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    
    # Add callback query handler (for buttons)
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Start the bot
    logger.info("Starting bot...")
    logger.info("Bot is ready! Commands: /start, /batch, /txt2csv, /help")
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )

if __name__ == '__main__':
    main()
