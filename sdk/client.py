sdk/client.py  
Responsibility: public interface.

Key class:

EUGrantsClient

Method:

query(text: str) -> str
from EU_Funds_and_Grants_AI.sdk.client import EUGrantsClient

client = EUGrantsClient()
response = client.query("Find AI-related grants for Bosnia and Herzegovina")
print(response)

