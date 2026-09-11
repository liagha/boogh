"""boogh config is endpoints, keys, paths."""
import os

base = "https://snappfood.ir"
apigw = "https://apigw.snappfood.ir"
area = "https://marketing-area.snappfood.ir"
area_key = "88sqcXFr5QHtvZKt6lJTySCxflFG5CPrs8XyfXUhQRSjyrrRI0TRB3595LxDvF8i"
user = "https://user.snappfood.ir"

proxy = "https://app.snapp.taxi/api/api-base"
api = "https://app.snapp.taxi/api"
oauth = "https://app.snapp.taxi/api/api-passenger-oauth"

ride_client = "ios_sadjfhasd9871231hfso234"
ride_secret = "23497shjlf982734-=1031nln"
ride_version = "v18.44.1"
captcha_client = "71C84A80-395B-448E-A240-B7DC939186D3"

food_client = "PWA"
food_version = "6.0.0"
home_lat = 35.774
home_long = 51.418

agent = {"User-Agent": "boogh/0.1", "Accept-Language": "fa"}
ride_headers = {"App-Version": "pwa", "x-app-version": ride_version,
                "x-app-name": "passenger-pwa", "Content-Type": "application/json"}

old_store = os.path.expanduser("~/.config/snapppp/tokens.json")
store = os.path.expanduser("~/.config/boogh/tokens.json")
