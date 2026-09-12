import os
import requests
import time
import random
import sys
from flask import Flask, redirect
from threading import Thread

# --- SECRETS (Fetched from Render Environment Variables) ---
TOKEN = os.environ.get('DISCORD_TOKEN')
RESEND_API_KEY = os.environ.get('RESEND_API_KEY')
RECEIVER_EMAIL = os.environ.get('RECEIVER_EMAIL')

# --- CONFIGURATION ---
CHANNEL_ID = '832183081825730630'

# Set to True if you want the "owo buy 1" sequence included
ENABLE_BUY_COMMAND = False 

URL = f'https://discord.com/api/v9/channels/{CHANNEL_ID}/messages'

HEADERS = {
    'Authorization': TOKEN,
    'Content-Type': 'application/json'
}

# --- CONTROL STATE & WEB SERVER ---
is_running = True  # Script starts in active state

app = Flask('')

@app.route('/')
def home():
    status_color = "#4CAF50" if is_running else "#f44336"
    status_text = "RUNNING 🟢" if is_running else "PAUSED 🔴"
    return f'''
    <div style="text-align:center; font-family:Arial, sans-serif; margin-top:50px;">
        <h1>OwO Bot Dashboard</h1>
        <h2>Status: <span style="color:{status_color};">{status_text}</span></h2>
        <br>
        <a href="/start"><button style="padding:15px 30px; font-size:18px; background-color:#4CAF50; color:white; border:none; border-radius:5px; cursor:pointer; margin-right:10px;">START BOT</button></a>
        <a href="/stop"><button style="padding:15px 30px; font-size:18px; background-color:#f44336; color:white; border:none; border-radius:5px; cursor:pointer;">STOP BOT</button></a>
    </div>
    '''

@app.route('/start')
def start_bot():
    global is_running
    is_running = True
    return redirect('/')

@app.route('/stop')
def stop_bot():
    global is_running
    is_running = False
    return redirect('/')

def run_server():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_server)
    t.start()

# --- CORE SCRIPT ---
def send_alert_email():
    if not RESEND_API_KEY or not RECEIVER_EMAIL:
        print("\n[-] Resend credentials missing. Skipping email.")
        return

    try:
        headers = {
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "from": "OwO Bot <onboarding@resend.dev>",
            "to": [RECEIVER_EMAIL],
            "subject": "🚨 OwO Captcha Alert!",
            "html": "<p>An OwO captcha was detected on Discord. The farming script has paused to prevent a ban.</p>"
        }
        response = requests.post("https://api.resend.com/emails", headers=headers, json=payload)
        if response.status_code == 200:
            print("\n[+] Captcha alert email sent via Resend API.")
        else:
            print(f"\n[-] Failed to send email: {response.text}")
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
    global is_running
    if check_captcha and check_for_captcha():
        print("\n" + "="*50)
        print("[!!!] CAPTCHA DETECTED! PAUSING SCRIPT [!!!]")
        print("="*50)
        is_running = False  
        send_alert_email()
        return False

    try:
        response = requests.post(URL, headers=HEADERS, json={'content': content})
        if response.status_code == 200:
            print(f"[{time.strftime('%X')}] Sent: {content}")
        elif response.status_code == 429:
            retry_after = response.json().get('retry_after', 5)
            print(f"[{time.strftime('%X')}] Rate limited. Backing off for {retry_after}s...")
            time.sleep(retry_after)
        else:
            print(f"[{time.strftime('%X')}] Failed to send. Status: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    return True

def human_sleep(min_sec, max_sec):
    time.sleep(random.uniform(min_sec, max_sec))

def run_farmer():
    global is_running
    if not TOKEN:
        print("[!] ERROR: DISCORD_TOKEN environment variable is missing.")
        return

    print("\nStarting continuous farming script worker.")
    loops = 0

    while True:
        # If stopped from the web UI, wait without sending API requests
        if not is_running:
            time.sleep(2)
            continue

        if ENABLE_BUY_COMMAND:
            if not send_message("owo buy 1"): continue
            human_sleep(3.2, 4.2) 
            if not send_message("owo"): continue
            human_sleep(3.2, 4.2)
            if not send_message("owo buy 1"): continue
            human_sleep(3.2, 4.2)
            if not send_message("owoh"): continue
        else:
            if not send_message("owo"): continue
            human_sleep(10.5, 12.0) 
            if not send_message("owoh"): continue

        human_sleep(0.5, 0.9)
        if not send_message("owob", check_captcha=False): continue
        
        cooldown_sleep = random.uniform(3.5, 5.0)
        print(f"--> Cycle complete. Resting for {cooldown_sleep:.1f}s...\n")
        time.sleep(cooldown_sleep)

        loops += 1
        
        if loops % random.randint(20, 25) == 0:
            break_time = random.uniform(60, 120)
            print(f"\n[!] Taking a human break for {break_time:.1f} seconds...\n")
            for _ in range(int(break_time)):
                if not is_running:
                    break
                time.sleep(1)

if __name__ == "__main__":
    keep_alive()
    try:
        run_farmer()
    except KeyboardInterrupt:
        print("\nScript manually stopped.")
        
