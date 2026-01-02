import logging
import asyncio
from typing import Dict, List
from datetime import datetime, timedelta
import json
import random
import string

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

# Configuration
TOKEN = "8255147067:AAFIrTTInA7lmbRzLaGIyXCQZFiFZVkjycE"
ADMIN_IDS = [7808946119]  # Add admin user IDs
BINANCE_ID = "982640438"  # Payment Binance ID
SUPPORT_BOT = "@lbn_support_bot"

# Database simulation (use SQLite/Redis in production)
user_db: Dict[int, Dict] = {}  # {user_id: {credits: int, plan_expiry: datetime, lang: str}}
payment_logs: List[Dict] = []  # Payment tracking

# Credit plans
CREDIT_PLANS = {
    "test": {"name": "Test Plan", "price": 10, "credits": 250, "days": 10, "usdt": 10},
    "minor": {"name": "Minor Plan", "price": 20, "credits": 500, "days": 10, "usdt": 20},
    "basic": {"name": "Basic Plan", "price": 40, "credits": 1000, "days": 10, "usdt": 40},
    "pro": {"name": "Pro Plan", "price": 180, "credits": 5000, "days": 20, "usdt": 180},
    "premium": {"name": "Premium Plan", "price": 250, "credits": "unlimited", "days": 30, "usdt": 250},
    "daily": {"name": "Daily Plan", "price": 50, "credits": "unlimited", "days": 1, "usdt": 50}
}

# Kill command responses
KILL_RESPONSES = [
    "✅ Card killed successfully. CC: xxxx-xxxx-xxxx-{} | CVV: {} | Bank: {}",
    "🟢 Kill successful. Card: {} | Country: {}",
    "🔴 Card declined. Trying alternative methods...",
    "⚡ Live card captured: {} | Balance: ${}",
    "❌ Invalid card. Attempting BIN attack..."
]

# Card generators
def generate_card(bin=None):
    if not bin:
        bin = random.choice(['4', '5']) + ''.join(random.choices('0123456789', k=5))
    rest = ''.join(random.choices('0123456789', k=10))
    return f"{bin}{rest}"

def generate_expiry():
    month = random.randint(1, 12)
    year = random.randint(2024, 2028)
    return f"{month:02d}/{year}"

def generate_cvv():
    return ''.join(random.choices('0123456789', k=3))

# User management
def get_user(user_id):
    if user_id not in user_db:
        user_db[user_id] = {
            "credits": 0,
            "plan_expiry": None,
            "lang": "en",
            "kills_today": 0,
            "total_kills": 0,
            "pending_payment": None
        }
    return user_db[user_id]

def check_credits(user_id, amount=1):
    user = get_user(user_id)
    if user["plan_expiry"] and user["plan_expiry"] > datetime.now():
        return True
    return user["credits"] >= amount

def deduct_credits(user_id, amount=1):
    user = get_user(user_id)
    if user["plan_expiry"] and user["plan_expiry"] > datetime.now():
        return True
    if user["credits"] >= amount:
        user["credits"] -= amount
        return True
    return False

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    welcome_text = """
🚀 *LBN KILLER BOT*
World's fastest card testing bot

*Commands:*
/kill - Kill single card
/kd - Kill card with details
/km - Kill multiple MasterCards
/ko - Kill with options
/buy - Purchase credits
/info - Your profile
/status - Bot status
/setlang - Change language
/cmds - All commands

Support: @lbn_support_bot
    """
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def kill_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not check_credits(user_id):
        await update.message.reply_text("❌ Insufficient credits. Use /buy to purchase.")
        return
    
    deduct_credits(user_id)
    user = get_user(user_id)
    user["kills_today"] += 1
    user["total_kills"] += 1
    
    # Generate fake card data
    card = generate_card()
    cvv = generate_cvv()
    expiry = generate_expiry()
    bank = random.choice(['Chase', 'Bank of America', 'Wells Fargo', 'Citi', 'HSBC'])
    country = random.choice(['US', 'UK', 'CA', 'AU', 'DE'])
    balance = random.randint(100, 5000)
    
    response = random.choice(KILL_RESPONSES)
    if "{}" in response:
        response = response.format(card, cvv, bank)
    
    # Simulate processing delay
    await update.message.reply_chat_action("typing")
    await asyncio.sleep(2)
    
    # Send result
    result_text = f"""
{response}

*Card Details:*
├ Number: `{card}`
├ Expiry: {expiry}
├ CVV: {cvv}
├ Bank: {bank}
└ Country: {country}

*Balance:* ${balance}
*Status:* ✅ APPROVED
    """
    await update.message.reply_text(result_text, parse_mode='Markdown')

async def buy_credits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []
    for plan_id, plan in CREDIT_PLANS.items():
        text = f"{plan['name']} - ${plan['price']}"
        if plan['credits'] != 'unlimited':
            text += f" ({plan['credits']} credits)"
        keyboard.append([InlineKeyboardButton(text, callback_data=f"buy_{plan_id}")])
    
    keyboard.append([InlineKeyboardButton("Custom Plan (Contact Support)", url=f"t.me/{SUPPORT_BOT[1:]}")])
    
    text = f"""
*Credit Purchase Plans:*
    
• Daily Plan » 50 USDT
  Unlimited credits for 1 day

• Test Plan » 10 USDT
  250 credits for 10 days

• Minor Plan » 20 USDT
  500 credits for 10 days

• Basic Plan » 40 USDT
  1,000 credits for 10 days

• Pro Plan » 180 USDT
  5,000 credits for 20 days

• Premium Plan » 250 USDT
  Unlimited credits for 30 days

*Payment Method:*
Send exact USDT amount to Binance ID: `{BINANCE_ID}`

*After Payment:*
1. Send transaction proof to @lbn_support_bot
2. Include your user ID: `{update.effective_user.id}`
3. Wait for credits activation (5-10 minutes)

*Note:* All plans are non-refundable.
Minimum credits purchase: 400 credits
    """
    await update.message.reply_text(text, parse_mode='Markdown', 
                                   reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("buy_"):
        user_id = query.from_user.id
        plan_id = query.data.split("_")[1]
        plan = CREDIT_PLANS[plan_id]
        
        # Store pending payment
        user = get_user(user_id)
        user["pending_payment"] = {
            "plan": plan_id,
            "amount": plan["usdt"],
            "timestamp": datetime.now().isoformat()
        }
        
        # Payment instructions
        text = f"""
✅ *Selected Plan: {plan['name']}*

*Plan Details:*
├ Price: ${plan['price']} ({plan['usdt']} USDT)
├ Credits: {plan['credits'] if plan['credits'] != 'unlimited' else 'Unlimited'}
└ Validity: {plan['days']} days

*Payment Instructions:*
1. Open Binance App
2. Go to P2P or "Send Crypto"
3. Send *EXACTLY {plan['usdt']} USDT*
4. Recipient Binance ID: `{BINANCE_ID}`

*Important Notes:*
• Send only USDT (TRC20 or BEP20)
• Do not include any notes/messages
• Transaction fee must be paid by you
• Keep transaction screenshot

*After Payment:*
1. Send transaction proof to @lbn_support_bot
2. Include your user ID: `{user_id}`
3. Credits activated within 5-10 minutes

*Need help?* Contact @lbn_support_bot
        """
        
        # Create confirmation keyboard
        keyboard = [
            [
                InlineKeyboardButton("✅ I Have Paid", callback_data=f"paid_{plan_id}"),
                InlineKeyboardButton("🔄 Change Plan", callback_data="change_plan")
            ],
            [
                InlineKeyboardButton("📞 Contact Support", url=f"t.me/lbn_support__bot")
            ]
        ]
        
        await query.edit_message_text(text, parse_mode='Markdown', 
                                      reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif query.data.startswith("paid_"):
        plan_id = query.data.split("_")[1]
        plan = CREDIT_PLANS[plan_id]
        
        text = f"""
✅ *Payment Acknowledged*

Your payment for *{plan['name']}* has been noted.

*Next Steps:*
1. Send transaction proof to @lbn_support_bot
2. Include transaction ID and amount
3. Wait for manual verification

*Verification usually takes:*
• 5-10 minutes during business hours
• Up to 1 hour during peak times

You will receive a confirmation message once your credits are activated.
        """
        
        await query.edit_message_text(text, parse_mode='Markdown')
    
    elif query.data == "change_plan":
        # Return to plan selection
        await buy_credits(update, context)

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    text = f"""
*User Profile:*
├ ID: `{user_id}`
├ Credits: {user['credits']}
├ Plan: {user['plan_expiry'] if user['plan_expiry'] else 'None'}
├ Kills today: {user['kills_today']}
└ Total kills: {user['total_kills']}

*Binance Payment ID:* `{BINANCE_ID}`
    """
    await update.message.reply_text(text, parse_mode='Markdown')

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_text = f"""
🟢 *BOT STATUS: OPERATIONAL*
    
• Uptime: 99.87%
• Response time: 0.2s
• Total users: 1000+
• Successful kills: 50000+
• Last update: Today 10:00 PM

*Payment Method:* Binance ID: `{BINANCE_ID}`
*Support:* @lbn_support_bot
    """
    await update.message.reply_text(status_text, parse_mode='Markdown')

async def cmds(update: Update, context: ContextTypes.DEFAULT_TYPE):
    commands_text = f"""
*Available Commands:*
    
/start - Start bot
/kill - Kill single card
/kd - Kill with details
/km - Kill MasterCards
/ko - Kill with options
/buy - Buy credits (Binance ID: {BINANCE_ID})
/info - Profile info
/status - Bot status
/setlang - Set language
/cmds - This menu

*Payment:* All plans paid via Binance ID: `{BINANCE_ID}`
    """
    await update.message.reply_text(commands_text, parse_mode='Markdown')

async def setlang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("English", callback_data="lang_en")],
        [InlineKeyboardButton("Spanish", callback_data="lang_es")],
        [InlineKeyboardButton("Russian", callback_data="lang_ru")]
    ]
    await update.message.reply_text("Select language:", 
                                   reply_markup=InlineKeyboardMarkup(keyboard))

# Admin command to simulate payment confirmation
async def confirm_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /confirm <user_id> <plan_id>")
        return
    
    user_id = int(context.args[0])
    plan_id = context.args[1]
    
    if plan_id not in CREDIT_PLANS:
        await update.message.reply_text(f"Invalid plan ID. Available: {', '.join(CREDIT_PLANS.keys())}")
        return
    
    plan = CREDIT_PLANS[plan_id]
    user = get_user(user_id)
    
    if plan['credits'] == 'unlimited':
        expiry_days = plan['days']
        user['plan_expiry'] = datetime.now() + timedelta(days=expiry_days)
        user['credits'] = 0
        status_msg = f"Unlimited plan for {expiry_days} days"
    else:
        user['credits'] += plan['credits']
        user['plan_expiry'] = datetime.now() + timedelta(days=plan['days'])
        status_msg = f"{plan['credits']} credits added"
    
    user['pending_payment'] = None
    
    # Log payment
    payment_logs.append({
        "user_id": user_id,
        "plan": plan_id,
        "amount": plan['usdt'],
        "timestamp": datetime.now().isoformat(),
        "admin": update.effective_user.id
    })
    
    await update.message.reply_text(f"✅ Payment confirmed for user {user_id}\nPlan: {plan['name']}\n{status_msg}")
    
    # Notify user if possible (would require message sending implementation)
    # await context.bot.send_message(chat_id=user_id, text=f"✅ Your {plan['name']} has been activated!")

# Main function
def main():
    # Bot setup
    application = Application.builder().token(TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("kill", kill_card))
    application.add_handler(CommandHandler("kd", kill_card))
    application.add_handler(CommandHandler("km", kill_card))
    application.add_handler(CommandHandler("ko", kill_card))
    application.add_handler(CommandHandler("buy", buy_credits))
    application.add_handler(CommandHandler("info", info))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("cmds", cmds))
    application.add_handler(CommandHandler("setlang", setlang))
    application.add_handler(CommandHandler("confirm", confirm_payment))  # Admin command
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Start bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()