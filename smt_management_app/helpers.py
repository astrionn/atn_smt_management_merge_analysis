from threading import Thread
import io
import qrcode

from django.http import FileResponse, JsonResponse
from django.views.decorators.csrf import requires_csrf_token, csrf_exempt
from django.middleware.csrf import get_token


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
            "open_jobs_prepared": open_jobs_created,
            "open_jobs_finished": open_jobs_finished,
        }
    )


@csrf_exempt
def print_carrier(request, carrier_name):
    """
    Print a label for the given carrier containing barcode information.

    Args:
    - request: HTTP request object
    - carrier: Name of the carrier to print the label for

    Returns:
    - JsonResponse: Success or failure message
    """

    class DymoDummy:

        def print_label(self, text1, text2):
            print(f"printing label {text1,text2}")

    dymo = DymoDummy()
    # dymo = DymoHandler()

    # Check if the carrier exists
    try:
        carrier = Carrier.objects.get(name=carrier_name, archived=False)
    except Carrier.DoesNotExist:
        return JsonResponse({"success": False, "message": "Carrier not found"})

    article = carrier.article

    if not dymo:  # Assuming dymo is defined somewhere
        return JsonResponse(
            {"success": False, "message": "Dymo label printer not reachable"}
        )

    # Start a thread to print the label
    Thread(
        target=dymo.print_label, args=(carrier.name, article.name), daemon=True
    ).start()

    return JsonResponse({"success": True})


def archive_carrier(request, carrier_name):
    carrier_queryset = Carrier.objects.filter(name=carrier_name)
    if not carrier_queryset:
        return JsonResponse({"success": False, "message": "Carrier not found."})
    carrier = carrier_queryset.first()

    if carrier.archived:
        return JsonResponse({"success": False, "message": "Carrier is archived."})

    carrier.archived = True
    carrier.save()

    return JsonResponse(
        {"success": True, "message": f"Carrier {carrier.name} has been archived."}
    )
