FinAssist BH - Grant Eligibility Assessment Engine
Napredni sistem za procjenu podobnosti za grantove i EU fondove
"""

import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import json
import logging

logger = logging.getLogger(__name__)

class OrganizationType(Enum):
    """Tipovi organizacija"""
    MSP = "msp"  # Mala i srednja preduzeća
    NGO = "ngo"  # Nevladine organizacije
    JAVNA_INSTITUCIJA = "javna_institucija"
    OBRAZOVNA_INSTITUCIJA = "obrazovna_institucija"
    STARTUP = "startup"
    PREDUZETNIK = "preduzetnik"
    POLJOPRIVREDNIK = "poljoprivrednik"
    GRAD_OPCINA = "grad_opcina"
    OSTALO = "ostalo"

class ProjectCategory(Enum):
    """Kategorije projekata"""
    INOVACIJE = "inovacije"
    DIGITALIZACIJA = "digitalizacija"
    ZELENA_EKONOMIJA = "zelena_ekonomija"
    TURIZAM = "turizam"
    POLJOPRIVREDA = "poljoprivreda"
    OBRAZOVANJE = "obrazovanje"
    ZDRAVSTVO = "zdravstvo"
    INFRASTRUKTURA = "infrastruktura"
    KULTURA = "kultura"
    SPORT = "sport"
    SOCIJALNA_INKLUZIJA = "socijalna_inkluzija"
    ENERGETIKA = "energetika"
    TRANSPORT = "transport"
    OKOLIŠ = "okoliš"
    RURALNI_RAZVOJ = "ruralni_razvoj"

class EligibilityLevel(Enum):
    """Nivoi podobnosti"""
    VISOKA = "visoka"  # 80-100%
    SREDNJA = "srednja"  # 60-79%
    NISKA = "niska"  # 40-59%
    VRLO_NISKA = "vrlo_niska"  # 0-39%

@dataclass
class ProjectProfile:
    """Profil projekta za procjenu"""
    organization_type: OrganizationType
    organization_size: int  # broj zaposlenih
    annual_revenue: Optional[float]  # godišnji prihod u BAM
    location: str  # grad/općina
    entity: str  # FBiH, RS, BD
    project_category: ProjectCategory
    project_budget: float  # planiran budžet u BAM
    project_duration: int  # trajanje u mjesecima
    has_cofinancing: bool  # da li ima sufinansiranje
    cofinancing_percentage: float  # postotak sufinansiranja
    team_size: int  # broj članova tima
    has_experience: bool  # prethodno iskustvo s EU projektima
    innovation_level: int  # nivo inovativnosti (1-5)
    sustainability_score: int  # održivost (1-5)
    social_impact_score: int  # društveni uticaj (1-5)
    target_groups: List[str]  # ciljne grupe
    partnerships: List[str]  # partnerstva
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class EligibilityCriteria:
    """Kriteriji podobnosti za grant"""
    grant_id: str
    grant_name: str
    eligible_organizations: List[OrganizationType]
    eligible_locations: List[str]  # gradovi/regije
    eligible_entities: List[str]  # FBiH, RS, BD
    min_budget: Optional[float]
    max_budget: Optional[float]
    max_duration: Optional[int]
    required_cofinancing: Optional[float]
    eligible_categories: List[ProjectCategory]
    min_team_size: Optional[int]
    requires_experience: bool
    min_innovation_level: Optional[int]
    sustainability_required: bool
    social_impact_required: bool
    required_partnerships: List[str]
    age_restrictions: Optional[Tuple[int, int]]  # min, max godine
    deadline: datetime
    additional_criteria: Dict[str, Any] = field(default_factory=dict)

@dataclass
class EligibilityAssessment:
    """Rezultat procjene podobnosti"""
    project_profile: ProjectProfile
    grant_criteria: EligibilityCriteria
    overall_score: float  # 0-100
    eligibility_level: EligibilityLevel
    passed_criteria: List[str]
    failed_criteria: List[str]
    recommendations: List[str]
    risk_factors: List[str]
    improvement_suggestions: List[str]
    confidence_score: float  # pouzdanost procjene
    assessment_date: datetime = field(default_factory=datetime.now)

class FinAssistEligibilityEngine:
    """Glavni engine za procjenu podobnosti"""
    
    def __init__(self):
        self.criteria_database = self._initialize_criteria_database()
        self.scoring_weights = self._initialize_scoring_weights()
        self.location_mappings = self._initialize_location_mappings()
        
    def _initialize_criteria_database(self) -> Dict[str, EligibilityCriteria]:
        """Inicijalizuje bazu kriterija za različite grantove"""
        return {
            # IPA Fondovi
            "ipa_msp_konkurentnost": EligibilityCriteria(
                grant_id="ipa_msp_konkurentnost",
                grant_name="IPA - Jačanje konkurentnosti MSP",
                eligible_organizations=[OrganizationType.MSP, OrganizationType.STARTUP],
                eligible_locations=["sve_lokacije"],
                eligible_entities=["FBiH", "RS", "BD"],
                min_budget=10000.0,
                max_budget=200000.0,
                max_duration=24,
                required_cofinancing=15.0,
                eligible_categories=[
                    ProjectCategory.INOVACIJE, 
                    ProjectCategory.DIGITALIZACIJA,
                    ProjectCategory.ZELENA_EKONOMIJA
                ],
                min_team_size=2,
                requires_experience=False,
                min_innovation_level=3,
                sustainability_required=True,
                social_impact_required=False,
                required_partnerships=[],
                age_restrictions=None,
                deadline=datetime(2026, 6, 30)
            ),
            
            "ipa_ruralni_razvoj": EligibilityCriteria(
                grant_id="ipa_ruralni_razvoj",
                grant_name="IPA - Ruralni razvoj i poljoprivreda",
                eligible_organizations=[
                    OrganizationType.POLJOPRIVREDNIK, 
                    OrganizationType.MSP,
                    OrganizationType.GRAD_OPCINA
                ],
                eligible_locations=["ruralne_oblasti"],
                eligible_entities=["FBiH", "RS"],
                min_budget=5000.0,
                max_budget=150000.0,
                max_duration=36,
                required_cofinancing=20.0,
                eligible_categories=[
                    ProjectCategory.POLJOPRIVREDA,
                    ProjectCategory.RURALNI_RAZVOJ,
                    ProjectCategory.TURIZAM
                ],
                min_team_size=1,
                requires_experience=False,
                min_innovation_level=2,
                sustainability_required=True,
                social_impact_required=True,
                required_partnerships=[],
                age_restrictions=None,
                deadline=datetime(2026, 8, 15)
            ),
            
            "ipa_civilno_drustvo": EligibilityCriteria(
                grant_id="ipa_civilno_drustvo",
                grant_name="IPA - Jačanje civilnog društva",
                eligible_organizations=[OrganizationType.NGO],
                eligible_locations=["sve_lokacije"],
                eligible_entities=["FBiH", "RS", "BD"],
                min_budget=3000.0,
                max_budget=50000.0,
                max_duration=18,
                required_cofinancing=10.0,
                eligible_categories=[
                    ProjectCategory.SOCIJALNA_INKLUZIJA,
                    ProjectCategory.OBRAZOVANJE,
                    ProjectCategory.KULTURA
                ],
                min_team_size=3,
                requires_experience=True,
                min_innovation_level=2,
                sustainability_required=False,
                social_impact_required=True,
                required_partnerships=["lokalna_zajednica"],
                age_restrictions=None,
                deadline=datetime(2026, 5, 20)
            ),
            
            # Nacionalni grantovi FBiH
            "fbih_msp_subvencije": EligibilityCriteria(
                grant_id="fbih_msp_subvencije",
                grant_name="FBiH - Subvencije za MSP",
                eligible_organizations=[OrganizationType.MSP, OrganizationType.PREDUZETNIK],
                eligible_locations=["fbih_lokacije"],
                eligible_entities=["FBiH"],
                min_budget=2000.0,
                max_budget=100000.0,
                max_duration=12,
                required_cofinancing=25.0,
                eligible_categories=[
                    ProjectCategory.INOVACIJE,
                    ProjectCategory.DIGITALIZACIJA,
                    ProjectCategory.TURIZAM
                ],
                min_team_size=1,
                requires_experience=False,
                min_innovation_level=2,
                sustainability_required=False,
                social_impact_required=False,
                required_partnerships=[],
                age_restrictions=(18, 65),
                deadline=datetime(2026, 4, 30)
            ),
            
            # Nacionalni grantovi RS
            "rs_privreda_poticaji": EligibilityCriteria(
                grant_id="rs_privreda_poticaji",
                grant_name="RS - Poticaji za privredu",
                eligible_organizations=[OrganizationType.MSP, OrganizationType.STARTUP],
                eligible_locations=["rs_lokacije"],
                eligible_entities=["RS"],
                min_budget=5000.0,
                max_budget=80000.0,
                max_duration=18,
                required_cofinancing=20.0,
                eligible_categories=[
                    ProjectCategory.INOVACIJE,
                    ProjectCategory.ENERGETIKA,
                    ProjectCategory.TRANSPORT
                ],
                min_team_size=2,
                requires_experience=False,
                min_innovation_level=3,
                sustainability_required=True,
                social_impact_required=False,
                required_partnerships=[],
                age_restrictions=None,
                deadline=datetime(2026, 7, 15)
            ),
            
            # Kantonalni grantovi
            "ks_startup_fond": EligibilityCriteria(
                grant_id="ks_startup_fond",
                grant_name="Kanton Sarajevo - Startup fond",
                eligible_organizations=[OrganizationType.STARTUP, OrganizationType.MSP],
                eligible_locations=["sarajevo", "ilidža", "novi_grad", "centar", "novo_sarajevo"],
                eligible_entities=["FBiH"],
                min_budget=1000.0,
                max_budget=30000.0,
                max_duration=12,
                required_cofinancing=15.0,
                eligible_categories=[
                    ProjectCategory.INOVACIJE,
                    ProjectCategory.DIGITALIZACIJA
                ],
                min_team_size=2,
                requires_experience=False,
                min_innovation_level=4,
                sustainability_required=False,
                social_impact_required=False,
                required_partnerships=[],
                age_restrictions=(18, 35),
                deadline=datetime(2026, 3, 31)
            ),
            
            # Fondovi za okoliš
            "okoliš_fbih_energetika": EligibilityCriteria(
                grant_id="okoliš_fbih_energetika",
                grant_name="Fond za okoliš FBiH - Energetska efikasnost",
                eligible_organizations=[
                    OrganizationType.MSP,
                    OrganizationType.JAVNA_INSTITUCIJA,
                    OrganizationType.GRAD_OPCINA
                ],
                eligible_locations=["fbih_lokacije"],
                eligible_entities=["FBiH"],
                min_budget=15000.0,
                max_budget=500000.0,
                max_duration=24,
                required_cofinancing=30.0,
                eligible_categories=[
                    ProjectCategory.ENERGETIKA,
                    ProjectCategory.ZELENA_EKONOMIJA,
                    ProjectCategory.OKOLIŠ
                ],
                min_team_size=3,
                requires_experience=True,
                min_innovation_level=3,
                sustainability_required=True,
                social_impact_required=True,
                required_partnerships=["tehnički_partner"],
                age_restrictions=None,
                deadline=datetime(2026, 9, 30)
            )
        }
    
    def _initialize_scoring_weights(self) -> Dict[str, float]:
        """Inicijalizuje težine za scoring"""
        return {
            "organization_match": 0.20,
            "location_match": 0.15,
            "budget_fit": 0.15,
            "category_match": 0.15,
            "cofinancing_capability": 0.10,
            "team_adequacy": 0.08,
            "experience_level": 0.07,
            "innovation_score": 0.05,
            "sustainability_score": 0.03,
            "social_impact_score": 0.02
        }
    
    def _initialize_location_mappings(self) -> Dict[str, List[str]]:
        """Mapiranje lokacija"""
        return {
            "sve_lokacije": ["*"],
            "fbih_lokacije": [
                "sarajevo", "zenica", "tuzla", "mostar", "bihać", "cazin", "velika_kladuša",
                "livno", "tomislavgrad", "široki_brijeg", "čapljina", "trebinje", "goražde"
            ],
            "rs_lokacije": [
                "banja_luka", "prijedor", "doboj", "bijeljina", "zvornik", "srebrenica",
                "višegrad", "foča", "trebinje", "gacko", "nevesinje"
            ],
            "ruralne_oblasti": [
                "cazin", "velika_kladuša", "livno", "tomislavgrad", "gacko", "nevesinje",
                "višegrad", "foča", "srebrenica", "goražde"
            ]
        }
    
    def assess_eligibility(self, project_profile: ProjectProfile, 
                          grant_id: str) -> EligibilityAssessment:
        """Glavna funkcija za procjenu podobnosti"""
        
        if grant_id not in self.criteria_database:
            raise ValueError(f"Grant {grant_id} ne postoji u bazi")
        
        criteria = self.criteria_database[grant_id]
        
        # Provjeri osnovne kriterije
        basic_checks = self._check_basic_eligibility(project_profile, criteria)
        
        # Izračunaj detaljni score
        detailed_score = self._calculate_detailed_score(project_profile, criteria)
        
        # Kombiniraj rezultate
        overall_score = self._combine_scores(basic_checks, detailed_score)
        
        # Odredi nivo podobnosti
        eligibility_level = self._determine_eligibility_level(overall_score)
        
        # Generiraj preporuke
        recommendations = self._generate_recommendations(
            project_profile, criteria, basic_checks, detailed_score
        )
        
        # Identifikuj rizike
        risk_factors = self._identify_risk_factors(project_profile, criteria)
        
        # Predloži poboljšanja
        improvements = self._suggest_improvements(
            project_profile, criteria, basic_checks
        )
        
        # Izračunaj pouzdanost
        confidence = self._calculate_confidence(project_profile, criteria)
        
        return EligibilityAssessment(
            project_profile=project_profile,
            grant_criteria=criteria,
            overall_score=overall_score,
            eligibility_level=eligibility_level,
            passed_criteria=basic_checks["passed"],
            failed_criteria=basic_checks["failed"],
            recommendations=recommendations,
            risk_factors=risk_factors,
            improvement_suggestions=improvements,
            confidence_score=confidence
        )
    
    def _check_basic_eligibility(self, profile: ProjectProfile, 
                                criteria: EligibilityCriteria) -> Dict[str, List[str]]:
        """Provjera osnovnih kriterija podobnosti"""
        passed = []
        failed = []
        
        # Tip organizacije
        if profile.organization_type in criteria.eligible_organizations:
            passed.append("Tip organizacije odgovara")
        else:
            failed.append(f"Tip organizacije ({profile.organization_type.value}) nije podoban")
        
        # Lokacija
        location_match = self._check_location_eligibility(profile.location, criteria.eligible_locations)
        if location_match:
            passed.append("Lokacija odgovara")
        else:
            failed.append(f"Lokacija ({profile.location}) nije podobna")
        
        # Entitet
        if profile.entity in criteria.eligible_entities:
            passed.append("Entitet odgovara")
        else:
            failed.append(f"Entitet ({profile.entity}) nije podoban")
        
        # Budžet
        if criteria.min_budget and profile.project_budget < criteria.min_budget:
            failed.append(f"Budžet prenizak (min: {criteria.min_budget} BAM)")
        elif criteria.max_budget and profile.project_budget > criteria.max_budget:
            failed.append(f"Budžet previsok (max: {criteria.max_budget} BAM)")
        else:
            passed.append("Budžet odgovara")
        
        # Trajanje
        if criteria.max_duration and profile.project_duration > criteria.max_duration:
            failed.append(f"Trajanje predugo (max: {criteria.max_duration} mjeseci)")
        else:
            passed.append("Trajanje odgovara")
        
        # Sufinansiranje
        if criteria.required_cofinancing and profile.cofinancing_percentage < criteria.required_cofinancing:
            failed.append(f"Nedovoljno sufinansiranje (potrebno: {criteria.required_cofinancing}%)")
        else:
            passed.append("Sufinansiranje odgovara")
        
        # Kategorija projekta
        if profile.project_category in criteria.eligible_categories:
            passed.append("Kategorija projekta odgovara")
        else:
            failed.append(f"Kategorija ({profile.project_category.value}) nije podobna")
        
        # Veličina tima
        if criteria.min_team_size and profile.team_size < criteria.min_team_size:
            failed.append(f"Tim premali (min: {criteria.min_team_size} članova)")
        else:
            passed.append("Veličina tima odgovara")
        
        # Iskustvo
        if criteria.requires_experience and not profile.has_experience:
            failed.append("Potrebno je prethodno iskustvo s EU projektima")
        else:
            passed.append("Iskustvo odgovara")
        
        # Nivo inovativnosti
        if criteria.min_innovation_level and profile.innovation_level < criteria.min_innovation_level:
            failed.append(f"Nedovoljan nivo inovativnosti (min: {criteria.min_innovation_level})")
        else:
            passed.append("Nivo inovativnosti odgovara")
        
        # Održivost
        if criteria.sustainability_required and profile.sustainability_score < 3:
            failed.append("Potreban viši score održivosti")
        else:
            passed.append("Održivost odgovara")
        
        # Društveni uticaj
        if criteria.social_impact_required and profile.social_impact_score < 3:
            failed.append("Potreban viši score društvenog uticaja")
        else:
            passed.append("Društveni uticaj odgovara")
        
        # Deadline
        if datetime.now() > criteria.deadline:
            failed.append("Deadline je prošao")
        else:
            passed.append("Deadline nije prošao")
        
        return {"passed": passed, "failed": failed}
    
    def _check_location_eligibility(self, location: str, eligible_locations: List[str]) -> bool:
        """Provjera podobnosti lokacije"""
        if "sve_lokacije" in eligible_locations:
            return True
        
        for eligible_group in eligible_locations:
            if eligible_group in self.location_mappings:
                mapped_locations = self.location_mappings[eligible_group]
                if "*" in mapped_locations or location.lower() in [loc.lower() for loc in mapped_locations]:
                    return True
            elif location.lower() == eligible_group.lower():
                return True
        
        return False
    
    def _calculate_detailed_score(self, profile: ProjectProfile, 
                                 criteria: EligibilityCriteria) -> Dict[str, float]:
        """Detaljno izračunavanje score-a"""
        scores = {}
        
        # Organization match score
        if profile.organization_type in criteria.eligible_organizations:
            scores["organization_match"] = 100.0
        else:
            scores["organization_match"] = 0.0
        
        # Location match score
        if self._check_location_eligibility(profile.location, criteria.eligible_locations):
            scores["location_match"] = 100.0
        else:
            scores["location_match"] = 0.0
        
        # Budget fit score
        scores["budget_fit"] = self._calculate_budget_fit_score(profile, criteria)
        
        # Category match score
        if profile.project_category in criteria.eligible_categories:
            scores["category_match"] = 100.0
        else:
            scores["category_match"] = 0.0
        
        # Cofinancing capability score
        scores["cofinancing_capability"] = self._calculate_cofinancing_score(profile, criteria)
        
        # Team adequacy score
        scores["team_adequacy"] = self._calculate_team_score(profile, criteria)
        
        # Experience level score
        scores["experience_level"] = self._calculate_experience_score(profile, criteria)
        
        # Innovation score
        scores["innovation_score"] = (profile.innovation_level / 5.0) * 100.0
        
        # Sustainability score
        scores["sustainability_score"] = (profile.sustainability_score / 5.0) * 100.0
        
        # Social impact score
        scores["social_impact_score"] = (profile.social_impact_score / 5.0) * 100.0
        
        return scores
    
    def _calculate_budget_fit_score(self, profile: ProjectProfile, 
                                   criteria: EligibilityCriteria) -> float:
        """Izračunava score za budžet"""
        budget = profile.project_budget
        
        if criteria.min_budget and budget < criteria.min_budget:
            return 0.0
        
        if criteria.max_budget and budget > criteria.max_budget:
            return 0.0
        
        # Optimalan budžet je oko 70% maksimalnog
        if criteria.max_budget:
            optimal_budget = criteria.max_budget * 0.7
            if budget <= optimal_budget:
                return 100.0
            else:
                # Linearno smanjenje do max_budget
                return 100.0 - ((budget - optimal_budget) / (criteria.max_budget - optimal_budget)) * 30.0
        
        return 100.0
    
    def _calculate_cofinancing_score(self, profile: ProjectProfile, 
                                    criteria: EligibilityCriteria) -> float:
        """Izračunava score za sufinansiranje"""
        if not criteria.required_cofinancing:
            return 100.0
        
        if profile.cofinancing_percentage < criteria.required_cofinancing:
            return 0.0
        
        # Bonus za više sufinansiranje
        excess = profile.cofinancing_percentage - criteria.required_cofinancing
        bonus = min(excess * 2, 20)  # Max 20% bonus
        
        return min(100.0 + bonus, 100.0)
    
    def _calculate_team_score(self, profile: ProjectProfile, 
                             criteria: EligibilityCriteria) -> float:
        """Izračunava score za tim"""
        if criteria.min_team_size and profile.team_size < criteria.min_team_size:
            return 0.0
        
        # Optimalan tim je 2-3x veći od minimalnog
        if criteria.min_team_size:
            optimal_size = criteria.min_team_size * 2.5
            if profile.team_size <= optimal_size:
                return 100.0
            else:
                # Smanjenje za prevelike timove
                return max(70.0, 100.0 - (profile.team_size - optimal_size) * 5)
        
        return 100.0
    
    def _calculate_experience_score(self, profile: ProjectProfile, 
                                   criteria: EligibilityCriteria) -> float:
        """Izračunava score za iskustvo"""
        if criteria.requires_experience and not profile.has_experience:
            return 0.0
        
        if profile.has_experience:
            return 100.0
        else:
            return 80.0  # Može proći bez iskustva ako nije obavezno
    
    def _combine_scores(self, basic_checks: Dict[str, List[str]], 
                       detailed_scores: Dict[str, float]) -> float:
        """Kombinira osnovne provjere i detaljne score-ove"""
        
        # Ako ne prolazi osnovne kriterije, maksimalni score je 39%
        failed_count = len(basic_checks["failed"])
        if failed_count > 0:
            penalty = min(failed_count * 15, 60)  # Max 60% penalty
            max_possible_score = 100 - penalty
        else:
            max_possible_score = 100
        
        # Izračunaj weighted score
        weighted_score = 0.0
        for criterion, weight in self.scoring_weights.items():
            if criterion in detailed_scores:
                weighted_score += detailed_scores[criterion] * weight
        
        # Primijeni ograničenje
        final_score = min(weighted_score, max_possible_score)
        
        return round(final_score, 2)
    
    def _determine_eligibility_level(self, score: float) -> EligibilityLevel:
        """Određuje nivo podobnosti na osnovu score-a"""
        if score >= 80:
            return EligibilityLevel.VISOKA
        elif score >= 60:
            return EligibilityLevel.SREDNJA
        elif score >= 40:
            return EligibilityLevel.NISKA
        else:
            return EligibilityLevel.VRLO_NISKA
    
    def _generate_recommendations(self, profile: ProjectProfile, 
                                 criteria: EligibilityCriteria,
                                 basic_checks: Dict[str, List[str]], 
                                 detailed_scores: Dict[str, float]) -> List[str]:
        """Generiše preporuke za poboljšanje"""
        recommendations = []
        
        # Preporuke na osnovu neuspješnih kriterija
        for failed in basic_checks["failed"]:
            if "budžet prenizak" in failed.lower():
                recommendations.append("Povećajte planiran budžet projekta ili potražite dodatne izvore finansiranja")
            elif "budžet previsok" in failed.lower():
                recommendations.append("Smanjite opseg projekta ili podijelite ga u faze")
            elif "sufinansiranje" in failed.lower():
                recommendations.append("Osigurajte dodatne izvore sufinansiranja (vlastita sredstva, partneri, drugi grantovi)")
            elif "tim premali" in failed.lower():
                recommendations.append("Proširite projektni tim ili uključite dodatne partnere")
            elif "iskustvo" in failed.lower():
                recommendations.append("Uključite partnera s iskustvom u EU projektima ili angažirajte konsultanta")
            elif "inovativnost" in failed.lower():
                recommendations.append("Pojačajte inovativni aspekt projekta ili dodajte nove tehnologije")
        
        # Preporuke na osnovu score-ova
        if detailed_scores.get("innovation_score", 0) < 60:
            recommendations.append("Istaknite inovativne elemente vašeg projekta")
        
        if detailed_scores.get("sustainability_score", 0) < 60:
            recommendations.append("Razvijte plan održivosti projekta nakon završetka finansiranja")
        
        if detailed_scores.get("social_impact_score", 0) < 60:
            recommendations.append("Jasnije definirajte društveni uticaj i korist projekta")
        
        # Opće preporuke
        if len(basic_checks["failed"]) == 0:
            recommendations.append("Vaš projekt ispunjava osnovne kriterije - fokusirajte se na kvalitetu aplikacije")
        
        return recommendations
    
    def _identify_risk_factors(self, profile: ProjectProfile, 
                              criteria: EligibilityCriteria) -> List[str]:
        """Identifikuje faktore rizika"""
        risks = []
        
        # Vremenski rizik
        days_to_deadline = (criteria.deadline - datetime.now()).days
        if days_to_deadline < 30:
            risks.append(f"Kratak rok za prijavu ({days_to_deadline} dana)")
        
        # Budžetski rizik
        if criteria.max_budget and profile.project_budget > criteria.max_budget * 0.9:
            risks.append("Budžet blizu gornje granice - rizik od odbacivanja")
        
        # Rizik sufinansiranja
        if criteria.required_cofinancing and profile.cofinancing_percentage < criteria.required_cofinancing * 1.2:
            risks.append("Sufinansiranje blizu minimuma - rizik u slučaju promjene troškova")
        
        # Rizik iskustva
        if criteria.requires_experience and not profile.has_experience:
            risks.append("Nedostatak iskustva može utjecati na kvalitetu aplikacije")
        
        # Konkurencijski rizik
        if profile.project_category in [ProjectCategory.INOVACIJE, ProjectCategory.DIGITALIZACIJA]:
            risks.append("Visoka konkurencija u ovoj kategoriji")
        
        return risks
    
    def _suggest_improvements(self, profile: ProjectProfile, 
                             criteria: EligibilityCriteria,
                             basic_checks: Dict[str, List[str]]) -> List[str]:
        """Predlaže konkretna poboljšanja"""
        improvements = []
        
        # Poboljšanja za neuspješne kriterije
        for failed in basic_checks["failed"]:
            if "lokacija" in failed.lower():
                improvements.append("Razmislite o partnerstvu s organizacijom iz podobne lokacije")
            elif "tip organizacije" in failed.lower():
                improvements.append("Promijenite status organizacije ili formirajte konzorcij")
            elif "kategorija" in failed.lower():
                improvements.append("Prilagodite fokus projekta podobnim kategorijama")
        
        # Opća poboljšanja
        if profile.innovation_level < 4:
            improvements.append("Dodajte inovativne tehnologije ili pristupe")
        
        if profile.sustainability_score < 4:
            improvements.append("Razvijte detaljniji plan održivosti")
        
        if profile.social_impact_score < 3:
            improvements.append("Jasnije definirajte društvene koristi")
        
        if not profile.partnerships:
            improvements.append("Uspostavite partnerstva s relevantnim organizacijama")
        
        return improvements
    
    def _calculate_confidence(self, profile: ProjectProfile, 
                             criteria: EligibilityCriteria) -> float:
        """Izračunava pouzdanost procjene"""
        confidence_factors = []
        
        # Kompletnost podataka
        completeness = 0
        total_fields = 15
        
        if profile.annual_revenue is not None:
            completeness += 1
        if profile.location:
            completeness += 1
        if profile.project_budget > 0:
            completeness += 1
        if profile.project_duration > 0:
            completeness += 1
        if profile.cofinancing_percentage >= 0:
            completeness += 1
        if profile.team_size > 0:
            completeness += 1
        if profile.innovation_level > 0:
            completeness += 1
        if profile.sustainability_score > 0:
            completeness += 1
        if profile.social_impact_score > 0:
            completeness += 1
        if profile.target_groups:
            completeness += 1
        
        completeness += 5  # Osnovni podaci uvijek postoje
        
        data_completeness = (completeness / total_fields) * 100
        confidence_factors.append(data_completeness)
        
        # Jasnoća kriterija
        criteria_clarity = 85.0  # Pretpostavljamo dobru jasnoću
        confidence_factors.append(criteria_clarity)
        
        # Aktualnost podataka
        days_old = (datetime.now() - profile.created_at).days
        if days_old < 7:
            recency_score = 100.0
        elif days_old < 30:
            recency_score = 90.0
        elif days_old < 90:
            recency_score = 75.0
        else:
            recency_score = 60.0
        
        confidence_factors.append(recency_score)
        
        # Prosječna pouzdanost
        average_confidence = sum(confidence_factors) / len(confidence_factors)
        
        return round(average_confidence, 2)
    
    def batch_assess_eligibility(self, project_profile: ProjectProfile) -> List[EligibilityAssessment]:
        """Procjenjuje podobnost za sve dostupne grantove"""
        assessments = []
        
        for grant_id in self.criteria_database.keys():
            try:
                assessment = self.assess_eligibility(project_profile, grant_id)
                assessments.append(assessment)
            except Exception as e:
                logger.error(f"Greška pri procjeni za grant {grant_id}: {str(e)}")
        
        # Sortiraj po score-u
        assessments.sort(key=lambda x: x.overall_score, reverse=True)
        
        return assessments
    
    def get_best_matches(self, project_profile: ProjectProfile, 
                        limit: int = 5) -> List[EligibilityAssessment]:
        """Vraća najbolje poklapanja za projekt"""
        all_assessments = self.batch_assess_eligibility(project_profile)
        
        # Filtriraj samo one s visokom ili srednjom podobnosti
        good_matches = [
            assessment for assessment in all_assessments
            if assessment.eligibility_level in [EligibilityLevel.VISOKA, EligibilityLevel.SREDNJA]
        ]
        
        return good_matches[:limit]
    
    def generate_eligibility_report(self, project_profile: ProjectProfile) -> Dict[str, Any]:
        """Generiše detaljni izvještaj o podobnosti"""
        assessments = self.batch_assess_eligibility(project_profile)
        
        # Statistike
        total_grants = len(assessments)
        high_eligibility = len([a for a in assessments if a.eligibility_level == EligibilityLevel.VISOKA])
        medium_eligibility = len([a for a in assessments if a.eligibility_level == EligibilityLevel.SREDNJA])
        
        # Najbolji grantovi
        best_matches = assessments[:3]
        
        # Najčešći problemi
        all_failed_criteria = []
        for assessment in assessments:
            all_failed_criteria.extend(assessment.failed_criteria)
        
        common_issues = {}
        for issue in all_failed_criteria:
            common_issues[issue] = common_issues.get(issue, 0) + 1
        
        # Sortiraj po učestalosti
        sorted_issues = sorted(common_issues.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "project_summary": {
                "organization_type": project_profile.organization_type.value,
                "location": project_profile.location,
                "category": project_profile.project_category.value,
                "budget": project_profile.project_budget
            },
            "eligibility_statistics": {
                "total_grants_checked": total_grants,
                "high_eligibility_count": high_eligibility,
                "medium_eligibility_count": medium_eligibility,
                "success_rate": round((high_eligibility + medium_eligibility) / total_grants * 100, 2)
            },
            "best_matches": [
                {
                    "grant_name": assessment.grant_criteria.grant_name,
                    "score": assessment.overall_score,
                    "level": assessment.eligibility_level.value,
                    "deadline": assessment.grant_criteria.deadline.strftime("%d.%m.%Y")
                }
                for assessment in best_matches
            ],
            "common_issues": sorted_issues[:5],
            "overall_recommendations": self._generate_overall_recommendations(assessments),
            "generated_at": datetime.now().isoformat()
        }
    
    def _generate_overall_recommendations(self, assessments: List[EligibilityAssessment]) -> List[str]:
        """Generiše opće preporuke na osnovu svih procjena"""
        all_recommendations = []
        for assessment in assessments:
            all_recommendations.extend(assessment.recommendations)
        
        # Brojanje preporuka
        recommendation_counts = {}
        for rec in all_recommendations:
            recommendation_counts[rec] = recommendation_counts.get(rec, 0) + 1
        
        # Vrati najčešće preporuke
        sorted_recommendations = sorted(
            recommendation_counts.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        return [rec[0] for rec in sorted_recommendations[:5]]

# Primjer korištenja
def main():
    """Testiranje eligibility engine-a"""
    engine = FinAssistEligibilityEngine()
    
    # Kreiraj test profil
    test_profile = ProjectProfile(
        organization_type=OrganizationType.MSP,
        organization_size=15,
        annual_revenue=250000.0,
        location="sarajevo",
        entity="FBiH",
        project_category=ProjectCategory.DIGITALIZACIJA,
        project_budget=50000.0,
        project_duration=18,
        has_cofinancing=True,
        cofinancing_percentage=20.0,
        team_size=4,
        has_experience=False,
        innovation_level=4,
        sustainability_score=3,
        social_impact_score=4,
        target_groups=["MSP", "startups"],
        partnerships=["tehnološki_partner"]
    )
    
    # Procijeni podobnost za specifičan grant
    assessment = engine.assess_eligibility(test_profile, "ipa_msp_konkurentnost")
    
    print(f"Grant: {assessment.grant_criteria.grant_name}")
    print(f"Score: {assessment.overall_score}%")
    print(f"Nivo: {assessment.eligibility_level.value}")
    print(f"Prošli kriteriji: {len(assessment.passed_criteria)}")
    print(f"Neuspješni kriteriji: {len(assessment.failed_criteria)}")
    
    # Pronađi najbolja poklapanja
    best_matches = engine.get_best_matches(test_profile, 3)
    print(f"\nNajbolja poklapanja:")
    for match in best_matches:
        print(f"- {match.grant_criteria.grant_name}: {match.overall_score}%")
    
    # Generiši izvještaj
    report = engine.generate_eligibility_report(test_profile)
    print(f"\nIzvještaj: {report['eligibility_statistics']}")

if __name__ == "__main__":
    main()
