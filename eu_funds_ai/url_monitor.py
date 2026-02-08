FinAssist BH - URL Monitoring and Grant Scraping System
Sistem za praćenje i skrejpovanje grantova iz svih relevantnih izvora u BiH
"""

import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse
import json

# Konfiguracija logging-a
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Grant:
    """Klasa za reprezentaciju grantova"""
    title: str
    description: str
    deadline: Optional[datetime]
    amount: Optional[str]
    eligibility: List[str]
    source_url: str
    source_name: str
    category: str
    status: str = "active"
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

@dataclass
class MonitoringSource:
    """Klasa za definisanje izvora za praćenje"""
    name: str
    url: str
    category: str
    selector_patterns: Dict[str, str]
    update_frequency: int = 24  # sati
    last_checked: Optional[datetime] = None
    is_active: bool = True

class FinAssistURLMonitor:
    """Glavni sistem za praćenje URL-ova i grantova"""
    
    def __init__(self):
        self.sources = self._initialize_sources()
        self.session = None
        self.grants_database = []
        
    def _initialize_sources(self) -> List[MonitoringSource]:
        """Inicijalizuje sve izvore za praćenje"""
        return [
            # EU Fondovi
            MonitoringSource(
                name="Delegacija EU u BiH",
                url="https://europa.ba/",
                category="EU_FONDOVI",
                selector_patterns={
                    "grants": ".news-item, .tender-item",
                    "title": "h3, h2, .title",
                    "description": ".description, .excerpt, p",
                    "deadline": ".deadline, .date",
                    "link": "a"
                }
            ),
            MonitoringSource(
                name="CFCU BiH",
                url="http://www.cfcubh.ba/",
                category="IPA_FONDOVI",
                selector_patterns={
                    "grants": ".tender, .call, .announcement",
                    "title": "h3, h2, .title",
                    "description": ".content, .description",
                    "deadline": ".deadline, .date",
                    "link": "a"
                }
            ),
            
            # Državna razina BiH
            MonitoringSource(
                name="Vijeće ministara BiH",
                url="https://www.vijeceministara.gov.ba/",
                category="DRZAVNA_RAZINA",
                selector_patterns={
                    "grants": ".news-item, .announcement",
                    "title": "h3, h2",
                    "description": ".content, p",
                    "deadline": ".date",
                    "link": "a"
                }
            ),
            MonitoringSource(
                name="MVTEO BiH",
                url="http://mvteo.gov.ba/",
                category="DRZAVNA_RAZINA",
                selector_patterns={
                    "grants": ".program, .tender",
                    "title": "h3, h2",
                    "description": ".description",
                    "deadline": ".deadline",
                    "link": "a"
                }
            ),
            MonitoringSource(
                name="FIPA BiH",
                url="https://fipa.gov.ba/",
                category="INVESTICIJE",
                selector_patterns={
                    "grants": ".incentive, .program",
                    "title": "h3, h2",
                    "description": ".content",
                    "deadline": ".date",
                    "link": "a"
                }
            ),
            
            # Federacija BiH
            MonitoringSource(
                name="Vlada FBiH",
                url="https://www.fbihvlada.gov.ba/",
                category="FBIH",
                selector_patterns={
                    "grants": ".tender, .call",
                    "title": "h3, h2",
                    "description": ".content",
                    "deadline": ".date",
                    "link": "a"
                }
            ),
            MonitoringSource(
                name="Ministarstvo razvoja FBiH",
                url="https://www.fmrpo.gov.ba/",
                category="FBIH_MSP",
                selector_patterns={
                    "grants": ".program, .subvencija",
                    "title": "h3, h2",
                    "description": ".description",
                    "deadline": ".deadline",
                    "link": "a"
                }
            ),
            
            # Republika Srpska
            MonitoringSource(
                name="Vlada RS",
                url="https://www.vladars.net/",
                category="RS",
                selector_patterns={
                    "grants": ".tender, .program",
                    "title": "h3, h2",
                    "description": ".content",
                    "deadline": ".date",
                    "link": "a"
                }
            ),
            MonitoringSource(
                name="Ministarstvo privrede RS",
                url="http://privreda.vladars.net/",
                category="RS_PRIVREDA",
                selector_patterns={
                    "grants": ".subvencija, .poticaj",
                    "title": "h3, h2",
                    "description": ".description",
                    "deadline": ".deadline",
                    "link": "a"
                }
            ),
            
            # Kantoni
            MonitoringSource(
                name="Kanton Sarajevo",
                url="https://ks.gov.ba/",
                category="KANTON_SA",
                selector_patterns={
                    "grants": ".natjecaj, .tender",
                    "title": "h3, h2",
                    "description": ".content",
                    "deadline": ".date",
                    "link": "a"
                }
            ),
            MonitoringSource(
                name="Unsko-sanski kanton",
                url="https://usk.ba/",
                category="KANTON_USK",
                selector_patterns={
                    "grants": ".natjecaj, .poziv",
                    "title": "h3, h2",
                    "description": ".content",
                    "deadline": ".date",
                    "link": "a"
                }
            ),
            MonitoringSource(
                name="Zeničko-dobojski kanton",
                url="https://zdk.ba/",
                category="KANTON_ZDK",
                selector_patterns={
                    "grants": ".natjecaj, .tender",
                    "title": "h3, h2",
                    "description": ".content",
                    "deadline": ".date",
                    "link": "a"
                }
            ),
            MonitoringSource(
                name="Tuzlanski kanton",
                url="https://tk.kim.ba/",
                category="KANTON_TK",
                selector_patterns={
                    "grants": ".natjecaj, .poziv",
                    "title": "h3, h2",
                    "description": ".content",
                    "deadline": ".date",
                    "link": "a"
                }
            ),
            MonitoringSource(
                name="Hercegovačko-neretvanski kanton",
                url="https://hnk-cbcg.gov.ba/",
                category="KANTON_HNK",
                selector_patterns={
                    "grants": ".natjecaj, .tender",
                    "title": "h3, h2",
                    "description": ".content",
                    "deadline": ".date",
                    "link": "a"
                }
            ),
            
            # Gradovi i općine
            MonitoringSource(
                name="Grad Sarajevo",
                url="https://sarajevo.ba/",
                category="GRAD_SARAJEVO",
                selector_patterns={
                    "grants": ".natjecaj, .subvencija",
                    "title": "h3, h2",
                    "description": ".content",
                    "deadline": ".date",
                    "link": "a"
                }
            ),
            MonitoringSource(
                name="Općina Novi Grad Sarajevo",
                url="https://novigradsarajevo.ba/",
                category="OPCINA_NOVI_GRAD",
                selector_patterns={
                    "grants": ".natjecaj, .poziv",
                    "title": "h3, h2",
                    "description": ".content",
                    "deadline": ".date",
                    "link": "a"
                }
            ),
            MonitoringSource(
                name="Grad Banja Luka",
                url="https://banjaluka.rs.ba/",
                category="GRAD_BANJA_LUKA",
                selector_patterns={
                    "grants": ".natjecaj, .tender",
                    "title": "h3, h2",
                    "description": ".content",
                    "deadline": ".date",
                    "link": "a"
                }
            ),
            MonitoringSource(
                name="Općina Tuzla",
                url="https://tuzla.ba/",
                category="OPCINA_TUZLA",
                selector_patterns={
                    "grants": ".natjecaj, .poziv",
                    "title": "h3, h2",
                    "description": ".content",
                    "deadline": ".date",
                    "link": "a"
                }
            ),
            
            # Fondovi za okoliš
            MonitoringSource(
                name="Fond za zaštitu okoliša FBiH",
                url="http://fondzzopfbih.ba/",
                category="OKOLIŠ_FBIH",
                selector_patterns={
                    "grants": ".natjecaj, .program",
                    "title": "h3, h2",
                    "description": ".content",
                    "deadline": ".date",
                    "link": "a"
                }
            ),
            MonitoringSource(
                name="Fond za zaštitu okoliša RS",
                url="http://fondzazastituokolisars.net/",
                category="OKOLIŠ_RS",
                selector_patterns={
                    "grants": ".natjecaj, .program",
                    "title": "h3, h2",
                    "description": ".content",
                    "deadline": ".date",
                    "link": "a"
                }
            ),
            
            # Razvojne agencije
            MonitoringSource(
                name="ARDA BiH",
                url="https://arda.gov.ba/",
                category="RAZVOJ",
                selector_patterns={
                    "grants": ".projekt, .program",
                    "title": "h3, h2",
                    "description": ".content",
                    "deadline": ".date",
                    "link": "a"
                }
            )
        ]
    
    async def __aenter__(self):
        """Async context manager ulaz"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={
                'User-Agent': 'FinAssist BH Grant Monitor 1.0',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'bs,hr,sr,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager izlaz"""
        if self.session:
            await self.session.close()
    
    async def fetch_page(self, url: str) -> Optional[str]:
        """Dohvaća sadržaj stranice"""
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    content = await response.text()
                    logger.info(f"Uspješno dohvaćena stranica: {url}")
                    return content
                else:
                    logger.warning(f"HTTP {response.status} za {url}")
                    return None
        except Exception as e:
            logger.error(f"Greška pri dohvaćanju {url}: {str(e)}")
            return None
    
    def parse_grants_from_page(self, html_content: str, source: MonitoringSource) -> List[Grant]:
        """Parsira grantove iz HTML sadržaja"""
        grants = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Pronađi sve elemente koji sadrže grantove
            grant_elements = soup.select(source.selector_patterns.get('grants', '.grant'))
            
            for element in grant_elements:
                try:
                    # Izvuci naslov
                    title_elem = element.select_one(source.selector_patterns.get('title', 'h3'))
                    title = title_elem.get_text(strip=True) if title_elem else "Nepoznat naslov"
                    
                    # Provjeri da li je relevantan grant
                    if not self._is_relevant_grant(title):
                        continue
                    
                    # Izvuci opis
                    desc_elem = element.select_one(source.selector_patterns.get('description', 'p'))
                    description = desc_elem.get_text(strip=True) if desc_elem else ""
                    
                    # Izvuci deadline
                    deadline_elem = element.select_one(source.selector_patterns.get('deadline', '.date'))
                    deadline = self._parse_deadline(deadline_elem.get_text(strip=True) if deadline_elem else "")
                    
                    # Izvuci link
                    link_elem = element.select_one(source.selector_patterns.get('link', 'a'))
                    link = urljoin(source.url, link_elem.get('href')) if link_elem and link_elem.get('href') else source.url
                    
                    # Odredi eligibility na osnovu kategorije
                    eligibility = self._determine_eligibility(source.category, title, description)
                    
                    # Kreiraj grant objekt
                    grant = Grant(
                        title=title,
                        description=description[:500] + "..." if len(description) > 500 else description,
                        deadline=deadline,
                        amount=self._extract_amount(description),
                        eligibility=eligibility,
                        source_url=link,
                        source_name=source.name,
                        category=source.category
                    )
                    
                    grants.append(grant)
                    
                except Exception as e:
                    logger.error(f"Greška pri parsiranju elementa: {str(e)}")
                    continue
            
            logger.info(f"Pronađeno {len(grants)} grantova na {source.name}")
            
        except Exception as e:
            logger.error(f"Greška pri parsiranju stranice {source.name}: {str(e)}")
        
        return grants
    
    def _is_relevant_grant(self, title: str) -> bool:
        """Provjerava da li je grant relevantan"""
        relevant_keywords = [
            'grant', 'natječaj', 'poziv', 'subvencija', 'poticaj', 'fond', 'program',
            'tender', 'javni poziv', 'javni natječaj', 'bespovratna sredstva',
            'finansiranje', 'podrška', 'pomoć', 'sredstva', 'konkurs'
        ]
        
        title_lower = title.lower()
        return any(keyword in title_lower for keyword in relevant_keywords)
    
    def _parse_deadline(self, date_text: str) -> Optional[datetime]:
        """Parsira deadline iz teksta"""
        if not date_text:
            return None
        
        # Različiti formati datuma koji se koriste u BiH
        date_patterns = [
            r'(\d{1,2})\.(\d{1,2})\.(\d{4})',  # dd.mm.yyyy
            r'(\d{1,2})/(\d{1,2})/(\d{4})',   # dd/mm/yyyy
            r'(\d{4})-(\d{1,2})-(\d{1,2})',   # yyyy-mm-dd
            r'(\d{1,2})\s+(\w+)\s+(\d{4})',   # dd mjesec yyyy
        ]
        
        months_bs = {
            'januar': 1, 'februar': 2, 'mart': 3, 'april': 4, 'maj': 5, 'juni': 6,
            'juli': 7, 'august': 8, 'septembar': 9, 'oktobar': 10, 'novembar': 11, 'decembar': 12,
            'siječanj': 1, 'veljača': 2, 'ožujak': 3, 'travanj': 4, 'svibanj': 5, 'lipanj': 6,
            'srpanj': 7, 'kolovoz': 8, 'rujan': 9, 'listopad': 10, 'studeni': 11, 'prosinac': 12
        }
        
        for pattern in date_patterns:
            match = re.search(pattern, date_text.lower())
            if match:
                try:
                    if len(match.groups()) == 3:
                        if pattern.endswith(r'(\d{4})') and not pattern.startswith(r'(\d{4})'):
                            # dd.mm.yyyy ili dd/mm/yyyy
                            day, month, year = map(int, match.groups())
                        elif pattern.startswith(r'(\d{4})'):
                            # yyyy-mm-dd
                            year, month, day = map(int, match.groups())
                        else:
                            # dd mjesec yyyy
                            day = int(match.group(1))
                            month_name = match.group(2).lower()
                            month = months_bs.get(month_name, 1)
                            year = int(match.group(3))
                        
                        return datetime(year, month, day)
                except ValueError:
                    continue
        
        return None
    
    def _extract_amount(self, text: str) -> Optional[str]:
        """Izvlači iznos iz teksta"""
        # Pretraži različite formate iznosa
        amount_patterns = [
            r'(\d+(?:\.\d+)?)\s*(?:KM|BAM|EUR|€)',
            r'(\d+(?:,\d+)?)\s*(?:hiljada|tisuća|milijuna?)',
            r'do\s+(\d+(?:\.\d+)?)',
            r'maksimalno\s+(\d+(?:\.\d+)?)',
        ]
        
        for pattern in amount_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return None
    
    def _determine_eligibility(self, category: str, title: str, description: str) -> List[str]:
        """Određuje eligibility na osnovu kategorije i sadržaja"""
        eligibility = []
        
        # Osnovna eligibility na osnovu kategorije
        category_eligibility = {
            'EU_FONDOVI': ['NGO', 'Javne institucije', 'Privatni sektor'],
            'IPA_FONDOVI': ['Javne institucije', 'NGO', 'Obrazovne institucije'],
            'DRZAVNA_RAZINA': ['Svi subjekti u BiH'],
            'FBIH': ['Subjekti registrovani u FBiH'],
            'RS': ['Subjekti registrovani u RS'],
            'FBIH_MSP': ['Mala i srednja preduzeća', 'Preduzetnici'],
            'RS_PRIVREDA': ['Privredni subjekti u RS'],
            'INVESTICIJE': ['Investitori', 'Privredni subjekti'],
            'OKOLIŠ_FBIH': ['Ekološki projekti u FBiH'],
            'OKOLIŠ_RS': ['Ekološki projekti u RS'],
            'RAZVOJ': ['Razvojni projekti', 'Javne institucije']
        }
        
        eligibility.extend(category_eligibility.get(category, ['Opći']))
        
        # Dodatna eligibility na osnovu sadržaja
        text_combined = (title + " " + description).lower()
        
        if any(word in text_combined for word in ['msp', 'malo', 'srednje', 'preduzeće']):
            eligibility.append('MSP')
        
        if any(word in text_combined for word in ['ngo', 'udruga', 'organizacija']):
            eligibility.append('NGO')
        
        if any(word in text_combined for word in ['student', 'obrazovanje', 'škola']):
            eligibility.append('Obrazovne institucije')
        
        if any(word in text_combined for word in ['startup', 'inovacija', 'tehnologija']):
            eligibility.append('Startups')
        
        return list(set(eligibility))  # Ukloni duplikate
    
    async def monitor_source(self, source: MonitoringSource) -> List[Grant]:
        """Prati jedan izvor"""
        logger.info(f"Praćenje izvora: {source.name}")
        
        # Provjeri da li je vrijeme za ažuriranje
        if (source.last_checked and 
            datetime.now() - source.last_checked < timedelta(hours=source.update_frequency)):
            logger.info(f"Izvor {source.name} je nedavno provjeren, preskačem")
            return []
        
        html_content = await self.fetch_page(source.url)
        if not html_content:
            return []
        
        grants = self.parse_grants_from_page(html_content, source)
        source.last_checked = datetime.now()
        
        return grants
    
    async def monitor_all_sources(self) -> List[Grant]:
        """Prati sve aktivne izvore"""
        logger.info("Pokretanje praćenja svih izvora...")
        
        active_sources = [source for source in self.sources if source.is_active]
        
        # Kreiraj taskove za sve izvore
        tasks = [self.monitor_source(source) for source in active_sources]
        
        # Pokreni sve taskove paralelno
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Skupi sve grantove
        all_grants = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Greška pri praćenju {active_sources[i].name}: {str(result)}")
            else:
                all_grants.extend(result)
        
        # Ukloni duplikate
        unique_grants = self._remove_duplicates(all_grants)
        
        # Ažuriraj bazu podataka
        self.grants_database.extend(unique_grants)
        
        logger.info(f"Ukupno pronađeno {len(unique_grants)} novih grantova")
        
        return unique_grants
    
    def _remove_duplicates(self, grants: List[Grant]) -> List[Grant]:
        """Uklanja duplikate na osnovu naslova i izvora"""
        seen = set()
        unique_grants = []
        
        for grant in grants:
            key = (grant.title.lower().strip(), grant.source_name)
            if key not in seen:
                seen.add(key)
                unique_grants.append(grant)
        
        return unique_grants
    
    def get_grants_by_category(self, category: str) -> List[Grant]:
        """Vraća grantove po kategoriji"""
        return [grant for grant in self.grants_database if grant.category == category]
    
    def get_active_grants(self) -> List[Grant]:
        """Vraća aktivne grantove (oni koji nisu istekli)"""
        now = datetime.now()
        return [
            grant for grant in self.grants_database 
            if grant.deadline is None or grant.deadline > now
        ]
    
    def get_grants_expiring_soon(self, days: int = 7) -> List[Grant]:
        """Vraća grantove koji ističu uskoro"""
        cutoff_date = datetime.now() + timedelta(days=days)
        return [
            grant for grant in self.grants_database 
            if grant.deadline and grant.deadline <= cutoff_date
        ]
    
    def export_grants_json(self, filename: str = None) -> str:
        """Izvozi grantove u JSON format"""
        if filename is None:
            filename = f"grants_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        grants_data = []
        for grant in self.grants_database:
            grant_dict = {
                'title': grant.title,
                'description': grant.description,
                'deadline': grant.deadline.isoformat() if grant.deadline else None,
                'amount': grant.amount,
                'eligibility': grant.eligibility,
                'source_url': grant.source_url,
                'source_name': grant.source_name,
                'category': grant.category,
                'status': grant.status,
                'created_at': grant.created_at.isoformat()
            }
            grants_data.append(grant_dict)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(grants_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Izvezeno {len(grants_data)} grantova u {filename}")
        return filename
    
    def get_statistics(self) -> Dict:
        """Vraća statistike o grantovima"""
        total_grants = len(self.grants_database)
        active_grants = len(self.get_active_grants())
        expiring_soon = len(self.get_grants_expiring_soon())
        
        categories = {}
        for grant in self.grants_database:
            categories[grant.category] = categories.get(grant.category, 0) + 1
        
        return {
            'total_grants': total_grants,
            'active_grants': active_grants,
            'expiring_soon': expiring_soon,
            'categories': categories,
            'last_update': datetime.now().isoformat(),
            'sources_monitored': len([s for s in self.sources if s.is_active])
        }

# Primjer korištenja
async def main():
    """Glavna funkcija za testiranje"""
    async with FinAssistURLMonitor() as monitor:
        # Pokreni praćenje svih izvora
        new_grants = await monitor.monitor_all_sources()
        
        print(f"Pronađeno {len(new_grants)} novih grantova")
        
        # Prikaži statistike
        stats = monitor.get_statistics()
        print(f"Statistike: {stats}")
        
        # Prikaži grantove koji ističu uskoro
        expiring = monitor.get_grants_expiring_soon(14)
        print(f"Grantovi koji ističu u sljedećih 14 dana: {len(expiring)}")
        
        # Izvezi u JSON
        filename = monitor.export_grants_json()
        print(f"Grantovi izvezeni u: {filename}")

if __name__ == "__main__":
    asyncio.run(main())
