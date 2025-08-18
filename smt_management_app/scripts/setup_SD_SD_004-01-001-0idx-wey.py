from smt_management_app.models import Storage, StorageSlot


def run():
    storage = Storage.objects.create(
        name=f"Storage_4",
        capacity=1060,  # Total LEDs: 2×200 + 5×132 = 1060
        device="NeoLight",
        ip_address="192.168.178.223",
        ip_port=5000,
    )

    led_number = 0

    print("Creating storage slots for rack 004...")
    print("Phase 1: First half of each layer...")

    # Phase 1: First halves of all layers
    # Layer 1 first half: 004-01-001 to 004-01-100
    print("Layer 1 first half (001-100)...")
    for slot_num in range(1, 101):
        qr_val = f"004-01-{str(slot_num).zfill(3)}"
        storage_slot = StorageSlot.objects.create(
            name=led_number, storage=storage, qr_value=qr_val
        )
        led_number += 1

    # Layer 2 first half: 004-02-001 to 004-02-100
    print("Layer 2 first half (001-100)...")
    for slot_num in range(1, 101):
        qr_val = f"004-02-{str(slot_num).zfill(3)}"
        storage_slot = StorageSlot.objects.create(
            name=led_number, storage=storage, qr_value=qr_val
        )
        led_number += 1

    # Layers 3-7 first halves: 66 slots each (132/2 = 66)
    for layer in range(3, 8):
        print(f"Layer {layer} first half (001-066)...")
        for slot_num in range(1, 67):  # 1-66
            qr_val = f"004-{str(layer).zfill(2)}-{str(slot_num).zfill(3)}"
            storage_slot = StorageSlot.objects.create(
                name=led_number, storage=storage, qr_value=qr_val
            )
            led_number += 1

    print(f"\nAfter first halves, LED number is: {led_number}")
    print("Phase 2: Second half of each layer...")

    # Phase 2: Second halves of all layers
    # Layer 1 second half: 004-01-101 to 004-01-200
    print("Layer 1 second half (101-200)...")
    for slot_num in range(101, 201):
        qr_val = f"004-01-{str(slot_num).zfill(3)}"
        storage_slot = StorageSlot.objects.create(
            name=led_number, storage=storage, qr_value=qr_val
        )
        led_number += 1

    # Layer 2 second half: 004-02-101 to 004-02-200
    print("Layer 2 second half (101-200)...")
    for slot_num in range(101, 201):
        qr_val = f"004-02-{str(slot_num).zfill(3)}"
        storage_slot = StorageSlot.objects.create(
            name=led_number, storage=storage, qr_value=qr_val
        )
        led_number += 1

    # Layers 3-7 second halves: 66 slots each (67-132)
    for layer in range(3, 8):
        print(f"Layer {layer} second half (067-132)...")
        for slot_num in range(67, 133):  # 67-132
            qr_val = f"004-{str(layer).zfill(2)}-{str(slot_num).zfill(3)}"
            storage_slot = StorageSlot.objects.create(
                name=led_number, storage=storage, qr_value=qr_val
            )
            led_number += 1

    print(f"\nTotal LEDs created: {led_number} (0-{led_number-1})")

    # Verification: Print key mappings
    print("\n=== Verification ===")
    test_mappings = [
        (0, "004-01-001"),
        (99, "004-01-100"),
        (100, "004-02-001"),
        (199, "004-02-100"),
        (200, "004-03-001"),
        (265, "004-03-066"),
        (266, "004-04-001"),
        (529, "004-07-066"),
        (530, "004-01-101"),
        (629, "004-01-200"),
        (630, "004-02-101"),
        (729, "004-02-200"),
        (730, "004-03-067"),
        (1059, "004-07-132"),
    ]

    print("Key LED mappings:")
    for led_id, expected_qr in test_mappings:
        if led_id < led_number:
            slot = StorageSlot.objects.get(name=led_id, storage=storage)
            status = "✓" if slot.qr_value == expected_qr else "✗"
            print(f"LED {led_id}: {slot.qr_value} {status}")
        else:
            print(f"LED {led_id}: Out of range")
