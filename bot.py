import telebot
import random
import threading
import time
from collections import defaultdict
from flask import Flask
import os

TOKEN = os.environ.get('8558970838:AAESTBxZnt64rUzg4x-WLNjhPWa_mt3BrXo')  
if not TOKEN:
    print("BOT_TOKEN missing!")
    exit(1)
bot = telebot.TeleBot(TOKEN)
print(f"Bot started")

# Storage for waiting users and pairs (user_id -> partner_id)
waiting_users = set()
pairs = {}  # user_id -> partner_id
lock = threading.Lock()

app = Flask(__name__)

@app.route('/')
def home():
    return 'Bot is alive! Anon chat running 24/7.'

def keep_alive():
    app.run(host='0.0.0.0', port=8080)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Welcome to Anonymous Chat!\n\nCommands:\n/find - Find a random partner\n/leave - Disconnect from chat\n\nSend messages to chat once paired!")

@bot.message_handler(commands=['find'])
def find_partner(message):
    user_id = message.from_user.id
    with lock:
        if user_id in pairs:
            bot.reply_to(message, "You're already paired! Send /leave first.")
            return
        if user_id in waiting_users:
            bot.reply_to(message, "Already finding... Wait.")
            return
        
        waiting_users.add(user_id)
        bot.reply_to(message, "Finding partner... Stay here!")
    
    # Poll for pair in background
    def poll_for_pair():
        time.sleep(2)  # Short delay
        with lock:
            waiting_users.discard(user_id)
            if len(waiting_users) >= 1:
                partner = waiting_users.pop()
                if partner != user_id:  # No self-pair
                    pairs[user_id] = partner
                    pairs[partner] = user_id
                    bot.send_message(user_id, "✅ Paired anonymously! Chat now (use /leave to stop).")
                    bot.send_message(partner, "✅ Paired anonymously! Chat now (use /leave to stop).")
                else:
                    waiting_users.add(user_id)
                    bot.send_message(user_id, "No partner yet. Try /find again.")
    
    threading.Thread(target=poll_for_pair).start()

@bot.message_handler(commands=['leave'])
def leave(message):
    user_id = message.from_user.id
    with lock:
        if user_id in pairs:
            partner = pairs.pop(user_id)
            pairs.pop(partner, None)
            bot.send_message(partner, "❌ Partner left the chat.")
            bot.send_message(user_id, "Left chat. Use /find for new partner.")
        else:
            bot.reply_to(message, "Not in a chat.")

@bot.message_handler(func=lambda m: True)
def relay_message(message):
    user_id = message.from_user.id
    with lock:
        if user_id in pairs:
            partner = pairs[user_id]
            bot.send_message(partner, f"Anon: {message.text}")

if __name__ == '__main__':
    threading.Thread(target=keep_alive, daemon=True).start()
    print("Bot starting...")
    bot.infinity_polling()
