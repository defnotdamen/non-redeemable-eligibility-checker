import requests
from datetime import datetime, timedelta
import pytz
import os
from termcolor import colored
from concurrent.futures import ThreadPoolExecutor
import logging
import time
import sys
import colorama

colorama.init(autoreset=True)


def format_date(date):
    day = date.day
    if 10 <= day <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
    return date.strftime(f"{day}{suffix} %B %Y")


def check_latest_payment(token, proxy=None, retry_count=3):
    if not token or len(token) < 30:
        return None
    
    token = token.strip()
    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
        "User-Agent": "Discord/150000 CFNetwork/1333.0.4 Darwin/21.5.0"
    }

    url = "https://discord.com/api/v9/users/@me/billing/payments?limit=30"
    
    if proxy:
        if not proxy.startswith('http://') and not proxy.startswith('https://'):
            proxy = f"http://{proxy}"
        proxies = {"http": proxy, "https": proxy}
    else:
        proxies = {}

    for attempt in range(retry_count):
        try:
            response = requests.get(url, headers=headers, proxies=proxies, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            if not data:
                print(colored(f"[{token[:15]}...] No payment records found.", 'yellow'))
                return None

            latest_payment = max(data, key=lambda p: p.get("created_at", 0))
            created_at_str = latest_payment.get("created_at")
            
            if not created_at_str:
                return None
                
            try:
                created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
            except ValueError:
                created_at = datetime.utcfromtimestamp(int(created_at_str)).replace(tzinfo=pytz.UTC)
            
            current_time = datetime.now(pytz.utc)
            days_since_payment = (current_time - created_at).days

            nitro_url = "https://discord.com/api/v9/users/@me/billing/subscriptions"
            try:
                nitro_response = requests.get(nitro_url, headers=headers, proxies=proxies, timeout=15)
                nitro_response.raise_for_status()
                nitro_data = nitro_response.json()
                
                nitro_active = any(subscription.get("type") == 1 for subscription in nitro_data)
            except Exception:
                nitro_active = False

            if nitro_active or days_since_payment < 30:
                print(colored(f"Ineligible - {token[:15]}...", 'red'))
                return "Ineligible"

            card_url = "https://discord.com/api/v9/users/@me/billing/payment-sources"
            try:
                card_response = requests.get(card_url, headers=headers, proxies=proxies, timeout=15)
                card_response.raise_for_status()
                card_data = card_response.json()
                
                if card_data:
                    for card in card_data:
                        card_status = card.get('valid', False)
                        card_used = card.get('used', False)
                        
                        if days_since_payment >= 30 and not card_status:
                            print(colored(f"Eligible - {token[:15]}...", 'green'))
                            return "Eligible"
            except Exception:
                pass

            print(colored(f"[{token[:15]}...] Failed to meet criteria.", 'yellow'))
            return None
            
        except requests.exceptions.RequestException as e:
            if attempt < retry_count - 1:
                time.sleep(2 * (attempt + 1))
                continue
            print(colored(f"[{token[:15]}...] Error: {str(e)}", 'red', attrs=['bold']))
            return None
            
        except Exception as e:
            print(f"[{token[:15]}...] Error: {str(e)}")
            return None


def check_payments_in_parallel(tokens_file, output_file, proxy=None, max_workers=5):
    eligible_tokens = []
    ineligible_tokens = []
    
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    from threading import Lock
    file_lock = Lock()

    try:
        with open(tokens_file, 'r') as f:
            tokens = [line.strip() for line in f.readlines() if line.strip()]
    except FileNotFoundError:
        print(colored(f"Error: File '{tokens_file}' not found.", 'red', attrs=['bold']))
        return
    except Exception as e:
        print(colored(f"Error reading tokens file: {str(e)}", 'red', attrs=['bold']))
        return

    if not tokens:
        print(colored("No tokens found in the input file.", 'yellow', attrs=['bold']))
        return
        
    def process_token(token):
        result = check_latest_payment(token, proxy)
        
        if result:
            with file_lock:
                with open(output_file, 'a') as output:
                    if result == "Eligible":
                        output.write(f"Eligible - {token}\n")
                        eligible_tokens.append(token)
                    elif result == "Ineligible":
                        output.write(f"Ineligible - {token}\n")
                        ineligible_tokens.append(token)
        
        return token, result

    try:
        total_tokens = len(tokens)
        print(colored(f"Processing {total_tokens} tokens...", 'cyan'))
        
        with ThreadPoolExecutor(max_workers=max(1, max_workers)) as executor:
            for i, (token, result) in enumerate(executor.map(process_token, tokens), 1):
                if i % 5 == 0 or i == total_tokens:
                    progress_percent = (i / total_tokens) * 100
                    print(colored(f"Progress: {i}/{total_tokens} ({progress_percent:.1f}%)", 'cyan'))

            eligible_count = len(eligible_tokens)
            ineligible_count = len(ineligible_tokens)
            unknown_count = len(tokens) - eligible_count - ineligible_count
            
            print("\n" + "="*50)
            print(colored("SUMMARY", 'cyan', attrs=['bold']))
            print(colored(f"✅ Eligible: {eligible_count}", 'green', attrs=['bold']))
            print(colored(f"❌ Ineligible: {ineligible_count}", 'red'))
            print(colored(f"❓ Unknown/Error: {unknown_count}", 'yellow'))
            print("="*50)
            
    except Exception as e:
        print(colored(f"Error processing tokens: {str(e)}", 'red', attrs=['bold']))


if __name__ == "__main__":
    try:
        print(colored("="*50, 'blue'))
        print(colored("DISCORD PAYMENT ELIGIBILITY CHECKER", 'cyan', attrs=['bold']))
        print(colored("="*50, 'blue'))
        
        proxy = "http://fqevse3wb6d829o-country-any:4eN23H7pgWdJ1Cq@resi.rainproxy.io:9090"
        tokens_file = 'tokens.txt'
        output_file = 'output.txt'
        max_workers = 10
        
        print(colored(f"Input file: {tokens_file}", 'cyan'))
        print(colored(f"Output file: {output_file}", 'cyan'))
        print(colored(f"Workers: {max_workers}", 'cyan'))
        print(colored(f"Using proxy: {'Yes' if proxy else 'No'}", 'cyan'))
        print(colored("="*50, 'blue'))
        
        check_payments_in_parallel(tokens_file, output_file, proxy, max_workers)
    except KeyboardInterrupt:
        print(colored("\nProcess interrupted by user. Exiting...", 'cyan'))
        sys.exit(0)
    except Exception as e:
        print(colored(f"Unexpected error: {str(e)}", 'red', attrs=['bold']))