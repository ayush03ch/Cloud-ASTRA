# supervisor/dispatcher.py
from agents.s3_agent.s3_agent import S3Agent

class Dispatcher:
    """
    Sends tasks to appropriate service agents.
    For now, supports only S3.
    """

    def __init__(self, creds):
        self.creds = creds

    def dispatch(self):
        results = {}
        # Run S3 Agent
        s3_agent = S3Agent(self.creds)
        results["s3"] = s3_agent.scan()

        # In future: add EC2Agent, IAMAgent, etc.
        return results
