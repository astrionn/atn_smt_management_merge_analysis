# Test script for combined slots feature
# Save as: smt_management_app/scripts/test_combined_slots.py

from smt_management_app.models import Storage, StorageSlot, merge_storage_slots
from django.db import transaction


def run():
    """
    Test script to demonstrate combined slots functionality.

    This script:
    1. Creates a test storage with slots
    2. Demonstrates merging adjacent slots
    3. Tests LED control for combined slots
    4. Tests QR code lookup for combined slots
    """

    print("=== Combined Slots Feature Test ===\n")

    # Create test storage if it doesn't exist
    storage, created = Storage.objects.get_or_create(
        name="Test_Storage_Combined",
        defaults={
            "capacity": 100,
            "device": "Dummy",  # Use Dummy for testing without hardware
        },
    )

    if created:
        print(f"Created test storage: {storage.name}")
    else:
        print(f"Using existing storage: {storage.name}")

    # Create some test slots if they don't exist
    slots = []
    for i in range(1, 6):
        slot, created = StorageSlot.objects.get_or_create(
            name=i,
            storage=storage,
            defaults={
                "qr_value": f"QR_{storage.name}_{i:03d}",
                "diameter": 7,
                "width": 12,
            },
        )
        slots.append(slot)
        if created:
            print(f"Created slot {slot.name} with QR code: {slot.qr_value}")

    print("\n--- Testing Slot Merging ---")

    # Merge slots 2 and 3 into slot 1
    primary_slot = slots[0]  # Slot 1
    slots_to_merge = [slots[1], slots[2]]  # Slots 2 and 3

    print(f"\nBefore merging:")
    print(f"Primary slot {primary_slot.name}:")
    print(f"  - QR codes: {primary_slot.get_all_qr_codes()}")
    print(f"  - LED positions: {primary_slot.get_all_slot_names()}")
    print(f"  - Is combined: {primary_slot.is_combined_slot()}")

    try:
        # Perform the merge
        merged_slot = merge_storage_slots(primary_slot, *slots_to_merge)

        print(f"\nAfter merging:")
        print(f"Primary slot {merged_slot.name}:")
        print(f"  - QR codes: {merged_slot.get_all_qr_codes()}")
        print(f"  - LED positions: {merged_slot.get_all_slot_names()}")
        print(f"  - Is combined: {merged_slot.is_combined_slot()}")
        print(f"  - Dimensions: {merged_slot.diameter}mm x {merged_slot.width}mm")

        # Verify slots 2 and 3 are deleted
        print(f"\nSlots deleted: {[s.name for s in slots_to_merge]}")

    except ValueError as e:
        print(f"Error during merge: {e}")

    print("\n--- Testing LED Control ---")

    # Test LED control
    from smt_management_app.utils.led_shelf_dispatcher import LED_shelf_dispatcher

    dispatcher = LED_shelf_dispatcher(storage)

    # Turn on LED for the combined slot
    print(f"\nTurning on LEDs for combined slot {merged_slot.name}")
    dispatcher.led_on(merged_slot.name, "blue")
    print("(In real hardware, LEDs 1, 2, and 3 would all turn blue)")

    # Turn off LED
    print(f"\nTurning off LEDs for combined slot {merged_slot.name}")
    dispatcher.led_off(merged_slot.name)

    print("\n--- Testing QR Code Lookup ---")

    # Test QR code lookup
    from smt_management_app.collecting import find_slot_by_qr_code, slot_matches_qr_code

    # Test finding slot by any of its QR codes
    test_qr_codes = [
        "QR_Test_Storage_Combined_001",
        "QR_Test_Storage_Combined_002",
        "QR_Test_Storage_Combined_003",
    ]

    for qr_code in test_qr_codes:
        found_slot = find_slot_by_qr_code(qr_code, storage.name)
        if found_slot:
            print(f"\nQR code '{qr_code}' found slot: {found_slot.name}")
            print(f"  - Matches: {slot_matches_qr_code(found_slot, qr_code)}")
        else:
            print(f"\nQR code '{qr_code}' not found")

    print("\n--- Testing Multiple Combined Slots ---")

    # Create another combined slot from slots 4 and 5
    if len(StorageSlot.objects.filter(storage=storage, name__in=[4, 5])) == 2:
        slot_4 = StorageSlot.objects.get(storage=storage, name=4)
        slot_5 = StorageSlot.objects.get(storage=storage, name=5)

        merged_slot_2 = merge_storage_slots(slot_4, slot_5)
        print(f"\nCreated second combined slot from slots 4 and 5:")
        print(f"  - QR codes: {merged_slot_2.get_all_qr_codes()}")
        print(f"  - LED positions: {merged_slot_2.get_all_slot_names()}")

    print("\n--- Summary ---")

    # Show all remaining slots in the storage
    remaining_slots = StorageSlot.objects.filter(storage=storage).order_by("name")
    print(f"\nRemaining slots in {storage.name}:")
    for slot in remaining_slots:
        print(f"  Slot {slot.name}:")
        print(f"    - QR codes: {slot.get_all_qr_codes()}")
        print(f"    - LED positions: {slot.get_all_slot_names()}")
        print(f"    - Combined: {slot.is_combined_slot()}")

    print("\n=== Test Complete ===")


# Usage notes:
# To run this test:
# python manage.py runscript test_combined_slots
#
# To test with real carriers:
# 1. Create carriers and store them
# 2. Use the merge_storage_slots function to combine slots
# 3. Try collecting carriers using either QR code
# 4. Verify both LEDs light up
