from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'^http/auction/(?P<luxury_shoe_id>\d+)/$', consumers.AuctionConsumer.as_asgi()),
]
