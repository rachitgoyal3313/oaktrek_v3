import json
import asyncio
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import LuxuryShoe, Bid

logger = logging.getLogger('auctions')

AUCTION_STATE = {}

class AuctionConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        logger.info(f"WebSocket connect attempt for URL: {self.scope['path']}")
        try:
            self.luxury_shoe_id = self.scope['url_route']['kwargs']['luxury_shoe_id']
            self.room_group_name = f'auction_{self.luxury_shoe_id}'
            logger.info(f"Connecting to room: {self.room_group_name}")

            # Join room group
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            logger.info(f"Joined channel layer group: {self.room_group_name}")
            await self.accept()
            logger.info("WebSocket connection accepted")

            # Initialize auction state
            luxury_shoe = await self.get_luxury_shoe()
            logger.info(f"Retrieved LuxuryShoe: {luxury_shoe}")

            if self.luxury_shoe_id not in AUCTION_STATE:
                AUCTION_STATE[self.luxury_shoe_id] = {
                    'winner': None,
                    'end_time': luxury_shoe.auction_end
                }
            
            if luxury_shoe.is_active:
                now = timezone.now()
                logger.info(f"Current time: {now}, Auction start: {luxury_shoe.auction_start}, Auction end: {luxury_shoe.auction_end}")
                if now >= luxury_shoe.auction_start:
                    expected_end = luxury_shoe.auction_end
                    AUCTION_STATE[self.luxury_shoe_id]['end_time'] = expected_end
                    
                    if now >= expected_end:
                        logger.info("Auction has ended, processing winner")
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
                        logger.info("Sending auction details")
                        await self.send(text_data=json.dumps({
                            'auction_details': {
                                'end_time': expected_end.isoformat(),
                                'is_active': luxury_shoe.is_active,
                                'current_time': now.isoformat()
                            }
                        }))
                        asyncio.create_task(self.check_auction_end())
        except Exception as e:
            logger.error(f"WebSocket connection error: {str(e)}", exc_info=True)
            await self.close(code=4000)

    async def disconnect(self, close_code):
        logger.info(f"WebSocket disconnected with code: {close_code}")
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        pass

    async def bid_update(self, event):
        await self.send(text_data=json.dumps({
            'bid': event['bid']
        }))

    async def auction_winner(self, event):
        await self.send(text_data=json.dumps({
            'winner': event['winner'],
            'amount': event['amount']
        }))

    async def check_auction_end(self):
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

    @database_sync_to_async
    def get_highest_bid(self):
        return Bid.objects.filter(luxury_shoe_id=self.luxury_shoe_id).order_by('-amount').first()
        
    @database_sync_to_async
    def get_luxury_shoe(self):
        logger.info(f"Fetching LuxuryShoe with id: {self.luxury_shoe_id}")
        try:
            return LuxuryShoe.objects.get(id=self.luxury_shoe_id)
        except LuxuryShoe.DoesNotExist:
            logger.error(f"LuxuryShoe with id {self.luxury_shoe_id} does not exist")
            raise
        
    @database_sync_to_async
    def end_auction(self, shoe):
        if shoe.is_active:
            shoe.is_active = False
            shoe.auction_end = timezone.now()
            shoe.save()