from smt_management_app.models import *
import random


def run():
    storage = Storage.objects.create(name=f"Storage_1", capacity=1400, device="Dummy")
    # storage2 = Storage.objects.create(name=f"Storage_2", capacity=1400, device="Dummy")

    storage_slots = []
    # storage2_slots = []

    for i in range(1, 1401):
        storage_slot = StorageSlot.objects.create(name=i, storage=storage)
        # storage_slot2 = StorageSlot.objects.create(name=i, storage=storage2)
        storage_slots.append(storage_slot)
        # storage2_slots.append(storage_slot2)
        if i > 700:
            i -= 700

        row = (i - 1) // 100 + 1
        lamp = (i - 1) % 100 + 1
        if int(storage_slot.name) > 700:
            lamp += 100

        qr_val = f"S11227-{str(row).zfill(2)}-{str(lamp).zfill(3)}"

        storage_slot.qr_value = qr_val
        storage_slot.save()

        # storage_slot2.qr_value = qr_val
        # storage_slot2.save()
