class Event:
    def __init__(self, agent, action, *args, **kwargs):
        self.agent = agent
        self.action = action
        self.args = args
        self.kwargs = kwargs

    async def process(self):
        result = await self.agent.organization.perform_action(self.action, *self.args, **self.kwargs)
        return result