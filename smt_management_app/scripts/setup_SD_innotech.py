from ipaddress import ip_address
from smt_management_app.models import Storage, StorageSlot


def run():
    """
    Setup script for S11227-01-001 storage rack

    Rack specifications:
    - 1400 slots total (7 rows × 200 slots per row)
    - 0-based lamp numbering (lamp 0 = first slot)
    - Row structure:
      * Row 1: S11227-01-001 to S11227-01-200 (lamps 0-199)
      * Row 2: S11227-02-001 to S11227-02-200 (lamps 200-399)
      * Row 3: S11227-03-001 to S11227-03-200 (lamps 400-599)
      * Row 4: S11227-04-001 to S11227-04-200 (lamps 600-799)
      * Row 5: S11227-05-001 to S11227-05-200 (lamps 800-999)
      * Row 6: S11227-06-001 to S11227-06-200 (lamps 1000-1199)
      * Row 7: S11227-07-001 to S11227-07-200 (lamps 1200-1399)
    """

    # Create the storage object
    storage = Storage.objects.create(
        name="Storage_S11227",
        capacity=1400,
        device="NeoLight",
        ip_address="192.168.188.23",
        ip_port=5000,
    )

    print(f"Created storage: {storage.name} with capacity {storage.capacity}")

    # Create storage slots
    for lamp_number in range(1400):  # Lamp 0 to 1399
        # Calculate row and position within row (200 slots per row)
        row = (lamp_number // 200) + 1
        position_in_row = (lamp_number % 200) + 1

        qr_value = f"S11227-{str(row).zfill(2)}-{str(position_in_row).zfill(3)}"

        storage_slot = StorageSlot.objects.create(
            name=lamp_number,  # 0-based lamp numbering
            storage=storage,
            qr_value=qr_value,
        )

        # Print progress every 200 slots (end of each row)
        if lamp_number % 200 == 199:
            print(f"Completed row {row}: Lamp {lamp_number-199} to {lamp_number}")

    print(f"\nSetup complete! Created {storage.capacity} storage slots.")

    # Verification output
    print("\n=== Verification ===")
    print("First few slots:")
    for i in range(5):
        slot = StorageSlot.objects.get(name=i, storage=storage)
        print(f"Lamp {i}: {slot.qr_value}")

    print("\nEnd of Row 1 / Start of Row 2:")
    for i in range(198, 203):
        slot = StorageSlot.objects.get(name=i, storage=storage)
        print(f"Lamp {i}: {slot.qr_value}")

    print("\nEnd of Row 2 / Start of Row 3:")
    for i in range(398, 403):
        slot = StorageSlot.objects.get(name=i, storage=storage)
        print(f"Lamp {i}: {slot.qr_value}")

    print("\nLast few slots:")
    for i in range(1395, 1400):
        slot = StorageSlot.objects.get(name=i, storage=storage)
        print(f"Lamp {i}: {slot.qr_value}")


def verify_setup():
    """
    Verification function to check if the setup was created correctly
    """
    try:
        storage = Storage.objects.get(name="Storage_S11227")

        print(f"=== VERIFICATION REPORT ===")
        print(f"Storage: {storage.name}")
        print(f"Capacity: {storage.capacity}")
        print(f"Device: {storage.device}")

        # Check total count
        slot_count = StorageSlot.objects.filter(storage=storage).count()
        print(f"Total slots created: {slot_count}")

        # Check slots per row
        print(f"\nSlots per row:")
        all_rows_correct = True
        for row in range(1, 8):  # 7 rows
            row_count = StorageSlot.objects.filter(
                storage=storage, qr_value__startswith=f"S11227-{str(row).zfill(2)}-"
            ).count()
            status = "✓" if row_count == 200 else "✗"
            print(f"  Row {row}: {row_count}/200 {status}")
            if row_count != 200:
                all_rows_correct = False

        # Test key mappings
        test_cases = [
            (0, "S11227-01-001"),  # First slot
            (199, "S11227-01-200"),  # Last slot of row 1
            (200, "S11227-02-001"),  # First slot of row 2
            (399, "S11227-02-200"),  # Last slot of row 2
            (400, "S11227-03-001"),  # First slot of row 3
            (1399, "S11227-07-200"),  # Last slot (row 7, position 200)
        ]

        print(f"\nTesting key mappings:")
        all_correct = True

        for lamp_num, expected_qr in test_cases:
            try:
                slot = StorageSlot.objects.get(name=lamp_num, storage=storage)
                if slot.qr_value == expected_qr:
                    print(f"✓ Lamp {lamp_num}: {slot.qr_value}")
                else:
                    print(
                        f"✗ Lamp {lamp_num}: Expected {expected_qr}, got {slot.qr_value}"
                    )
                    all_correct = False
            except StorageSlot.DoesNotExist:
                print(f"✗ Lamp {lamp_num}: Slot not found")
                all_correct = False

        if all_correct and all_rows_correct and slot_count == 1400:
            print(f"\n✓ Setup verification PASSED! All slots correctly configured.")
        else:
            print(f"\n⚠️ Setup verification FAILED! Please check the configuration.")

    except Storage.DoesNotExist:
        print("❌ Storage 'Storage_S11227' not found.")
        print("Make sure to run the main setup script first.")


if __name__ == "__main__":
    # Run setup
    run()

    # Run verification
    print("\n" + "=" * 50)
    verify_setup()
