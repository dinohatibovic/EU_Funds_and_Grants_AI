"""
GENAI CLIENT - Communication with Gemini 2.0 Flash
===================================================
Corrected for google-genai v1.62.0
"""

from google import genai
import os
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load .env from current directory
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(env_path)

class GenAIClient:
    """Client for Gemini 2.0 Flash."""
    
    def __init__(self, temperature: float = 0.7):
        """Initialize GenAIClient."""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.error("❌ GEMINI_API_KEY not found!")
            raise EnvironmentError("GEMINI_API_KEY not found!")
        
        try:
            self.client = genai.Client(api_key=api_key)
            self.model = "gemini-2.0-flash"
            self.temperature = temperature
            logger.info(f"✅ GenAIClient initialized: {self.model}")
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            raise

    def generate(self, prompt: str) -> str:
        """Generates response based on prompt."""
        try:
            logger.info(f"🔄 Generating response...")
            
            # CORRECT API: Use 'contents' parameter
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt  # ← KEY PARAMETER
            )
            
            result = response.text
            logger.info(f"✅ Response generated ({len(result)} chars)")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            return ""

    def generate_with_context(self, prompt: str, context: str) -> str:
        """Generates response with context."""
        try:
            full_prompt = f"""
CONTEXT:
{context}

QUERY:
{prompt}

INSTRUCTIONS:
- Use only information from the context
- Be specific and precise
"""
            
            logger.info("🔄 Generating with context...")
            response = self.client.models.generate_content(
                model=self.model,
                contents=full_prompt
            )
            
            result = response.text
            logger.info(f"✅ Response generated")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            return ""

    def get_model_info(self) -> dict:
        """Returns model information."""
        return {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": 2048
        }


if __name__ == "__main__":
    try:
        print("\n" + "=" * 70)
        print("TESTING GENAI CLIENT")
        print("=" * 70)
        
        client = GenAIClient(temperature=0.7)
        print(f"\n✅ Client initialized")
        print(f"   Model: {client.model}")
        
        # Test generation
        print("\n📌 TEST: Generate Response")
        response = client.generate("What are EU grants?")
        if response:
            print(f"✅ Success!")
            print(f"Response: {response[:200]}...")
        else:
            print("❌ Failed")
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

