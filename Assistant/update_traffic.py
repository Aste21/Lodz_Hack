#!/usr/bin/env python3
"""
Prosty skrypt do aktualizacji informacji o komunikacji.
Można uruchomić przez cron lub ręcznie.
"""

from traffic_scraper import TrafficInfoScraper
import sys

def main():
    print("Aktualizowanie informacji o komunikacji miejskiej...")
    scraper = TrafficInfoScraper()
    
    try:
        data = scraper.scrape_all()
        
        print(f"\n✓ Pobrano:")
        print(f"  - Zmiany rozkładów: {len(data['changes'])}")
        print(f"  - Utrudnienia: {len(data['utrudnienia'])}")
        print(f"  - Remonty: {len(data['remonty'])}")
        print(f"  - Łącznie: {data['total_items']} informacji")
        
        # Zapisujemy
        scraper.save_consolidated(data, "traffic_info.txt")
        scraper.save_json(data, "traffic_info.json")
        
        print("\n✓ Zaktualizowano pliki: traffic_info.txt i traffic_info.json")
        return 0
        
    except Exception as e:
        print(f"\n✗ Błąd: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())

