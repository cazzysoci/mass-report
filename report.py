import os
import sys
import json
import csv
import argparse
from modules.reporter import FacebookReporterAdvanced
from dotenv import load_dotenv

load_dotenv()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-e", "--email", help="Facebook email")
    parser.add_argument("-p", "--password", help="Facebook password")
    parser.add_argument("-f", "--file", required=True, help="Profiles file (csv/json/txt)")
    parser.add_argument("-c", "--config", default="config.json", help="Config file path")
    parser.add_argument("--delay", type=int, default=90, help="Delay between reports (seconds)")
    parser.add_argument("--captcha", help="2Captcha API key")
    parser.add_argument("--env", action="store_true", help="Load credentials from .env")
    args = parser.parse_args()
    
    email = args.email
    password = args.password
    
    if args.env:
        email = os.getenv("FACEBOOK_EMAIL", email)
        password = os.getenv("FACEBOOK_PASSWORD", password)
        
    if not email or not password:
        print("[-] Email and password required. Use -e, -p or --env")
        sys.exit(1)
        
    profiles = []
    try:
        with open(args.file, 'r', encoding='utf-8') as f:
            ext = args.file.split('.')[-1].lower()
            if ext == "csv":
                reader = csv.DictReader(f)
                for row in reader:
                    profiles.append({
                        'url': row['url'].strip(),
                        'reason': row.get('reason', 'harassment').strip()
                    })
            elif ext == "json":
                profiles = json.load(f)
            else:
                for line in f:
                    url = line.strip()
                    if url and not url.startswith('#'):
                        profiles.append({'url': url, 'reason': 'harassment'})
    except Exception as e:
        print(f"[-] Error loading profiles: {e}")
        sys.exit(1)
        
    if not profiles:
        print("[-] No profiles loaded")
        sys.exit(1)
        
    print(f"[*] Loaded {len(profiles)} profiles")
    
    reporter = FacebookReporterAdvanced(
        email=email,
        password=password,
        config_path=args.config,
        captcha_api_key=args.captcha
    )
    
    try:
        reporter.run(profiles, delay=args.delay)
    except KeyboardInterrupt:
        print("\n[!] Interrupted by user")
    except Exception as e:
        print(f"\n[-] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        reporter.browser.close()

if __name__ == "__main__":
    main()