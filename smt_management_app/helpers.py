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
    free_slots = StorageSlot.objects.filter(carrier__isnull=True).count()
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
            "free_slots": free_slots,
            "storages": active_storages,
            "total_finished_jobs": total_finished_jobs,
            "open_jobs_created": open_jobs_created,
            "open_jobs_prepared": open_jobs_prepared,
            "open_jobs_finished": open_jobs_finished,
        }
    )


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
                message_d=carrier.storage.name if carrier.storage else "No Storage",
                carrier_uid=str(carrier.name),  # Add carrier UID for QR code
                label_height_mm=25,  # Smaller label height for better fit
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
