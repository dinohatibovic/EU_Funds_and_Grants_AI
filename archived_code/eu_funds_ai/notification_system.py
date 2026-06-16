FinAssist BH - Automated Notification System
Sistem za automatske notifikacije o grantovima, deadlinovima i statusima
"""

import asyncio
import smtplib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import json
import logging
import aiohttp
from jinja2 import Template

logger = logging.getLogger(__name__)

class NotificationPriority(Enum):
    """Prioriteti notifikacija"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class NotificationChannel(Enum):
    """Kanali za slanje notifikacija"""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"
    WEBHOOK = "webhook"

class NotificationTemplate(Enum):
    """Tipovi template-a za notifikacije"""
    NEW_GRANT = "new_grant"
    DEADLINE_REMINDER = "deadline_reminder"
    ELIGIBILITY_MATCH = "eligibility_match"
    SUBSCRIPTION_EXPIRY = "subscription_expiry"
    PAYMENT_CONFIRMATION = "payment_confirmation"
    ASSESSMENT_COMPLETE = "assessment_complete"
    WEEKLY_DIGEST = "weekly_digest"
    MONTHLY_REPORT = "monthly_report"

@dataclass
class NotificationPreferences:
    """Korisničke preference za notifikacije"""
    user_id: str
    email_enabled: bool = True
    sms_enabled: bool = False
    push_enabled: bool = True
    in_app_enabled: bool = True
    
    # Specifične preference
    new_grants: bool = True
    deadline_reminders: bool = True
    eligibility_matches: bool = True
    subscription_updates: bool = True
    weekly_digest: bool = True
    monthly_report: bool = False
    
    # Timing preference
    preferred_time: str = "09:00"  # HH:MM format
    timezone: str = "Europe/Sarajevo"
    
    # Frequency settings
    digest_frequency: str = "weekly"  # daily, weekly, monthly
    reminder_days: List[int] = field(default_factory=lambda: [7, 3, 1])  # Dani prije deadline-a

@dataclass
class NotificationContent:
    """Sadržaj notifikacije"""
    template_type: NotificationTemplate
    subject: str
    title: str
    message: str
    html_content: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    attachments: List[str] = field(default_factory=list)
    action_buttons: List[Dict[str, str]] = field(default_factory=list)

@dataclass
class Notification:
    """Notifikacija za slanje"""
    notification_id: str
    user_id: str
    channel: NotificationChannel
    priority: NotificationPriority
    content: NotificationContent
    scheduled_time: Optional[datetime] = None
    sent_time: Optional[datetime] = None
    is_sent: bool = False
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if not self.notification_id:
            import uuid
            self.notification_id = str(uuid.uuid4())

class FinAssistNotificationSystem:
    """Glavni sistem za notifikacije"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.preferences: Dict[str, NotificationPreferences] = {}
        self.pending_notifications: List[Notification] = []
        self.sent_notifications: List[Notification] = []
        self.templates = self._initialize_templates()
        
        # Email konfiguracija
        self.smtp_server = config.get('smtp_server', 'smtp.gmail.com')
        self.smtp_port = config.get('smtp_port', 587)
        self.smtp_username = config.get('smtp_username')
        self.smtp_password = config.get('smtp_password')
        self.from_email = config.get('from_email', 'noreply@finassist.ba')
        
        # SMS konfiguracija (Twilio ili slično)
        self.sms_api_key = config.get('sms_api_key')
        self.sms_api_secret = config.get('sms_api_secret')
        
        # Push notifikacije (Firebase ili slično)
        self.push_api_key = config.get('push_api_key')
        
    def _initialize_templates(self) -> Dict[NotificationTemplate, Dict[str, str]]:
        """Inicijalizuje template-e za notifikacije"""
        return {
            NotificationTemplate.NEW_GRANT: {
                'subject_bs': 'Novi grant dostupan: {{grant_name}}',
                'subject_en': 'New grant available: {{grant_name}}',
                'title_bs': 'Novi Grant Dostupan',
                'title_en': 'New Grant Available',
                'message_bs': '''
Poštovani {{user_name}},

Dostupan je novi grant koji odgovara vašem profilu:

📋 **{{grant_name}}**
💰 Budžet: {{grant_budget}}
📅 Deadline: {{grant_deadline}}
🎯 Kategorija: {{grant_category}}
⭐ Podobnost: {{eligibility_score}}%

{{grant_description}}

**Sljedeći koraci:**
1. Pregledajte detaljne kriterije
2. Pripremite potrebnu dokumentaciju
3. Pošaljite aplikaciju prije deadline-a

[Pogledaj Grant]({{grant_url}}) | [Procijeni Podobnost]({{assessment_url}})

Srdačan pozdrav,
FinAssist BH Tim
                ''',
                'html_template': '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0; padding: 0; }
        .header { background: #2563eb; color: white; padding: 0; text-align: center; }
        .content { padding: 0; background: #f8f9fa; }
        .grant-info { background: white; padding: 0; border-radius: 8px; margin: 0; }
        .button { display: inline-block; padding: 0; background: #2563eb; color: white; text-decoration: none; border-radius: 6px; margin: 0; }
        .footer { text-align: center; padding: 0; color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 Novi Grant Dostupan</h1>
        </div>
        <div class="content">
            <p>Poštovani {{user_name}},</p>
            <p>Dostupan je novi grant koji odgovara vašem profilu:</p>
            
            <div class="grant-info">
                <h3>📋 {{grant_name}}</h3>
                <p><strong>💰 Budžet:</strong> {{grant_budget}}</p>
                <p><strong>📅 Deadline:</strong> {{grant_deadline}}</p>
                <p><strong>🎯 Kategorija:</strong> {{grant_category}}</p>
                <p><strong>⭐ Podobnost:</strong> {{eligibility_score}}%</p>
                <p>{{grant_description}}</p>
            </div>
            
            <h4>Sljedeći koraci:</h4>
            <ol>
                <li>Pregledajte detaljne kriterije</li>
                <li>Pripremite potrebnu dokumentaciju</li>
                <li>Pošaljite aplikaciju prije deadline-a</li>
            </ol>
            
            <div style="text-align: center; margin: 0;">
                <a href="{{grant_url}}" class="button">Pogledaj Grant</a>
                <a href="{{assessment_url}}" class="button">Procijeni Podobnost</a>
            </div>
        </div>
        <div class="footer">
            <p>FinAssist BH - Vaš ključ do EU i nacionalnih grantova</p>
        </div>
    </div>
</body>
</html>
                '''
            },
            
            NotificationTemplate.DEADLINE_REMINDER: {
                'subject_bs': '⏰ Podsjetnik: {{grant_name}} ističe za {{days_left}} dana',
                'subject_en': '⏰ Reminder: {{grant_name}} expires in {{days_left}} days',
                'title_bs': 'Podsjetnik o Deadline-u',
                'title_en': 'Deadline Reminder',
                'message_bs': '''
Poštovani {{user_name}},

Podsjetnik da grant "{{grant_name}}" ističe za {{days_left}} dana.

📅 **Deadline: {{grant_deadline}}**
⏰ **Preostalo vrijeme: {{days_left}} dana**

{% if days_left <= 3 %}
🚨 **HITNO**: Vrlo malo vremena ostalo!
{% endif %}

**Potrebne akcije:**
- Finalizirajte aplikaciju
- Provjerite svu dokumentaciju
- Pošaljite prije deadline-a

[Nastavi s Aplikacijom]({{application_url}})

Srdačan pozdrav,
FinAssist BH Tim
                ''',
                'html_template': '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0; padding: 0; }
        .header { background: #f59e0b; color: white; padding: 0; text-align: center; }
        .content { padding: 0; background: #f8f9fa; }
        .urgent { background: #fee2e2; border: 2px solid #ef4444; padding: 0; border-radius: 8px; margin: 0; }
        .warning { background: #fef3c7; border: 2px solid #f59e0b; padding: 0; border-radius: 8px; margin: 0; }
        .button { display: inline-block; padding: 0; background: #f59e0b; color: white; text-decoration: none; border-radius: 6px; margin: 0; }
        .footer { text-align: center; padding: 0; color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⏰ Podsjetnik o Deadline-u</h1>
        </div>
        <div class="content">
            <p>Poštovani {{user_name}},</p>
            
            {% if days_left <= 3 %}
            <div class="urgent">
                <h3>🚨 HITNO: Vrlo malo vremena ostalo!</h3>
                <p>Grant "{{grant_name}}" ističe za samo {{days_left}} dana.</p>
            </div>
            {% else %}
            <div class="warning">
                <p>Grant "{{grant_name}}" ističe za {{days_left}} dana.</p>
            </div>
            {% endif %}
            
            <p><strong>📅 Deadline:</strong> {{grant_deadline}}</p>
            <p><strong>⏰ Preostalo vrijeme:</strong> {{days_left}} dana</p>
            
            <h4>Potrebne akcije:</h4>
            <ul>
                <li>Finalizirajte aplikaciju</li>
                <li>Provjerite svu dokumentaciju</li>
                <li>Pošaljite prije deadline-a</li>
            </ul>
            
            <div style="text-align: center; margin: 0;">
                <a href="{{application_url}}" class="button">Nastavi s Aplikacijom</a>
            </div>
        </div>
        <div class="footer">
            <p>FinAssist BH - Vaš ključ do EU i nacionalnih grantova</p>
        </div>
    </div>
</body>
</html>
                '''
            },
            
            NotificationTemplate.ELIGIBILITY_MATCH: {
                'subject_bs': '🎯 Pronašli smo savršen grant za vas!',
                'subject_en': '🎯 We found a perfect grant for you!',
                'title_bs': 'Savršeno Poklapanje',
                'title_en': 'Perfect Match',
                'message_bs': '''
Poštovani {{user_name}},

Odličan je vijest! Pronašli smo grant koji se savršeno uklapa s vašim profilom:

🎯 **{{grant_name}}**
⭐ **Podobnost: {{eligibility_score}}%**
💰 **Budžet: {{grant_budget}}**
📅 **Deadline: {{grant_deadline}}**

**Zašto je ovo savršeno poklapanje:**
{% for reason in match_reasons %}
✅ {{reason}}
{% endfor %}

**Preporučeni sljedeći koraci:**
{% for step in recommended_steps %}
{{loop.index}}. {{step}}
{% endfor %}

[Započni Aplikaciju]({{application_url}}) | [Detaljnu Procjenu]({{assessment_url}})

Srdačan pozdrav,
FinAssist BH Tim
                '''
            },
            
            NotificationTemplate.WEEKLY_DIGEST: {
                'subject_bs': '📊 Vaš sedmični pregled grantova',
                'subject_en': '📊 Your weekly grants digest',
                'title_bs': 'Sedmični Pregled',
                'title_en': 'Weekly Digest',
                'message_bs': '''
Poštovani {{user_name}},

Evo vašeg sedmičnog pregleda aktivnosti:

📈 **Statistike:**
- Novi grantovi: {{new_grants_count}}
- Poklapanja: {{matches_count}}
- Deadline-ovi ove sedmice: {{deadlines_count}}

🎯 **Najbolja poklapanja:**
{% for grant in top_matches %}
- {{grant.name}} ({{grant.score}}%)
{% endfor %}

⏰ **Nadolazeći deadline-ovi:**
{% for deadline in upcoming_deadlines %}
- {{deadline.grant_name}}: {{deadline.date}}
{% endfor %}

[Pogledaj Sve Grantove]({{grants_url}}) | [Ažuriraj Profile]({{profile_url}})

Srdačan pozdrav,
FinAssist BH Tim
                '''
            }
        }
    
    def set_user_preferences(self, user_id: str, preferences: NotificationPreferences):
        """Postavlja korisničke preference"""
        self.preferences[user_id] = preferences
        logger.info(f"Ažurirane preference za korisnika {user_id}")
    
    def get_user_preferences(self, user_id: str) -> Optional[NotificationPreferences]:
        """Dohvaća korisničke preference"""
        return self.preferences.get(user_id)
    
    async def send_notification(self, notification: Notification) -> bool:
        """Šalje notifikaciju preko odgovarajućeg kanala"""
        try:
            if notification.channel == NotificationChannel.EMAIL:
                success = await self._send_email(notification)
            elif notification.channel == NotificationChannel.SMS:
                success = await self._send_sms(notification)
            elif notification.channel == NotificationChannel.PUSH:
                success = await self._send_push(notification)
            elif notification.channel == NotificationChannel.IN_APP:
                success = await self._send_in_app(notification)
            elif notification.channel == NotificationChannel.WEBHOOK:
                success = await self._send_webhook(notification)
            else:
                logger.error(f"Nepoznat kanal: {notification.channel}")
                return False
            
            if success:
                notification.is_sent = True
                notification.sent_time = datetime.now()
                self.sent_notifications.append(notification)
                logger.info(f"Uspješno poslana notifikacija {notification.notification_id}")
            else:
                notification.retry_count += 1
                if notification.retry_count < notification.max_retries:
                    # Dodaj za retry
                    notification.scheduled_time = datetime.now() + timedelta(minutes=5 * notification.retry_count)
                    logger.warning(f"Retry notifikacije {notification.notification_id} ({notification.retry_count}/{notification.max_retries})")
                else:
                    logger.error(f"Neuspješno slanje notifikacije {notification.notification_id} nakon {notification.max_retries} pokušaja")
            
            return success
            
        except Exception as e:
            logger.error(f"Greška pri slanju notifikacije {notification.notification_id}: {str(e)}")
            return False
    
    async def _send_email(self, notification: Notification) -> bool:
        """Šalje email notifikaciju"""
        try:
            # Kreiraj email poruku
            msg = MIMEMultipart('alternative')
            msg['Subject'] = notification.content.subject
            msg['From'] = self.from_email
            msg['To'] = self._get_user_email(notification.user_id)
            
            # Dodaj text verziju
            text_part = MIMEText(notification.content.message, 'plain', 'utf-8')
            msg.attach(text_part)
            
            # Dodaj HTML verziju ako postoji
            if notification.content.html_content:
                html_part = MIMEText(notification.content.html_content, 'html', 'utf-8')
                msg.attach(html_part)
            
            # Dodaj attachments
            for attachment_path in notification.content.attachments:
                try:
                    with open(attachment_path, 'rb') as f:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(f.read())
                        encoders.encode_base64(part)
                        part.add_header(
                            'Content-Disposition',
                            f'attachment; filename= {attachment_path.split("/")[-1]}'
                        )
                        msg.attach(part)
                except Exception as e:
                    logger.warning(f"Greška pri dodavanju attachment-a {attachment_path}: {str(e)}")
            
            # Pošalji email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            return True
            
        except Exception as e:
            logger.error(f"Greška pri slanju email-a: {str(e)}")
            return False
    
    async def _send_sms(self, notification: Notification) -> bool:
        """Šalje SMS notifikaciju"""
        try:
            phone_number = self._get_user_phone(notification.user_id)
            if not phone_number:
                logger.warning(f"Nema telefon broj za korisnika {notification.user_id}")
                return False
            
            # Skrati poruku za SMS
            sms_message = notification.content.message[:160]
            
            # Ovdje bi se pozivao SMS API (Twilio, Nexmo, itd.)
            # Simulacija za sada
            logger.info(f"SMS poslana na {phone_number}: {sms_message}")
            return True
            
        except Exception as e:
            logger.error(f"Greška pri slanju SMS-a: {str(e)}")
            return False
    
    async def _send_push(self, notification: Notification) -> bool:
        """Šalje push notifikaciju"""
        try:
            device_token = self._get_user_device_token(notification.user_id)
            if not device_token:
                logger.warning(f"Nema device token za korisnika {notification.user_id}")
                return False
            
            # Ovdje bi se pozivao Firebase Cloud Messaging ili slično
            # Simulacija za sada
            logger.info(f"Push notifikacija poslana: {notification.content.title}")
            return True
            
        except Exception as e:
            logger.error(f"Greška pri slanju push notifikacije: {str(e)}")
            return False
    
    async def _send_in_app(self, notification: Notification) -> bool:
        """Šalje in-app notifikaciju"""
        try:
            # Spremi u bazu za prikaz u aplikaciji
            # Simulacija za sada
            logger.info(f"In-app notifikacija kreirana za korisnika {notification.user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Greška pri kreiranju in-app notifikacije: {str(e)}")
            return False
    
    async def _send_webhook(self, notification: Notification) -> bool:
        """Šalje webhook notifikaciju"""
        try:
            webhook_url = self._get_user_webhook(notification.user_id)
            if not webhook_url:
                return False
            
            payload = {
                'notification_id': notification.notification_id,
                'user_id': notification.user_id,
                'type': notification.content.template_type.value,
                'title': notification.content.title,
                'message': notification.content.message,
                'data': notification.content.data,
                'timestamp': datetime.now().isoformat()
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    return response.status == 200
                    
        except Exception as e:
            logger.error(f"Greška pri slanju webhook-a: {str(e)}")
            return False
    
    def create_notification(self, user_id: str, template_type: NotificationTemplate,
                          data: Dict[str, Any], priority: NotificationPriority = NotificationPriority.MEDIUM,
                          channels: List[NotificationChannel] = None) -> List[Notification]:
        """Kreira notifikacije za korisnika"""
        
        preferences = self.get_user_preferences(user_id)
        if not preferences:
            logger.warning(f"Nema preference za korisnika {user_id}")
            return []
        
        # Provjeri da li korisnik želi ovaj tip notifikacije
        if not self._should_send_notification(preferences, template_type):
            logger.info(f"Korisnik {user_id} ne želi {template_type.value} notifikacije")
            return []
        
        # Odredi kanale
        if channels is None:
            channels = self._get_enabled_channels(preferences)
        
        notifications = []
        
        for channel in channels:
            # Kreiraj sadržaj
            content = self._create_notification_content(template_type, data, preferences.user_id)
            
            notification = Notification(
                notification_id="",  # Će biti generisan u __post_init__
                user_id=user_id,
                channel=channel,
                priority=priority,
                content=content
            )
            
            notifications.append(notification)
            self.pending_notifications.append(notification)
        
        logger.info(f"Kreirane {len(notifications)} notifikacije za korisnika {user_id}")
        return notifications
    
    def _should_send_notification(self, preferences: NotificationPreferences, 
                                 template_type: NotificationTemplate) -> bool:
        """Provjera da li treba poslati notifikaciju"""
        mapping = {
            NotificationTemplate.NEW_GRANT: preferences.new_grants,
            NotificationTemplate.DEADLINE_REMINDER: preferences.deadline_reminders,
            NotificationTemplate.ELIGIBILITY_MATCH: preferences.eligibility_matches,
            NotificationTemplate.SUBSCRIPTION_EXPIRY: preferences.subscription_updates,
            NotificationTemplate.PAYMENT_CONFIRMATION: preferences.subscription_updates,
            NotificationTemplate.WEEKLY_DIGEST: preferences.weekly_digest,
            NotificationTemplate.MONTHLY_REPORT: preferences.monthly_report
        }
        
        return mapping.get(template_type, True)
    
    def _get_enabled_channels(self, preferences: NotificationPreferences) -> List[NotificationChannel]:
        """Vraća omogućene kanale za korisnika"""
        channels = []
        
        if preferences.email_enabled:
            channels.append(NotificationChannel.EMAIL)
        if preferences.sms_enabled:
            channels.append(NotificationChannel.SMS)
        if preferences.push_enabled:
            channels.append(NotificationChannel.PUSH)
        if preferences.in_app_enabled:
            channels.append(NotificationChannel.IN_APP)
        
        return channels
    
    def _create_notification_content(self, template_type: NotificationTemplate,
                                   data: Dict[str, Any], user_id: str) -> NotificationContent:
        """Kreira sadržaj notifikacije"""
        
        template = self.templates.get(template_type, {})
        
        # Dodaj korisničke podatke
        user_data = self._get_user_data(user_id)
        data.update(user_data)
        
        # Renderuj template-e
        subject = self._render_template(template.get('subject_bs', ''), data)
        title = self._render_template(template.get('title_bs', ''), data)
        message = self._render_template(template.get('message_bs', ''), data)
        
        html_content = None
        if 'html_template' in template:
            html_content = self._render_template(template['html_template'], data)
        
        return NotificationContent(
            template_type=template_type,
            subject=subject,
            title=title,
            message=message,
            html_content=html_content,
            data=data
        )
    
    def _render_template(self, template_str: str, data: Dict[str, Any]) -> str:
        """Renderuje Jinja2 template"""
        try:
            template = Template(template_str)
            return template.render(**data)
        except Exception as e:
            logger.error(f"Greška pri renderovanju template-a: {str(e)}")
            return template_str
    
    def _get_user_data(self, user_id: str) -> Dict[str, Any]:
        """Dohvaća podatke o korisniku"""
        # Ovdje bi se pozivala baza podataka
        # Simulacija za sada
        return {
            'user_name': 'Marko Marković',
            'user_email': 'marko@example.com'
        }
    
    def _get_user_email(self, user_id: str) -> str:
        """Dohvaća email korisnika"""
        # Ovdje bi se pozivala baza podataka
        return "test@example.com"
    
    def _get_user_phone(self, user_id: str) -> Optional[str]:
        """Dohvaća telefon korisnika"""
        # Ovdje bi se pozivala baza podataka
        return None
    
    def _get_user_device_token(self, user_id: str) -> Optional[str]:
        """Dohvaća device token korisnika"""
        # Ovdje bi se pozivala baza podataka
        return None
    
    def _get_user_webhook(self, user_id: str) -> Optional[str]:
        """Dohvaća webhook URL korisnika"""
        # Ovdje bi se pozivala baza podataka
        return None
    
    async def process_pending_notifications(self):
        """Obrađuje sve pending notifikacije"""
        current_time = datetime.now()
        
        # Filtriraj notifikacije koje treba poslati
        to_send = [
            notification for notification in self.pending_notifications
            if (notification.scheduled_time is None or 
                notification.scheduled_time <= current_time) and
               not notification.is_sent
        ]
        
        logger.info(f"Obrađujem {len(to_send)} notifikacija")
        
        # Pošalji notifikacije
        tasks = [self.send_notification(notification) for notification in to_send]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Ukloni uspješno poslane iz pending liste
        self.pending_notifications = [
            notification for notification in self.pending_notifications
            if not notification.is_sent
        ]
        
        successful = sum(1 for result in results if result is True)
        logger.info(f"Uspješno poslano {successful}/{len(to_send)} notifikacija")
    
    def schedule_deadline_reminders(self, grants: List[Dict[str, Any]]):
        """Zakazuje podsjetke za deadline-ove"""
        for grant in grants:
            deadline = grant.get('deadline')
            if not deadline:
                continue
            
            # Zakaži podsjetke za sve korisnike koji prate ovaj grant
            interested_users = self._get_interested_users(grant)
            
            for user_id in interested_users:
                preferences = self.get_user_preferences(user_id)
                if not preferences or not preferences.deadline_reminders:
                    continue
                
                # Kreiraj podsjetke za različite dane
                for days_before in preferences.reminder_days:
                    reminder_date = deadline - timedelta(days=days_before)
                    
                    if reminder_date > datetime.now():
                        data = {
                            'grant_name': grant['name'],
                            'grant_deadline': deadline.strftime('%d.%m.%Y'),
                            'days_left': days_before,
                            'application_url': f"https://finassist.ba/grants/{grant['id']}/apply"
                        }
                        
                        notifications = self.create_notification(
                            user_id=user_id,
                            template_type=NotificationTemplate.DEADLINE_REMINDER,
                            data=data,
                            priority=NotificationPriority.HIGH if days_before <= 3 else NotificationPriority.MEDIUM
                        )
                        
                        # Zakaži za određeno vrijeme
                        for notification in notifications:
                            notification.scheduled_time = reminder_date.replace(
                                hour=int(preferences.preferred_time.split(':')[0]),
                                minute=int(preferences.preferred_time.split(':')[1])
                            )
    
    def _get_interested_users(self, grant: Dict[str, Any]) -> List[str]:
        """Vraća korisnike zainteresovane za grant"""
        # Ovdje bi se pozivala baza podataka ili eligibility engine
        # Simulacija za sada
        return list(self.preferences.keys())
    
    def create_weekly_digest(self, user_id: str) -> Optional[Notification]:
        """Kreira sedmični digest za korisnika"""
        preferences = self.get_user_preferences(user_id)
        if not preferences or not preferences.weekly_digest:
            return None
        
        # Pripremi podatke za digest
        data = {
            'new_grants_count': 5,
            'matches_count': 3,
            'deadlines_count': 2,
            'top_matches': [
                {'name': 'IPA MSP Konkurentnost', 'score': 85},
                {'name': 'FBiH Startup Fond', 'score': 78},
                {'name': 'Okoliš Energetika', 'score': 72}
            ],
            'upcoming_deadlines': [
                {'grant_name': 'Kanton Sarajevo Startup', 'date': '31.03.2026'},
                {'grant_name': 'FBiH MSP Subvencije', 'date': '30.04.2026'}
            ],
            'grants_url': 'https://finassist.ba/grants',
            'profile_url': 'https://finassist.ba/profile'
        }
        
        notifications = self.create_notification(
            user_id=user_id,
            template_type=NotificationTemplate.WEEKLY_DIGEST,
            data=data,
            priority=NotificationPriority.LOW
        )
        
        return notifications[0] if notifications else None
    
    def get_notification_statistics(self) -> Dict[str, Any]:
        """Vraća statistike notifikacija"""
        total_sent = len(self.sent_notifications)
        total_pending = len(self.pending_notifications)
        
        # Statistike po kanalima
        channel_stats = {}
        for notification in self.sent_notifications:
            channel = notification.channel.value
            channel_stats[channel] = channel_stats.get(channel, 0) + 1
        
        # Statistike po tipovima
        type_stats = {}
        for notification in self.sent_notifications:
            template_type = notification.content.template_type.value
            type_stats[template_type] = type_stats.get(template_type, 0) + 1
        
        # Success rate
        failed_notifications = [
            n for n in self.sent_notifications + self.pending_notifications
            if n.retry_count >= n.max_retries and not n.is_sent
        ]
        
        success_rate = (total_sent / (total_sent + len(failed_notifications)) * 100) if (total_sent + len(failed_notifications)) > 0 else 0
        
        return {
            'total_sent': total_sent,
            'total_pending': total_pending,
            'total_failed': len(failed_notifications),
            'success_rate': round(success_rate, 2),
            'channel_distribution': channel_stats,
            'type_distribution': type_stats,
            'active_users': len(self.preferences)
        }

# Primjer korištenja
async def main():
    """Testiranje notification sistema"""
    
    # Konfiguracija
    config = {
        'smtp_server': 'smtp.gmail.com',
        'smtp_port': 587,
        'smtp_username': 'your-email@gmail.com',
        'smtp_password': 'your-password',
        'from_email': 'noreply@finassist.ba'
    }
    
    # Kreiraj sistem
    notification_system = FinAssistNotificationSystem(config)
    
    # Postavi korisničke preference
    preferences = NotificationPreferences(
        user_id="user123",
        email_enabled=True,
        new_grants=True,
        deadline_reminders=True,
        preferred_time="09:00",
        reminder_days=[7, 3, 1]
    )
    
    notification_system.set_user_preferences("user123", preferences)
    
    # Kreiraj notifikaciju o novom grantu
    grant_data = {
        'grant_name': 'IPA - Jačanje konkurentnosti MSP',
        'grant_budget': '10.000 - 200.000 BAM',
        'grant_deadline': '30.06.2026',
        'grant_category': 'Inovacije',
        'eligibility_score': 85,
        'grant_description': 'Grant za povećanje konkurentnosti malih i srednjih preduzeća...',
        'grant_url': 'https://finassist.ba/grants/ipa-msp',
        'assessment_url': 'https://finassist.ba/assessment/ipa-msp'
    }
    
    notifications = notification_system.create_notification(
        user_id="user123",
        template_type=NotificationTemplate.NEW_GRANT,
        data=grant_data,
        priority=NotificationPriority.HIGH
    )
    
    print(f"Kreirane {len(notifications)} notifikacije")
    
    # Obradi pending notifikacije
    await notification_system.process_pending_notifications()
    
    # Prikaži statistike
    stats = notification_system.get_notification_statistics()
    print(f"Statistike: {stats}")

if __name__ == "__main__":
    asyncio.run(main())
