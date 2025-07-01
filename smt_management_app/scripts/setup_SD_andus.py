from smt_management_app.models import Storage, StorageSlot


def run():
    storage = Storage.objects.create(
        name=f"Storage_1",
        capacity=1031,  # LEDs 0-1030
        device="Dummy",
    )

    # Define row configurations
    rows_config = [
        {"row": 1, "max_slots": 200},
        {"row": 2, "max_slots": 200},
        {"row": 3, "max_slots": 200},
        {"row": 4, "max_slots": 200},
        {"row": 5, "max_slots": 132},
        {"row": 6, "max_slots": 99},
    ]

    # Calculate first half limits for each row
    first_half_limits = [
        100,  # Row 1: 001-100
        100,  # Row 2: 001-100
        100,  # Row 3: 001-100
        100,  # Row 4: 001-100
        66,  # Row 5: 001-066
        33,  # Row 6: 001-033
    ]

    led_number = 0

    # Phase 1: First half of each row
    print("Creating first half of each row...")
    for row_idx, config in enumerate(rows_config):
        row_num = config["row"]
        first_half_limit = first_half_limits[row_idx]

        for slot_num in range(1, first_half_limit + 1):
            qr_val = f"S11501-{str(row_num).zfill(2)}-{str(slot_num).zfill(3)}"

            storage_slot = StorageSlot.objects.create(
                name=led_number, storage=storage, qr_value=qr_val
            )

            print(f"LED {led_number}: {qr_val}")
            led_number += 1

    # Phase 2: Second half of each row
    print(f"\nStarting second half at LED {led_number}...")
    for row_idx, config in enumerate(rows_config):
        row_num = config["row"]
        max_slots = config["max_slots"]
        first_half_limit = first_half_limits[row_idx]

        # Only create second half if there are slots beyond the first half
        if max_slots > first_half_limit:
            for slot_num in range(first_half_limit + 1, max_slots + 1):
                qr_val = f"S11501-{str(row_num).zfill(2)}-{str(slot_num).zfill(3)}"

                storage_slot = StorageSlot.objects.create(
                    name=led_number, storage=storage, qr_value=qr_val
                )

                print(f"LED {led_number}: {qr_val}")
                led_number += 1

    print(f"\nTotal LEDs created: {led_number} (0-{led_number-1})")

    # Verification: Print some key mappings
    print("\n=== Verification ===")
    print("First few LEDs:")
    for i in range(5):
        slot = StorageSlot.objects.get(name=i, storage=storage)
        print(f"LED {i}: {slot.qr_value}")

    print("\nTransition around LED 99-101:")
    for i in range(98, 102):
        slot = StorageSlot.objects.get(name=i, storage=storage)
        print(f"LED {i}: {slot.qr_value}")

    print("\nSecond half start:")
    # Calculate where second half starts (after all first halves)
    second_half_start = sum(first_half_limits)
    for i in range(second_half_start - 1, second_half_start + 2):
        slot = StorageSlot.objects.get(name=i, storage=storage)
        print(f"LED {i}: {slot.qr_value}")
