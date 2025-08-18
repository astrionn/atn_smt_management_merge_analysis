from smt_management_app.models import *
import random


def run():
    storage = Storage.objects.create(
        name=f"Storage_3",
        capacity=1400,
        device="NeoLight",
        ip_address="192.168.178.222",
        ip_port=5000,
    )

    storage_slots = []

    for i in range(1, 1401):
        storage_slot = StorageSlot.objects.create(name=i - 1, storage=storage)
        storage_slots.append(storage_slot)

        if i > 700:
            i -= 700

        row = (i - 1) // 100 + 1
        lamp = (i - 1) % 100 + 1

        # Changed condition from > 700 to >= 700 since names are now 0-indexed
        if int(storage_slot.name) >= 700:
            lamp += 100

        qr_val = f"003-{str(row).zfill(2)}-{str(lamp).zfill(3)}"

        storage_slot.qr_value = qr_val
        storage_slot.save()
