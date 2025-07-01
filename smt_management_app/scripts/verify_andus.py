from smt_management_app.models import Storage, StorageSlot


def run():
    """
    Verification script for S11501 storage setup.
    Checks if the storage and slots were created correctly.
    """
    try:
        storage = Storage.objects.get(name="Storage_S11501")
        print(f"Found storage: {storage.name} with capacity {storage.capacity}")

        # Get total slot count
        total_slots = StorageSlot.objects.filter(storage=storage).count()
        print(f"Total slots in database: {total_slots}")

        # Check some sample slots from each section
        sample_qrs = [
            "S11501-01-001",  # First slot row 1
            "S11501-01-200",  # Last slot row 1
            "S11501-02-001",  # First slot row 2
            "S11501-02-200",  # Last slot row 2
            "S11501-03-001",  # First slot row 3
            "S11501-03-200",  # Last slot row 3
            "S11501-04-001",  # First slot row 4
            "S11501-04-200",  # Last slot row 4
            "S11501-05-001",  # First double-LED slot
            "S11501-05-132",  # Last double-LED slot
            "S11501-06-001",  # First slot row 6
            "S11501-06-033",  # Last double-LED in row 6
            "S11501-06-034",  # First triple-LED in row 6
            "S11501-06-099",  # Last slot
        ]

        print("\nSample slot verification:")
        found_slots = 0
        for qr in sample_qrs:
            try:
                slot = StorageSlot.objects.get(storage=storage, qr_value=qr)
                related_info = ""
                if hasattr(slot, "related_names") and slot.related_names:
                    related_info = f" (+ related LEDs: {slot.related_names})"
                print(f"  ✓ {qr}: Slot {slot.name}{related_info}")
                found_slots += 1
            except StorageSlot.DoesNotExist:
                print(f"  ✗ {qr}: NOT FOUND")

        print(f"\nVerification results:")
        print(f"  Sample slots found: {found_slots}/{len(sample_qrs)}")

        # Count slots by row for detailed verification
        print(f"\nSlot count by row:")
        for row in range(1, 7):
            row_slots = StorageSlot.objects.filter(
                storage=storage, qr_value__startswith=f"S11501-{str(row).zfill(2)}-"
            ).count()
            print(f"  Row {row}: {row_slots} slots")

        # Expected counts
        expected_counts = {
            1: 200,
            2: 200,
            3: 200,
            4: 200,  # Single LED rows
            5: 132,  # Double LED row
            6: 99,  # Mixed LED row (33 double + 66 triple)
        }

        print(f"\nExpected vs Actual:")
        all_correct = True
        for row, expected in expected_counts.items():
            actual = StorageSlot.objects.filter(
                storage=storage, qr_value__startswith=f"S11501-{str(row).zfill(2)}-"
            ).count()
            status = "✓" if actual == expected else "✗"
            print(f"  Row {row}: {actual}/{expected} {status}")
            if actual != expected:
                all_correct = False

        expected_total = sum(expected_counts.values())
        total_status = "✓" if total_slots == expected_total else "✗"
        print(f"  Total: {total_slots}/{expected_total} {total_status}")

        if all_correct and found_slots == len(sample_qrs):
            print(f"\n🎉 Verification PASSED! Storage setup is correct.")
        else:
            print(f"\n⚠️ Verification FAILED! Some issues detected.")

    except Storage.DoesNotExist:
        print("❌ Storage 'Storage_S11501' not found.")
        print("Make sure to run the main setup script first.")
        return

    except Exception as e:
        print(f"❌ Error during verification: {str(e)}")


def detailed_verification():
    """
    Run a more detailed verification with LED position analysis
    """
    try:
        storage = Storage.objects.get(name="Storage_S11501")
        print(f"=== DETAILED VERIFICATION ===")
        print(f"Storage: {storage.name}")

        # Analyze LED positions for multi-LED slots
        print(f"\nAnalyzing LED positions for multi-LED slots:")

        # Check row 5 (double LED)
        print(f"\nRow 5 (Double LED slots):")
        row5_slots = StorageSlot.objects.filter(
            storage=storage, qr_value__startswith="S11501-05-"
        ).order_by("qr_value")[
            :5
        ]  # First 5 for sample

        for slot in row5_slots:
            related_info = ""
            if hasattr(slot, "related_names") and slot.related_names:
                related_info = f" + {slot.related_names}"
            print(f"  {slot.qr_value}: LED {slot.name}{related_info}")

        # Check row 6 (mixed LED)
        print(f"\nRow 6 (Mixed LED slots - first few from each section):")

        # Double LED section (001-033)
        row6_double = (
            StorageSlot.objects.filter(
                storage=storage, qr_value__startswith="S11501-06-"
            )
            .filter(qr_value__regex=r"S11501-06-0[0-2][0-9]$")
            .order_by("qr_value")[:3]
        )

        for slot in row6_double:
            related_info = ""
            if hasattr(slot, "related_names") and slot.related_names:
                related_info = f" + {slot.related_names}"
            print(f"  {slot.qr_value}: LED {slot.name}{related_info} (double)")

        # Triple LED section (034-099)
        row6_triple = (
            StorageSlot.objects.filter(
                storage=storage, qr_value__startswith="S11501-06-"
            )
            .filter(qr_value__regex=r"S11501-06-0[3-4][0-9]$")
            .order_by("qr_value")[:3]
        )

        for slot in row6_triple:
            related_info = ""
            if hasattr(slot, "related_names") and slot.related_names:
                related_info = f" + {slot.related_names}"
            print(f"  {slot.qr_value}: LED {slot.name}{related_info} (triple)")

        print(f"\n=== END DETAILED VERIFICATION ===")

    except Storage.DoesNotExist:
        print("❌ Storage not found for detailed verification.")


if __name__ == "__main__":
    # Run basic verification
    run()

    # Uncomment the line below to run detailed verification too
    # detailed_verification()
