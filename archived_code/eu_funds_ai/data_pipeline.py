FinAssist BH - Data Processing Pipeline
Napredni sistem za obradu, čišćenje i analizu podataka o grantovima
"""

import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import re
import logging
from pathlib import Path
import hashlib
from concurrent.futures import ThreadPoolExecutor
import aiofiles

logger = logging.getLogger(__name__)

class DataSource(Enum):
    """Tipovi izvora podataka"""
    WEB_SCRAPING = "web_scraping"
    API = "api"
    MANUAL_UPLOAD = "manual_upload"
    EMAIL_PARSING = "email_parsing"
    PDF_EXTRACTION = "pdf_extraction"
    RSS_FEED = "rss_feed"

class DataQuality(Enum):
    """Kvalitet podataka"""
    EXCELLENT = "excellent"  # 90-100%
    GOOD = "good"           # 70-89%
    FAIR = "fair"           # 50-69%
    POOR = "poor"           # 0-49%

class ProcessingStatus(Enum):
    """Status obrade"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class DataRecord:
    """Osnovni zapis podataka"""
    record_id: str
    source: DataSource
    source_url: str
    raw_data: Dict[str, Any]
    processed_data: Optional[Dict[str, Any]] = None
    quality_score: Optional[float] = None
    quality_level: Optional[DataQuality] = None
    processing_status: ProcessingStatus = ProcessingStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    processed_at: Optional[datetime] = None
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.record_id:
            # Generiraj ID na osnovu sadržaja
            content_hash = hashlib.md5(
                json.dumps(self.raw_data, sort_keys=True).encode()
            ).hexdigest()
            self.record_id = f"{self.source.value}_{content_hash[:12]}"

@dataclass
class GrantData:
    """Strukturirani podaci o grantu"""
    grant_id: str
    title: str
    description: str
    organization: str
    deadline: Optional[datetime]
    budget_min: Optional[float]
    budget_max: Optional[float]
    currency: str = "BAM"
    categories: List[str] = field(default_factory=list)
    eligibility_criteria: List[str] = field(default_factory=list)
    required_documents: List[str] = field(default_factory=list)
    contact_info: Dict[str, str] = field(default_factory=dict)
    application_url: Optional[str] = None
    source_url: str = ""
    entity: Optional[str] = None  # FBiH, RS, BD
    location: Optional[str] = None
    language: str = "bs"
    is_active: bool = True
    confidence_score: float = 0.0
    extracted_at: datetime = field(default_factory=datetime.now)

class FinAssistDataPipeline:
    """Glavni sistem za obradu podataka"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.raw_data: List[DataRecord] = []
        self.processed_grants: List[GrantData] = []
        self.processing_stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'duplicates_removed': 0,
            'quality_improved': 0
        }
        
        # Regex patterns za različite tipove podataka
        self.patterns = self._initialize_patterns()
        
        # Mapiranje organizacija
        self.organization_mapping = self._initialize_organization_mapping()
        
        # Kategorije mapiranje
        self.category_mapping = self._initialize_category_mapping()
        
    def _initialize_patterns(self) -> Dict[str, re.Pattern]:
        """Inicijalizuje regex pattern-e"""
        return {
            'deadline': re.compile(
                r'(?:deadline|rok|do|until|prije|before)[\s:]*(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{4})',
                re.IGNORECASE
            ),
            'budget': re.compile(
                r'(?:budžet|budget|iznos|amount|do|up to|maksimalno|max)[\s:]*(\d+(?:[.,]\d+)?)\s*(?:KM|BAM|EUR|€)',
                re.IGNORECASE
            ),
            'budget_range': re.compile(
                r'(\d+(?:[.,]\d+)?)\s*(?:-|do|to)\s*(\d+(?:[.,]\d+)?)\s*(?:KM|BAM|EUR|€)',
                re.IGNORECASE
            ),
            'email': re.compile(
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            ),
            'phone': re.compile(
                r'(?:\+387|0)[\s\-]?(?:\d{2}[\s\-]?\d{3}[\s\-]?\d{3,4}|\d{8,9})'
            ),
            'url': re.compile(
                r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?'
            )
        }
    
    def _initialize_organization_mapping(self) -> Dict[str, str]:
        """Mapiranje naziva organizacija"""
        return {
            # EU institucije
            'delegacija eu': 'Delegacija Europske unije u BiH',
            'eu delegation': 'Delegacija Europske unije u BiH',
            'cfcu': 'Centralna jedinica za ugovaranje IPA projekata',
            'european commission': 'Europska komisija',
            
            # Državne institucije BiH
            'vijeće ministara': 'Vijeće ministara BiH',
            'council of ministers': 'Vijeće ministara BiH',
            'mvteo': 'Ministarstvo vanjske trgovine i ekonomskih odnosa BiH',
            'fipa': 'Agencija za unapređenje stranih investicija BiH',
            
            # FBiH institucije
            'vlada fbih': 'Vlada Federacije BiH',
            'government fbih': 'Vlada Federacije BiH',
            'ministarstvo razvoja fbih': 'Ministarstvo razvoja, poduzetništva i obrta FBiH',
            'fond za okoliš fbih': 'Fond za zaštitu okoliša FBiH',
            
            # RS institucije
            'vlada rs': 'Vlada Republike Srpske',
            'government rs': 'Vlada Republike Srpske',
            'ministarstvo privrede rs': 'Ministarstvo privrede Republike Srpske',
            'fond za okoliš rs': 'Fond za zaštitu okoliša RS',
            
            # Kantoni
            'kanton sarajevo': 'Kanton Sarajevo',
            'usk': 'Unsko-sanski kanton',
            'zdk': 'Zeničko-dobojski kanton',
            'tk': 'Tuzlanski kanton',
            'hnk': 'Hercegovačko-neretvanski kanton',
            
            # Gradovi
            'grad sarajevo': 'Grad Sarajevo',
            'grad banja luka': 'Grad Banja Luka',
            'općina tuzla': 'Općina Tuzla'
        }
    
    def _initialize_category_mapping(self) -> Dict[str, List[str]]:
        """Mapiranje kategorija"""
        return {
            'inovacije': ['innovation', 'inovacija', 'tehnologija', 'technology', 'r&d', 'research'],
            'digitalizacija': ['digital', 'digitalization', 'ict', 'it', 'software', 'app'],
            'zelena_ekonomija': ['green', 'zelena', 'okoliš', 'environment', 'sustainability', 'održivost'],
            'turizam': ['tourism', 'turizam', 'travel', 'putovanje', 'heritage', 'baština'],
            'poljoprivreda': ['agriculture', 'poljoprivreda', 'farming', 'rural', 'ruralni'],
            'obrazovanje': ['education', 'obrazovanje', 'training', 'obuka', 'škola', 'school'],
            'zdravstvo': ['health', 'zdravstvo', 'medical', 'medicinski', 'hospital'],
            'kultura': ['culture', 'kultura', 'art', 'umjetnost', 'heritage', 'baština'],
            'sport': ['sport', 'sports', 'recreation', 'rekreacija', 'fitness'],
            'energetika': ['energy', 'energija', 'renewable', 'obnovljiva', 'solar', 'wind']
        }
    
    async def add_raw_data(self, source: DataSource, source_url: str, 
                          data: Dict[str, Any], metadata: Dict[str, Any] = None) -> DataRecord:
        """Dodaje sirove podatke u pipeline"""
        
        record = DataRecord(
            record_id="",  # Će biti generisan
            source=source,
            source_url=source_url,
            raw_data=data,
            metadata=metadata or {}
        )
        
        self.raw_data.append(record)
        logger.info(f"Dodani sirovi podaci: {record.record_id}")
        
        return record
    
    async def process_all_data(self) -> Dict[str, Any]:
        """Obrađuje sve sirove podatke"""
        logger.info(f"Pokretanje obrade {len(self.raw_data)} zapisa")
        
        # Resetuj statistike
        self.processing_stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'duplicates_removed': 0,
            'quality_improved': 0
        }
        
        # Obradi podatke paralelno
        tasks = []
        for record in self.raw_data:
            if record.processing_status == ProcessingStatus.PENDING:
                tasks.append(self._process_single_record(record))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analiziraj rezultate
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Greška pri obradi zapisa {i}: {str(result)}")
                self.processing_stats['failed'] += 1
            else:
                self.processing_stats['successful'] += 1
        
        self.processing_stats['total_processed'] = len(tasks)
        
        # Ukloni duplikate
        await self._remove_duplicates()
        
        # Poboljšaj kvalitet
        await self._improve_data_quality()
        
        logger.info(f"Obrada završena: {self.processing_stats}")
        
        return self.processing_stats
    
    async def _process_single_record(self, record: DataRecord) -> GrantData:
        """Obrađuje jedan zapis"""
        try:
            record.processing_status = ProcessingStatus.PROCESSING
            
            # Izvuci strukturirane podatke
            grant_data = await self._extract_grant_data(record)
            
            # Provjeri kvalitet
            quality_score = self._calculate_quality_score(grant_data, record)
            record.quality_score = quality_score
            record.quality_level = self._determine_quality_level(quality_score)
            
            # Spremi obrađene podatke
            record.processed_data = grant_data.__dict__
            record.processing_status = ProcessingStatus.COMPLETED
            record.processed_at = datetime.now()
            
            # Dodaj u listu obrađenih grantova
            self.processed_grants.append(grant_data)
            
            logger.debug(f"Uspješno obrađen zapis {record.record_id}")
            return grant_data
            
        except Exception as e:
            record.processing_status = ProcessingStatus.FAILED
            record.errors.append(str(e))
            logger.error(f"Greška pri obradi zapisa {record.record_id}: {str(e)}")
            raise
    
    async def _extract_grant_data(self, record: DataRecord) -> GrantData:
        """Izvlači strukturirane podatke o grantu"""
        raw = record.raw_data
        
        # Osnovni podaci
        title = self._extract_title(raw)
        description = self._extract_description(raw)
        organization = self._extract_organization(raw)
        
        # Deadline
        deadline = self._extract_deadline(raw)
        
        # Budžet
        budget_min, budget_max, currency = self._extract_budget(raw)
        
        # Kategorije
        categories = self._extract_categories(raw)
        
        # Kriteriji podobnosti
        eligibility_criteria = self._extract_eligibility_criteria(raw)
        
        # Potrebni dokumenti
        required_documents = self._extract_required_documents(raw)
        
        # Kontakt informacije
        contact_info = self._extract_contact_info(raw)
        
        # URL aplikacije
        application_url = self._extract_application_url(raw)
        
        # Entitet i lokacija
        entity = self._extract_entity(raw, organization)
        location = self._extract_location(raw)
        
        # Jezik
        language = self._detect_language(raw)
        
        # Generiraj ID
        grant_id = self._generate_grant_id(title, organization)
        
        return GrantData(
            grant_id=grant_id,
            title=title,
            description=description,
            organization=organization,
            deadline=deadline,
            budget_min=budget_min,
            budget_max=budget_max,
            currency=currency,
            categories=categories,
            eligibility_criteria=eligibility_criteria,
            required_documents=required_documents,
            contact_info=contact_info,
            application_url=application_url,
            source_url=record.source_url,
            entity=entity,
            location=location,
            language=language
        )
    
    def _extract_title(self, raw_data: Dict[str, Any]) -> str:
        """Izvlači naslov"""
        # Pokušaj različite ključeve
        for key in ['title', 'naslov', 'name', 'naziv', 'heading', 'h1', 'h2']:
            if key in raw_data and raw_data[key]:
                title = str(raw_data[key]).strip()
                if len(title) > 10:  # Minimalna duljina
                    return self._clean_text(title)
        
        # Ako nema eksplicitnog naslova, pokušaj iz sadržaja
        content = raw_data.get('content', '') or raw_data.get('text', '')
        if content:
            lines = content.split('\n')
            for line in lines[:5]:  # Provjeri prvih 5 linija
                line = line.strip()
                if len(line) > 10 and len(line) < 200:
                    return self._clean_text(line)
        
        return "Nepoznat naslov"
    
    def _extract_description(self, raw_data: Dict[str, Any]) -> str:
        """Izvlači opis"""
        for key in ['description', 'opis', 'content', 'sadržaj', 'text', 'body']:
            if key in raw_data and raw_data[key]:
                desc = str(raw_data[key]).strip()
                if len(desc) > 50:
                    return self._clean_text(desc)[:2000]  # Ograniči na 2000 znakova
        
        return ""
    
    def _extract_organization(self, raw_data: Dict[str, Any]) -> str:
        """Izvlači organizaciju"""
        for key in ['organization', 'organizacija', 'publisher', 'izdavač', 'source', 'izvor']:
            if key in raw_data and raw_data[key]:
                org = str(raw_data[key]).strip()
                
                # Provjeri mapiranje
                org_lower = org.lower()
                for mapped_key, mapped_value in self.organization_mapping.items():
                    if mapped_key in org_lower:
                        return mapped_value
                
                return self._clean_text(org)
        
        # Pokušaj izvući iz URL-a
        url = raw_data.get('url', '') or raw_data.get('source_url', '')
        if url:
            domain = re.search(r'https?://(?:www\.)?([^/]+)', url)
            if domain:
                domain_name = domain.group(1)
                if 'europa.ba' in domain_name:
                    return 'Delegacija Europske unije u BiH'
                elif 'cfcubh.ba' in domain_name:
                    return 'Centralna jedinica za ugovaranje IPA projekata'
                elif 'fbihvlada.gov.ba' in domain_name:
                    return 'Vlada Federacije BiH'
                elif 'vladars.net' in domain_name:
                    return 'Vlada Republike Srpske'
        
        return "Nepoznata organizacija"
    
    def _extract_deadline(self, raw_data: Dict[str, Any]) -> Optional[datetime]:
        """Izvlači deadline"""
        # Direktni ključevi
        for key in ['deadline', 'rok', 'due_date', 'end_date', 'expires']:
            if key in raw_data and raw_data[key]:
                date_str = str(raw_data[key])
                parsed_date = self._parse_date(date_str)
                if parsed_date:
                    return parsed_date
        
        # Pretraži u tekstu
        text_content = ' '.join([
            str(raw_data.get('content', '')),
            str(raw_data.get('description', '')),
            str(raw_data.get('text', ''))
        ])
        
        deadline_match = self.patterns['deadline'].search(text_content)
        if deadline_match:
            day, month, year = deadline_match.groups()
            try:
                return datetime(int(year), int(month), int(day))
            except ValueError:
                pass
        
        return None
    
    def _extract_budget(self, raw_data: Dict[str, Any]) -> Tuple[Optional[float], Optional[float], str]:
        """Izvlači budžet"""
        budget_min = None
        budget_max = None
        currency = "BAM"
        
        # Direktni ključevi
        for key in ['budget', 'budžet', 'amount', 'iznos', 'funding']:
            if key in raw_data and raw_data[key]:
                budget_str = str(raw_data[key])
                min_val, max_val, curr = self._parse_budget(budget_str)
                if min_val or max_val:
                    return min_val, max_val, curr
        
        # Pretraži u tekstu
        text_content = ' '.join([
            str(raw_data.get('content', '')),
            str(raw_data.get('description', '')),
            str(raw_data.get('text', ''))
        ])
        
        # Pokušaj range format
        range_match = self.patterns['budget_range'].search(text_content)
        if range_match:
            min_str, max_str = range_match.groups()
            budget_min = self._parse_number(min_str)
            budget_max = self._parse_number(max_str)
            
            # Odredi valutu
            if 'EUR' in range_match.group(0) or '€' in range_match.group(0):
                currency = "EUR"
        
        # Pokušaj pojedinačni iznos
        if not budget_min and not budget_max:
            budget_match = self.patterns['budget'].search(text_content)
            if budget_match:
                amount_str = budget_match.group(1)
                amount = self._parse_number(amount_str)
                if amount:
                    budget_max = amount
                    
                    if 'EUR' in budget_match.group(0) or '€' in budget_match.group(0):
                        currency = "EUR"
        
        return budget_min, budget_max, currency
    
    def _extract_categories(self, raw_data: Dict[str, Any]) -> List[str]:
        """Izvlači kategorije"""
        categories = []
        
        # Direktni ključevi
        for key in ['categories', 'kategorije', 'tags', 'oznake', 'type', 'tip']:
            if key in raw_data and raw_data[key]:
                if isinstance(raw_data[key], list):
                    categories.extend([str(cat).strip() for cat in raw_data[key]])
                else:
                    categories.append(str(raw_data[key]).strip())
        
        # Analiziraj sadržaj
        text_content = ' '.join([
            str(raw_data.get('title', '')),
            str(raw_data.get('description', '')),
            str(raw_data.get('content', ''))
        ]).lower()
        
        for category, keywords in self.category_mapping.items():
            for keyword in keywords:
                if keyword.lower() in text_content:
                    if category not in categories:
                        categories.append(category)
                    break
        
        return categories
    
    def _extract_eligibility_criteria(self, raw_data: Dict[str, Any]) -> List[str]:
        """Izvlači kriterije podobnosti"""
        criteria = []
        
        # Direktni ključevi
        for key in ['eligibility', 'podobnost', 'criteria', 'kriteriji', 'requirements', 'zahtjevi']:
            if key in raw_data and raw_data[key]:
                if isinstance(raw_data[key], list):
                    criteria.extend([str(crit).strip() for crit in raw_data[key]])
                else:
                    criteria.append(str(raw_data[key]).strip())
        
        # Pretraži u tekstu
        text_content = str(raw_data.get('content', '')) + ' ' + str(raw_data.get('description', ''))
        
        # Ključne riječi za kriterije
        criteria_keywords = [
            r'mala i srednja preduzeća|msp|sme',
            r'nevladine organizacije|ngo',
            r'javne institucije',
            r'obrazovne institucije',
            r'startups?|startup',
            r'preduzetnici',
            r'poljoprivrednici',
            r'gradovi|općine',
            r'sufinansiranje|cofinancing',
            r'partnerstvo|partnership',
            r'iskustvo|experience'
        ]
        
        for pattern in criteria_keywords:
            matches = re.findall(pattern, text_content, re.IGNORECASE)
            for match in matches:
                if match not in criteria:
                    criteria.append(match)
        
        return criteria
    
    def _extract_required_documents(self, raw_data: Dict[str, Any]) -> List[str]:
        """Izvlači potrebne dokumente"""
        documents = []
        
        # Direktni ključevi
        for key in ['documents', 'dokumenti', 'attachments', 'prilozi', 'files']:
            if key in raw_data and raw_data[key]:
                if isinstance(raw_data[key], list):
                    documents.extend([str(doc).strip() for doc in raw_data[key]])
                else:
                    documents.append(str(raw_data[key]).strip())
        
        # Pretraži u tekstu
        text_content = str(raw_data.get('content', ''))
        
        # Tipični dokumenti
        doc_patterns = [
            r'projektni prijedlog|project proposal',
            r'budžet|budget',
            r'cv|životopis|curriculum vitae',
            r'pregled troškova|cost breakdown',
            r'pismo namjere|letter of intent',
            r'potvrda o registraciji|registration certificate',
            r'finansijski izvještaj|financial report',
            r'plan održivosti|sustainability plan'
        ]
        
        for pattern in doc_patterns:
            if re.search(pattern, text_content, re.IGNORECASE):
                documents.append(pattern.split('|')[0])
        
        return documents
    
    def _extract_contact_info(self, raw_data: Dict[str, Any]) -> Dict[str, str]:
        """Izvlači kontakt informacije"""
        contact = {}
        
        # Direktni ključevi
        if 'contact' in raw_data:
            contact.update(raw_data['contact'])
        
        # Pretraži email i telefon u tekstu
        text_content = ' '.join([
            str(raw_data.get('content', '')),
            str(raw_data.get('description', '')),
            str(raw_data.get('contact_info', ''))
        ])
        
        # Email
        email_matches = self.patterns['email'].findall(text_content)
        if email_matches:
            contact['email'] = email_matches[0]
        
        # Telefon
        phone_matches = self.patterns['phone'].findall(text_content)
        if phone_matches:
            contact['phone'] = phone_matches[0]
        
        return contact
    
    def _extract_application_url(self, raw_data: Dict[str, Any]) -> Optional[str]:
        """Izvlači URL za aplikaciju"""
        # Direktni ključevi
        for key in ['application_url', 'apply_url', 'link', 'url']:
            if key in raw_data and raw_data[key]:
                url = str(raw_data[key]).strip()
                if url.startswith('http'):
                    return url
        
        # Pretraži u tekstu
        text_content = str(raw_data.get('content', ''))
        url_matches = self.patterns['url'].findall(text_content)
        
        for url in url_matches:
            if any(keyword in url.lower() for keyword in ['apply', 'application', 'prijava', 'natječaj']):
                return url
        
        # Vrati prvi URL ako nema specifičan
        if url_matches:
            return url_matches[0]
        
        return None
    
    def _extract_entity(self, raw_data: Dict[str, Any], organization: str) -> Optional[str]:
        """Određuje entitet (FBiH, RS, BD)"""
        # Na osnovu organizacije
        org_lower = organization.lower()
        
        if any(keyword in org_lower for keyword in ['fbih', 'federacija', 'federation', 'kanton']):
            return "FBiH"
        elif any(keyword in org_lower for keyword in ['rs', 'republika srpska', 'vladars']):
            return "RS"
        elif any(keyword in org_lower for keyword in ['brčko', 'brcko', 'distrikt']):
            return "BD"
        elif any(keyword in org_lower for keyword in ['bih', 'bosnia', 'vijeće ministara', 'council']):
            return "BiH"
        
        # Pretraži u sadržaju
        text_content = ' '.join([
            str(raw_data.get('content', '')),
            str(raw_data.get('description', ''))
        ]).lower()
        
        if 'federacija' in text_content or 'fbih' in text_content:
            return "FBiH"
        elif 'republika srpska' in text_content or 'vladars' in text_content:
            return "RS"
        elif 'brčko' in text_content or 'distrikt' in text_content:
            return "BD"
        
        return None
    
    def _extract_location(self, raw_data: Dict[str, Any]) -> Optional[str]:
        """Izvlači lokaciju"""
        # Direktni ključevi
        for key in ['location', 'lokacija', 'city', 'grad', 'place', 'mjesto']:
            if key in raw_data and raw_data[key]:
                return str(raw_data[key]).strip()
        
        # Pretraži u tekstu
        text_content = ' '.join([
            str(raw_data.get('content', '')),
            str(raw_data.get('description', ''))
        ]).lower()
        
        # Poznate lokacije
        locations = [
            'sarajevo', 'banja luka', 'tuzla', 'zenica', 'mostar', 'bihać', 'prijedor',
            'doboj', 'bijeljina', 'trebinje', 'cazin', 'velika kladuša', 'livno',
            'tomislavgrad', 'široki brijeg', 'čapljina', 'goražde', 'foča', 'višegrad'
        ]
        
        for location in locations:
            if location in text_content:
                return location.title()
        
        return None
    
    def _detect_language(self, raw_data: Dict[str, Any]) -> str:
        """Detektuje jezik"""
        text_content = ' '.join([
            str(raw_data.get('title', '')),
            str(raw_data.get('description', '')),
            str(raw_data.get('content', ''))
        ]).lower()
        
        # Jednostavna detekcija na osnovu ključnih riječi
        bs_keywords = ['natječaj', 'poziv', 'grant', 'subvencija', 'poticaj', 'sredstva', 'financiranje']
        en_keywords = ['call', 'tender', 'funding', 'grant', 'application', 'deadline']
        
        bs_count = sum(1 for keyword in bs_keywords if keyword in text_content)
        en_count = sum(1 for keyword in en_keywords if keyword in text_content)
        
        if bs_count > en_count:
            return "bs"
        elif en_count > bs_count:
            return "en"
        else:
            return "bs"  # Default
    
    def _generate_grant_id(self, title: str, organization: str) -> str:
        """Generiše jedinstveni ID za grant"""
        # Kreiraj hash na osnovu naslova i organizacije
        content = f"{title}_{organization}".lower()
        hash_value = hashlib.md5(content.encode()).hexdigest()
        return f"grant_{hash_value[:12]}"
    
    def _clean_text(self, text: str) -> str:
        """Čisti tekst"""
        # Ukloni višestruke razmake
        text = re.sub(r'\s+', ' ', text)
        
        # Ukloni HTML tagove
        text = re.sub(r'<[^>]+>', '', text)
        
        # Ukloni specijalne znakove na početku i kraju
        text = text.strip(' \t\n\r\f\v-•*')
        
        return text
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parsira datum iz stringa"""
        date_str = date_str.strip()
        
        # Različiti formati
        formats = [
            '%d.%m.%Y',
            '%d/%m/%Y',
            '%Y-%m-%d',
            '%d-%m-%Y',
            '%d.%m.%y',
            '%d/%m/%y'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        return None
    
    def _parse_budget(self, budget_str: str) -> Tuple[Optional[float], Optional[float], str]:
        """Parsira budžet iz stringa"""
        budget_str = budget_str.lower()
        currency = "BAM"
        
        if 'eur' in budget_str or '€' in budget_str:
            currency = "EUR"
        
        # Ukloni valutu i ostale znakove
        clean_str = re.sub(r'[^\d.,\-\s]', '', budget_str)
        
        # Pokušaj range
        range_match = re.search(r'(\d+(?:[.,]\d+)?)\s*[-–]\s*(\d+(?:[.,]\d+)?)', clean_str)
        if range_match:
            min_val = self._parse_number(range_match.group(1))
            max_val = self._parse_number(range_match.group(2))
            return min_val, max_val, currency
        
        # Pojedinačni broj
        number_match = re.search(r'(\d+(?:[.,]\d+)?)', clean_str)
        if number_match:
            amount = self._parse_number(number_match.group(1))
            return None, amount, currency
        
        return None, None, currency
    
    def _parse_number(self, number_str: str) -> Optional[float]:
        """Parsira broj iz stringa"""
        try:
            # Zamijeni zarez s točkom
            number_str = number_str.replace(',', '.')
            return float(number_str)
        except ValueError:
            return None
    
    def _calculate_quality_score(self, grant_data: GrantData, record: DataRecord) -> float:
        """Izračunava score kvaliteta podataka"""
        score = 0.0
        max_score = 100.0
        
        # Osnovni podaci (40 bodova)
        if grant_data.title and grant_data.title != "Nepoznat naslov":
            score += 15
        if grant_data.description and len(grant_data.description) > 50:
            score += 15
        if grant_data.organization and grant_data.organization != "Nepoznata organizacija":
            score += 10
        
        # Deadline (15 bodova)
        if grant_data.deadline:
            score += 15
        
        # Budžet (15 bodova)
        if grant_data.budget_min or grant_data.budget_max:
            score += 10
            if grant_data.budget_min and grant_data.budget_max:
                score += 5
        
        # Kategorije (10 bodova)
        if grant_data.categories:
            score += min(len(grant_data.categories) * 3, 10)
        
        # Kontakt informacije (10 bodova)
        if grant_data.contact_info:
            score += len(grant_data.contact_info) * 3
            score = min(score, max_score - 10)  # Ograniči na 10 bodova za kontakt
        
        # URL aplikacije (5 bodova)
        if grant_data.application_url:
            score += 5
        
        # Entitet i lokacija (5 bodova)
        if grant_data.entity:
            score += 2.5
        if grant_data.location:
            score += 2.5
        
        return min(score, max_score)
    
    def _determine_quality_level(self, score: float) -> DataQuality:
        """Određuje nivo kvaliteta"""
        if score >= 90:
            return DataQuality.EXCELLENT
        elif score >= 70:
            return DataQuality.GOOD
        elif score >= 50:
            return DataQuality.FAIR
        else:
            return DataQuality.POOR
    
    async def _remove_duplicates(self):
        """Uklanja duplikate"""
        seen_grants = {}
        unique_grants = []
        
        for grant in self.processed_grants:
            # Kreiraj ključ za poređenje
            key = f"{grant.title.lower()}_{grant.organization.lower()}"
            
            if key in seen_grants:
                # Duplikat - zadrži bolji
                existing_grant = seen_grants[key]
                if grant.confidence_score > existing_grant.confidence_score:
                    # Zamijeni s boljim
                    unique_grants = [g for g in unique_grants if g.grant_id != existing_grant.grant_id]
                    unique_grants.append(grant)
                    seen_grants[key] = grant
                
                self.processing_stats['duplicates_removed'] += 1
            else:
                seen_grants[key] = grant
                unique_grants.append(grant)
        
        self.processed_grants = unique_grants
        logger.info(f"Uklonjeno {self.processing_stats['duplicates_removed']} duplikata")
    
    async def _improve_data_quality(self):
        """Poboljšava kvalitet podataka"""
        improved_count = 0
        
        for grant in self.processed_grants:
            original_score = grant.confidence_score
            
            # Poboljšaj naslov
            if grant.title:
                grant.title = self._improve_title(grant.title)
            
            # Poboljšaj opis
            if grant.description:
                grant.description = self._improve_description(grant.description)
            
            # Poboljšaj kategorije
            grant.categories = self._improve_categories(grant.categories, grant.title, grant.description)
            
            # Poboljšaj organizaciju
            grant.organization = self._improve_organization(grant.organization)
            
            # Preračunaj confidence score
            # (Ovdje bi trebala biti kompleksnija logika)
            new_score = original_score + 5  # Jednostavno poboljšanje
            grant.confidence_score = min(new_score, 100.0)
            
            if grant.confidence_score > original_score:
                improved_count += 1
        
        self.processing_stats['quality_improved'] = improved_count
        logger.info(f"Poboljšan kvalitet za {improved_count} grantova")
    
    def _improve_title(self, title: str) -> str:
        """Poboljšava naslov"""
        # Ukloni duplikate riječi
        words = title.split()
        unique_words = []
        for word in words:
            if word.lower() not in [w.lower() for w in unique_words]:
                unique_words.append(word)
        
        # Kapitaliziraj prvo slovo
        improved_title = ' '.join(unique_words)
        if improved_title:
            improved_title = improved_title[0].upper() + improved_title[1:]
        
        return improved_title
    
    def _improve_description(self, description: str) -> str:
        """Poboljšava opis"""
        # Ukloni duplikate rečenica
        sentences = description.split('.')
        unique_sentences = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and sentence not in unique_sentences:
                unique_sentences.append(sentence)
        
        return '. '.join(unique_sentences)
    
    def _improve_categories(self, categories: List[str], title: str, description: str) -> List[str]:
        """Poboljšava kategorije"""
        improved_categories = list(categories)
        
        # Dodaj kategorije na osnovu sadržaja
        text_content = f"{title} {description}".lower()
        
        for category, keywords in self.category_mapping.items():
            if category not in improved_categories:
                for keyword in keywords:
                    if keyword.lower() in text_content:
                        improved_categories.append(category)
                        break
        
        return improved_categories
    
    def _improve_organization(self, organization: str) -> str:
        """Poboljšava naziv organizacije"""
        org_lower = organization.lower()
        
        # Provjeri mapiranje
        for mapped_key, mapped_value in self.organization_mapping.items():
            if mapped_key in org_lower:
                return mapped_value
        
        return organization
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """Vraća statistike obrade"""
        total_records = len(self.raw_data)
        processed_records = len([r for r in self.raw_data if r.processing_status == ProcessingStatus.COMPLETED])
        
        # Kvalitet distribucija
        quality_distribution = {}
        for record in self.raw_data:
            if record.quality_level:
                level = record.quality_level.value
                quality_distribution[level] = quality_distribution.get(level, 0) + 1
        
        # Izvori distribucija
        source_distribution = {}
        for record in self.raw_data:
            source = record.source.value
            source_distribution[source] = source_distribution.get(source, 0) + 1
        
        # Prosječni quality score
        quality_scores = [r.quality_score for r in self.raw_data if r.quality_score is not None]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        return {
            'total_records': total_records,
            'processed_records': processed_records,
            'processing_rate': (processed_records / total_records * 100) if total_records > 0 else 0,
            'quality_distribution': quality_distribution,
            'source_distribution': source_distribution,
            'average_quality_score': round(avg_quality, 2),
            'total_grants': len(self.processed_grants),
            'processing_stats': self.processing_stats
        }
    
    async def export_processed_data(self, format: str = "json", filename: str = None) -> str:
        """Izvozi obrađene podatke"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"processed_grants_{timestamp}.{format}"
        
        if format.lower() == "json":
            data = [grant.__dict__ for grant in self.processed_grants]
            
            # Konvertuj datetime objekte u string
            for grant_data in data:
                for key, value in grant_data.items():
                    if isinstance(value, datetime):
                        grant_data[key] = value.isoformat()
            
            async with aiofiles.open(filename, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(data, ensure_ascii=False, indent=2))
        
        elif format.lower() == "csv":
            # Konvertuj u DataFrame
            data = []
            for grant in self.processed_grants:
                row = grant.__dict__.copy()
                # Konvertuj liste u stringove
                for key, value in row.items():
                    if isinstance(value, list):
                        row[key] = '; '.join(map(str, value))
                    elif isinstance(value, dict):
                        row[key] = json.dumps(value, ensure_ascii=False)
                    elif isinstance(value, datetime):
                        row[key] = value.isoformat()
                data.append(row)
            
            df = pd.DataFrame(data)
            df.to_csv(filename, index=False, encoding='utf-8')
        
        logger.info(f"Izvezeni podaci u {filename}")
        return filename

# Primjer korištenja
async def main():
    """Testiranje data pipeline-a"""
    
    # Konfiguracija
    config = {
        'max_workers': 4,
        'quality_threshold': 50.0
    }
    
    # Kreiraj pipeline
    pipeline = FinAssistDataPipeline(config)
    
    # Dodaj test podatke
    test_data = {
        'title': 'IPA - Jačanje konkurentnosti MSP',
        'content': '''
        Poziv za prijave projekata u okviru IPA programa za jačanje konkurentnosti 
        malih i srednjih preduzeća. Budžet: 10.000 - 200.000 BAM.
        Deadline: 30.06.2026. Kontakt: info@cfcubh.ba
        ''',
        'organization': 'CFCU BiH',
        'url': 'http://www.cfcubh.ba/tender/123'
    }
    
    await pipeline.add_raw_data(
        source=DataSource.WEB_SCRAPING,
        source_url='http://www.cfcubh.ba/tender/123',
        data=test_data
    )
    
    # Obradi podatke
    stats = await pipeline.process_all_data()
    print(f"Statistike obrade: {stats}")
    
    # Prikaži obrađene grantove
    for grant in pipeline.processed_grants:
        print(f"Grant: {grant.title}")
        print(f"Organizacija: {grant.organization}")
        print(f"Deadline: {grant.deadline}")
        print(f"Budžet: {grant.budget_min} - {grant.budget_max} {grant.currency}")
        print(f"Kategorije: {grant.categories}")
        print("---")
    
    # Izvezi podatke
    filename = await pipeline.export_processed_data("json")
    print(f"Podaci izvezeni u: {filename}")
    
    # Prikaži statistike
    processing_stats = pipeline.get_processing_statistics()
    print(f"Finalne statistike: {processing_stats}")

if __name__ == "__main__":
    asyncio.run(main())
