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

        self.article_names = [f"article_{i}" for i in range(1, 10)]
        for article_name in self.article_names:
            Article.objects.create(name=article_name)

        self.carrier_names = [f"carrier_{i}" for i in range(1, 10)]
        for i, carrier_name in enumerate(self.carrier_names):
            Carrier.objects.create(
                name=carrier_name,
                article=Article(self.article_names[i]),
                delivered=True,
            )

        self.storage_names = [f"storage_{i}" for i in range(1, 3)]
        for storage_name in self.storage_names:
            Storage.objects.create(name=storage_name, device="Dummy", capacity=1400)

        self.storage_slot_names = [i for i in range(1, 1401)]
        for storage_slot_name in self.storage_slot_names:
            StorageSlot.objects.create(
                name=storage_slot_name,
                qr_value=f"{self.storage_names[0]}_{storage_slot_name}_qr_value",
                storage=Storage(self.storage_names[0]),
            )
            StorageSlot.objects.create(
                name=storage_slot_name,
                qr_value=f"{self.storage_names[1]}_{storage_slot_name}_qr_value",
                storage=Storage(self.storage_names[1]),
            )

    def test_workinglight_on_start(self):
        query = input(f"Are all workinglights of {self.storage_names} green ? [Y/n]")
        if query.lower() == "n":
            raise Exception

    def test_store_carrier_flow(self):

        # user does everything right
        for i, carrier_name in enumerate(self.carrier_names[:-5]):
            storage_name = self.storage_names[(i % 2) - 1]
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

        # user scans wrong slot
        carrier_name = self.carrier_names[-5]
        storage_name = self.storage_names[0]
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

        false_slot_name = slot_name
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

    def test_store_carrier_choose_slot_flow(self):
        pass
