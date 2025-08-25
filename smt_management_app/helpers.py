from threading import Thread
import io
import qrcode

from django.http import FileResponse, JsonResponse
from django.views.decorators.csrf import requires_csrf_token, csrf_exempt
from django.middleware.csrf import get_token
from django.db.models import Q


from .utils.brother import BrotherQLHandler
from .models import (
    Manufacturer,
    Provider,
    Article,
    Carrier,
    Machine,
    MachineSlot,
    Storage,
    StorageSlot,
    Job,
    Board,
    BoardArticle,
    LocalFile,
)


def create_qr_code(request, code):
    img = qrcode.make(code)
    buffer = io.BytesIO()
    img.save(buffer)
    buffer.seek(0)
    return FileResponse(buffer, filename=f"{code}.png")


@requires_csrf_token
def get_csrf_token(request):
    csrf_token = get_token(request)
    response = JsonResponse({"csrf_token": csrf_token})
    response["X-CSRFToken"] = csrf_token
    return response


def check_unique(request, field, value):
    # for evaluating/indicating uniqueness while the user is typing in a field where unqiueness is required
    if field == "sapnumber":
        unique = not Article.objects.filter(sap_number=value).exists()
        return JsonResponse({"success": unique})


def check_pk_unique(request, model_name, value):
    # for evaluating/indicating uniqueness while the user is typing in a field where unqiueness is required ; pk abstraction
    if model_name.lower() == "carrier":
        model = Carrier

    if model_name.lower() == "article":
        model = Article

    if model_name.lower() == "job":
        model = Job

    if model_name.lower() == "board":
        model = Board

    try:
        model.objects.get(pk=value)
        is_unique = False
        error_message = "The primary key value is not unique."
    except model.DoesNotExist:
        is_unique = True
        error_message = None

    return JsonResponse(
        {
            "success": is_unique,
            "error_message": error_message,
        }
    )


def dashboard_data(request):
    """
    Fetches data for the dashboard including total carriers, undelivered carriers,
    carriers in storage, available storage slots, and active storages.
    Combined slots are counted as one logical slot.
    """
    total_carriers = Carrier.objects.filter(archived=False).count()
    undelivered_carriers = Carrier.objects.filter(
        archived=False, delivered=False
    ).count()
    carriers_in_storage = Carrier.objects.filter(
        archived=False, storage_slot__isnull=False
    ).count()
    carriers_in_production = Carrier.objects.filter(
        archived=False, storage_slot__isnull=True, delivered=True
    ).count()

    # Count free slots considering combined slots
    free_slots_count = count_logical_free_slots()

    active_storages = Storage.objects.filter(archived=False).count()
    total_finished_jobs = Job.objects.filter(status=2).count()
    open_jobs_created = Job.objects.filter(archived=False, status=0).count()
    open_jobs_prepared = Job.objects.filter(archived=False, status=1).count()
    open_jobs_finished = Job.objects.filter(archived=False, status=2).count()

    return JsonResponse(
        {
            "total_carriers": total_carriers,
            "not_delivered": undelivered_carriers,
            "in_storage": carriers_in_storage,
            "in_production": carriers_in_production,
            "free_slots": free_slots_count,
            "storages": active_storages,
            "total_finished_jobs": total_finished_jobs,
            "open_jobs_created": open_jobs_created,
            "open_jobs_prepared": open_jobs_prepared,
            "open_jobs_finished": open_jobs_finished,
        }
    )


def count_logical_free_slots():
    """
    Count free slots treating combined slots as one logical slot.

    Algorithm:
    1. Get all free slots
    2. For each slot, if it's part of a combined group, only count the "primary" slot
    3. A primary slot is one that appears first when sorting by name
    """
    free_slots = StorageSlot.objects.filter(carrier__isnull=True)

    counted_slots = set()
    logical_count = 0

    for slot in free_slots:
        # Skip if we've already counted this slot as part of a group
        if slot.name in counted_slots:
            continue

        # Get all slots in this group
        all_slot_names = slot.get_all_slot_names()

        # Mark all slots in the group as counted
        counted_slots.update(all_slot_names)

        # Count this group as one logical slot
        logical_count += 1

    return logical_count


@csrf_exempt
def print_carrier(request, carrier_name):
    """
    Print a label for the given carrier containing barcode information.

    Args:
    - request: HTTP request object
    - carrier_name: Name of the carrier to print the label for

    Returns:
    - JsonResponse: Success or failure message
    """

    class BrotherDummy:
        """Dummy class for testing without actual printer"""

        def print_label(self, message_a, message_b, message_c):
            print(
                f"printing label - Barcode: {message_a}, Article: {message_b}, Description: {message_c}"
            )
            return True

    # Use dummy for testing, replace with actual handler for production
    # brother_printer = BrotherDummy()

    # Initialize Brother QL printer handler
    brother_printer = BrotherQLHandler()

    # Check if the carrier exists
    try:
        carrier = Carrier.objects.get(name=carrier_name, archived=False)
    except Carrier.DoesNotExist:
        return JsonResponse({"success": False, "message": "Carrier not found"})

    article = carrier.article

    if not brother_printer:
        return JsonResponse(
            {"success": False, "message": "Brother QL label printer not reachable"}
        )

    # Test printer connection before attempting to print
    try:
        if not brother_printer.test_connection():
            return JsonResponse(
                {"success": False, "message": "Brother QL printer not responding"}
            )
    except Exception as e:
        return JsonResponse(
            {"success": False, "message": f"Printer connection error: {str(e)}"}
        )

    def print_label_threaded():
        """Thread function to print the label"""
        try:
            success = brother_printer.print_label(
                message_a=carrier.name,  # Barcode content + carrier field
                message_b=article.name,  # Article field
                message_c=article.description,  # Description field
                carrier_uid=str(carrier.name),  # Add carrier UID for QR code
            )
            if not success:
                print(f"Failed to print label for carrier: {carrier_name}")
        except Exception as e:
            print(f"Error in print thread for carrier {carrier_name}: {e}")

    # Start a thread to print the label
    Thread(
        target=print_label_threaded,
        daemon=True,
    ).start()

    return JsonResponse(
        {
            "success": True,
            "message": f"Label printing started for carrier: {carrier_name}",
        }
    )


def archive_carrier(request, carrier_name):
    carrier_queryset = Carrier.objects.filter(name=carrier_name)
    if not carrier_queryset:
        return JsonResponse(
            {"success": False, "message": f"Carrier {carrier_name} not found."}
        )
    carrier = carrier_queryset.first()

    if carrier.archived:
        return JsonResponse(
            {"success": False, "message": f"Carrier {carrier.name} is archived."}
        )

    carrier.archived = True
    if carrier.storage_slot:
        carrier.storage_slot = None
    carrier.save()

    return JsonResponse(
        {"success": True, "message": f"Carrier {carrier.name} has been archived."}
    )


def get_collect_queue(request):
    # FIXED: Filter out carriers without storage_slot to prevent crashes
    queued_carriers = Carrier.objects.filter(
        collecting=True, archived=False, storage_slot__isnull=False
    )
    collection_queue = [
        {
            "carrier": queued_carrier.name,
            "storage": queued_carrier.storage_slot.storage.name,
            "slot": queued_carrier.storage_slot.qr_value,
        }
        for queued_carrier in queued_carriers
    ]

    response_message = {
        "queue": collection_queue,
    }

    return JsonResponse(response_message)


def find_slot_by_qr_code(qr_code, storage_name=None):
    """
    Find slot by ANY of its QR codes (primary or additional).

    Args:
        qr_code: The QR code to search for
        storage_name: Optional storage name to narrow search

    Returns:
        StorageSlot instance or None
    """
    from django.db.utils import NotSupportedError

    query = Q(qr_value=qr_code)
    if storage_name:
        query &= Q(storage__name=storage_name)

    try:
        # Attempt to use JSONField __contains lookup
        query |= Q(qr_codes__contains=qr_code)
        slot = StorageSlot.objects.filter(query).first()
    except NotSupportedError:
        # Fall back to manual filtering for backends like PostgreSQL
        base_qs = StorageSlot.objects.filter(Q(qr_value=qr_code))
        if storage_name:
            base_qs = base_qs.filter(storage__name=storage_name)

        base_qs = list(base_qs)  # force evaluation
        matching_slots = base_qs[:]

        for slot in StorageSlot.objects.all():
            if slot.qr_codes and qr_code in slot.qr_codes:
                if storage_name is None or (
                    slot.storage and slot.storage.name == storage_name
                ):
                    matching_slots.append(slot)

        slot = matching_slots[0] if matching_slots else None

    return slot


def slot_matches_qr_code(slot, qr_code):
    """
    Check if slot matches QR code (checking all QR codes).

    Args:
        slot: StorageSlot instance
        qr_code: QR code to check

    Returns:
        bool: True if QR code matches any of slot's QR codes
    """
    if not slot:
        return False
    return qr_code in slot.get_all_qr_codes()


def assign_carrier_to_job(request, job_name, carrier_name):
    """Assign a carrier to a job and update job status if fully prepared."""
    print("assign_carrier_to_job")
    print(f"job_name: {job_name}")
    print(f"carrier_name: {carrier_name}")

    job = Job.objects.filter(name=job_name).first()
    print(f"job: {job}")

    carrier = Carrier.objects.filter(name=carrier_name, archived=False).first()
    print(f"carrier: {carrier}")

    if job and carrier:
        job.carriers.add(carrier)
        print("Carrier added to job")

        if job.carriers.count() == job.board.articles.count():
            job.status = 1
            print("Job status updated to 1")

        job.save()
        print("Job saved")

        carrier.reserved = True
        carrier.save()
        print("Carrier reserved")

        return JsonResponse({"success": True})
    else:
        return JsonResponse({"success": False})


@csrf_exempt
def deliver_all_carriers(request):
    """Mark all non-archived carriers as delivered."""
    i = Carrier.objects.filter(archived=False).update(delivered=True)
    return JsonResponse({"success": True, "updated_amount": i})
