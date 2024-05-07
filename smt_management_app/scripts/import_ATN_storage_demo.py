from ipaddress import ip_address
from smt_management_app.models import (
    Manufacturer,
    Provider,
    Storage,
    StorageSlot,
    Article,
    Carrier,
)
import random


def run():
    storage = Storage.objects.create(
        name=f"Storage_1",
        capacity=1400,
        device="NeoLight",
        ip_address="192.168.178.12",
        ip_port=5000,
    )
    for i in range(1, 1401):
        storage_slot = StorageSlot.objects.create(name=i, storage=storage)

        if storage_slot.name > 700:
            i -= 700

        if (
            storage_slot.name > 600 and storage_slot.name <= 700
        ):  # top row was inserted the wrong way around but the qr codes are not
            i = 1301 - i

        row = (i - 1) // 100 + 1
        lamp = (i - 1) % 100 + 1
        if storage_slot.name > 700:
            lamp += 100
        qr_val = f"002-{str(row).zfill(2)}-{str(lamp).zfill(3)}"

        storage_slot.qr_value = qr_val
        storage_slot.save()

    manufacturers = []
    for i in range(1, 4):
        manufacturers.append(Manufacturer.objects.create(name=f"Manufacturer_{i}"))

    providers = []
    for i in range(1, 11):
        providers.append(Provider.objects.create(name=f"Provider_{i}"))

    articles = []
    for i in range(1, 11):
        articles.append(
            Article.objects.create(
                name=f"Article_{i}",
                description=f"Some text describing Article_{i}.",
                manufacturer=manufacturers[i % 3],
                manufacturer_description=f"Alternative number for Article_{i} from {manufacturers[i%3].name}.",
                provider1=providers[i % 4 + 1],
                provider1_description=f"Alternative number for Article_{i} from {providers[i%4+1].name}.",
                provider2=providers[i % 4 + 2],
                provider2_description=f"Alternative number for Article_{i} from {providers[i%4+2].name}.",
                provider3=providers[i % 4 + 3],
                provider3_description=f"Alternative number for Article_{i} from {providers[i%4+3].name}.",
                provider4=providers[i % 4 + 4],
                provider4_description=f"Alternative number for Article_{i} from {providers[i%4+4].name}.",
                provider5=providers[i % 4 + 5],
                provider5_description=f"Alternative number for Article_{i} from {providers[i%4+5].name}.",
                sap_number=".".join(
                    [
                        "".join([str(random.randint(0, 9)) for _ in range(3)])
                        for _ in range(4)
                    ]
                ),
            )
        )

    carriers = []
    for i in range(1, 40):
        carriers.append(
            Carrier.objects.create(
                name=f"{i}",
                article=articles[i % 10],
                quantity_original=2000,
                quantity_current=random.randint(1000, 2000),
                lot_number=f"Bestellung_{i%4}",
            )
        )
