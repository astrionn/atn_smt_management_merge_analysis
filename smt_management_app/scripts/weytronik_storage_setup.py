from smt_management_app.models import StorageSlot


def run():
    qs = StorageSlot.objects.all().order_by("name")
    for ss in qs:
        print(f"\n{ss.name}")
        i = int(ss.name)
        if i > 700:
            i -= 700

        row = (i - 1) // 100 + 1
        lamp = (i - 1) % 100 + 1
        if int(ss.name) > 700:
            lamp += 100
        print(f"row {row}")
        print(f"lamp {lamp}")
        ss.qr_value = f"001-{str(row).zfill(2)}-{str(lamp).zfill(3)}"
        print(ss.qr_value)
        print()
        ss.save()
