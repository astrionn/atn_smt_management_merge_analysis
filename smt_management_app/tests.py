
import json

from logging import getLogger, DEBUG
from random import randint
import random


from django.test import TestCase
from django.test.client import Client
from django.utils.timezone import get_default_timezone
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.uploadedfile import SimpleUploadedFile

from .models import (
    AbstractBaseModel,
    Article,
    Carrier,
    Storage,
    StorageSlot,
    Board,
)

# Create your tests here.
# created by todo.org tangle

UserModel = get_user_model()


class CommonSetUpTestCase(TestCase):
    user_model = (None,)
    CLIENT = (None,)
    TZ = (None,)
    USER_EMAIL = (None,)
    PASSWORD = (None,)
    USERNAME = (None,)
    logger = None

    @classmethod
    def setUp(cls) -> None:
        cls.logger = getLogger(__name__)
        cls.logger.setLevel(level=DEBUG)
        cls.USERNAME = "testuser"
        cls.PASSWORD = "NeverUseThisPassword12345"
        cls.USER_EMAIL = "test@storageguide.com"
        cls.TZ = get_default_timezone()
        cls.CLIENT = Client(enforce_csrf_checks=False)

        try:
            cls.user_model = UserModel.objects.get(username=cls.USERNAME)
        except ObjectDoesNotExist:
            cls.user_model = UserModel.objects.create_user(
                username=cls.USERNAME,
                password=cls.PASSWORD,
                email=cls.USER_EMAIL,
            )

        printing = False
        # verfiy setup worked and display all fields and method in the class dict of the testcase
        if printing:
            from pprint import pprint as pp

            print("\n\n", cls, "\n\n", cls.__dict__, "\n\n")
            for name, att in cls.__dict__.items():
                print(name, att)
                print(
                    f'\n\nMy Name is "{name}" !\nMy class is "{att.__class__}" It\'s name is "{att.name if isinstance(att,AbstractBaseModel) else att}"\n'
                )
                if isinstance(att, AbstractBaseModel):
                    pp(att.__dict__)
                    pass

    @classmethod
    def print_qs(cls, qs):
        # print the dict of every object return in the queryset
        if not qs:
            return
        for o in qs:
            print(o, o.__dict__, "\n")
            pass

    @classmethod
    def get_random_name(cls, prefix=None):
        return f"{prefix}_{randint(1,1000)}"

    @classmethod
    def login_client(cls):
        cls.logger.info("Logging in client...")
        cls.CLIENT.login(username=cls.USERNAME, password=cls.PASSWORD)

    @classmethod
    def logout_client(cls):
        cls.logger.info("Logging out client...")
        cls.CLIENT.logout()

    def test_view_creating_article(cls):
        rand_name = cls.get_random_name("article")
        resp_create = cls.CLIENT.post(
            "/api/article/", {"name": rand_name, "description": "123123123123123"}
        )
        jdata = resp_create.json()
        resp_display = cls.CLIENT.get(f"/api/article/{rand_name}/?format=json")

        jdata2 = resp_display.json()
        cls.assertEqual(jdata, jdata2)
        return jdata2

    def test_view_creating_carrier(cls):
        art_json = cls.test_view_creating_article()
        # print(art_json)
        rand_name = cls.get_random_name("carrier")
        data = {
            "name": rand_name,
            "article": art_json["name"],
            "quantity_current": 1000,
        }
        # pp(data)
        resp_create = cls.CLIENT.post("/api/carrier/", data)

        jdata = resp_create.json()
        # pp(jdata)
        resp_display = cls.CLIENT.get(f"/api/carrier/{rand_name}/?format=json")

        jdata2 = resp_display.json()
        # pp(jdata)
        # pp(jdata2)
        cls.assertEqual(jdata, jdata2)
        return jdata2

    def test_view_creating_articles_from_file(cls):
        """tests a 2-step workflow:
        - uploading a csv file and getting the userspace headers and getting the file name returned
        - sending a mapping from user space to internal space of headers along with the filename and getting success or failure message of creation
        """

        # all fields and relations of Article model
        headers = [
            "name",
            "provider1",
            "provider1_description",
            "provider2",
            "provider2_description",
            "provider3",
            "provider3_description",
            "provider4",
            "provider4_description",
            "provider5",
            "provider5_description",
            "manufacturer",
            "manufacturer_description",
            "description",
            "sap_number",
            "created_at",
            "updated_at",
            "archived",
            "board",
            "boardarticle",
            "carrier",
        ]
        # print("\narticle headers")
        # pp(headers)

        # add some random to it to simulate the user having different names to our internal representation
        headers_salted = [k + cls.get_random_name("_aaaa") for k in headers]
        # print("\nsalted article headers")
        # pp(headers_salted)

        # build csv file
        file_content = ",".join(headers_salted)
        file_content += "\n"

        for i in range(5):
            values = []
            for h in headers:
                if h == "provider":
                    values.append(
                        f'"{cls.get_random_name(h)},{cls.get_random_name(h)}"'
                    )
                elif h in ["archived"]:
                    values.append(str(True))
                else:
                    values.append(cls.get_random_name(h))

            file_content += ",".join(values)
            file_content += "\n"
        # print("\ncsv data: ", file_content)
        f = SimpleUploadedFile(
            "file.csv", bytes(file_content, encoding="utf8"), content_type="text/plain"
        )

        # upload csv file
        resp_create = cls.CLIENT.post(
            "/api/save_file_and_get_headers/", {"file": f, "upload_type": "article"}
        )
        resp_create_json = resp_create.json()
        # print("\ncreated articles response ")
        # print(resp_create_json)
        headers_salted2 = resp_create_json["header_fields"]
        # print("\nheaders of the file")
        # pp(headers_salted2)

        headers2 = resp_create_json["object_fields"]
        # print("fields of the model")
        # pp(headers2)
        file_name = resp_create_json["file_name"]
        # print("\nComparing salted headers")
        # pp(headers_salted)
        # pp(headers_salted2)
        cls.assertEqual(sorted(headers_salted), sorted(headers_salted2))
        # print("\nComparing headers")
        # pp(headers)
        # pp(headers2)
        cls.assertEqual(sorted(headers), sorted(headers2))

        # provide user mapping
        map_ = {k: v for k, v in zip(sorted(headers), sorted(headers_salted2))}

        # print("\nuser mapping:")
        # pp(map_)

        # post
        resp_map = cls.CLIENT.post(
            "/api/user_mapping_and_file_processing/",
            {"file_name": file_name, "map": json.dumps(map_)},
        )
        msg = resp_map.json()
        # print("created response")
        # pp(msg)

    def test_view_creating_carriers_from_file(cls):
        """tests a 2-step workflow:
        - uploading a csv file and getting the userspace headers and getting the file name returned
        - sending a mapping from user space to internal space of headers along with the filename and getting success or failure message of creation
        """

        # all fields and relations of Carrier model (Carrier._meta.fields)
        headers = [
            "name",
            "created_at",
            "updated_at",
            "archived",
            "article",
            "diameter",
            "width",
            "container_type",
            "quantity_original",
            "quantity_current",
            "lot_number",
            "reserved",
            "delivered",
            "collecting",
            "storage",
            "storage_slot",
            "machine_slot",
            "job",
        ]

        # add some random to it to simulate the user having different names to our internal representation
        headers_salted = [k + cls.get_random_name("_aaaa") for k in headers]

        # build csv file
        file_content = ",".join(headers_salted)
        file_content += "\n"

        for i in range(5):
            values = []
            for h in headers:
                if h in ["archived", "collecting", "reserved"]:
                    values.append(str(False))
                elif h in ["delivered"]:
                    values.append(str(True))
                elif h in [
                    "created_at",
                    "updated_at",
                    "storage",
                    "storage_slot",
                    "machine_slot",
                ]:
                    values.append("")
                elif h in ["article"]:
                    art_randname = cls.get_random_name("article")
                    a = Article.objects.create(name=art_randname)
                    values.append(a.name)
                elif h in ["diameter"]:
                    values.append(7)
                elif h in ["width"]:
                    values.append(8)
                elif h in ["container_type"]:
                    values.append(0)
                elif h in ["quantity_current", "quantity_original"]:
                    values.append(1000)
                elif h in ["name"]:
                    values.append(cls.get_random_name("carrier"))
                else:
                    values.append(cls.get_random_name(h))
            values = [str(v) for v in values]
            file_content += ",".join(values)
            file_content += "\n"

        f = SimpleUploadedFile(
            "file.csv", bytes(file_content, encoding="utf8"), content_type="text/plain"
        )

        # upload csv file
        resp_create = cls.CLIENT.post(
            "/api/save_file_and_get_headers/", {"file": f, "upload_type": "carrier"}
        )
        resp_create_json = resp_create.json()

        headers_salted2 = resp_create_json["header_fields"]
        headers2 = resp_create_json["object_fields"]
        file_name = resp_create_json["file_name"]

        cls.assertEqual(sorted(headers_salted), sorted(headers_salted2))
        cls.assertEqual(sorted(headers), sorted(headers2))

        # provide user mapping
        map_ = {k: v for k, v in zip(sorted(headers), sorted(headers_salted2))}
        # post
        resp_map = cls.CLIENT.post(
            "/api/user_mapping_and_file_processing/",
            {"file_name": file_name, "map": json.dumps(map_)},
        )
        msg = resp_map.json()

    # create a csv file with bunch of articles
    # get_csv_headers(file) -> file_name
    # create_articles_from_file(file_name,headers) -> created X didnt create Y
    # Articles.objects.all
    # assert equal

    def test_view_displaying_carriers(cls):
        # create carriers with different attributes
        data = {
            "articles": [cls.get_random_name("article") for _ in range(3)],
            "manufacturers": [cls.get_random_name("manufacturer") for _ in range(3)],
            "providers": [cls.get_random_name("provider") for _ in range(3)],
            "lot_numbers": [cls.get_random_name("lot_number") for _ in range(3)],
        }

        for a in data["articles"]:
            cls.CLIENT.post("/api/article/", {"name": a})

        for m in data["manufacturers"]:
            cls.CLIENT.post("/api/manufacturer/", {"name": m})

        for p in data["providers"]:
            cls.CLIENT.post("/api/provider/", {"name": p})

        carriers = [
            {
                "name": cls.get_random_name("carrier"),
                "article": random.choice(data["articles"]),
                "manufacturer": random.choice(data["manufacturers"]),
                "provider": random.choice(data["providers"]),
                "lot_number": random.choice(data["lot_numbers"]),
                "quantity_current": 1000,
            }
            for i in range(3)
        ]
        carriers_clean = [
            {k: v for k, v in c.items() if k not in ["provider", "manufacturer"]}
            for c in carriers
        ]
        resps = []
        for c in carriers:
            resp = cls.CLIENT.post("/api/carrier/", c)
            resps.append(resp.json())

        # get carriers

        resp = cls.CLIENT.get("/api/carrier/?format=json")
        jdata = resp.json()
        jdata = jdata["results"]
        jdata_clean = [
            {k: v for k, v in j.items() if k in carriers[0].keys()} for j in jdata
        ]

        # pp(carriers_clean)
        # pp(jdata)
        # pp(jdata_clean)
        cls.assertEqual(jdata_clean, carriers_clean)

    def test_view_deleting_carriers(cls):
        art_randname = cls.get_random_name("article")
        a = Article.objects.create(name=art_randname)

        car_randname = cls.get_random_name("carrier")
        c = Carrier.objects.create(name=car_randname, article=a, quantity_current=1000)

        c_qs = Carrier.objects.filter(name=car_randname).first()
        cls.assertEqual(c, c_qs)

        resp_del = cls.CLIENT.delete(f"/api/carrier/{c.name}/")

        cls.assertEqual(Carrier.objects.filter(name=car_randname).first(), None)

    def test_view_delivering_carriers(cls):
        # Article.objects.create
        # Carrier.objects.create
        # edit_carrier()
        # Carrier.objects.all
        # assertEqual
        art_randname = cls.get_random_name("article")
        a = Article.objects.create(name=art_randname)

        car_randname = cls.get_random_name("carrier")
        c = Carrier.objects.create(name=car_randname, article=a, quantity_current=1000)

        resp_edit = cls.CLIENT.patch(
            f"/api/carrier/{car_randname}/",
            json.dumps({"quantity_current": 999, "delivered": True}),
            content_type="application/json",
        )
        resp_display = cls.CLIENT.get(f"/api/carrier/?name={car_randname}")
        cls.assertEqual(resp_display.json()["results"][0]["delivered"], True)
        cls.assertEqual(resp_display.json()["results"][0]["quantity_current"], 999)

    def test_view_QR_printing_carriers(cls):
        pass

    # Article.objects.create
    # Carrier.objects.create
    # print_label()

    def test_view_displaying_storages(cls):
        # Article.objects.create
        # Carrier.objects.create
        # Storage.objects.create
        # StorageSlot.objects.create
        # get_carriers(storage)

        art_randname = cls.get_random_name("article")
        a = Article.objects.create(name=art_randname)

        car_randname = cls.get_random_name("carrier")
        c = Carrier.objects.create(name=car_randname, article=a, quantity_current=1000)

        car_randname2 = cls.get_random_name("carrier")
        c2 = Carrier.objects.create(
            name=car_randname2, article=a, quantity_current=1000
        )

        stor_randname = cls.get_random_name("storage")
        s = Storage.objects.create(name=stor_randname, capacity=1000)

        stor_slot_randname = cls.get_random_name("storage_slot")
        ss = StorageSlot.objects.create(name=stor_slot_randname, storage=s)

        stor_slot_randname2 = cls.get_random_name("storage_slot")
        ss2 = StorageSlot.objects.create(name=stor_slot_randname2, storage=s)

        c.storage_slot = ss
        c.save()
        c2.storage_slot = ss2
        c2.save()
        resp_display = cls.CLIENT.get(f"/api/get_storage_content/{s.name}/?format=json")
        # pp(resp_display.json())
        # pp([c.__dict__,c2.__dict__])

    def test_view_collect_carriers(cls):
        art_randname = cls.get_random_name("article")
        a = Article.objects.create(name=art_randname)

        car_randname = cls.get_random_name("carrier")
        c = Carrier.objects.create(name=car_randname, article=a, quantity_current=1000)

        car_randname2 = cls.get_random_name("carrier")
        c2 = Carrier.objects.create(
            name=car_randname2, article=a, quantity_current=1000
        )

        stor_randname = cls.get_random_name("storage")
        s = Storage.objects.create(name=stor_randname, capacity=1000)

        stor_slot_randname = cls.get_random_name("storage_slot")
        stor_slot_randqr = f"qrval_{stor_slot_randname[-3:]}"
        ss = StorageSlot.objects.create(
            name=stor_slot_randname, qr_value=stor_slot_randqr, storage=s
        )

        stor_slot_randname2 = cls.get_random_name("storage_slot")
        stor_slot_randqr2 = f"qrval_{stor_slot_randname2[-3:]}"
        ss2 = StorageSlot.objects.create(
            name=stor_slot_randname2, qr_value=stor_slot_randqr2, storage=s
        )

        c.storage_slot = ss
        c.save()
        c2.storage_slot = ss2
        c2.save()

        # collect_carrier(carrier) -> storage, slot, carrier, queue
        resp_collect = cls.CLIENT.get(f"/api/collect_carrier/{car_randname}/")
        resp_collect2 = cls.CLIENT.get(f"/api/collect_carrier/{car_randname2}/")
        # pp(resp_collect.json())
        # pp(resp_collect2.json())
        jdata = resp_collect.json()
        jdata2 = resp_collect2.json()

        cls.assertIn(
            {
                "carrier": car_randname,
                "slot": stor_slot_randqr,
                "storage": stor_randname,
            },
            jdata2["queue"],
        )

        cls.assertIn(
            {
                "carrier": car_randname2,
                "slot": stor_slot_randqr2,
                "storage": stor_randname,
            },
            jdata2["queue"],
        )

        slot = jdata["slot"]
        slot2 = jdata2["slot"]
        # collect carrier_confirm_slot(slot, carrier) -> storage, slot, carrier, queue
        resp_confirm = cls.CLIENT.post(
            f"/api/collect_carrier_confirm/{car_randname}/{slot}/"
        )
        # pp(resp_confirm.json())
        resp_confirm2 = cls.CLIENT.post(
            f"/api/collect_carrier_confirm/{car_randname2}/{slot2}/"
        )
        # pp(resp_confirm2.json())
        cls.assertTrue(not resp_confirm2.json()["queue"])

    def test_view_collect_carriers_job(cls):
        art_randname = cls.get_random_name("article")
        a = Article.objects.create(name=art_randname)

        art_randname2 = cls.get_random_name("article")
        a2 = Article.objects.create(name=art_randname2)

        car_randname = cls.get_random_name("carrier")
        c = Carrier.objects.create(name=car_randname, article=a, quantity_current=1000)

        car_randname2 = cls.get_random_name("carrier")
        c2 = Carrier.objects.create(
            name=car_randname2, article=a, quantity_current=1000
        )

        stor_randname = cls.get_random_name("storage")
        s = Storage.objects.create(name=stor_randname, capacity=1000)

        stor_slot_randname = cls.get_random_name("storage_slot")
        ss = StorageSlot.objects.create(name=stor_slot_randname, storage=s)

        stor_slot_randname2 = cls.get_random_name("storage_slot")
        ss2 = StorageSlot.objects.create(name=stor_slot_randname2, storage=s)

        c.storage_slot = ss
        c.save()
        c2.storage_slot = ss2
        c2.save()

        bor_randname = cls.get_random_name("board")
        resp_board_create = cls.CLIENT.post(
            "/api/board/",
            {
                "name": bor_randname,
            },
        )

        for ba in [art_randname, art_randname2]:
            resp_boardarticles_create = cls.CLIENT.post(
                "/api/boardarticle/",
                {
                    "name": f"{bor_randname}_{ba}",
                    "article": ba,
                    "count": 10,
                    "board": bor_randname,
                },
            )
            # pp(resp_boardarticles_create.__dict__)

        bb = Board.objects.all()
        b = bb.first()
        # print(b)
        # print(b.boardarticle_set.all())
        # print(b.articles.all())
        job = {
            "name": cls.get_random_name("job"),
            "board": b.name,
            "count": 100,
            "start_at": "2023-01-01 8:00:00.000",  # iso-8601
            "finish_at": "2023-01-01 18:00:00.000",
        }
        resp_job_create = cls.CLIENT.post("/api/job/", job)
        # pp(resp_job_create.json())

        resp_job_display = cls.CLIENT.get(f'/api/job/{job["name"]}/?format=json')
        # pp(resp_job_display.json())

        resp_job_display_boardarticles = cls.CLIENT.get(
            f'/api/boardarticle/?format=json&board={job["board"]}'
        )
        # pp(resp_job_display_boardarticles.json())

    def test_view_storing_carrier(cls):
        art_randname = cls.get_random_name("article")
        a = Article.objects.create(name=art_randname)

        car_randname = cls.get_random_name("carrier")
        c = Carrier.objects.create(name=car_randname, article=a, quantity_current=1000)
        c.delivered = True
        c.save()

        car_randname2 = cls.get_random_name("carrier")
        c2 = Carrier.objects.create(
            name=car_randname2, article=a, quantity_current=1000
        )
        c2.delivered = True
        c2.save()

        car_randname3 = cls.get_random_name("carrier")
        c3 = Carrier.objects.create(
            name=car_randname3, article=a, quantity_current=1000
        )
        c3.delivered = True
        c3.save()

        stor_randname = cls.get_random_name("storage")
        s = Storage.objects.create(name=stor_randname, capacity=1000)

        stor_slot_randname = cls.get_random_name("storage_slot")
        ss = StorageSlot.objects.create(name=stor_slot_randname, storage=s)

        stor_slot_randname2 = cls.get_random_name("storage_slot")
        ss2 = StorageSlot.objects.create(name=stor_slot_randname2, storage=s)

        stor_slot_randname3 = cls.get_random_name("storage_slot")
        ss3 = StorageSlot.objects.create(name=stor_slot_randname3, storage=s)
        c3.storage_slot = ss3
        c3.save()
        resp_store = cls.CLIENT.post(f"/api/store_carrier/{c.name}/{s.name}/")
        # pp(resp_store.__dict__)

    def test_view_resetting_leds(cls):
        pass

    # Storage.objects.create
    # StorageSlot.objects.create
    # reset_leds_for_storage(storage)

    def test_view_creating_job(cls):
        art_randname = cls.get_random_name("article")
        a = Article.objects.create(name=art_randname)

        art_randname2 = cls.get_random_name("article")
        a2 = Article.objects.create(name=art_randname2)

        car_randname = cls.get_random_name("carrier")
        c = Carrier.objects.create(name=car_randname, article=a, quantity_current=1000)

        car_randname2 = cls.get_random_name("carrier")
        c2 = Carrier.objects.create(
            name=car_randname2, article=a, quantity_current=1000
        )

        stor_randname = cls.get_random_name("storage")
        s = Storage.objects.create(name=stor_randname, capacity=1000)

        stor_slot_randname = cls.get_random_name("storage_slot")
        ss = StorageSlot.objects.create(name=stor_slot_randname, storage=s)

        stor_slot_randname2 = cls.get_random_name("storage_slot")
        ss2 = StorageSlot.objects.create(name=stor_slot_randname2, storage=s)

        c.storage_slot = ss
        c.save()
        c2.storage_slot = ss2
        c2.save()

        bor_randname = cls.get_random_name("board")
        resp_board_create = cls.CLIENT.post(
            "/api/board/",
            {
                "name": bor_randname,
            },
        )

        for ba in [art_randname, art_randname2]:
            resp_boardarticles_create = cls.CLIENT.post(
                "/api/boardarticle/",
                {
                    "name": f"{bor_randname}_{ba}",
                    "article": ba,
                    "count": 10,
                    "board": bor_randname,
                },
            )
            # pp(resp_boardarticles_create.__dict__)

        bb = Board.objects.all()
        b = bb.first()
        # print(b)
        # print(b.boardarticle_set.all())
        # print(b.articles.all())
        job = {
            "name": cls.get_random_name("job"),
            "board": b.name,
            "count": 100,
            "start_at": "2023-01-01 8:00:00.000",  # iso-8601
            "finish_at": "2023-01-01 18:00:00.000",
        }
        resp_job_create = cls.CLIENT.post("/api/job/", job)
        # pp(resp_job_create.__dict__)

        resp_job_display = cls.CLIENT.get(f'/api/job/{job["name"]}/?format=json')
        # pp(resp_job_display.__dict__)

    def test_view_creating_board_from_file(cls):
        # create articles, carriers, storage, storage_slots
        art_randname = cls.get_random_name("article")
        a = Article.objects.create(name=art_randname)

        art_randname2 = cls.get_random_name("article")
        Article.objects.create(name=art_randname2)

        car_randname = cls.get_random_name("carrier")
        c = Carrier.objects.create(name=car_randname, article=a, quantity_current=1000)

        car_randname2 = cls.get_random_name("carrier")
        c2 = Carrier.objects.create(
            name=car_randname2, article=a, quantity_current=1000
        )

        stor_randname = cls.get_random_name("storage")
        s = Storage.objects.create(name=stor_randname, capacity=1000)

        stor_slot_randname = cls.get_random_name("storage_slot")
        ss = StorageSlot.objects.create(name=stor_slot_randname, storage=s)

        stor_slot_randname2 = cls.get_random_name("storage_slot")
        ss2 = StorageSlot.objects.create(name=stor_slot_randname2, storage=s)

        c.storage_slot = ss
        c.save()
        c2.storage_slot = ss2
        c2.save()

        # create new empty board

        bor_randname = cls.get_random_name("board")
        resp_board_create = cls.CLIENT.post(
            "/api/board/",
            {
                "name": bor_randname,
            },
        )

        # create a csv file with bunch of article names and counts
        # get_csv_headers(file) -> file_name
        # create_board_from_file(file_name,headers) -> created X didnt create Y
        # assert equal
        articles = [art_randname, art_randname2]
        counts = [random.randint(1, 100), random.randint(1, 100)]
        csv_string = "article123,count123\n"
        for a, c in zip(articles, counts):
            csv_string += f"{a},{c}\n"

        f = SimpleUploadedFile("file.csv", bytes(csv_string, encoding="utf8"))
        resp_create = cls.CLIENT.post(
            "/api/save_file_and_get_headers/",
            {"file": f, "upload_type": "board", "board_name": bor_randname},
        )
        resp_create_json = resp_create.json()
        headers = resp_create_json["header_fields"]
        file_name = resp_create_json["file_name"]
        # print(f"response")
        # pp(resp_create_json)
        # print(f"headers")
        # pp(headers)
        # print(f"filename")
        # pp(file_name)

        map_ = {k: v for k, v in zip(["article", "count"], headers)}
        # print(f"map_")
        # pp(map_)
        resp_map = cls.CLIENT.post(
            "/api/user_mapping_and_file_processing/",
            {"file_name": file_name, "map": json.dumps(map_)},
        )
        msg = resp_map.json()
        # print(f"resp file upload")
        # pp(msg)

        resp_board = cls.CLIENT.get(
            f"/api/boardarticle/?board={bor_randname}&format=json"
        )
        resp_board_json = resp_board.json()["results"]
        # print("resp_board_json")
        # pp(resp_board_json)

        cls.assertEqual(len(articles), len(resp_board_json))

        for ba in resp_board_json:
            cls.assertEqual(articles.index(ba["article"]), counts.index(ba["count"]))

    def test_create_and_prepare_job(cls):
        art_randname = cls.get_random_name("article")
        a = Article.objects.create(name=art_randname)

        art_randname2 = cls.get_random_name("article")
        a2 = Article.objects.create(name=art_randname2)

        car_randname = cls.get_random_name("carrier")
        c = Carrier.objects.create(name=car_randname, article=a, quantity_current=1000)

        car_randname2 = cls.get_random_name("carrier")
        c2 = Carrier.objects.create(
            name=car_randname2, article=a2, quantity_current=1000
        )

        stor_randname = cls.get_random_name("storage")
        s = Storage.objects.create(name=stor_randname, capacity=1000)

        stor_slot_randname = cls.get_random_name("storage_slot")
        ss = StorageSlot.objects.create(name=stor_slot_randname, storage=s)

        stor_slot_randname2 = cls.get_random_name("storage_slot")
        ss2 = StorageSlot.objects.create(name=stor_slot_randname2, storage=s)

        c.storage_slot = ss
        c.save()
        c2.storage_slot = ss2
        c2.save()

        bor_randname = cls.get_random_name("board")
        resp_board_create = cls.CLIENT.post(
            "/api/board/",
            {
                "name": bor_randname,
            },
        )
        """in the frontend form for creating a job there is a field for the board 
           with a dropdown of existing boards and an additional option at the bottom of the dropdown to create a new one.
           
           If an existing board is selected, fetch all boardarticles and display them in a non editable fashion.
           
           If a new board is created the user can optionally load the board via a file(2
           columns of a csv file with header matching akin to article/carrier file upload)
           The displayed board is then uneditable aswell, since its been created and saved.
           
           If a new board is created without fileupload the user can manually choose article-count pairs.

           Either way the board is created, it is firstly created empty with just a name and boardarticles are associated in the following step.
        """

        for ba in [art_randname, art_randname2]:
            resp_boardarticles_create = cls.CLIENT.post(
                "/api/boardarticle/",
                {
                    "name": f"{bor_randname}_{ba}",
                    "article": ba,
                    "count": 10,
                    "board": bor_randname,
                },
            )
            # pp(resp_boardarticles_create.__dict__)

        """ The above shows the manual option.
        """

        bb = Board.objects.all()
        b = bb.first()
        job = {
            "name": cls.get_random_name("job"),
            "board": b.name,
            "count": 100,
            "start_at": "2023-01-01 8:00:00.000",  # iso-8601
            "finish_at": "2023-01-01 18:00:00.000",
        }
        resp_job_create = cls.CLIENT.post("/api/job/", job)

        resp_job_display = cls.CLIENT.get(f'/api/job/{job["name"]}/?format=json')

        resp_job_display_boardarticles = cls.CLIENT.get(
            f'/api/boardarticle/?format=json&board={job["board"]}'
        )

        # for board article that is not in job's carriers article search available carriers and assign to job

        boardarticles = resp_job_display_boardarticles.json()["results"]
        jobs_carriers = resp_job_display.json()["carriers"]
        """
        print(f"The job:\n")
        pp(resp_job_display.json())

        print(f"The boardarticles:\n")
        pp(boardarticles)

        print(f"Checking if all boardarticles have corresponding jobcarrier.\n")"""
        for ba in boardarticles:
            # print(f"Checking {ba['article']}\n")
            for c in jobs_carriers:
                # print(f"against {c.name}")
                if ba["article"] == c["article"]:
                    # print(f"they match")
                    break
            else:
                # print(f"boardarticle {ba['article']} has no carrier\n")

                potential_carriers = cls.CLIENT.get(
                    f'/api/carrier/?article__name={ba["article"]}'
                )
                # print(f"potential carriers for article {ba['article']}:\n")
                # pp(potential_carriers.json())
                selected_carrier = potential_carriers.json()["results"][0]
                # print(f"For {ba['article']} the carrier {selected_carrier['name']} is selected.")
                assign_to_job_request = cls.CLIENT.post(
                    f"/api/assign_carrier_to_job/{job['name']}/{selected_carrier['name']}/"
                )

        resp_job_prepared_display = cls.CLIENT.get(
            f'/api/job/{job["name"]}/?format=json'
        )
        # print(f"job after assignment:\n")
        # pp(resp_job_prepared_display.json())

        articles_board = [ba["article"] for ba in boardarticles]
        articles_jobcarrier = [
            cls.CLIENT.get(f"/api/carrier/?name={c}").json()["results"][0]["article"]
            for c in resp_job_prepared_display.json()["carriers"]
        ]
        cls.assertEqual(sorted(articles_board), sorted(articles_jobcarrier))
