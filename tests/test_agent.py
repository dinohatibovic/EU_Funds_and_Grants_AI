from agent.agent import EUFundsAgent

def test_answer_returns_string():
    agent = EUFundsAgent()
    result = agent.answer("Test upit")
    assert isinstance(result, str)

