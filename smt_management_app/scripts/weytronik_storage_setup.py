from smt_management_app.models import Storage, StorageSlot


def run():
    storage = Storage.objects.create(
        name="Storage_1",
        capacity=1400,
        device="NeoLight",
        ip_address="192.168.178.11",
        ip_port=5000,
    )

    for i, j in enumerate(range(1, storage.capacity + 1)):
        if i > 700:
            i -= 700

        row = (i - 1) // 100 + 1
        lamp = (i - 1) % 100 + 1
        if j > 700:
            lamp += 100
        qr_value = f"001-{str(row).zfill(2)}-{str(lamp).zfill(3)}"
        slot = StorageSlot.objects.create(name=j, storage=storage, qr_value=qr_value)
