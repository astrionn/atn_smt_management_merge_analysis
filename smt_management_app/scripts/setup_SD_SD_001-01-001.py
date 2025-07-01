from ipaddress import ip_address
from smt_management_app.models import *


def run():
    storage = Storage.objects.create(
        name=f"Storage_1",
        capacity=1400,
        device="Dummy",
    )
    # storage2 = Storage.objects.create(name=f"Storage_2", capacity=1400, device="Dummy")

    storage_slots = []
    # storage2_slots = []

    for i in range(1400):  # 0 to 1399
        storage_slot = StorageSlot.objects.create(name=i, storage=storage)
        storage_slots.append(storage_slot)

        # Calculate the sequence pattern
        # Every 200 iterations: first part increments, last part resets to 001
        first_part = (i // 200) + 1  # 1, 2, 3, 4, 5, 6, 7 (for 1400 slots)
        last_part = (i % 200) + 1  # 1-200, then resets
        # Format QR value: S11227-XX-XXX
        qr_val = f"S11501-{str(first_part).zfill(2)}-{str(last_part).zfill(3)}"
        storage_slot.qr_value = qr_val
        storage_slot.save()
        print(f"Created slot {storage_slot.name} with QR code: {storage_slot.qr_value}")

        # storage_slot2.qr_value = qr_val
        # storage_slot2.save()
