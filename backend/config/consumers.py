from channels.generic.websocket import AsyncJsonWebsocketConsumer

class LiveDashboardConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        await self.accept()
        await self.send_json({'type': 'connected', 'message': 'اتصال داشبورد زنده برقرار شد'})

    async def receive_json(self, content, **kwargs):
        if content.get('type') == 'ping':
            await self.send_json({'type': 'pong'})
