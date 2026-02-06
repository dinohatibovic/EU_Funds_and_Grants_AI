import os
from dotenv import load_dotenv

load_dotenv()

from agent.agent import EUFundsAgent

if __name__ == "__main__":
    agent = EUFundsAgent()
    question = "Koji EU grantovi postoje za mala preduzeća u BiH?"
    answer = agent.answer(question)
    print("\n❓ Pitanje:", question)
    print("\n💬 Odgovor:\n", answer)
