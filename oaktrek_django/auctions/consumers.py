import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import LuxuryShoe, Bid

# In-memory store for auction state
AUCTION_STATE = {}

class AuctionConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            self.luxury_shoe_id = self.scope['url_route']['kwargs']['luxury_shoe_id']
            self.room_group_name = f'auction_{self.luxury_shoe_id}'
            
            # Join room group
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            await self.accept()

            # Log successful connection
            print(f"WebSocket connection established for auction {self.luxury_shoe_id}")

            # Initialize auction state if not exists
            luxury_shoe = await self.get_luxury_shoe()
            
            if self.luxury_shoe_id not in AUCTION_STATE:
                AUCTION_STATE[self.luxury_shoe_id] = {
                    'winner': None,
                    'end_time': luxury_shoe.auction_end
                }
                
            if luxury_shoe.is_active:
                now = timezone.now()
                if now >= luxury_shoe.auction_start:
                    # Use auction_end directly
                    expected_end = luxury_shoe.auction_end
                    AUCTION_STATE[self.luxury_shoe_id]['end_time'] = expected_end
                    
                    # Check if auction has already ended
                    if now >= expected_end:
                        await self.end_auction(luxury_shoe)
                        highest_bid = await self.get_highest_bid()
                        winner = highest_bid.user.username if highest_bid else None
                        amount = float(highest_bid.amount) if highest_bid else None
                        await self.channel_layer.group_send(
                            self.room_group_name,
                            {
                                'type': 'auction_winner',
                                'winner': winner,
                                'amount': amount
                            }
                        )
                    else:
                        # Send auction details
                        await self.send(text_data=json.dumps({
                            'auction_details': {
                                'end_time': expected_end.isoformat(),
                                'is_active': luxury_shoe.is_active,
                                'current_time': now.isoformat()
                            }
                        }))
                        # Start background task to check auction end
                        asyncio.create_task(self.check_auction_end())
        except Exception as e:
            print(f"Error in WebSocket connect: {e}")
            # Still try to accept the connection even if there's an error
            await self.accept()
            # Send error message to client
            await self.send(text_data=json.dumps({
                'error': f"Connection error: {str(e)}"
            }))

    async def disconnect(self, close_code):
        try:
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
            print(f"WebSocket disconnected for auction {self.luxury_shoe_id} with code {close_code}")
        except Exception as e:
            print(f"Error in disconnect: {e}")

    async def receive(self, text_data):
        try:
            # Log received data for debugging
            print(f"Received message: {text_data}")
            # You can process incoming messages here if needed
            data = json.loads(text_data)
            print(f"Processed message data: {data}")
        except Exception as e:
            print(f"Error in receive: {e}")

    async def bid_update(self, event):
        try:
            # Send the bid data including the reload flag
            await self.send(text_data=json.dumps({
                'bid': event['bid']
            }))
            print(f"Sent bid update: {event['bid']}")
        except Exception as e:
            print(f"Error in bid_update: {e}")

    async def auction_winner(self, event):
        try:
            await self.send(text_data=json.dumps({
                'winner': event['winner'],
                'amount': event['amount']
            }))
            print(f"Sent auction winner: {event['winner']}")
        except Exception as e:
            print(f"Error in auction_winner: {e}")

    async def check_auction_end(self):
        try:
            state = AUCTION_STATE[self.luxury_shoe_id]
            luxury_shoe = await self.get_luxury_shoe()
            
            while luxury_shoe.is_active:
                now = timezone.now()
                expected_end = state.get('end_time')
                
                if expected_end and now >= expected_end:
                    await self.end_auction(luxury_shoe)
                    highest_bid = await self.get_highest_bid()
                    winner = highest_bid.user.username if highest_bid else None
                    amount = float(highest_bid.amount) if highest_bid else None
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            'type': 'auction_winner',
                            'winner': winner,
                            'amount': amount
                        }
                    )
                    break
                
                await asyncio.sleep(1)
        except Exception as e:
            print(f"Error in check_auction_end: {e}")

    @database_sync_to_async
    def get_highest_bid(self):
        return Bid.objects.filter(luxury_shoe_id=self.luxury_shoe_id).order_by('-amount').first()
        
    @database_sync_to_async
    def get_luxury_shoe(self):
        return LuxuryShoe.objects.get(id=self.luxury_shoe_id)
        
    @database_sync_to_async
    def end_auction(self, shoe):
        if shoe.is_active:
            shoe.is_active = False
            shoe.auction_end = timezone.now()
            shoe.save()