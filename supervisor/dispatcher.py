# supervisor/dispatcher.py
from agents.s3_agent.s3_agent import S3Agent

class Dispatcher:
    """
    Sends tasks to appropriate service agents.
    For now, supports only S3.
    """

    def __init__(self, creds):
        self.creds = creds

    def dispatch(self, user_intent_input=None):
        results = {}
        # Run S3 Agent with intent input
        s3_agent = S3Agent(creds=self.creds)
        results["s3"] = s3_agent.scan(user_intent_input=user_intent_input)

        # In future: add EC2Agent, IAMAgent, etc.
        return results
