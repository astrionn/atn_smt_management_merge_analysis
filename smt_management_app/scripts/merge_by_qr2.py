# Save as: smt_management_app/scripts/merge_by_qr_codes_improved.py

from smt_management_app.models import StorageSlot, merge_storage_slots, Storage
from smt_management_app.collecting import find_slot_by_qr_code
from smt_management_app.utils.led_shelf_dispatcher import LED_shelf_dispatcher
from django.db import transaction
from threading import Thread
import time


def light_up_slots(slots, color="yellow"):
    """
    Light up a list of slots with the specified color.

    Args:
        slots: List of StorageSlot objects to light up
        color: Color to use (default: yellow)
    """
    # Group slots by storage to create dispatchers
    storage_dispatchers = {}

    for slot in slots:
        storage = slot.storage
        if storage.name not in storage_dispatchers:
            storage_dispatchers[storage.name] = LED_shelf_dispatcher(storage)

        # Set LED state and start lighting thread
        slot.led_state = 1
        slot.save()

        Thread(
            target=storage_dispatchers[storage.name].led_on,
            kwargs={"lamp": slot.name, "color": color},
        ).start()


def turn_off_slots(slots):
    """
    Turn off LEDs for a list of slots.

    Args:
        slots: List of StorageSlot objects to turn off
    """
    # Group slots by storage to create dispatchers
    storage_dispatchers = {}

    for slot in slots:
        storage = slot.storage
        if storage.name not in storage_dispatchers:
            storage_dispatchers[storage.name] = LED_shelf_dispatcher(storage)

        # Set LED state and turn off
        slot.led_state = 0
        slot.save()

        Thread(
            target=storage_dispatchers[storage.name].led_off, kwargs={"lamp": slot.name}
        ).start()


def find_master_slot_for_qr(qr_code):
    """
    Find the master slot that contains this QR code.
    Returns the actual master slot, not a related slot.
    """
    # First try to find by primary qr_value
    try:
        slot = StorageSlot.objects.get(qr_value=qr_code)
        return slot
    except StorageSlot.DoesNotExist:
        pass

    # Then search in qr_codes arrays (this means it's part of a combined slot)
    slots_with_qr = StorageSlot.objects.filter(qr_codes__contains=[qr_code])
    if slots_with_qr.exists():
        return slots_with_qr.first()

    return None


def validate_merge_operation(slot1, slot2):
    """
    Validate that two slots can be merged.
    Returns (is_valid, error_message, operation_type)

    operation_type can be:
    - 'merge_independent': Both slots are independent
    - 'extend_combined': Adding independent slot to combined slot
    - 'already_combined': Slots are already part of the same combined slot
    - 'invalid': Cannot merge
    """

    # Check if slots are from the same storage
    if slot1.storage != slot2.storage:
        return (
            False,
            f"Slots are from different storages: {slot1.storage.name} vs {slot2.storage.name}",
            "invalid",
        )

    # Check if slots are occupied
    for slot in [slot1, slot2]:
        if hasattr(slot, "carrier") and slot.carrier:
            return (
                False,
                f"Slot {slot.name} is occupied by carrier {slot.carrier.name}",
                "invalid",
            )
        if hasattr(slot, "nominated_carrier") and slot.nominated_carrier:
            return (
                False,
                f"Slot {slot.name} has nominated carrier {slot.nominated_carrier.name}",
                "invalid",
            )

    # Get all slot names that each slot controls
    slot1_names = set(slot1.get_all_slot_names())
    slot2_names = set(slot2.get_all_slot_names())

    # Check if there's any overlap in the slot names they control
    overlap = slot1_names.intersection(slot2_names)
    if overlap:
        if slot1_names == slot2_names:
            return (
                False,
                f"Slots {slot1.name} and {slot2.name} are already part of the same combined slot (controlling slots: {sorted(overlap)})",
                "already_combined",
            )
        else:
            return (
                False,
                f"Slots have overlapping controlled slots: {sorted(overlap)}",
                "invalid",
            )

    # Determine operation type
    if slot1.is_combined_slot() and slot2.is_combined_slot():
        return True, "Merging two combined slots", "merge_combined"
    elif slot1.is_combined_slot() or slot2.is_combined_slot():
        return True, "Extending combined slot with independent slot", "extend_combined"
    else:
        return True, "Merging two independent slots", "merge_independent"


def run():
    """
    Improved slot merge script with proper validation.
    """

    print("=== Improved Slot Merge by QR Codes with Validation ===\n")
    print("This script allows you to merge slots with proper validation.")
    print("It will reject merges if slots are already combined or in invalid states.")
    print("LEDs will light up to show which slots are being merged!")
    print("Enter 'quit' or 'exit' for any QR code to stop.\n")

    while True:
        print("-" * 70)
        print("Starting new merge operation...")

        # Prompt user for QR codes
        qr1 = input("Enter first QR code (will be the master): ").strip()

        # Check for exit conditions
        if qr1.lower() in ["quit", "exit", "q"]:
            print("Exiting merge script. Goodbye!")
            break

        qr2 = input("Enter second QR code to merge into first: ").strip()

        # Check for exit conditions
        if qr2.lower() in ["quit", "exit", "q"]:
            print("Exiting merge script. Goodbye!")
            break

        # Validate inputs
        if qr1 == qr2:
            print("❌ Error: Both QR codes are the same. Please try again.\n")
            continue

        if not qr1 or not qr2:
            print("❌ Error: Empty QR code entered. Please try again.\n")
            continue

        # Find the master slots for each QR code
        print(f"\n🔍 Looking up QR codes...")
        slot1 = find_master_slot_for_qr(qr1)
        slot2 = find_master_slot_for_qr(qr2)

        if not slot1:
            print(
                f"❌ Error: QR code '{qr1}' could not be resolved to any slot. Please try again.\n"
            )
            continue

        if not slot2:
            print(
                f"❌ Error: QR code '{qr2}' could not be resolved to any slot. Please try again.\n"
            )
            continue

        print(f"✅ Found Master Slot 1: {slot1.name} (Storage: {slot1.storage.name})")
        print(f"✅ Found Master Slot 2: {slot2.name} (Storage: {slot2.storage.name})")

        # Show current state of slots
        print(f"\n📊 Current slot states:")
        print(f"  Slot {slot1.name}:")
        print(f"    - Primary QR: {slot1.qr_value}")
        print(f"    - Additional QRs: {slot1.qr_codes}")
        print(f"    - Controls slots: {slot1.get_all_slot_names()}")
        print(f"    - Is combined: {slot1.is_combined_slot()}")

        print(f"  Slot {slot2.name}:")
        print(f"    - Primary QR: {slot2.qr_value}")
        print(f"    - Additional QRs: {slot2.qr_codes}")
        print(f"    - Controls slots: {slot2.get_all_slot_names()}")
        print(f"    - Is combined: {slot2.is_combined_slot()}")

        # Validate the merge operation
        is_valid, message, operation_type = validate_merge_operation(slot1, slot2)

        if not is_valid:
            print(f"\n❌ Cannot merge: {message}\n")
            continue

        print(f"\n✅ Validation passed: {message}")
        print(f"📋 Operation type: {operation_type}")

        # Collect all slots that will be involved
        # For the merge, we need all actual StorageSlot objects
        all_slot_names_1 = slot1.get_all_slot_names()
        all_slot_names_2 = slot2.get_all_slot_names()

        # Get actual slot objects, excluding those that don't exist
        actual_slots_1 = []
        actual_slots_2 = []

        for name in all_slot_names_1:
            try:
                slot_obj = StorageSlot.objects.get(storage=slot1.storage, name=name)
                actual_slots_1.append(slot_obj)
            except StorageSlot.DoesNotExist:
                print(
                    f"⚠️  Warning: Slot {name} referenced by {slot1.name} does not exist (cleaning up references)"
                )

        for name in all_slot_names_2:
            try:
                slot_obj = StorageSlot.objects.get(storage=slot2.storage, name=name)
                if slot_obj not in actual_slots_1:  # Avoid duplicates
                    actual_slots_2.append(slot_obj)
            except StorageSlot.DoesNotExist:
                print(
                    f"⚠️  Warning: Slot {name} referenced by {slot2.name} does not exist (cleaning up references)"
                )

        all_merge_slots = actual_slots_1 + actual_slots_2

        print(f"\n🔍 Slots to be involved in merge:")
        print(f"  Primary (will remain): {slot1.name}")
        print(f"  From slot1 group: {[s.name for s in actual_slots_1]}")
        print(f"  From slot2 group: {[s.name for s in actual_slots_2]}")
        print(f"  Will be deleted after merge: {[s.name for s in actual_slots_2]}")

        # Light up all slots
        print(f"\n💡 Lighting up all slots involved in YELLOW...")

        try:
            light_up_slots(all_merge_slots, "yellow")

            print(f"\n💡 All {len(all_merge_slots)} slots are now lit in YELLOW.")
            confirmation = input(
                "Press Enter to continue with the merge, or type 'cancel' to abort: "
            ).strip()

            if confirmation.lower() in ["cancel", "c", "abort", "no", "n"]:
                print("🚫 Merge cancelled by user.")
                turn_off_slots(all_merge_slots)
                continue

            print(f"\n🔄 Performing merge operation...")

            with transaction.atomic():
                # Perform the merge with slot1 as primary, and only actual_slots_2 as additional
                merged_slot = merge_storage_slots(slot1, *actual_slots_2)

            # Turn off all the slots that were lit
            print("🔄 Turning off merge indication LEDs...")
            turn_off_slots(all_merge_slots)

            # Wait a moment then light up the merged slot in green
            time.sleep(0.5)
            print("✅ Lighting up merged slot in GREEN...")
            light_up_slots([merged_slot], "green")

            print(f"\n🎉 Merge successful!")
            print(f"  - Master slot: {merged_slot.name}")
            print(f"  - All QR codes: {merged_slot.get_all_qr_codes()}")
            print(f"  - Controls slots: {merged_slot.get_all_slot_names()}")
            print(f"  - Is combined: {merged_slot.is_combined_slot()}")
            print(f"  - Deleted slots: {[s.name for s in actual_slots_2]}")

            # Keep the success LED on for a few seconds
            time.sleep(3)
            print("🔄 Turning off success LED...")
            turn_off_slots([merged_slot])

        except KeyboardInterrupt:
            print("\n\n⚠️ Merge cancelled by user!")
            print("🔄 Turning off all LEDs...")
            turn_off_slots(all_merge_slots)

        except Exception as e:
            print(f"❌ Merge failed: {e}")
            print("Please check the error and try again.")

            # Turn off LEDs and light them red briefly to indicate error
            print("🔄 Indicating error with RED LEDs...")
            turn_off_slots(all_merge_slots)
            time.sleep(0.5)
            light_up_slots(all_merge_slots, "red")
            time.sleep(2)
            turn_off_slots(all_merge_slots)

        print()  # Add some spacing for the next iteration

    print("\n=== Done ===")


def cleanup_orphaned_references():
    """
    Utility function to clean up orphaned references in related_names
    that point to slots that no longer exist.
    """
    print("🧹 Cleaning up orphaned slot references...")

    cleaned_count = 0
    for slot in StorageSlot.objects.all():
        if slot.related_names:
            # Check which related names actually exist
            valid_names = []
            for name in slot.related_names:
                if StorageSlot.objects.filter(storage=slot.storage, name=name).exists():
                    valid_names.append(name)
                else:
                    print(
                        f"  Removing orphaned reference: slot {slot.name} -> {name} (doesn't exist)"
                    )
                    cleaned_count += 1

            if len(valid_names) != len(slot.related_names):
                slot.related_names = valid_names
                slot.save()

    print(f"✅ Cleaned up {cleaned_count} orphaned references")


if __name__ == "__main__":
    print("Run with: python manage.py runscript merge_by_qr_codes_improved")
    print("Or to clean up orphaned references: ")
    print(
        "  from scripts.merge_by_qr_codes_improved import cleanup_orphaned_references"
    )
    print("  cleanup_orphaned_references()")
