import requests
from datetime import datetime
import pytz
import os
import random
from termcolor import colored
from concurrent.futures import ThreadPoolExecutor

def load_list(filename):
    with open(filename, 'r') as f:
        return [line.strip() for line in f if line.strip()]

def format_date(date):
    day = date.day
    suffix = 'th' if 10 <= day <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
    return date.strftime(f"{day}{suffix} %B %Y")

def check_latest_payment(token, proxy=None):
    headers = {
        "Authorization": token.strip(),
        "Content-Type": "application/json",
        "User-Agent": "Discord/150000 CFNetwork/1333.0.4 Darwin/21.5.0"
    }

    proxies = {"http": proxy, "https": proxy} if proxy else {}

    try:
        url = "https://discord.com/api/v9/users/@me/billing/payments?limit=30"
        response = requests.get(url, headers=headers, proxies=proxies, timeout=10)
        if response.status_code != 200:
            print(f"[{token[:30]}...] ❌ Failed to get payment records.")
            return None

        data = response.json()
        if not data:
            print(f"[{token[:30]}...] ❌ No payment history.")
            return None

        latest_payment = max(data, key=lambda p: p["created_at"])
        created_at = latest_payment["created_at"]
        created_at = datetime.fromisoformat(created_at) if isinstance(created_at, str) else created_at
        if created_at.tzinfo is None:
            created_at = pytz.utc.localize(created_at)

        current_time = datetime.now(pytz.utc)
        days_since_payment = (current_time - created_at).days

        nitro_url = "https://discord.com/api/v9/users/@me/billing/subscriptions"
        nitro_response = requests.get(nitro_url, headers=headers, proxies=proxies, timeout=10)
        nitro_active = False
        if nitro_response.status_code == 200:
            for sub in nitro_response.json():
                if sub.get("type") in (1, 2):
                    nitro_active = True
                    break

        if nitro_active or days_since_payment < 30:
            return "Ineligible"

        card_url = "https://discord.com/api/v9/users/@me/billing/payment-sources"
        card_response = requests.get(card_url, headers=headers, proxies=proxies, timeout=10)
        if card_response.status_code == 200:
            for card in card_response.json():
                if not card.get('valid', False):
                    return "Eligible"

        print(f"[{token[:30]}...] ❌ No usable card found.")
        return None

    except Exception as e:
        print(f"[{token[:30]}...] ❌ Error: {e}")
        return None

def check_payments_in_parallel(tokens_file, proxies_file, output_dir=".", max_workers=10):
    tokens = load_list(tokens_file)
    proxies = load_list(proxies_file)

    eligible_path = os.path.join(output_dir, "eligible.txt")
    ineligible_path = os.path.join(output_dir, "ineligible.txt")
    log_path = os.path.join(output_dir, "output.txt")

    with open(eligible_path, 'w') as eligible_file, \
         open(ineligible_path, 'w') as ineligible_file, \
         open(log_path, 'w') as log_file:

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = executor.map(
                lambda token: (check_latest_payment(token, random.choice(proxies)), token),
                tokens
            )

            for result, token in results:
                line = f"{result} - {token[:30]}...\n"
                if result == "Eligible":
                    eligible_file.write(token + '\n')
                    log_file.write(line)
                    print(colored(f"Eligible - {token[:30]}...", 'green'))
                elif result == "Ineligible":
                    ineligible_file.write(token + '\n')
                    log_file.write(line)
                    print(colored(f"Ineligible - {token[:30]}...", 'red'))

if __name__ == "__main__":
    check_payments_in_parallel('tokens.txt', 'proxies.txt', '.', max_workers=10)
