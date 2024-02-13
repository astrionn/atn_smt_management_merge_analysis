from pprint import pprint as pp

from django.test import TestCase
from django.test.client import Client

from smt_management_app.models import (
    Article,
    Carrier,
    Storage,
    StorageSlot,
)


class StoringTestCase(TestCase):

    def setUp(self):
        print("Running tests for storing.")
        self.client = Client()

        self.article_name = "article_0"
        Article.objects.create(name=self.article_name)

        self.carrier_name = "carrier_0"
        Carrier.objects.create(
            name=self.carrier_name,
            article=Article(self.article_name),
            delivered=True,
        )

        self.storage_name = "storage_0"
        Storage.objects.create(name=self.storage_name, device="Dummy", capacity=1400)

        self.storage_slot_names = [i for i in range(1, 1401)]
        for storage_slot_name in self.storage_slot_names:
            StorageSlot.objects.create(
                name=storage_slot_name,
                qr_value=f"{self.storage_name}_{storage_slot_name}_qr_value",
                storage=Storage(self.storage_name),
            )

    def test_workinglight_on(self):
        query = input(f"Are all workinglights of {self.storage_name} green ? [Y/n]")
        if query.lower() == "n":
            raise Exception

    def test_store_carrier_success(self):
        # user does everything right
        carrier_name = self.carrier_name
        storage_name = self.storage_name
        response_store = self.client.get(
            f"/api/store_carrier/{carrier_name}/{storage_name}/"
        )

        if not response_store.json()["success"]:
            raise Exception
        slot_name = response_store.json()["slot"]
        query = input(
            f"Is slot {slot_name} of storage {storage_name} blue and is the workinglight yellow? [Y/n]"
        )
        if query.lower() == "n":
            raise Exception

        response_confirm = self.client.get(
            f"/api/store_carrier_confirm/{carrier_name}/{storage_name}/{slot_name}/"
        )
        if not response_confirm.json()["success"]:
            raise Exception

        query = input(
            f"Is slot {slot_name} of storage {storage_name} turned off and is the workinglight back to only green ? [Y/n]"
        )
        if query.lower() == "n":
            raise Exception

    def test_store_carrier_fail_wrong_slot(self):
        # user scans wrong slot
        carrier_name = self.carrier_name
        storage_name = self.storage_name

        response_store = self.client.get(
            f"/api/store_carrier/{carrier_name}/{storage_name}/"
        )
        if not response_store.json()["success"]:
            raise Exception
        slot_name = response_store.json()["slot"]
        query = input(
            f"Is slot {slot_name} of storage {storage_name} blue and is the workinglight yellow? [Y/n]"
        )
        if query.lower() == "n":
            raise Exception

        for slot in self.storage_slot_names:
            false_slot_name = slot
            if not false_slot_name == slot_name:
                break

        response_confirm = self.client.get(
            f"/api/store_carrier_confirm/{carrier_name}/{storage_name}/{false_slot_name}/"
        )
        if response_confirm.json()["success"]:
            raise Exception
        query = input(
            f"Is slot {false_slot_name} of storage {storage_name} red for a short duration? [Y/n]"
        )
        if query.lower() == "n":
            raise Exception

    def test_store_carrier_fail_carrier_does_not_exists(self):
        carrier_name = "carrier_that_doesn_not_exsist"
        storage_name = self.storage_name

        response_store = self.client.get(
            f"/api/store_carrier/{carrier_name}/{storage_name}/"
        )
        if response_store.json()["success"]:
            raise Exception

    def test_store_carrier_fail_carrier_is_collecting(self):
        carrier_name = self.carrier_name
        storage_name = self.storage_name
        response_store = self.client.get(
            f"/api/store_carrier/{carrier_name}/{storage_name}/"
        )
        response_confirm = self.client.get(
            f"/api/store_carrier_confirm/{carrier_name}/{storage_name}/{response_store.json()['slot']}/"
        )
        response_collecting = self.client.patch(f"/api/collect_carrier/{carrier_name}/")
        response_store_again = self.client.get(
            f"/api/store_carrier/{carrier_name}/{storage_name}/"
        )
        if response_store_again.json()["success"]:
            raise Exception

    def test_store_carrier_fail_carrier_is_archived(self):
        carrier_name = self.carrier_name
        storage_name = self.storage_name
        response_archive = self.client.patch(
            f"/api/carrier/{carrier_name}/", json={"archived": True}
        )
        response_store = self.client.get(
            f"/api/store_carrier/{carrier_name}/{storage_name}/"
        )
        if response_store.json()["success"]:
            pp(response_archive.json())
            raise Exception

    def test_store_carrier_fail_is_not_delivered(self):
        carrier_name = self.carrier_name
        storage_name = self.storage_name
        response_archive = self.client.patch(
            f"/api/carrier/{carrier_name}/", {"delivered": False}
        )
        response_store = self.client.get(
            f"/api/store_carrier/{carrier_name}/{storage_name}/"
        )
        if response_store.json()["success"]:
            raise Exception

    def test_store_carrier_fail_is_stored(self):
        carrier_name = self.carrier_name
        storage_name = self.storage_name
        response_store = self.client.get(
            f"/api/store_carrier/{carrier_name}/{storage_name}/"
        )
        slot_name = response_store.json()["slot"]
        response_confirm = self.client.get(
            f"/api/store_carrier_confirm/{carrier_name}/{storage_name}/{slot_name}/"
        )
        response_store_again = self.client.get(
            f"/api/store_carrier/{carrier_name}/{storage_name}/"
        )
        if response_store_again.json()["success"]:
            raise Exception

    def test_store_carrier_fail_storage_does_not_exists(self):
        carrier_name = self.carrier_name
        storage_name = "stroage_that_does_not_exsist"

        response_store = self.client.get(
            f"/api/store_carrier/{carrier_name}/{storage_name}/"
        )
        if response_store.json()["success"]:
            raise Exception

    def test_store_carrier_fail_no_free_slot(self):
        # create Carrier for every slot and fill the slot
        article = Article.objects.get(name=self.article_name)
        for slot_name in self.storage_slot_names:
            slot = StorageSlot.objects.get(name=slot_name)
            Carrier.objects.create(
                name=f"carrier_{slot_name}", storage_slot=slot, article=article
            )
        carrier_name = self.carrier_name
        storage_name = self.storage_name
        response_store = self.client.get(
            f"/api/store_carrier/{carrier_name}/{storage_name}/"
        )

        if response_store.json()["success"]:
            raise Exception

    def test_store_carrier_choose_slot_flow(self):
        pass
