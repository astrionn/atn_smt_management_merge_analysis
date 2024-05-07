from smt_management_app.models import Storage, StorageSlot


def run():
    storage = Storage.objects.get(
        name="Storage_2",
    )

    for i, j in enumerate(range(1, storage.capacity + 1)):
        i+=1
        if i > 700:
            i -= 700

        row = (i - 1) // 100 + 1
        lamp = (i - 1) % 100 + 1
        if j > 700:
            lamp += 100
        # modify head of following line for storage 1/2/3...
        qr_value = f"002-{str(row).zfill(2)}-{str(lamp).zfill(3)}"
        slot = StorageSlot.objects.create(name=j, storage=storage, qr_value=qr_value)
        #print(f"{i=} || {j=} || {row=} || {lamp=} || {qr_value=} " )
