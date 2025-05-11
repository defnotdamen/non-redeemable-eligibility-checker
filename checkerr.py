import requests
from datetime import datetime, timedelta
import pytz
import os
from termcolor import colored
from concurrent.futures import ThreadPoolExecutor


def format_date(date):
    day = date.day
    if 10 <= day <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
    return date.strftime(f"{day}{suffix} %B %Y")


def check_latest_payment(token, proxy=None):
    headers = {
        "Authorization": token.strip(),
        "Content-Type": "application/json",
        "User-Agent": "Discord/150000 CFNetwork/1333.0.4 Darwin/21.5.0"
    }

    url = "https://discord.com/api/v9/users/@me/billing/payments?limit=30"
    proxies = {"http": proxy, "https": proxy} if proxy else {}

    try:
        
        response = requests.get(url, headers=headers, proxies=proxies)
        if response.status_code == 200:
            data = response.json()
            if not data:
                print(f"[{token[:30]}...] ❌ No payment records found.")
                return

           
            latest_payment = max(data, key=lambda p: p["created_at"])
            created_at = latest_payment["created_at"]
            created_at = datetime.fromisoformat(created_at) if isinstance(created_at, str) else created_at

            
            if created_at.tzinfo is None:
                created_at = pytz.utc.localize(created_at)

           
            current_time = datetime.now(pytz.utc)

           
            days_since_payment = (current_time - created_at).days

           
            nitro_url = "https://discord.com/api/v9/users/@me/billing/subscriptions"
            nitro_response = requests.get(nitro_url, headers=headers, proxies=proxies)
            nitro_active = False
            if nitro_response.status_code == 200:
                nitro_data = nitro_response.json()
                
                for subscription in nitro_data:
                    if subscription["type"] == 1:  
                        nitro_active = True
                        break

            
            if nitro_active or days_since_payment < 30:
                print(colored(f"Ineligible - {token[:30]}...", 'red'))
                return "Ineligible"

            
            card_url = "https://discord.com/api/v9/users/@me/billing/payment-sources"
            card_response = requests.get(card_url, headers=headers, proxies=proxies)
            if card_response.status_code == 200:
                card_data = card_response.json()
                if card_data:
                    for card in card_data:
                        card_status = card.get('valid', False)
                        card_used = card.get('used', False)
                        
                        if days_since_payment >= 30 and not card_status:
                            print(colored(f"Eligible - {token[:30]}...", 'green'))
                            return "Eligible"

        print(f"[{token[:30]}...] ❌ Failed to fetch data or card details.")
        return None
    except Exception as e:
        print(f"[{token[:30]}...] ❌ An error occurred: {str(e)}")
        return None

from concurrent.futures import ThreadPoolExecutor


def check_payments_in_parallel(tokens_file, output_file, proxy=None, max_workers=5):
    eligible_tokens = []
    ineligible_tokens = []

    with open(tokens_file, 'r') as f:
        tokens = [line.strip() for line in f.readlines()]

   
    with open(output_file, 'a') as output:
       
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = executor.map(lambda token: check_latest_payment(token, proxy), tokens)


            
            for result, token in zip(results, tokens):
                if result == "Eligible":
                    eligible_tokens.append(token)
                    output.write(f"Eligible - {token[:30]}...\n")
                    print(f"Eligible - {token[:30]}...")  
                elif result == "Ineligible":
                    ineligible_tokens.append(token)
                    output.write(f"Ineligible - {token[:30]}...\n")
                    print(f"Ineligible - {token[:30]}...") 


proxy = ""
check_payments_in_parallel('tokens.txt', 'output.txt', proxy, max_workers=10)
