FinAssist BH - Subscription Management System
Sistem za upravljanje pretplatama i korisničkim planovima
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

class SubscriptionTier(Enum):
    """Tipovi pretplata"""
    BASIC = "basic"
    STANDARD = "standard"
    PREMIUM = "premium"

class PaymentStatus(Enum):
    """Status plaćanja"""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"

class NotificationType(Enum):
    """Tipovi notifikacija"""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"

@dataclass
class SubscriptionPlan:
    """Definicija plana pretplate"""
    tier: SubscriptionTier
    name_bs: str
    name_en: str
    price_bam: Decimal
    price_eur: Decimal
    duration_days: int
    features: Dict[str, any]
    limits: Dict[str, int]
    description_bs: str
    description_en: str
    is_active: bool = True
    
    def __post_init__(self):
        """Validacija nakon inicijalizacije"""
        if self.price_bam < 0 or self.price_eur < 0:
            raise ValueError("Cijena ne može biti negativna")
        if self.duration_days <= 0:
            raise ValueError("Trajanje mora biti pozitivno")

@dataclass
class User:
    """Korisnik sistema"""
    user_id: str
    email: str
    first_name: str
    last_name: str
    phone: Optional[str] = None
    organization: Optional[str] = None
    organization_type: Optional[str] = None  # MSP, NGO, Javna institucija, itd.
    location: Optional[str] = None  # Grad/općina
    preferred_language: str = "bs"
    notification_preferences: List[NotificationType] = field(default_factory=lambda: [NotificationType.EMAIL])
    created_at: datetime = field(default_factory=datetime.now)
    last_login: Optional[datetime] = None
    is_active: bool = True
    
    def __post_init__(self):
        if not self.user_id:
            self.user_id = str(uuid.uuid4())

@dataclass
class Subscription:
    """Aktivna pretplata korisnika"""
    subscription_id: str
    user_id: str
    plan: SubscriptionPlan
    start_date: datetime
    end_date: datetime
    is_active: bool = True
    auto_renew: bool = False
    usage_stats: Dict[str, int] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if not self.subscription_id:
            self.subscription_id = str(uuid.uuid4())
        
        # Inicijaliziraj usage stats
        if not self.usage_stats:
            self.usage_stats = {
                'grants_viewed': 0,
                'assessments_done': 0,
                'reports_generated': 0,
                'consultations_used': 0
            }
    
    @property
    def days_remaining(self) -> int:
        """Broj dana do isteka"""
        if not self.is_active:
            return 0
        remaining = (self.end_date - datetime.now()).days
        return max(0, remaining)
    
    @property
    def is_expired(self) -> bool:
        """Da li je pretplata istekla"""
        return datetime.now() > self.end_date
    
    def can_use_feature(self, feature: str, current_usage: int = None) -> bool:
        """Provjera da li korisnik može koristiti feature"""
        if not self.is_active or self.is_expired:
            return False
        
        if feature not in self.plan.limits:
            return True
        
        limit = self.plan.limits[feature]
        if limit == -1:  # Unlimited
            return True
        
        if current_usage is None:
            current_usage = self.usage_stats.get(feature, 0)
        
        return current_usage < limit

@dataclass
class Payment:
    """Zapis o plaćanju"""
    payment_id: str
    user_id: str
    subscription_id: str
    amount_bam: Decimal
    amount_eur: Decimal
    currency: str
    payment_method: str
    status: PaymentStatus
    transaction_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    processed_at: Optional[datetime] = None
    
    def __post_init__(self):
        if not self.payment_id:
            self.payment_id = str(uuid.uuid4())

class FinAssistSubscriptionManager:
    """Glavni sistem za upravljanje pretplatama"""
    
    def __init__(self):
        self.plans = self._initialize_plans()
        self.users: Dict[str, User] = {}
        self.subscriptions: Dict[str, Subscription] = {}
        self.payments: Dict[str, Payment] = {}
        
    def _initialize_plans(self) -> Dict[SubscriptionTier, SubscriptionPlan]:
        """Inicijalizuje planove pretplata"""
        return {
            SubscriptionTier.BASIC: SubscriptionPlan(
                tier=SubscriptionTier.BASIC,
                name_bs="BASIC (besplatno)",
                name_en="BASIC (free)",
                price_bam=Decimal('0.00'),
                price_eur=Decimal('0.00'),
                duration_days=30,
                features={
                    'grant_browsing': True,
                    'basic_assessment': True,
                    'email_notifications': True,
                    'basic_support': True
                },
                limits={
                    'grants_viewed': 3,  # 3 natječaja mjesečno
                    'assessments_done': 1,  # 1 osnovna procjena
                    'reports_generated': 0,  # Nema izvještaja
                    'consultations_used': 0  # Nema konzultacija
                },
                description_bs="Pregled 3 natječaja mjesečno, osnovna procjena projekta",
                description_en="View 3 tenders monthly, basic project assessment"
            ),
            
            SubscriptionTier.STANDARD: SubscriptionPlan(
                tier=SubscriptionTier.STANDARD,
                name_bs="STANDARD",
                name_en="STANDARD",
                price_bam=Decimal('9.99'),
                price_eur=Decimal('5.10'),
                duration_days=30,
                features={
                    'grant_browsing': True,
                    'advanced_assessment': True,
                    'document_preparation': True,
                    'monthly_reports': True,
                    'email_notifications': True,
                    'sms_notifications': True,
                    'priority_support': True
                },
                limits={
                    'grants_viewed': -1,  # Unlimited
                    'assessments_done': 10,  # 10 procjena mjesečno
                    'reports_generated': 1,  # 1 mjesečni izvještaj
                    'consultations_used': 0  # Nema konzultacija
                },
                description_bs="Pregled svih natječaja, temeljna projektna priprema, mjesečni izvještaj",
                description_en="View all tenders, basic project preparation, monthly report"
            ),
            
            SubscriptionTier.PREMIUM: SubscriptionPlan(
                tier=SubscriptionTier.PREMIUM,
                name_bs="PREMIUM",
                name_en="PREMIUM",
                price_bam=Decimal('29.99'),
                price_eur=Decimal('15.30'),
                duration_days=30,
                features={
                    'grant_browsing': True,
                    'advanced_assessment': True,
                    'document_preparation': True,
                    'document_assistance': True,
                    'expert_consultations': True,
                    'custom_reports': True,
                    'priority_notifications': True,
                    'dedicated_support': True,
                    'api_access': True
                },
                limits={
                    'grants_viewed': -1,  # Unlimited
                    'assessments_done': -1,  # Unlimited
                    'reports_generated': -1,  # Unlimited
                    'consultations_used': 3  # 3 konzultacije mjesečno
                },
                description_bs="Kompletnija analiza, pomoć oko dokumentacije, konzultacije s ekspertima",
                description_en="Complete analysis, documentation help, expert consultations"
            )
        }
    
    def create_user(self, email: str, first_name: str, last_name: str, **kwargs) -> User:
        """Kreira novog korisnika"""
        # Provjeri da li korisnik već postoji
        existing_user = self.get_user_by_email(email)
        if existing_user:
            raise ValueError(f"Korisnik s email adresom {email} već postoji")
        
        user = User(
            user_id=str(uuid.uuid4()),
            email=email,
            first_name=first_name,
            last_name=last_name,
            **kwargs
        )
        
        self.users[user.user_id] = user
        
        # Automatski kreiraj BASIC pretplatu
        self.create_subscription(user.user_id, SubscriptionTier.BASIC)
        
        logger.info(f"Kreiran novi korisnik: {email}")
        return user
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Pronađi korisnika po email adresi"""
        for user in self.users.values():
            if user.email.lower() == email.lower():
                return user
        return None
    
    def get_user(self, user_id: str) -> Optional[User]:
        """Pronađi korisnika po ID"""
        return self.users.get(user_id)
    
    def create_subscription(self, user_id: str, tier: SubscriptionTier, 
                          auto_renew: bool = False) -> Subscription:
        """Kreira novu pretplatu"""
        user = self.get_user(user_id)
        if not user:
            raise ValueError(f"Korisnik {user_id} ne postoji")
        
        plan = self.plans[tier]
        start_date = datetime.now()
        end_date = start_date + timedelta(days=plan.duration_days)
        
        # Deaktiviraj postojeće pretplate
        self._deactivate_user_subscriptions(user_id)
        
        subscription = Subscription(
            subscription_id=str(uuid.uuid4()),
            user_id=user_id,
            plan=plan,
            start_date=start_date,
            end_date=end_date,
            auto_renew=auto_renew
        )
        
        self.subscriptions[subscription.subscription_id] = subscription
        
        logger.info(f"Kreirana pretplata {tier.value} za korisnika {user_id}")
        return subscription
    
    def _deactivate_user_subscriptions(self, user_id: str):
        """Deaktivira sve postojeće pretplate korisnika"""
        for subscription in self.subscriptions.values():
            if subscription.user_id == user_id and subscription.is_active:
                subscription.is_active = False
    
    def get_active_subscription(self, user_id: str) -> Optional[Subscription]:
        """Vraća aktivnu pretplatu korisnika"""
        for subscription in self.subscriptions.values():
            if (subscription.user_id == user_id and 
                subscription.is_active and 
                not subscription.is_expired):
                return subscription
        return None
    
    def upgrade_subscription(self, user_id: str, new_tier: SubscriptionTier) -> Subscription:
        """Upgrade pretplate"""
        current_subscription = self.get_active_subscription(user_id)
        if not current_subscription:
            return self.create_subscription(user_id, new_tier)
        
        if current_subscription.plan.tier == new_tier:
            raise ValueError("Korisnik već ima ovu pretplatu")
        
        # Kreiraj novu pretplatu
        new_subscription = self.create_subscription(user_id, new_tier)
        
        # Prebaci usage stats
        new_subscription.usage_stats = current_subscription.usage_stats.copy()
        
        logger.info(f"Upgrade pretplate za korisnika {user_id} na {new_tier.value}")
        return new_subscription
    
    def process_payment(self, user_id: str, tier: SubscriptionTier, 
                       currency: str = "BAM", payment_method: str = "card") -> Payment:
        """Obrađuje plaćanje"""
        plan = self.plans[tier]
        amount = plan.price_bam if currency == "BAM" else plan.price_eur
        
        if amount == 0:
            # Besplatna pretplata
            subscription = self.create_subscription(user_id, tier)
            return None
        
        # Kreiraj payment zapis
        payment = Payment(
            payment_id=str(uuid.uuid4()),
            user_id=user_id,
            subscription_id="",  # Će biti ažurirano nakon kreiranja pretplate
            amount_bam=plan.price_bam,
            amount_eur=plan.price_eur,
            currency=currency,
            payment_method=payment_method,
            status=PaymentStatus.PENDING
        )
        
        # Simulacija plaćanja (u stvarnosti bi se pozivao payment gateway)
        success = self._simulate_payment_processing(payment)
        
        if success:
            payment.status = PaymentStatus.COMPLETED
            payment.processed_at = datetime.now()
            
            # Kreiraj pretplatu
            subscription = self.create_subscription(user_id, tier)
            payment.subscription_id = subscription.subscription_id
            
            logger.info(f"Uspješno plaćanje {payment.payment_id} za korisnika {user_id}")
        else:
            payment.status = PaymentStatus.FAILED
            logger.warning(f"Neuspješno plaćanje {payment.payment_id} za korisnika {user_id}")
        
        self.payments[payment.payment_id] = payment
        return payment
    
    def _simulate_payment_processing(self, payment: Payment) -> bool:
        """Simulira obradu plaćanja (za testiranje)"""
        # U stvarnosti bi se pozivao pravi payment gateway
        import random
        return random.random() > 0.1  # 90% success rate
    
    def record_usage(self, user_id: str, feature: str, amount: int = 1):
        """Bilježi korištenje feature-a"""
        subscription = self.get_active_subscription(user_id)
        if not subscription:
            raise ValueError("Korisnik nema aktivnu pretplatu")
        
        if feature in subscription.usage_stats:
            subscription.usage_stats[feature] += amount
        else:
            subscription.usage_stats[feature] = amount
        
        logger.debug(f"Zabilježeno korištenje {feature} za korisnika {user_id}")
    
    def can_user_access_feature(self, user_id: str, feature: str) -> Tuple[bool, str]:
        """Provjera da li korisnik može pristupiti feature-u"""
        subscription = self.get_active_subscription(user_id)
        
        if not subscription:
            return False, "Nema aktivne pretplate"
        
        if subscription.is_expired:
            return False, "Pretplata je istekla"
        
        # Provjeri da li plan podržava feature
        if feature not in subscription.plan.features or not subscription.plan.features[feature]:
            return False, f"Feature {feature} nije dostupan u vašem planu"
        
        # Provjeri limite
        if not subscription.can_use_feature(feature):
            limit = subscription.plan.limits.get(feature, 0)
            current = subscription.usage_stats.get(feature, 0)
            return False, f"Dosegnuli ste limit ({current}/{limit}) za {feature}"
        
        return True, "OK"
    
    def get_subscription_stats(self, user_id: str) -> Dict:
        """Vraća statistike pretplate"""
        subscription = self.get_active_subscription(user_id)
        if not subscription:
            return {"error": "Nema aktivne pretplate"}
        
        stats = {
            "plan": subscription.plan.name_bs,
            "tier": subscription.plan.tier.value,
            "days_remaining": subscription.days_remaining,
            "is_expired": subscription.is_expired,
            "usage": subscription.usage_stats,
            "limits": subscription.plan.limits,
            "features": subscription.plan.features
        }
        
        # Dodaj usage percentage
        usage_percentage = {}
        for feature, limit in subscription.plan.limits.items():
            if limit > 0:
                current = subscription.usage_stats.get(feature, 0)
                usage_percentage[feature] = (current / limit) * 100
            else:
                usage_percentage[feature] = 0
        
        stats["usage_percentage"] = usage_percentage
        return stats
    
    def get_expiring_subscriptions(self, days: int = 7) -> List[Subscription]:
        """Vraća pretplate koje ističu uskoro"""
        cutoff_date = datetime.now() + timedelta(days=days)
        expiring = []
        
        for subscription in self.subscriptions.values():
            if (subscription.is_active and 
                subscription.end_date <= cutoff_date and
                not subscription.is_expired):
                expiring.append(subscription)
        
        return expiring
    
    def auto_renew_subscriptions(self) -> List[str]:
        """Automatski obnovi pretplate koje su označene za auto-renewal"""
        renewed = []
        
        for subscription in self.subscriptions.values():
            if (subscription.auto_renew and 
                subscription.is_expired and 
                subscription.is_active):
                
                try:
                    # Pokušaj obnovu
                    payment = self.process_payment(
                        subscription.user_id, 
                        subscription.plan.tier
                    )
                    
                    if payment and payment.status == PaymentStatus.COMPLETED:
                        renewed.append(subscription.user_id)
                        logger.info(f"Auto-renewed subscription for user {subscription.user_id}")
                    
                except Exception as e:
                    logger.error(f"Failed to auto-renew subscription for user {subscription.user_id}: {str(e)}")
        
        return renewed
    
    def generate_invoice(self, payment_id: str) -> Dict:
        """Generiše račun za plaćanje"""
        payment = self.payments.get(payment_id)
        if not payment:
            raise ValueError("Plaćanje ne postoji")
        
        user = self.get_user(payment.user_id)
        subscription = self.subscriptions.get(payment.subscription_id)
        
        invoice = {
            "invoice_id": f"INV-{payment.payment_id[:8]}",
            "date": payment.created_at.strftime("%d.%m.%Y"),
            "user": {
                "name": f"{user.first_name} {user.last_name}",
                "email": user.email,
                "organization": user.organization
            },
            "items": [{
                "description": subscription.plan.name_bs if subscription else "FinAssist BH Pretplata",
                "amount": float(payment.amount_bam if payment.currency == "BAM" else payment.amount_eur),
                "currency": payment.currency
            }],
            "total": float(payment.amount_bam if payment.currency == "BAM" else payment.amount_eur),
            "currency": payment.currency,
            "status": payment.status.value
        }
        
        return invoice
    
    def export_user_data(self, user_id: str) -> Dict:
        """Izvozi sve podatke korisnika (GDPR compliance)"""
        user = self.get_user(user_id)
        if not user:
            raise ValueError("Korisnik ne postoji")
        
        user_subscriptions = [
            sub for sub in self.subscriptions.values() 
            if sub.user_id == user_id
        ]
        
        user_payments = [
            payment for payment in self.payments.values() 
            if payment.user_id == user_id
        ]
        
        return {
            "user": {
                "user_id": user.user_id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "phone": user.phone,
                "organization": user.organization,
                "organization_type": user.organization_type,
                "location": user.location,
                "preferred_language": user.preferred_language,
                "created_at": user.created_at.isoformat(),
                "last_login": user.last_login.isoformat() if user.last_login else None
            },
            "subscriptions": [
                {
                    "subscription_id": sub.subscription_id,
                    "plan": sub.plan.name_bs,
                    "start_date": sub.start_date.isoformat(),
                    "end_date": sub.end_date.isoformat(),
                    "is_active": sub.is_active,
                    "usage_stats": sub.usage_stats
                }
                for sub in user_subscriptions
            ],
            "payments": [
                {
                    "payment_id": payment.payment_id,
                    "amount": float(payment.amount_bam),
                    "currency": payment.currency,
                    "status": payment.status.value,
                    "created_at": payment.created_at.isoformat()
                }
                for payment in user_payments
            ]
        }
    
    def get_analytics(self) -> Dict:
        """Vraća analitiku pretplata"""
        total_users = len(self.users)
        active_subscriptions = len([
            sub for sub in self.subscriptions.values() 
            if sub.is_active and not sub.is_expired
        ])
        
        # Distribucija po planovima
        plan_distribution = {}
        for subscription in self.subscriptions.values():
            if subscription.is_active and not subscription.is_expired:
                tier = subscription.plan.tier.value
                plan_distribution[tier] = plan_distribution.get(tier, 0) + 1
        
        # Prihodi
        monthly_revenue = sum(
            payment.amount_bam for payment in self.payments.values()
            if (payment.status == PaymentStatus.COMPLETED and 
                payment.created_at >= datetime.now() - timedelta(days=30))
        )
        
        # Conversion rate
        paid_subscriptions = len([
            sub for sub in self.subscriptions.values()
            if (sub.is_active and not sub.is_expired and 
                sub.plan.tier != SubscriptionTier.BASIC)
        ])
        
        conversion_rate = (paid_subscriptions / total_users * 100) if total_users > 0 else 0
        
        return {
            "total_users": total_users,
            "active_subscriptions": active_subscriptions,
            "plan_distribution": plan_distribution,
            "monthly_revenue_bam": float(monthly_revenue),
            "conversion_rate": round(conversion_rate, 2),
            "churn_rate": self._calculate_churn_rate(),
            "average_revenue_per_user": float(monthly_revenue / total_users) if total_users > 0 else 0
        }
    
    def _calculate_churn_rate(self) -> float:
        """Računa churn rate"""
        # Jednostavna implementacija - korisnici koji su imali pretplatu ali je sada neaktivna
        churned_users = set()
        active_users = set()
        
        for subscription in self.subscriptions.values():
            if subscription.plan.tier != SubscriptionTier.BASIC:
                if subscription.is_expired and not subscription.is_active:
                    churned_users.add(subscription.user_id)
                elif subscription.is_active and not subscription.is_expired:
                    active_users.add(subscription.user_id)
        
        total_paid_users = len(churned_users | active_users)
        return (len(churned_users) / total_paid_users * 100) if total_paid_users > 0 else 0

# Primjer korištenja
def main():
    """Testiranje subscription managera"""
    manager = FinAssistSubscriptionManager()
    
    # Kreiraj korisnika
    user = manager.create_user(
        email="test@example.com",
        first_name="Marko",
        last_name="Marković",
        organization="Test d.o.o.",
        organization_type="MSP",
        location="Sarajevo"
    )
    
    print(f"Kreiran korisnik: {user.email}")
    
    # Provjeri početnu pretplatu
    subscription = manager.get_active_subscription(user.user_id)
    print(f"Početna pretplata: {subscription.plan.name_bs}")
    
    # Upgrade na STANDARD
    payment = manager.process_payment(user.user_id, SubscriptionTier.STANDARD)
    if payment and payment.status == PaymentStatus.COMPLETED:
        print("Uspješno plaćanje za STANDARD plan")
    
    # Provjeri statistike
    stats = manager.get_subscription_stats(user.user_id)
    print(f"Statistike pretplate: {stats}")
    
    # Simuliraj korištenje
    can_access, message = manager.can_user_access_feature(user.user_id, "grants_viewed")
    if can_access:
        manager.record_usage(user.user_id, "grants_viewed", 5)
        print("Zabilježeno korištenje grantova")
    
    # Analitika
    analytics = manager.get_analytics()
    print(f"Analitika: {analytics}")

if __name__ == "__main__":
    main()
