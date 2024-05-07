from smt_management_app.models import *


def run():
    carriers = Carrier.objects.all()

    for i, carrier in enumerate(carriers):
        carrier.name = input(f"{i}\n")
        carrier.save()
