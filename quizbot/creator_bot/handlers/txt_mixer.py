import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from ...txt_mixer_engine.sfg import process_sfg
from ...txt_mixer_engine.vajiram import process_vajiram
from ...txt_mixer_engine.vision import process_vision
from ...txt_mixer_engine.txtfixer import fix_questions_file, convert_format

user_state = {}

def get_main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚡ ForumIAS SFG (50 Q)", callback_data="txt_mode_sfg")],
        [InlineKeyboardButton("⚙️ Vajiram & Ravi (100 Q)", callback_data="txt_mode_vajiram")],
        [InlineKeyboardButton("🔮 VisionIAS (100 Q)", callback_data="txt_mode_vision")],
        [InlineKeyboardButton("📝 TXT File Fixer", callback_data="txt_show_txt_info")]
    ])

def get_back_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("↩️ Back to Menu", callback_data="txt_menu")]
    ])

def get_txt_fixer_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛠️ TXT Fixer (Blank lines)", callback_data="txt_fix_mode")],
        [InlineKeyboardButton("🔄 TXT Format (Emoji 😂)", callback_data="txt_format_mode")],
        [InlineKeyboardButton("↩️ Back to Main Menu", callback_data="txt_menu")]
    ])

async def txt_command(client: Client, message: Message):
    if not message.from_user:
        return
        
    chat_id = message.chat.id
    user_state[chat_id] = None
    
    text = (
        "╔══════════════════════════════════╗\n"
        "  🤖 <b>VAJI + SFG + VISION BOT</b>\n"
        "╚══════════════════════════════════╝\n\n"
        "Namaste! 👋 Swagat hai!\n\n"
        "Yeh bot do kaam karta hai:\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📄 <b>MODULE 1 — UPSC PDF → TXT</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "⚡ <b>ForumIAS SFG</b> — 50 Q (Solutions PDF bhejo)\n"
        "⚙️ <b>Vajiram & Ravi</b> — 100 Q (Test + Solutions PDF)\n"
        "🔮 <b>VisionIAS</b> — 100 Q (Test + Solutions PDF)\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📝 <b>MODULE 2 — TXT FILE FIXER</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "<b>Fixer:</b> Blank lines remove karna\n"
        "<b>Format:</b> Simple numbering ko 😂 emojis me badalna\n\n"
        "👇 <b>Neeche mode select karein:</b>"
    )
    
    await message.reply_text(text, reply_markup=get_main_keyboard(), quote=True)

async def txt_callback(client: Client, query: CallbackQuery):
    chat_id = query.message.chat.id
    data = query.data
    
    if data == "txt_menu":
        user_state[chat_id] = None
        await query.message.edit_text(
            "👇 <b>Main Menu. Mode select karein:</b>",
            reply_markup=get_main_keyboard()
        )
        return
        
    if data == "txt_show_txt_info":
        await query.message.edit_text(
            "📝 <b>TXT File Fixer & Formatter</b>\n\n"
            "<b>1. Fixer (Blank lines)</b>\n"
            "Ye mode aapki .txt file se saari faltu khali lines hata dega, aur questions ke beech me sirf ek gap rakhega.\n\n"
            "<b>2. Format (Emoji 😂)</b>\n"
            "Ye mode aapki numbering ko Q1. 😂 😂 options wale format me convert kar dega.\n\n"
            "👇 <b>Kya karna chahte hain?</b>",
            reply_markup=get_txt_fixer_keyboard()
        )
        return
        
    if data == "txt_fix_mode":
        user_state[chat_id] = {'mode': 'txt_fixer'}
        await query.message.edit_text(
            "🛠️ <b>TXT Fixer Mode</b> selected!\n\n"
            "Ab aap apni <b>.txt file</b> bhejein jisme se khali lines hatani hain.",
            reply_markup=get_back_keyboard()
        )
        return
        
    if data == "txt_format_mode":
        user_state[chat_id] = {'mode': 'txt_format'}
        await query.message.edit_text(
            "🔄 <b>TXT Format Mode</b> selected!\n\n"
            "Ab aap apni normal <b>.txt file</b> bhejein jise 😂 format me convert karna hai.",
            reply_markup=get_back_keyboard()
        )
        return
        
    if data == "txt_mode_sfg":
        user_state[chat_id] = {'mode': 'sfg', 'step': 'wait_sol'}
        await query.message.edit_text(
            "⚡ <b>ForumIAS SFG Mode</b> selected!\n\n"
            "📂 Kripya <b>Solutions PDF</b> file bhejein.",
            reply_markup=get_back_keyboard()
        )
        return
        
    if data == "txt_mode_vajiram":
        user_state[chat_id] = {'mode': 'vajiram', 'step': 'wait_test', 'test_buffer': None}
        await query.message.edit_text(
            "⚙️ <b>Vajiram & Ravi Mode</b> selected!\n\n"
            "Step 1: Kripya <b>Test Booklet PDF</b> bhejein.",
            reply_markup=get_back_keyboard()
        )
        return
        
    if data == "txt_mode_vision":
        user_state[chat_id] = {'mode': 'vision', 'step': 'wait_test', 'test_buffer': None}
        await query.message.edit_text(
            "🔮 <b>VisionIAS Mode</b> selected!\n\n"
            "Step 1: Kripya <b>Test Booklet PDF</b> bhejein.",
            reply_markup=get_back_keyboard()
        )
        return
        
async def txt_document_handler(client: Client, message: Message):
    chat_id = message.chat.id
    state = user_state.get(chat_id)
    
    if not state or not state.get('mode'):
        return
        
    mode = state['mode']
    doc = message.document
    if not doc:
        return
        
    if mode in ['txt_fixer', 'txt_format']:
        if not doc.file_name.endswith('.txt'):
            await message.reply_text("❌ Sirf .txt files bhejein!", reply_markup=get_back_keyboard())
            return
            
        status_msg = await message.reply_text("⏳ Processing file...")
        file_path = await message.download()
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        os.remove(file_path)
        
        if mode == 'txt_fixer':
            res = fix_questions_file(content)
            output = res['fixedContent']
            caption = (
                "✅ <b>TXT Fixed!</b>\n\n"
                f"Lines Removed: <b>{res['removedCount']}</b>\n"
                f"Final Lines: <b>{res['finalLines']}</b>"
            )
        else:
            output = convert_format(content)
            caption = "✅ <b>Format Converted!</b>"
            
        out_path = f"formatted_{doc.file_name}"
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(output)
            
        await message.reply_document(out_path, caption=caption, parse_mode=None)
        os.remove(out_path)
        await status_msg.delete()
        user_state[chat_id] = None
        return
        
    # PDF Modes
    if not doc.file_name.endswith('.pdf'):
        await message.reply_text("❌ Sirf PDF files bhejein!", reply_markup=get_back_keyboard())
        return
        
    step = state['step']
    status_msg = await message.reply_text("⬇️ Downloading PDF...")
    file_path = await message.download()
    
    with open(file_path, 'rb') as f:
        pdf_bytes = f.read()
    os.remove(file_path)
    
    if mode == 'sfg' and step == 'wait_sol':
        await status_msg.edit_text("⏳ Processing SFG PDF...")
        
        def on_progress(p, msg=""):
            pass # we can skip live updates to avoid hitting rate limits
            
        res = process_sfg(pdf_bytes, on_progress)
        
        if not res['success']:
            await status_msg.edit_text(f"❌ Error:\n{res['error']}", reply_markup=get_back_keyboard())
            return
            
        caption = (
            "⚡ <b>SFG Parsed Successfully!</b>\n\n"
            f"Questions extracted: <b>{res['questionCount']}</b>\n"
            f"Matches (✅): <b>{res['stats']['matched']}</b>\n"
            f"No answers found: <b>{res['stats']['noAns']}</b>\n"
            f"Explanations found: <b>{res['stats']['explanationsFound']}</b>"
        )
        out_path = "SFG_Converted.txt"
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(res['output'])
            
        await message.reply_document(out_path, caption=caption)
        os.remove(out_path)
        await status_msg.delete()
        user_state[chat_id] = None
        
    elif mode in ['vajiram', 'vision']:
        if step == 'wait_test':
            state['test_buffer'] = pdf_bytes
            state['step'] = 'wait_sol'
            await status_msg.edit_text("✅ Test Booklet Received!\n\nStep 2: Ab <b>Solutions Booklet PDF</b> bhejein.")
        elif step == 'wait_sol':
            await status_msg.edit_text(f"⏳ Processing {mode.title()} PDFs...")
            test_buf = state['test_buffer']
            sol_buf = pdf_bytes
            
            def on_progress(p, msg=""):
                pass
                
            if mode == 'vajiram':
                res = process_vajiram(test_buf, sol_buf, on_progress)
            else:
                res = process_vision(test_buf, sol_buf, on_progress)
                
            if not res['success']:
                await status_msg.edit_text(f"❌ Error:\n{res.get('error', 'Unknown error')}", reply_markup=get_back_keyboard())
                return
                
            caption = (
                f"✅ <b>{mode.title()} Parsed Successfully!</b>\n\n"
                f"Questions extracted: <b>{res['questionCount']}</b>\n"
                f"Matches (✅): <b>{res['stats']['matched']}</b>\n"
                f"No answers found: <b>{res['stats']['noAns']}</b>\n"
                f"Explanations found: <b>{res['stats']['explanationsFound']}</b>"
            )
            out_path = f"{mode.title()}_Converted.txt"
            with open(out_path, 'w', encoding='utf-8') as f:
                f.write(res['output'])
                
            await message.reply_document(out_path, caption=caption)
            os.remove(out_path)
            await status_msg.delete()
            user_state[chat_id] = None

def register(app: Client) -> None:
    app.on_message(filters.command("txt") & filters.private)(txt_command)
    app.on_callback_query(filters.regex(r"^txt_"))(txt_callback)
    app.on_message(filters.document & filters.private, group=1)(txt_document_handler)
