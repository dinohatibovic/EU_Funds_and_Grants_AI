from .genai_client import GenAIClient
from .rag_client import RAGClient

_SYSTEM_CONTEXT = """Ti si FinAssistBH — specijalizovani AI asistent za EU fondove i grantove
u Bosni i Hercegovini. Razvijen od strane Dino Hatibović, Tešanj.

TVOJI PRIORITETI (prema relevantnosti za korisnika):
1. TIER 1 — Lokalni (ZDK / Tešanj):
   - Općina Tešanj: www.tesanj.ba | Tel: +387 32 650 100
   - ZDK Ministarstvo privrede: zdk.ba/ministarstva/ministarstvo-za-privredu
   - ZEDA (Zenička razvojna agencija): zeda.ba/javni-pozivi/ | Tel: +387 32 449 400
   - Privredna komora ZDK: pkzdk.ba

2. TIER 2 — Federalni (FBiH):
   - FMRPO (28 mil. KM grantova 2026): javnipozivi.fmrpo.gov.ba ← PRIORITET
   - FMPVS (podrška u poljoprivredi): fmpvs.gov.ba | info@fmpvs.gov.ba
   - FBiH agregator: javnipozivi.gov.ba
   - FZZZ (sufinansiranje zapošljavanja): fzzz.ba
   - Fond za zaštitu okoliša: fzofbih.org.ba

3. TIER 3 — EU i međunarodni:
   - EU4Agri (30K–200K KM): javnipoziv.undp.ba
   - EU4CAET energetska efikasnost (99K–170K EUR, rok 30.03.2026.): eu4caet.ba
   - FIPA IT poticaji (do 150K KM): fipa.gov.ba
   - DEI BiH EU programi: dei.gov.ba

VAŽNE ČINJENICE:
- BiH je kandidat za EU — NIJE punopravna članica
- GIZ je implementator, ne finansijer (izvor je EU)
- Svaki grant mora imati: naziv, iznos, rok, URL, nivo pouzdanosti
- Oznake: ✅ VISOKA | ⚠️ SREDNJA | ❌ NEPOTVRĐENO
- Nikad ne navoditi rokove bez provjere

AKTIVNI HITNI POZIVI (mart 2026.):
- EU4CAET: rok 30.03.2026. (energetika, 99K–170K EUR, 50–80% pokriće) ⚠️ HITNO
- Innovate Bosnia: rok 31.03.2026. (startupi, max 50K KM) ⚠️ HITNO
- FMRPO: ~30.04.2026. (novo poduzetništvo, obrti, MSP)
- FIPA IT: 15.04.2026. (IT sektor, max 150K KM)
"""


class EUFundsAgent:
    def __init__(self):
        print("🤖 Inicijalizacija FinAssistBH agenta...")
        self.rag = RAGClient()
        self.genai = GenAIClient()

    def answer(self, query: str, language: str = "bs") -> str:
        """
        Generira AI odgovor koristeći RAG kontekst + Gemini.
        language: 'bs' (bosanski, default) ili 'en' (engleski)
        """
        rag_result = self.rag.get_context(query)
        has_context = rag_result and rag_result != "Nema rezultata."

        lang_instruction = (
            "Odgovaraj ISKLJUČIVO na bosanskom jeziku. Budi konkretan i koristan."
            if language == "bs"
            else "Answer in English. Be specific and helpful."
        )

        if has_context:
            prompt = f"""{_SYSTEM_CONTEXT}

{lang_instruction}

PRONAĐENI GRANTOVI IZ BAZE:
{rag_result}

KORISNIČKO PITANJE:
{query}

Odgovori na osnovu konteksta iznad. Navedi konkretne iznose, rokove i URL izvore.
Završi preporukom sljedećeg koraka (koji URL posjetiti ili s kim kontaktirati).
"""
        else:
            prompt = f"""{_SYSTEM_CONTEXT}

{lang_instruction}

NAPOMENA: Baza podataka nije pronašla direktno relevantne grantove za ovaj upit.
Koristi sistemsko znanje iz konteksta iznad da odgovoriš.

KORISNIČKO PITANJE:
{query}

Daj strukturiran odgovor. Ako ne znaš tačan odgovor, usmjeri korisnika na
javnipozivi.fmrpo.gov.ba ili javnipozivi.gov.ba za najsvježije informacije.
"""

        return self.genai.generate(prompt)
