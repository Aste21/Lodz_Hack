"""
Scraper do wyciągania informacji o zmianach w komunikacji miejskiej w Łodzi.
Pobiera dane z:
- MPK zmiany rozkładów
- MPK utrudnienia
- lodz.pl remonty
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Optional
import json
import re
from urllib.parse import urljoin


class TrafficInfoScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.base_url_mpk = "https://mpk.lodz.pl"
        self.base_url_lodz = "https://lodz.pl"
    
    def scrape_message_details(self, article_url: str) -> Dict:
        """Pobiera szczegóły komunikatu z podstrony."""
        try:
            response = self.session.get(article_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Szukamy głównej treści komunikatu
            content = soup.find('div', class_='content') or soup.find('main') or soup
            
            # Szukamy tabeli z komunikatem
            tables = content.find_all('table')
            details = {
                'title': '',
                'lines': [],
                'full_text': '',
                'komunikat_number': ''
            }
            
            # Szukamy tabeli z komunikatem (pomijamy pierwszą tabelę z menu linii)
            for table in tables:
                rows = table.find_all('tr')
                # Sprawdzamy czy to tabela z komunikatem (ma wiersze z tekstem o zmianach)
                is_message_table = False
                for row in rows:
                    row_text = row.get_text(strip=True)
                    if 'komunikat' in row_text.lower() or 'od dnia' in row_text.lower():
                        is_message_table = True
                        break
                
                if not is_message_table:
                    continue  # Pomijamy tabele z menu
                
                # To jest tabela z komunikatem
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 1:
                        cell_text = cells[0].get_text(separator='\n', strip=True)
                        
                        # Sprawdzamy czy to tytuł z datą i liniami
                        if 'od dnia' in cell_text.lower() and 'zmiana' in cell_text.lower():
                            details['title'] = cell_text
                            
                            # Wyciągamy linie z tytułu (linki lub tekst)
                            line_links = cells[0].find_all('a')
                            for link in line_links:
                                line_text = link.get_text(strip=True)
                                if line_text and line_text not in details['lines']:
                                    details['lines'].append(line_text)
                        
                        # Sprawdzamy czy to treść komunikatu
                        elif 'komunikat' in cell_text.lower() or len(cell_text) > 50:
                            if details['full_text']:
                                details['full_text'] += '\n\n' + cell_text
                            else:
                                details['full_text'] = cell_text
                            
                            # Szukamy numeru komunikatu
                            komunikat_match = re.search(r'Komunikat\s+(\d+/\d+)', cell_text, re.IGNORECASE)
                            if komunikat_match and not details['komunikat_number']:
                                details['komunikat_number'] = komunikat_match.group(1)
                        
                        # Jeśli mamy drugą kolumnę z dodatkowymi szczegółami
                        if len(cells) >= 2:
                            second_cell_text = cells[1].get_text(separator='\n', strip=True)
                            if second_cell_text and len(second_cell_text) > 20:
                                if details['full_text']:
                                    details['full_text'] += '\n\n' + second_cell_text
                                else:
                                    details['full_text'] = second_cell_text
            
            # Jeśli nie znaleźliśmy w tabeli, szukamy w innych miejscach
            if not details['full_text']:
                # Szukamy sekcji z komunikatem
                komunikat_section = content.find('h1') or content.find('h2')
                if komunikat_section:
                    details['title'] = komunikat_section.get_text(strip=True)
                
                # Szukamy paragrafów z treścią
                paragraphs = content.find_all(['p', 'div'])
                text_parts = []
                for p in paragraphs:
                    text = p.get_text(strip=True)
                    if text and len(text) > 20:
                        # Filtrujemy menu i nawigację
                        if not any(skip in text.lower() for skip in ['cookie', 'rodo', 'menu', 'start']):
                            text_parts.append(text)
                
                if text_parts:
                    details['full_text'] = '\n\n'.join(text_parts)
            
            return details
            
        except Exception as e:
            print(f"Błąd przy pobieraniu szczegółów komunikatu {article_url}: {e}")
            return {}
    
    def scrape_mpk_changes(self) -> List[Dict]:
        """Pobiera informacje o zmianach rozkładów jazdy z MPK."""
        url = "https://mpk.lodz.pl/rozklady/zmiany.jsp"
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            changes = []
            
            # Szukamy sekcji z planowanymi i aktualnymi zmianami
            content = soup.find('div', class_='content') or soup.find('main') or soup
            
            # Szukamy linków do szczegółowych komunikatów
            message_links = content.find_all('a', href=re.compile(r'wholemessage\.jsp\?articleId=\d+'))
            
            # Pobieramy szczegóły z komunikatów
            for link in message_links:
                href = link.get('href', '')
                if href:
                    # Linki są względne, więc dodajemy bazowy URL
                    if href.startswith('/'):
                        article_url = f"{self.base_url_mpk}{href}"
                    elif href.startswith('http'):
                        article_url = href
                    else:
                        article_url = f"{self.base_url_mpk}/rozklady/{href}"
                    
                    if article_url:
                        details = self.scrape_message_details(article_url)
                        if details.get('full_text') or details.get('title'):
                            # Wyciągamy też tekst z linku (może zawierać datę)
                            link_text = link.get_text(strip=True)
                            parent_text = ""
                            if link.parent:
                                parent_text = link.parent.get_text(separator=' ', strip=True)
                            
                            change_item = {
                                'type': 'zmiana_rozkładu',
                                'section': 'aktualne',
                                'title': details.get('title', link_text or parent_text),
                                'details': details.get('full_text', ''),
                                'lines': details.get('lines', []),
                                'komunikat_number': details.get('komunikat_number', ''),
                                'source': article_url,
                                'scraped_at': datetime.now().isoformat()
                            }
                            
                            # Jeśli mamy szczegóły, dodajemy je do opisu
                            if details.get('lines'):
                                change_item['details'] = f"Linie: {', '.join(details['lines'])}\n\n{change_item['details']}"
                            
                            changes.append(change_item)
            
            # Szukamy nagłówków i list zmian (dla zmian bez linków do komunikatów)
            headings = content.find_all(['h2', 'h3', 'h4', 'strong', 'b'])
            
            current_section = None
            for heading in headings:
                text = heading.get_text(strip=True)
                
                # Planowane zmiany
                if 'planowane' in text.lower() or 'planowane zmiany' in text.lower():
                    current_section = "planowane"
                    continue
                
                # Aktualne zmiany
                if 'aktualne' in text.lower() or 'aktualne zmiany' in text.lower():
                    current_section = "aktualne"
                    continue
                
                # Jeśli to nagłówek z datą/liniami
                if current_section and ('linii' in text.lower() or 'od dnia' in text.lower() or 
                                       'zmiana' in text.lower()):
                    # Sprawdzamy czy nie ma już linku do komunikatu
                    link = heading.find('a', href=re.compile(r'wholemessage'))
                    if not link:
                        # Szukamy następnych elementów z informacjami
                        next_elem = heading.find_next_sibling()
                        if next_elem:
                            details = next_elem.get_text(strip=True)
                            if details:
                                changes.append({
                                    'type': 'zmiana_rozkładu',
                                    'section': current_section,
                                    'title': text,
                                    'details': details,
                                    'source': url,
                                    'scraped_at': datetime.now().isoformat()
                                })
            
            # Alternatywnie: szukamy wszystkich elementów listy
            lists = content.find_all('ul')
            for ul in lists:
                items = ul.find_all('li')
                for item in items:
                    # Sprawdzamy czy nie ma już linku do komunikatu
                    link = item.find('a', href=re.compile(r'wholemessage'))
                    if link:
                        continue  # Już przetworzyliśmy
                    
                    text = item.get_text(strip=True)
                    if text and ('linii' in text.lower() or 'zmiana' in text.lower() or 
                                'od dnia' in text.lower()):
                        changes.append({
                            'type': 'zmiana_rozkładu',
                            'section': 'aktualne',
                            'title': '',
                            'details': text,
                            'source': url,
                            'scraped_at': datetime.now().isoformat()
                        })
            
            return changes
            
        except Exception as e:
            print(f"Błąd przy scrapowaniu zmian MPK: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def scrape_mpk_utrudnienia(self) -> List[Dict]:
        """Pobiera informacje o utrudnieniach w ruchu z MPK."""
        url = "https://www.mpk.lodz.pl/rozklady/utrudnienia.jsp"
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            utrudnienia = []
            
            # Szukamy tabeli z utrudnieniami
            tables = soup.find_all('table')
            
            for table in tables:
                # Szukamy wierszy w tabeli (pomijamy nagłówek)
                rows = table.find_all('tr')
                
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    
                    # Pomijamy wiersze nagłówkowe i puste
                    if len(cells) < 3:
                        continue
                    
                    # Sprawdzamy czy to wiersz z danymi (nie nagłówek)
                    first_cell_text = cells[0].get_text(strip=True).lower()
                    second_cell_text = cells[1].get_text(strip=True).lower() if len(cells) > 1 else ""
                    
                    # Filtrujemy nagłówki tabeli
                    if ('nr linii' in first_cell_text or 
                        'utrudnienie w ruchu' in first_cell_text or
                        'utrudnienie w ruchu' in second_cell_text or
                        'zmiana sytuacji' in first_cell_text or
                        first_cell_text == ''):
                        continue
                    
                    # Wyciągamy dane z komórek
                    lines_cell = cells[0] if len(cells) > 0 else None
                    utrudnienie_cell = cells[1] if len(cells) > 1 else None
                    zmiana_cell = cells[2] if len(cells) > 2 else None
                    
                    # Wyciągamy numery linii
                    lines = []
                    if lines_cell:
                        # Szukamy linków do linii
                        line_links = lines_cell.find_all('a')
                        for link in line_links:
                            line_text = link.get_text(strip=True)
                            # Filtrujemy puste i nieprawidłowe wartości
                            if line_text and line_text.isdigit() or (line_text and len(line_text) <= 5):
                                lines.append(line_text)
                        # Jeśli nie ma linków, bierzemy tekst
                        if not lines:
                            line_text = lines_cell.get_text(strip=True)
                            # Filtrujemy nagłówki i puste wartości
                            if (line_text and 
                                line_text not in ['Nr linii', ''] and 
                                not 'utrudnienie' in line_text.lower() and
                                (line_text.isdigit() or len(line_text) <= 5)):
                                lines = [line_text]
                    
                    # Jeśli nie znaleźliśmy linii, pomijamy ten wiersz
                    if not lines:
                        continue
                    
                    # Wyciągamy opis utrudnienia
                    utrudnienie_text = ""
                    if utrudnienie_cell:
                        utrudnienie_text = utrudnienie_cell.get_text(separator='\n', strip=True)
                        # Filtrujemy nagłówki
                        if 'utrudnienie w ruchu' in utrudnienie_text.lower():
                            utrudnienie_text = ""
                    
                    # Wyciągamy szczegóły zmiany sytuacji
                    zmiana_text = ""
                    if zmiana_cell:
                        zmiana_text = zmiana_cell.get_text(separator='\n', strip=True)
                        # Filtrujemy nagłówki
                        if 'zmiana sytuacji' in zmiana_text.lower() and len(zmiana_text) < 20:
                            zmiana_text = ""
                    
                    # Szukamy dat w całym wierszu i następnych wierszach
                    dates = []
                    # Sprawdzamy wszystkie komórki w wierszu
                    for cell in cells:
                        cell_text = cell.get_text(separator=' ', strip=True)
                        # Szukamy dat w formacie "Dodano dnia YYYY-MM-DD o godzinie HH:MM"
                        date_pattern = r'(\d{4}-\d{2}-\d{2}.*?\d{2}:\d{2})'
                        found_dates = re.findall(date_pattern, cell_text)
                        if found_dates:
                            dates.extend(found_dates)
                    
                    # Szukamy dat w następnych wierszach (mogą być w osobnych wierszach)
                    next_row = row.find_next_sibling('tr')
                    if next_row:
                        next_cells = next_row.find_all(['td', 'th'])
                        for cell in next_cells:
                            cell_text = cell.get_text(separator=' ', strip=True)
                            if 'dodano dnia' in cell_text.lower():
                                date_pattern = r'(\d{4}-\d{2}-\d{2}.*?\d{2}:\d{2})'
                                found_dates = re.findall(date_pattern, cell_text)
                                if found_dates:
                                    dates.extend(found_dates)
                                    break
                    
                    # Usuwamy duplikaty
                    dates = list(set(dates))
                    
                    # Dodajemy tylko jeśli mamy przynajmniej utrudnienie lub zmianę sytuacji
                    if not utrudnienie_text and not zmiana_text:
                        continue
                    
                    # Tworzymy pełny opis
                    full_details = []
                    if lines:
                        full_details.append(f"Linie: {', '.join(lines)}")
                    if utrudnienie_text:
                        full_details.append(f"Utrudnienie: {utrudnienie_text}")
                    if zmiana_text:
                        full_details.append(f"Zmiana sytuacji: {zmiana_text}")
                    if dates:
                        full_details.append(f"Data dodania: {', '.join(dates)}")
                    
                    if full_details:
                        utrudnienia.append({
                            'type': 'utrudnienie',
                            'lines': lines,
                            'title': f"Utrudnienie na liniach: {', '.join(lines) if lines else 'nieznane'}" + 
                                    (f" - {utrudnienie_text[:50]}..." if utrudnienie_text and len(utrudnienie_text) > 50 else ""),
                            'utrudnienie': utrudnienie_text,
                            'zmiana_sytuacji': zmiana_text,
                            'dates': dates,
                            'details': '\n\n'.join(full_details),
                            'source': url,
                            'scraped_at': datetime.now().isoformat()
                        })
            
            # Jeśli nie znaleźliśmy tabeli, próbujemy alternatywną metodę
            if not utrudnienia:
                content = soup.find('div', class_='content') or soup.find('main') or soup
                paragraphs = content.find_all(['p', 'div', 'li'])
                
                for p in paragraphs:
                    text = p.get_text(strip=True)
                    if not text or len(text) < 20:
                        continue
                    
                    keywords = ['utrudnienie', 'zamknięcie', 'remont', 'wypadek', 
                               'kolizja', 'awaria', 'nie kursuje', 'zmiana trasy',
                               'objazd', 'przystanek', 'linia', 'tramwaj', 'autobus']
                    
                    if any(keyword in text.lower() for keyword in keywords):
                        if len(text) > 50 and not any(skip in text.lower() for skip in 
                                                      ['cookie', 'rodo', 'polityka', 'menu']):
                            utrudnienia.append({
                                'type': 'utrudnienie',
                                'title': text[:100] + '...' if len(text) > 100 else text,
                                'details': text,
                                'source': url,
                                'scraped_at': datetime.now().isoformat()
                            })
            
            return utrudnienia
            
        except Exception as e:
            print(f"Błąd przy scrapowaniu utrudnień MPK: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def scrape_lodz_remonty(self) -> List[Dict]:
        """Pobiera informacje o remontach z lodz.pl."""
        url = "https://lodz.pl/remonty/"
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            remonty = []
            
            # Szukamy głównej treści
            content = soup.find('main') or soup.find('article') or soup.find('div', class_='content') or soup
            
            # 1. Planowane spotkania dotyczące remontów w 2026 r.
            headings = content.find_all(['h2', 'h3', 'h4'])
            for heading in headings:
                heading_text = heading.get_text(strip=True)
                
                # Szukamy sekcji o spotkaniach
                if 'remonty w 2026' in heading_text.lower() or 'zaplanuj z nami' in heading_text.lower():
                    # Szukamy tabeli ze spotkaniami
                    table = heading.find_next('table')
                    if table:
                        rows = table.find_all('tr')
                        meetings = []
                        for row in rows[1:]:  # Pomijamy nagłówek
                            cells = row.find_all(['td', 'th'])
                            if len(cells) >= 3:
                                area = cells[0].get_text(separator=' ', strip=True)
                                location = cells[1].get_text(separator=' ', strip=True)
                                date = cells[2].get_text(separator=' ', strip=True)
                                if area and location and date:
                                    meetings.append(f"{area}: {location} - {date}")
                        
                        if meetings:
                            remonty.append({
                                'type': 'remont',
                                'subtype': 'planowane_spotkania_2026',
                                'title': 'Planowane spotkania dotyczące remontów w 2026 r.',
                                'details': '\n'.join(meetings),
                                'source': url,
                                'scraped_at': datetime.now().isoformat()
                            })
            
            # 2. Planowane zmiany w ruchu
            for heading in headings:
                heading_text = heading.get_text(strip=True)
                if 'planowane zmiany w ruchu' in heading_text.lower() or 'rozpoczęcia remontów' in heading_text.lower():
                    # Szukamy listy ulic
                    next_elem = heading.find_next_sibling()
                    planned_changes = []
                    
                    # Szukamy w następnych elementach
                    current = next_elem
                    for _ in range(10):  # Sprawdzamy kilka następnych elementów
                        if not current:
                            break
                        text = current.get_text(strip=True)
                        if text and len(text) > 5 and len(text) < 200:
                            # Sprawdzamy czy to nazwa ulicy lub data
                            if any(char.isupper() for char in text) and not any(skip in text.lower() for skip in 
                                                                              ['cookie', 'menu', 'rodo', 'więcej']):
                                planned_changes.append(text)
                        current = current.find_next_sibling()
                        if current and current.name in ['h2', 'h3', 'h4']:
                            break
                    
                    if planned_changes:
                        remonty.append({
                            'type': 'remont',
                            'subtype': 'planowane_zmiany_ruchu',
                            'title': 'Planowane zmiany w ruchu i rozpoczęcia remontów',
                            'details': '\n'.join(planned_changes),
                            'source': url,
                            'scraped_at': datetime.now().isoformat()
                        })
            
            # 3. Aktualnie prowadzone prace na drogach
            for heading in headings:
                heading_text = heading.get_text(strip=True)
                if 'aktualnie prowadzone prace' in heading_text.lower() or 'prowadzone prace na drogach' in heading_text.lower():
                    # Szukamy wszystkich elementów po nagłówku do następnego nagłówka
                    active_remonts = []
                    current = heading
                    
                    # Przechodzimy przez wszystkie następne elementy
                    for _ in range(200):
                        current = current.find_next()
                        if not current:
                            break
                        
                        # Przerywamy na następnym nagłówku
                        if current.name in ['h2', 'h3', 'h4']:
                            next_heading = current.get_text(strip=True).lower()
                            if 'remonty ulic gruntowych' in next_heading or 'polecamy' in next_heading:
                                break
                        
                        # Szukamy nazw ulic w tekście
                        if current.name in ['div', 'p', 'li', 'span']:
                            text = current.get_text(strip=True)
                            
                            # Filtrujemy niepotrzebne teksty
                            if not text or len(text) < 3:
                                continue
                            if any(skip in text.lower() for skip in 
                                  ['cookie', 'menu', 'rodo', 'więcej', 'polecamy', 'informacje', 
                                   'remonty ulic gruntowych', 'wszystkie informacje']):
                                continue
                            
                            # Sprawdzamy czy to może być nazwa ulicy
                            # Nazwy ulic są zwykle krótkie, zaczynają się od dużej litery
                            # i mogą zawierać nawiasy z dodatkowymi informacjami
                            if (text[0].isupper() and 
                                (len(text) < 100 or '(' in text or ')' in text) and
                                not text.startswith('Od ') and
                                not text.startswith('W ') and
                                not text.startswith('Przebudowa') and
                                not text.startswith('Remont')):
                                
                                # Sprawdzamy czy to nie jest długi opis
                                words = text.split()
                                if len(words) < 15:  # Krótkie teksty to prawdopodobnie nazwy ulic
                                    if text not in active_remonts:
                                        active_remonts.append(text)
                    
                    if active_remonts:
                        remonty.append({
                            'type': 'remont',
                            'subtype': 'aktualne_prace',
                            'title': 'Aktualnie prowadzone prace na drogach',
                            'details': '\n'.join(active_remonts),
                            'source': url,
                            'scraped_at': datetime.now().isoformat()
                        })
            
            # 4. Remonty ulic gruntowych
            for heading in headings:
                heading_text = heading.get_text(strip=True)
                if 'remonty ulic gruntowych' in heading_text.lower():
                    # Szukamy listy ulic
                    dirt_roads = []
                    current = heading
                    
                    # Przechodzimy przez wszystkie następne elementy
                    for _ in range(200):
                        current = current.find_next()
                        if not current:
                            break
                        
                        # Przerywamy na następnym nagłówku
                        if current.name in ['h2', 'h3', 'h4']:
                            next_heading = current.get_text(strip=True).lower()
                            if 'polecamy' in next_heading or 'top 10' in next_heading:
                                break
                        
                        # Szukamy nazw ulic
                        if current.name in ['div', 'p', 'li', 'span']:
                            text = current.get_text(strip=True)
                            
                            # Filtrujemy niepotrzebne teksty
                            if not text or len(text) < 2:
                                continue
                            if any(skip in text.lower() for skip in 
                                  ['cookie', 'menu', 'rodo', 'więcej', 'polecamy', 'informacje',
                                   'ulice gruntowe to', 'na 2025 r. zaplanowano', 'oto pełna lista']):
                                continue
                            
                            # Sprawdzamy czy to nazwa ulicy
                            # Nazwy ulic są krótkie, zaczynają się od dużej litery
                            if (text[0].isupper() and 
                                len(text) < 50 and
                                not text.startswith('Na ') and
                                not text.startswith('Oto ') and
                                not text.startswith('Ulice ')):
                                
                                # Sprawdzamy czy to nie jest długi opis
                                words = text.split()
                                if len(words) < 5:  # Bardzo krótkie teksty to prawdopodobnie nazwy ulic
                                    if text not in dirt_roads:
                                        dirt_roads.append(text)
                    
                    if dirt_roads:
                        remonty.append({
                            'type': 'remont',
                            'subtype': 'ulice_gruntowe_2025',
                            'title': 'Remonty ulic gruntowych zaplanowanych na 2025 r.',
                            'details': '\n'.join(dirt_roads),
                            'source': url,
                            'scraped_at': datetime.now().isoformat()
                        })
            
            # 5. Dodatkowe szczegóły o remontach (szczegółowe opisy)
            # Szukamy sekcji z opisami remontów
            all_text = content.get_text(separator='\n', strip=True)
            # Szukamy sekcji z opisami ulic (zawierają szczegóły o zamknięciach, objazdach itp.)
            paragraphs = content.find_all(['p', 'div'])
            for p in paragraphs:
                text = p.get_text(strip=True)
                if len(text) > 100 and any(keyword in text.lower() for keyword in 
                                          ['zamknięta', 'objazd', 'prace prowadzone', 'remont jezdni', 
                                           'przebudowa', 'ruch', 'ulica']):
                    # Sprawdzamy czy to nie menu/nawigacja
                    if not any(skip in text.lower() for skip in ['cookie', 'rodo', 'menu główne', 'przeskocz']):
                        # Szukamy nazwy ulicy w tekście
                        title_match = re.search(r'^([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż\s]+(?:\([^)]+\))?)', text)
                        title = title_match.group(1) if title_match else text[:80] + '...'
                        
                        remonty.append({
                            'type': 'remont',
                            'subtype': 'szczegóły_remontu',
                            'title': title,
                            'details': text,
                            'source': url,
                            'scraped_at': datetime.now().isoformat()
                        })
            
            return remonty
            
        except Exception as e:
            print(f"Błąd przy scrapowaniu remontów lodz.pl: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def scrape_all(self) -> Dict:
        """Pobiera wszystkie informacje ze wszystkich źródeł."""
        print("Pobieranie zmian rozkładów z MPK...")
        changes = self.scrape_mpk_changes()
        
        print("Pobieranie utrudnień z MPK...")
        utrudnienia = self.scrape_mpk_utrudnienia()
        
        print("Pobieranie remontów z lodz.pl...")
        remonty = self.scrape_lodz_remonty()
        
        return {
            'changes': changes,
            'utrudnienia': utrudnienia,
            'remonty': remonty,
            'scraped_at': datetime.now().isoformat(),
            'total_items': len(changes) + len(utrudnienia) + len(remonty)
        }
    
    def consolidate_to_text(self, data: Dict) -> str:
        """Konsoliduje wszystkie dane w jeden tekst dla LLM."""
        text_parts = []
        
        text_parts.append("=" * 80)
        text_parts.append("AKTUALNE INFORMACJE O KOMUNIKACJI MIEJSKIEJ W ŁODZI")
        text_parts.append(f"Zaktualizowano: {data['scraped_at']}")
        text_parts.append("=" * 80)
        text_parts.append("")
        
        # Zmiany rozkładów
        if data['changes']:
            text_parts.append("\n## ZMIANY ROZKŁADÓW JAZDY (MPK)")
            text_parts.append("-" * 80)
            for change in data['changes']:
                section = change.get('section', '').upper()
                if section:
                    text_parts.append(f"\n[{section}]")
                
                # Numer komunikatu
                if change.get('komunikat_number'):
                    text_parts.append(f"Komunikat: {change['komunikat_number']}")
                
                # Tytuł
                if change.get('title'):
                    text_parts.append(f"Tytuł: {change['title']}")
                
                # Linie (jeśli są osobno)
                if change.get('lines') and not change.get('details', '').startswith('Linie:'):
                    text_parts.append(f"Linie: {', '.join(change['lines'])}")
                
                # Szczegóły
                if change.get('details'):
                    text_parts.append(f"\nSzczegóły:")
                    text_parts.append(change['details'])
                
                text_parts.append(f"\nŹródło: {change['source']}")
                text_parts.append("")
        
        # Utrudnienia
        if data['utrudnienia']:
            text_parts.append("\n## UTRUDNIENIA W RUCHU (MPK)")
            text_parts.append("-" * 80)
            for utrudnienie in data['utrudnienia']:
                # Linie
                if utrudnienie.get('lines'):
                    text_parts.append(f"\nLinie: {', '.join(utrudnienie['lines'])}")
                
                # Utrudnienie
                if utrudnienie.get('utrudnienie'):
                    text_parts.append(f"Utrudnienie: {utrudnienie['utrudnienie']}")
                
                # Zmiana sytuacji (objazdy, komunikacja zastępcza itp.)
                if utrudnienie.get('zmiana_sytuacji'):
                    text_parts.append(f"\nZmiana sytuacji:")
                    text_parts.append(utrudnienie['zmiana_sytuacji'])
                
                # Daty
                if utrudnienie.get('dates'):
                    text_parts.append(f"\nData dodania: {', '.join(utrudnienie['dates'])}")
                
                # Fallback do starego formatu jeśli nowe pola nie istnieją
                if not utrudnienie.get('utrudnienie') and not utrudnienie.get('zmiana_sytuacji'):
                    if utrudnienie.get('title'):
                        text_parts.append(f"\n{utrudnienie['title']}")
                    if utrudnienie.get('details'):
                        text_parts.append(f"{utrudnienie['details']}")
                
                text_parts.append(f"Źródło: {utrudnienie['source']}")
                text_parts.append("")
        
        # Remonty
        if data['remonty']:
            text_parts.append("\n## REMONTY I ZAMKNIĘCIA DRÓG (lodz.pl)")
            text_parts.append("-" * 80)
            
            # Grupujemy remonty według typu
            by_subtype = {}
            for remont in data['remonty']:
                subtype = remont.get('subtype', 'inne')
                if subtype not in by_subtype:
                    by_subtype[subtype] = []
                by_subtype[subtype].append(remont)
            
            # Wyświetlamy w logicznej kolejności
            subtype_order = [
                'planowane_spotkania_2026',
                'planowane_zmiany_ruchu',
                'aktualne_prace',
                'ulice_gruntowe_2025',
                'szczegóły_remontu',
                'inne'
            ]
            
            for subtype in subtype_order:
                if subtype in by_subtype:
                    for remont in by_subtype[subtype]:
                        if remont.get('date'):
                            text_parts.append(f"\nData: {remont['date']}")
                        if remont.get('title'):
                            text_parts.append(f"\n{remont['title']}")
                        if remont.get('details'):
                            text_parts.append(f"\n{remont['details']}")
                        text_parts.append(f"\nŹródło: {remont['source']}")
                        text_parts.append("")
            
            # Jeśli są remonty bez subtype
            if 'inne' not in by_subtype:
                for remont in data['remonty']:
                    if not remont.get('subtype'):
                        if remont.get('date'):
                            text_parts.append(f"\nData: {remont['date']}")
                        if remont.get('title'):
                            text_parts.append(f"Tytuł: {remont['title']}")
                        text_parts.append(f"Szczegóły: {remont['details']}")
                        text_parts.append(f"Źródło: {remont['source']}")
                        text_parts.append("")
        
        text_parts.append("\n" + "=" * 80)
        text_parts.append(f"Łącznie znaleziono: {data['total_items']} informacji")
        text_parts.append("=" * 80)
        
        return "\n".join(text_parts)
    
    def save_consolidated(self, data: Dict, filename: str = "traffic_info.txt"):
        """Zapisuje skonsolidowane dane do pliku tekstowego."""
        text = self.consolidate_to_text(data)
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"Zapisano skonsolidowane dane do {filename}")
        return filename
    
    def save_json(self, data: Dict, filename: str = "traffic_info.json"):
        """Zapisuje surowe dane do pliku JSON."""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Zapisano dane JSON do {filename}")
        return filename


if __name__ == "__main__":
    scraper = TrafficInfoScraper()
    
    print("Rozpoczynam scrapowanie...")
    data = scraper.scrape_all()
    
    print(f"\nZnaleziono:")
    print(f"  - Zmiany rozkładów: {len(data['changes'])}")
    print(f"  - Utrudnienia: {len(data['utrudnienia'])}")
    print(f"  - Remonty: {len(data['remonty'])}")
    print(f"  - Łącznie: {data['total_items']}")
    
    # Zapisujemy w obu formatach
    scraper.save_consolidated(data, "traffic_info.txt")
    scraper.save_json(data, "traffic_info.json")
    
    print("\nGotowe!")

