
class Event:
    def __init__(self, event_id, agent, action, *args, **kwargs):
        self.event_id = event_id
        self.agent = agent
        self.action = action
        self.args = args
        self.kwargs = kwargs

    async def process(self):
        result = await self.agent.organization.perform_action(self.action, *self.args, **self.kwargs)
        self.agent.organization.event_results[self.event_id] = result
