from smt_management_app.models import *
import random
import datetime


def run():
    storage = Storage.objects.create(name=f"Storage_1", capacity=1400, device="Dummy")
    storage2 = Storage.objects.create(name=f"Storage_2", capacity=1400, device="Dummy")

    storage_slots = []
    storage2_slots = []

    for i in range(1, 1401):
        storage_slot = StorageSlot.objects.create(name=i, storage=storage)
        storage_slot2 = StorageSlot.objects.create(name=i, storage=storage2)
        storage_slots.append(storage_slot)
        storage2_slots.append(storage_slot2)
        if i > 700:
            i -= 700

        row = (i - 1) // 100 + 1
        lamp = (i - 1) % 100 + 1
        if int(storage_slot.name) > 700:
            lamp += 100

        qr_val = f"001-{str(row).zfill(2)}-{str(lamp).zfill(3)}"

        storage_slot.qr_value = qr_val
        storage_slot.save()

        storage_slot2.qr_value = qr_val
        storage_slot2.save()

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
    storage_slots.extend(storage2_slots)

    carriers = []
    for i in range(1, 40):
        if (i - 1) % 3 == 0:
            j = None
        elif (i - 1) % 3 == 1:
            j = i - 1
        else:
            j = i + 1399
        carriers.append(
            Carrier.objects.create(
                name=f"{i}",
                article=articles[i % 10],
                quantity_original=2000,
                quantity_current=random.randint(1000, 2000),
                lot_number=f"Bestellung_{i%4}",
                storage_slot=storage_slots[j] if j else None,
                delivered=True,
            )
        )

    boards = []
    for i in range(1, 10):
        boards.append(Board.objects.create(name=f"board_{i}"))
        for j, article in enumerate(articles):
            if j > i:
                continue
            BoardArticle.objects.create(
                name=f"{i}_{article.name}",
                count=100,
                board=boards[i - 1],
                article=article,
            )

    jobs = []
    for i in range(1, 10):
        jobs.append(
            Job.objects.create(
                name=f"Job_{i}",
                description=f"Description of Job_{i}",
                board=boards[i - 1],
                count=100,
                customer=f"Customer_{i}",
                start_at=datetime.datetime.now() + datetime.timedelta(hours=1 * i),
                finish_at=datetime.datetime.now() + datetime.timedelta(hours=3 * i),
            )
        )

    j1 = jobs[0]
    b1 = j1.board
    for ba in b1.boardarticle_set.all():
        c = Carrier.objects.filter(article=ba.article, archived=False).first()
        j1.carriers.add(c)
        c.reserved = True
    if j1.carriers.count() == j1.board.articles.count():
        j1.status = 1

    j1.save()
