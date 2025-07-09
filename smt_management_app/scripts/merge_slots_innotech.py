# Save as: smt_management_app/scripts/merge_slots_innotech_simple.py

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
    """Get all slots that are part of a combined slot group."""
    visited = set()
    to_visit = {slot.name}
    storage = slot.storage

    while to_visit:
        current_name = to_visit.pop()
        if current_name in visited:
            continue
        visited.add(current_name)

        try:
            current_slot = StorageSlot.objects.get(storage=storage, name=current_name)
            if current_slot.related_names:
                for related_name in current_slot.related_names:
                    if related_name not in visited:
                        to_visit.add(related_name)

            # Find all slots that reference this slot
            all_slots_in_storage = StorageSlot.objects.filter(storage=storage)
            for potential_ref_slot in all_slots_in_storage:
                if (
                    potential_ref_slot.related_names
                    and current_name in potential_ref_slot.related_names
                ):
                    if potential_ref_slot.name not in visited:
                        to_visit.add(potential_ref_slot.name)
        except StorageSlot.DoesNotExist:
            continue

    return visited


def merge_two_slots(qr1, qr2):
    """
    Merge two slots using the bulletproof logic.
    Returns True if successful, False otherwise.
    """
    print(f"\n🔄 Merging {qr1} + {qr2}")

    # Find slots
    slot1 = find_slot_by_qr_code(qr1)
    slot2 = find_slot_by_qr_code(qr2)

    if not slot1:
        print(f"❌ QR code '{qr1}' not found")
        return False
    if not slot2:
        print(f"❌ QR code '{qr2}' not found")
        return False

    print(f"   Found: {slot1.name} + {slot2.name}")

    # Check basic requirements
    if slot1.storage != slot2.storage:
        print(f"❌ Different storages")
        return False

    # Check if occupied
    for slot in [slot1, slot2]:
        if hasattr(slot, "carrier") and slot.carrier:
            print(f"❌ Slot {slot.name} is occupied")
            return False
        if hasattr(slot, "nominated_carrier") and slot.nominated_carrier:
            print(f"❌ Slot {slot.name} has nominated carrier")
            return False

    # Get existing groups
    group1_names = get_complete_slot_group(slot1)
    group2_names = get_complete_slot_group(slot2)

    # Check if already merged
    if group1_names.intersection(group2_names):
        print(f"⚠️  Already merged")
        return False

    print(f"   Group 1: {sorted(group1_names)}")
    print(f"   Group 2: {sorted(group2_names)}")

    # Combine all slots
    all_slot_names = list(group1_names.union(group2_names))

    # Get all slot objects
    all_slots = []
    for name in all_slot_names:
        try:
            slot = StorageSlot.objects.get(storage=slot1.storage, name=name)
            all_slots.append(slot)
        except StorageSlot.DoesNotExist:
            print(f"❌ Slot {name} not found")
            return False

    # Light up slots
    light_up_slots(all_slots, "yellow")
    time.sleep(0.3)

    try:
        # Perform merge in transaction
        with transaction.atomic():
            print(f"   Merging {len(all_slots)} slots...")

            # Collect all QR codes
            all_qr_values = {}
            for slot in all_slots:
                if slot.qr_value and slot.qr_value.strip():
                    all_qr_values[slot.qr_value.strip()] = slot.name
                if slot.qr_codes:
                    for qr in slot.qr_codes:
                        if qr and qr.strip() and qr.strip() not in all_qr_values:
                            all_qr_values[qr.strip()] = "existing"

            # Calculate max dimensions
            max_diameter = max((slot.diameter or 0) for slot in all_slots)
            max_width = max((slot.width or 0) for slot in all_slots)

            # Sort for consistency
            all_slot_names_sorted = sorted([slot.name for slot in all_slots])
            all_qr_codes_sorted = sorted(all_qr_values.keys())

            # Update each slot
            for slot in all_slots:
                other_slot_names = [
                    name for name in all_slot_names_sorted if name != slot.name
                ]
                other_qr_codes = [
                    qr for qr in all_qr_codes_sorted if qr != slot.qr_value
                ]

                slot.related_names = other_slot_names
                slot.qr_codes = other_qr_codes

                if max_diameter > 0:
                    slot.diameter = max_diameter
                if max_width > 0:
                    slot.width = max_width

                slot.save()
                print(f"   ✓ Updated {slot.name}")

            # Atomic block will auto-commit on successful exit

        # Show success
        turn_off_slots(all_slots)
        time.sleep(0.2)
        light_up_slots(all_slots, "green")
        print(f"✅ Success: {len(all_slots)} slots merged")
        time.sleep(0.5)
        turn_off_slots(all_slots)

        return True

    except Exception as e:
        print(f"❌ Merge failed: {str(e)}")
        turn_off_slots(all_slots)
        time.sleep(0.2)
        light_up_slots(all_slots, "red")
        time.sleep(1)
        turn_off_slots(all_slots)
        return False


def run():
    """Main script to merge S11227 slots."""
    print("=== S11227 SLOT MERGE SCRIPT ===")
    print("⚠️  ENSURE DJANGO SERVER IS STOPPED!")
    print()

    # Check storage
    try:
        storage = Storage.objects.get(name="Storage_S11227")
        print(f"✓ Storage found: {storage.name}")
    except Storage.DoesNotExist:
        print("❌ Storage 'Storage_S11227' not found")
        return

    # Generate pairs
    pairs = []

    # Row 6: 001+002, 003+004, ..., 199+200
    for pos in range(1, 201, 2):
        qr1 = f"S11227-06-{str(pos).zfill(3)}"
        qr2 = f"S11227-06-{str(pos+1).zfill(3)}"
        pairs.append((qr1, qr2))

    # Row 7: 101+102, 103+104, ..., 199+200
    for pos in range(101, 201, 2):
        qr1 = f"S11227-07-{str(pos).zfill(3)}"
        qr2 = f"S11227-07-{str(pos+1).zfill(3)}"
        pairs.append((qr1, qr2))

    print(f"Generated {len(pairs)} pairs to merge")
    print("Starting merge process...")
    print("=" * 50)

    successful = 0
    failed = 0

    for i, (qr1, qr2) in enumerate(pairs, 1):
        print(f"\n[{i}/{len(pairs)}] Processing pair...")

        if merge_two_slots(qr1, qr2):
            successful += 1
        else:
            failed += 1

        # Progress update every 10 pairs
        if i % 10 == 0:
            print(
                f"\n📊 Progress: {i}/{len(pairs)} ({successful} success, {failed} failed)"
            )

    # Final summary
    print("\n" + "=" * 50)
    print("🎉 MERGE COMPLETE!")
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    if successful + failed > 0:
        success_rate = successful / (successful + failed) * 100
        print(f"📊 Success rate: {success_rate:.1f}%")


if __name__ == "__main__":
    run()
