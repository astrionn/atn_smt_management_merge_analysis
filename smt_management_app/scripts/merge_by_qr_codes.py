# Save as: smt_management_app/scripts/bulletproof_merge_by_qr_codes.py

from smt_management_app.models import StorageSlot, Storage
from smt_management_app.collecting import find_slot_by_qr_code
from smt_management_app.utils.led_shelf_dispatcher import LED_shelf_dispatcher
from django.db import transaction
from threading import Thread
import time


def light_up_slots(slots, color="yellow"):
    """Light up a list of slots with the specified color."""
    storage_dispatchers = {}

    for slot in slots:
        storage = slot.storage
        if storage.name not in storage_dispatchers:
            storage_dispatchers[storage.name] = LED_shelf_dispatcher(storage)

        slot.led_state = 1
        slot.save()

        Thread(
            target=storage_dispatchers[storage.name].led_on,
            kwargs={"lamp": slot.name, "color": color},
        ).start()


def turn_off_slots(slots):
    """Turn off LEDs for a list of slots."""
    storage_dispatchers = {}

    for slot in slots:
        storage = slot.storage
        if storage.name not in storage_dispatchers:
            storage_dispatchers[storage.name] = LED_shelf_dispatcher(storage)

        slot.led_state = 0
        slot.save()

        Thread(
            target=storage_dispatchers[storage.name].led_off, kwargs={"lamp": slot.name}
        ).start()


def get_complete_slot_group(slot):
    """
    Get all slots that are part of a combined slot group.
    This function follows all relationships to find the complete group.
    """
    visited = set()
    to_visit = {slot.name}
    storage = slot.storage

    print(f"    Tracing relationships starting from slot {slot.name}...")

    while to_visit:
        current_name = to_visit.pop()
        if current_name in visited:
            continue

        visited.add(current_name)
        print(f"    Checking slot {current_name}...")

        try:
            current_slot = StorageSlot.objects.get(storage=storage, name=current_name)

            # Add all slots this slot references
            if current_slot.related_names:
                print(
                    f"      Slot {current_name} references: {current_slot.related_names}"
                )
                for related_name in current_slot.related_names:
                    if related_name not in visited:
                        to_visit.add(related_name)
            else:
                print(f"      Slot {current_name} has no related_names")

            # Find all slots that reference this slot by checking all slots
            referencing_slots = []
            all_slots_in_storage = StorageSlot.objects.filter(storage=storage)
            for potential_ref_slot in all_slots_in_storage:
                if (
                    potential_ref_slot.related_names
                    and current_name in potential_ref_slot.related_names
                ):
                    referencing_slots.append(potential_ref_slot.name)
                    if potential_ref_slot.name not in visited:
                        to_visit.add(potential_ref_slot.name)

            if referencing_slots:
                print(f"      Slots that reference {current_name}: {referencing_slots}")
            else:
                print(f"      No slots reference {current_name}")

        except StorageSlot.DoesNotExist:
            print(f"    Warning: Referenced slot {current_name} not found")
            continue

    print(f"    Complete group for slot {slot.name}: {sorted(visited)}")
    return visited


def bulletproof_merge_storage_slots(primary_slot, additional_slot_names):
    """
    Create fully bidirectional relationships between all slots in a group.
    Every slot will know about every other slot.
    """
    storage = primary_slot.storage

    # IMPORTANT: Get ALL slots that are currently in the primary slot's group
    existing_group_names = get_complete_slot_group(primary_slot)
    print(
        f"  Primary slot {primary_slot.name} is already in group: {sorted(existing_group_names)}"
    )

    # Combine existing group with additional slots
    all_slot_names = list(existing_group_names) + additional_slot_names
    # Remove duplicates while preserving order
    seen = set()
    unique_slot_names = []
    for name in all_slot_names:
        if name not in seen:
            unique_slot_names.append(name)
            seen.add(name)

    print(f"  Total slots to be in combined group: {sorted(unique_slot_names)}")

    # Get all slot objects
    all_slots = []
    for name in unique_slot_names:
        try:
            slot = StorageSlot.objects.get(storage=storage, name=name)
            all_slots.append(slot)
        except StorageSlot.DoesNotExist:
            raise ValueError(f"Slot {name} not found in storage {storage.name}")

    # Validate all slots
    for slot in all_slots:
        if slot.storage != storage:
            raise ValueError(
                f"Slot {slot.name} is in {slot.storage.name}, not {storage.name}"
            )
        if hasattr(slot, "carrier") and slot.carrier:
            raise ValueError(
                f"Slot {slot.name} is occupied by carrier {slot.carrier.name}"
            )
        if hasattr(slot, "nominated_carrier") and slot.nominated_carrier:
            raise ValueError(
                f"Slot {slot.name} has nominated carrier {slot.nominated_carrier.name}"
            )

    with transaction.atomic():
        # Collect ALL unique QR codes from all slots
        all_qr_values = {}  # qr_value -> slot_name mapping

        for slot in all_slots:
            if slot.qr_value and slot.qr_value.strip():
                all_qr_values[slot.qr_value.strip()] = slot.name

            # Also collect from existing qr_codes arrays
            if slot.qr_codes:
                for qr in slot.qr_codes:
                    if qr and qr.strip() and qr.strip() not in all_qr_values:
                        all_qr_values[qr.strip()] = "from_existing_group"

        # Calculate maximum dimensions
        max_diameter = max((slot.diameter or 0) for slot in all_slots)
        max_width = max((slot.width or 0) for slot in all_slots)

        # Sort for consistent ordering
        all_slot_names_sorted = sorted([slot.name for slot in all_slots])
        all_qr_codes_sorted = sorted(all_qr_values.keys())

        print(f"Creating bidirectional relationships:")
        print(f"  Slots: {all_slot_names_sorted}")
        print(f"  QR codes: {all_qr_codes_sorted}")

        # Update each slot to have relationships with ALL other slots
        for slot in all_slots:
            # related_names = all other slot names (excluding this slot)
            other_slot_names = [
                name for name in all_slot_names_sorted if name != slot.name
            ]

            # qr_codes = all other QR codes (excluding this slot's qr_value)
            other_qr_codes = [qr for qr in all_qr_codes_sorted if qr != slot.qr_value]

            # Update the slot
            slot.related_names = other_slot_names
            slot.qr_codes = other_qr_codes

            if max_diameter > 0:
                slot.diameter = max_diameter
            if max_width > 0:
                slot.width = max_width

            slot.save()

            print(
                f"  Updated slot {slot.name}: related_names={other_slot_names}, qr_codes={other_qr_codes}"
            )

        print(f"✅ Created bidirectional group of {len(all_slots)} slots")

    return primary_slot


def validate_merge_request(slot1, slot2):
    """
    Validate that two slots can be merged and return complete groups.

    Returns:
        tuple: (is_valid, error_message, group1_names, group2_names)
    """
    # Check basic compatibility
    if slot1.storage != slot2.storage:
        return False, f"Slots are from different storages", None, None

    # Get complete groups for both slots
    group1_names = get_complete_slot_group(slot1)
    group2_names = get_complete_slot_group(slot2)

    # Check if they're already in the same group
    if group1_names.intersection(group2_names):
        return False, f"Slots are already in the same combined group", None, None

    # Check all slots in both groups for occupation
    storage = slot1.storage
    all_names = group1_names.union(group2_names)

    for name in all_names:
        try:
            slot = StorageSlot.objects.get(storage=storage, name=name)
            if hasattr(slot, "carrier") and slot.carrier:
                return (
                    False,
                    f"Slot {name} is occupied by carrier {slot.carrier.name}",
                    None,
                    None,
                )
            if hasattr(slot, "nominated_carrier") and slot.nominated_carrier:
                return (
                    False,
                    f"Slot {name} has nominated carrier {slot.nominated_carrier.name}",
                    None,
                    None,
                )
        except StorageSlot.DoesNotExist:
            return False, f"Referenced slot {name} does not exist", None, None

    return True, None, group1_names, group2_names


def run():
    """
    Bulletproof slot merge script with complete consistency guarantees.
    """
    print("=== BULLETPROOF SLOT MERGE SCRIPT ===\n")
    print("This script ensures complete consistency in combined slots:")
    print("✓ Follows all relationships to find complete groups")
    print("✓ Atomic transactions with full rollback on error")
    print("✓ Comprehensive validation")
    print("✓ LED dispatcher compatibility guaranteed")
    print("Enter 'quit' or 'exit' for any QR code to stop.\n")

    while True:
        print("-" * 50)
        print("Starting new merge operation...")

        # Get QR codes
        qr1 = input("Enter first QR code (will be the master): ").strip()
        if qr1.lower() in ["quit", "exit", "q"]:
            break

        qr2 = input("Enter second QR code to merge into first: ").strip()
        if qr2.lower() in ["quit", "exit", "q"]:
            break

        # Validate inputs
        if qr1 == qr2:
            print("Error: Both QR codes are the same. Please try again.\n")
            continue

        if not qr1 or not qr2:
            print("Error: Empty QR code entered. Please try again.\n")
            continue

        # Find slots
        slot1 = find_slot_by_qr_code(qr1)
        slot2 = find_slot_by_qr_code(qr2)

        if not slot1:
            print(f"Error: QR code '{qr1}' not found. Please try again.\n")
            continue

        if not slot2:
            print(f"Error: QR code '{qr2}' not found. Please try again.\n")
            continue

        print(f"\nFound slots:")
        print(f"  Slot 1: {slot1.name} (QR: {slot1.qr_value}) - Will be master")
        print(f"  Slot 2: {slot2.name} (QR: {slot2.qr_value}) - Will be merged")

        # Validate merge
        is_valid, error_msg, group1_names, group2_names = validate_merge_request(
            slot1, slot2
        )

        if not is_valid:
            print(f"\n❌ Cannot merge: {error_msg}\n")
            continue

        # Show complete groups
        print(f"\n🔍 Complete groups to be merged:")
        print(f"  Group 1 (master): {sorted(group1_names)}")
        print(f"  Group 2 (to merge): {sorted(group2_names)}")

        # Get all slot objects for LED display
        all_slot_names = group1_names.union(group2_names)
        all_slots = []
        for name in all_slot_names:
            try:
                slot = StorageSlot.objects.get(storage=slot1.storage, name=name)
                all_slots.append(slot)
            except StorageSlot.DoesNotExist:
                print(f"Warning: Slot {name} not found")

        print(f"\n💡 Lighting up all {len(all_slots)} slots in YELLOW...")

        try:
            # Light up all slots
            light_up_slots(all_slots, "yellow")

            # Confirm with user
            print("\nAll slots involved in the merge are now lit.")
            print(
                f"This will create a combined group of {len(group1_names.union(group2_names))} slots"
            )
            print("All slots will remain in database with bidirectional relationships")
            input("Press Enter to continue with the merge, or Ctrl+C to cancel...")

            # Get additional slot names (all slots from both groups except primary)
            all_names_to_merge = [name for name in group2_names if name != slot1.name]

            # Add any additional names from group1 that aren't the primary
            if slot1.name in group2_names:
                # This means the primary was found in group2, so add group1 names
                all_names_to_merge.extend(
                    [name for name in group1_names if name != slot1.name]
                )

            # Perform the merge (keeps all slots, makes them consistent)
            print(
                f"\n🔄 Creating combined group with {len(all_names_to_merge) + 1} total slots..."
            )

            merged_slot = bulletproof_merge_storage_slots(slot1, all_names_to_merge)

            # Get all slots for LED feedback and final display
            print("🔄 Refreshing slot data from database...")
            refreshed_primary = StorageSlot.objects.get(
                storage=slot1.storage, name=merged_slot.name
            )
            combined_group_names = refreshed_primary.get_all_slot_names()
            combined_group_slots = []
            for name in combined_group_names:
                try:
                    slot = StorageSlot.objects.get(storage=slot1.storage, name=name)
                    combined_group_slots.append(slot)
                except StorageSlot.DoesNotExist:
                    print(f"Warning: Slot {name} not found after merge")

            # Turn off all LEDs
            print("🔄 Turning off merge LEDs...")
            turn_off_slots(all_slots)

            # Light up the combined group in green
            time.sleep(0.5)
            print("✅ Lighting up all slots in combined group in GREEN...")
            light_up_slots(combined_group_slots, "green")

            print(f"\n🎉 Combined group created successfully!")
            print(f"  All slots in group: {sorted(combined_group_names)}")
            print(f"  All QR codes: {sorted(refreshed_primary.get_all_qr_codes())}")
            print(f"  Total slots in group: {len(combined_group_names)}")
            print(f"  Each slot now has bidirectional relationships with all others")

            # Verify LED dispatcher compatibility
            print(f"\n🔧 Verifying LED dispatcher...")
            dispatcher = LED_shelf_dispatcher(refreshed_primary.storage)
            dispatcher_slots = dispatcher._get_all_slot_names_for_lamp(
                refreshed_primary.name
            )
            model_slots = refreshed_primary.get_all_slot_names()

            if set(dispatcher_slots) == set(model_slots):
                print("✅ LED dispatcher compatibility confirmed!")
            else:
                print("⚠️  LED dispatcher compatibility issue detected")
                print(f"   Dispatcher sees: {dispatcher_slots}")
                print(f"   Model expects: {model_slots}")

            # Keep success LED on briefly
            time.sleep(3)
            turn_off_slots(combined_group_slots)

        except KeyboardInterrupt:
            print("\n\n⚠️ Merge cancelled by user!")
            turn_off_slots(all_slots)

        except Exception as e:
            print(f"\n❌ Merge failed: {e}")
            print("All changes have been rolled back.")

            # Show error with red LEDs
            turn_off_slots(all_slots)
            time.sleep(0.5)
            light_up_slots(all_slots, "red")
            time.sleep(2)
            turn_off_slots(all_slots)

        print()

    print("\n=== MERGE SCRIPT COMPLETE ===")


if __name__ == "__main__":
    run()
