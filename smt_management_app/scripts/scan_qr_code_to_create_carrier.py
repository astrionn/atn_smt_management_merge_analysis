from smt_management_app.models import Article, Carrier
from smt_management_app.utils.led_shelf_dispatcher import LED_shelf_dispatcher
import random

def run():
    aqs = Article.objects.all()
    while True:
        c = input('Scan UID...')
        new_c = Carrier.objects.create(name=c,article=random.choice(aqs),delivered=True,quantity_current=2000,quantity_original=2000)
        print()
        print(new_c)
        print()