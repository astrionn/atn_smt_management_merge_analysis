from ipaddress import ip_address
from smt_management_app.models import Storage, StorageSlot
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
