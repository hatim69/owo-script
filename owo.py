import os
import requests
import time
import random
import sys
import smtplib
from email.message import EmailMessage
from flask import Flask
from threading import Thread

# --- SECRETS (Fetched from Render Environment Variables) ---
TOKEN = os.environ.get('DISCORD_TOKEN')
EMAIL_APP_PASSWORD = os.environ.get('EMAIL_PASSWORD')

# --- CONFIGURATION ---
CHANNEL_ID = '832183081825730630'
SENDER_EMAIL = 'hatim4211786@gmail.com'
RECEIVER_EMAIL = 'hatimmithaiwala786@gmail.com'

# Set to True if you want the "owo buy 1" sequence included
ENABLE_BUY_COMMAND = False 

URL = f'https://discord.com/api/v9/channels/{CHANNEL_ID}/messages'

HEADERS = {
    'Authorization': TOKEN,
    'Content-Type': 'application/json'
}

# --- KEEP ALIVE WEB SERVER ---
app = Flask('')

@app.route('/')
def home():
    return "Farming bot is running!"

def run_server():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_server)
    t.start()

# --- CORE SCRIPT ---
def send_alert_email():
    if not SENDER_EMAIL or not EMAIL_APP_PASSWORD or not RECEIVER_EMAIL:
        print("\n[-] Email credentials missing. Skipping email alert.")
        return

    try:
        msg = EmailMessage()
        msg.set_content(f"An OwO captcha was detected on Discord. The farming script has immediately stopped to prevent a ban.")
        msg['Subject'] = '🚨 OwO Captcha Alert!'
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECEIVER_EMAIL

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, EMAIL_APP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("\n[+] Alert email sent successfully.")
    except Exception as e:
        print(f"\n[-] Failed to send email: {e}")

def check_for_captcha():
    try:
        response = requests.get(f"{URL}?limit=10", headers=HEADERS)
        if response.status_code == 200:
            for msg in response.json():
                raw_content = msg.get('content', '').lower()
                clean_content = raw_content.encode('ascii', 'ignore').decode('ascii')
                
                if "real human" in clean_content or "result in a ban" in clean_content:
                    return True
    except Exception:
        pass 
    return False

def send_message(content, check_captcha=True):
    if check_captcha and check_for_captcha():
        print("\n" + "="*50)
        print("[!!!] CAPTCHA DETECTED! STOPPING SCRIPT [!!!]")
        print("="*50)
        send_alert_email()
        os._exit(0) # Forces the entire app, including the web server, to stop

    try:
        response = requests.post(URL, headers=HEADERS, json={'content': content})
        if response.status_code == 200:
            print(f"[{time.strftime('%X')}] Sent: {content}")
        elif response.status_code == 429:
            retry_after = response.json().get('retry_after', 5)
            print(f"[{time.strftime('%X')}] Rate limited. Backing off for {retry_after}s...")
            time.sleep(retry_after)
    except Exception as e:
        print(f"Error: {e}")

def human_sleep(min_sec, max_sec):
    time.sleep(random.uniform(min_sec, max_sec))

def run_farmer():
    if not TOKEN:
        print("[!] ERROR: DISCORD_TOKEN environment variable is missing.")
        return

    print("\nStarting continuous farming script.")
    loops = 0

    while True:
        if ENABLE_BUY_COMMAND:
            send_message("owo buy 1")
            human_sleep(3.2, 4.2) 
            send_message("owo")
            human_sleep(3.2, 4.2)
            send_message("owo buy 1")
            human_sleep(3.2, 4.2)
            send_message("owoh")
        else:
            send_message("owo")
            human_sleep(10.5, 12.0) 
            send_message("owoh")

        human_sleep(0.5, 0.9)
        send_message("owob", check_captcha=False)
        
        cooldown_sleep = random.uniform(3.5, 5.0)
        print(f"--> Cycle complete. Resting for {cooldown_sleep:.1f}s...\n")
        time.sleep(cooldown_sleep)

        loops += 1
        
        if loops % random.randint(20, 25) == 0:
            break_time = random.uniform(60, 120)
            print(f"\n[!] Taking a human break for {break_time:.1f} seconds...\n")
            time.sleep(break_time)

if __name__ == "__main__":
    keep_alive() # Starts the web server in the background
    try:
        run_farmer()
    except KeyboardInterrupt:
        print("\nScript manually stopped.")
        os._exit(0)
