import json
import csv
from pprint import pprint as pp
from urllib import request

from django.views.decorators.csrf import csrf_exempt

from django.http import JsonResponse
from django.core.files import File
from rest_framework import viewsets, filters, generics, status
from rest_framework.mixins import DestroyModelMixin
from rest_framework.response import Response

import django_filters


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

from .filters import (
    ArticleFilter,
    BoardFilter,
    BoardArticleFilter,
    CarrierFilter,
    JobFilter,
    ManufacturerFilter,
    StorageSlotFilter,
)

from .serializers import (
    ArticleNameSerializer,
    ArticleSerializer,
    BoardArticleSerializer,
    BoardSerializer,
    CarrierNameSerializer,
    CarrierSerializer,
    JobSerializer,
    MachineSerializer,
    MachineSlotSerializer,
    ManufacturerNameSerializer,
    ManufacturerSerializer,
    ProviderNameSerializer,
    ProviderSerializer,
    StorageSerializer,
    StorageNameSerializer,
    StorageSlotSerializer,
    StorageSlotNameSerializer,
)

from .helpers import (
    create_qr_code,
    get_csrf_token,
    check_unique,
    check_pk_unique,
    dashboard_data,
    print_carrier,
    archive_carrier,
    get_collect_queue,
)

from .collecting import (
    collect_single_carrier,
    collect_single_carrier_confirm,
    collect_single_carrier_cancel,
    collect_carrier,
    collect_carrier_confirm,
    collect_carrier_cancel,
    collect_carrier_by_article,
    collect_carrier_by_article_confirm,
    collect_carrier_by_article_cancel,
    collect_carrier_by_article_select,
    collect_job,
)

from .storing import (
    store_carrier,
    store_carrier_confirm,
    store_carrier_cancel,
    store_carrier_choose_slot,
    store_carrier_choose_slot_confirm,
    store_carrier_choose_slot_cancel,
    # New functions for updated workflow
    store_carrier_choose_slot_all_storages,
    store_carrier_choose_slot_confirm_by_qr,
    store_carrier_choose_slot_cancel_all,
    fetch_available_storages_for_auto,
    store_auto_with_storage_selection,
    # New collect-and-store functions
    store_carrier_collect_and_store,
    store_carrier_choose_slot_collect_and_store,
)

from .extra_shelf_interactions import test_leds, reset_leds, change_slot_color


def assign_carrier_to_job(request, job_name, carrier_name):
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
    i = Carrier.objects.filter(archived=False).update(delivered=True)
    return JsonResponse({"success": True, "updated_amount": i})


@csrf_exempt
def save_file_and_get_headers(request):
    """
    first step of a 2 step workflow to create articles/carriers from a csv file
    this step saves the file for future processing and returns the headers of said csv file
    """
    if request.FILES and request.POST:
        lf = LocalFile.objects.create(
            file_object=File(request.FILES["file"]),
            upload_type=request.POST["upload_type"],
            delimiter=request.POST["delimiter"],
        )
        try:
            with open(lf.file_object.path, newline="") as f:
                csv_reader = csv.reader(f, delimiter=lf.delimiter)
                lf.headers = list(csv_reader.__next__())
                lf.save()
                if lf.upload_type == "article":
                    model_fields = [f.name for f in Article._meta.get_fields()]
                elif lf.upload_type == "carrier":
                    model_fields = [f.name for f in Carrier._meta.get_fields()]
                    if "lot_number" in request.POST.keys():
                        lf.lot_number = request.POST["lot_number"]
                        lf.save()
                elif lf.upload_type == "board":
                    model_fields = ["article", "count"]
                    if "board_name" in request.POST.keys():
                        lf.board_name = request.POST["board_name"]
                        lf.save()
                return JsonResponse(
                    {
                        "object_fields": sorted(model_fields),
                        "header_fields": sorted(lf.headers),
                        "file_name": lf.name,
                    }
                )
        except Exception as e:
            print(e)
            return JsonResponse({"success": False})
    return JsonResponse({"success": False})


@csrf_exempt
def user_mapping_and_file_processing(request):
    if request.method == "POST":
        file_name = request.POST.get("file_name")
        lf = LocalFile.objects.get(name=file_name)
        map_ = json.loads(request.POST["map"])
        map_ = {v: k for k, v in map_.items() if v and k}
        match lf.upload_type:
            case "article":
                return JsonResponse(
                    process_article_file(lf.file_object.path, lf.delimiter, map_)
                )
            case "carrier":
                return JsonResponse(
                    process_carrier_file(
                        lf.file_object.path, lf.delimiter, map_, lf.lot_number
                    )
                )
            case "board":
                return JsonResponse(
                    process_board_file(
                        lf.file_object.path, lf.delimiter, map_, lf.board_name
                    )
                )


def process_article_file(file_path, delimiter, map_):

    message = {
        "created": {"article": [], "manufacturer": [], "provider": []},
        "fail": {"article": [], "manufacturer": [], "provider": []},
    }
    with open(file_path, "r", encoding="ISO-8859-1") as f:
        csv_reader = csv.reader(f, delimiter=delimiter)
        headers = next(csv_reader)
        for row in csv_reader:
            article_dict = {}
            for i, col_name in enumerate(headers):
                alternate_col = map_.get(col_name)
                if alternate_col:
                    article_dict[alternate_col] = row[i]
            article_dict_only_strings = article_dict.copy()

            manufacturer_name = article_dict.get("manufacturer")
            if manufacturer_name:
                manufacturer, manufacturer_created = Manufacturer.objects.get_or_create(
                    name=manufacturer_name
                )
                article_dict["manufacturer"] = manufacturer
                if manufacturer_created:
                    message["created"]["manufacturer"].append(
                        {
                            k: v
                            for k, v in manufacturer.__dict__.items()
                            if k != "_state"
                        }
                    )

            provider_keys = [
                "provider1",
                "provider2",
                "provider3",
                "provider4",
                "provider5",
            ]
            for provider_key in provider_keys:
                if provider_key in article_dict and article_dict[provider_key]:
                    provider, provider_created = Provider.objects.get_or_create(
                        name=article_dict[provider_key]
                    )
                    article_dict[provider_key] = provider
                    if provider_created:
                        message["created"]["provider"].append(
                            {
                                k: v
                                for k, v in provider.__dict__.items()
                                if k != "_state"
                            }
                        )
            try:
                article = Article.objects.create(**article_dict)
                message["created"]["article"].append(
                    {k: v for k, v in article_dict_only_strings.items()}
                )
            except Exception as e:
                print(e)
                failed_article = article_dict_only_strings
                failed_article["error"] = str(e)
                message["fail"]["article"].append(failed_article)

    return message


def process_carrier_file(file_path, delimiter, map_, lot_number):
    print("process_carrier_file")
    print(f"file_path: {file_path}")
    print(f"delimiter: {delimiter}")
    print(f"map_:")
    pp(map_)
    print(f"lot_number: {lot_number}")

    message = {"created": {"carrier": []}, "fail": {"carrier": []}}
    with open(file_path, "r", encoding="ISO-8859-1") as f:
        csv_reader = csv.reader(f, delimiter=delimiter)
        headers = next(csv_reader)
        print("headers")
        print(headers)
        for row in csv_reader:
            print("row")
            print(row)
            carrier_dict = {}
            for i, col_name in enumerate(headers):
                alternate_col = map_.get(col_name)
                if alternate_col:
                    carrier_dict[alternate_col] = row[i]

            if lot_number:
                carrier_dict["lot_number"] = lot_number
                print("carrier_dict replace lot number")
                pp(carrier_dict)

            carrier_dict_only_strings = carrier_dict.copy()
            print("carrier_dict only strings")
            pp(carrier_dict_only_strings)

            article_name = carrier_dict.get("article")
            if article_name:
                try:
                    article = Article.objects.get(name=article_name)
                    carrier_dict["article"] = article
                except Exception as e:
                    print("article e", article_name, e)
                    failed_carrier = carrier_dict_only_strings.copy()
                    failed_carrier["error"] = str(e) + f" {article_name}"
                    message["fail"]["carrier"].append(failed_carrier)
                    continue
            print("carrier_dict replace article obj")
            pp(carrier_dict)
            integer_fields = [
                "diameter",
                "width",
                "container_type",
                "quantity_original",
                "quantity_current",
                "reserved",
                "delivered",
                "collecting",
            ]
            try:
                for field in integer_fields:
                    if field not in carrier_dict.keys():
                        continue
                    carrier_dict[field] = (
                        int(carrier_dict[field]) if carrier_dict[field] else ""
                    )
            except Exception as e:
                print("integer e", carrier_dict["name"], field, e)
                failed_carrier = carrier_dict_only_strings.copy()
                failed_carrier["error"] = str(e) + f" {carrier_dict['name']} {field}"
                message["fail"]["carrier"].append(failed_carrier)
                continue
            print("carrier_dict ensure numerics")
            pp(carrier_dict)
            try:
                carrier = Carrier.objects.create(**carrier_dict)
                message["created"]["carrier"].append(
                    {k: v for k, v in carrier_dict_only_strings.items()}
                )
            except Exception as e:
                print("carrier e", e)
                failed_carrier = {k: v for k, v in carrier_dict_only_strings.items()}
                failed_carrier["error"] = str(e)
                message["fail"]["carrier"].append(failed_carrier)
    return message


def process_board_file(file_path, delimiter, map_, board_name):

    message = {
        "created": {"board": [], "boardarticle": []},
        "fail": {"board": [], "boardarticle": []},
    }

    board = Board.objects.get(name=board_name)

    with open(file_path, "r", encoding="ISO-8859-1") as f:
        csv_reader = csv.reader(f, delimiter=delimiter)
        headers = next(csv_reader)
        for row in csv_reader:
            board_article_dict = {}
            for i, col_name in enumerate(headers):
                alternate_col = map_.get(col_name)
                if alternate_col:
                    board_article_dict[alternate_col] = row[i]

            board_article_dict_only_strings = board_article_dict.copy()
            print("board_article_dict only strings")
            pp(board_article_dict_only_strings)

            board_article_dict["board"] = board

            article_name = board_article_dict.get("article")
            if article_name:
                try:
                    article = Article.objects.get(name=article_name)
                    board_article_dict["article"] = article
                    board_article_dict["name"] = f"{board.name}_{article.name}"
                except Exception as e:
                    print("article e", article_name, e)
                    failed_board_article = board_article_dict_only_strings.copy()
                    failed_board_article["error"] = str(e) + f" {article_name}"
                    message["fail"]["boardarticle"].append(failed_board_article)
                    continue
                print("board_article_dict replace article obj")
                pp(board_article_dict)
            try:
                board_article_dict["count"] = int(board_article_dict["count"])
            except Exception as e:
                print("integer e", board_article_dict["name"], "count", e)
                failed_board_article = board_article_dict_only_strings.copy()
                failed_board_article["error"] = (
                    str(e) + f" {board_article_dict['name']} count"
                )
                message["fail"]["boardarticle"].append(failed_board_article)
                continue
            print("board_article_dict ensure numerics")
            pp(board_article_dict)

            try:
                board_article = BoardArticle.objects.create(**board_article_dict)
                message["created"]["boardarticle"].append(
                    {k: v for k, v in board_article_dict_only_strings.items()}
                )
            except Exception as e:
                print("board_article e", e)
                failed_board_article = {
                    k: v for k, v in board_article_dict_only_strings.items()
                }
                failed_board_article["error"] = str(e)
                message["fail"]["boardarticle"].append(failed_board_article)
    pp(message)
    return message


class ListStoragesAPI(generics.ListAPIView):
    """List Storages API"""

    model = Carrier
    serializer_class = CarrierSerializer

    def get_queryset(self):
        """Retrieve Carrier queryset based on storage slots"""
        storage = self.kwargs["storage"]
        slots_qs = StorageSlot.objects.filter(storage__name=storage)
        queryset = Carrier.objects.filter(storage_slot__in=slots_qs)
        return queryset


class ArticleNameViewSet(generics.ListAPIView):
    """Article Name ViewSet"""

    model = Article

    def get(self, request):
        """Get all articles and serialize their names"""
        queryset = Article.objects.all()
        serializer = ArticleNameSerializer(queryset, many=True)
        data = [{k: v for k, v in a.items()} for a in serializer.data]
        return JsonResponse(data, safe=False)


class ArticleViewSet(viewsets.ModelViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    filter_backends = (
        django_filters.rest_framework.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    )
    filterset_class = ArticleFilter
    ordering_fields = "__all__"

    def _process_related_object(self, request_data, field_name, model_class):
        """
        Helper method to process provider/manufacturer fields with consistent logic
        """
        field_data = request_data.pop(field_name, None)
        print(f"{field_name}", field_data)

        if field_data and field_data not in [
            [""],
            {"name": ""},
            None,
            {"name": None},
        ]:
            print(f"creating {field_name} name: {field_data}")

            # Handle both string and object formats
            if isinstance(field_data, str):
                # When user types a new name (freesolo input)
                name_str = field_data
            elif isinstance(field_data, dict) and "name" in field_data:
                # When user selects an existing item from autocomplete
                name_str = field_data["name"]
            else:
                # Fallback - try to convert to string
                name_str = str(field_data)

            obj, _ = model_class.objects.get_or_create(name=name_str)
            return obj
        return None

    def create(self, *args, **kwargs):
        request_data = self.request.data.copy()
        serializer_kwargs = {}

        # Process all providers
        for i in range(1, 6):
            provider_field = f"provider{i}"
            provider_obj = self._process_related_object(
                request_data, provider_field, Provider
            )
            if provider_obj:
                serializer_kwargs[provider_field] = provider_obj

        # Process manufacturer
        manufacturer_obj = self._process_related_object(
            request_data, "manufacturer", Manufacturer
        )
        if manufacturer_obj:
            serializer_kwargs["manufacturer"] = manufacturer_obj

        request_data.update(serializer_kwargs)
        serializer = self.get_serializer(data=request_data)

        if not serializer.is_valid():
            print("serializer.errors", serializer.errors)
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer.save()
        data = serializer.validated_data

        headers = self.get_success_headers(serializer.data)

        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )


class BoardViewSet(viewsets.ModelViewSet):
    queryset = Board.objects.all()
    serializer_class = BoardSerializer
    filter_backends = (
        django_filters.rest_framework.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    )
    filterset_class = BoardFilter


class BoardArticleViewSet(viewsets.ModelViewSet, DestroyModelMixin):
    queryset = BoardArticle.objects.all()
    serializer_class = BoardArticleSerializer
    filter_backends = (
        django_filters.rest_framework.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    )
    filterset_class = BoardArticleFilter


class CarrierNameViewSet(generics.ListAPIView):
    model = Carrier

    def get(self, request):
        queryset = Carrier.objects.all()
        serializer = CarrierNameSerializer(queryset, many=True)
        data = [{k: v for k, v in c.items()} for c in serializer.data]
        return JsonResponse(data, safe=False)


class StorageNameViewSet(generics.ListAPIView):
    model = Storage

    def get(self, request):
        queryset = Storage.objects.all()
        serializer = StorageNameSerializer(queryset, many=True)
        data = [{k: v for k, v in s.items()} for s in serializer.data]
        return JsonResponse(data, safe=False)


class StorageSlotNameViewSet(generics.ListAPIView):
    model = StorageSlot

    def get(self, request):
        queryset = StorageSlot.objects.all()
        serializer = StorageSlotNameSerializer(queryset, many=True)
        data = [{k: v for k, v in s.items()} for s in serializer.data]
        return JsonResponse(data, safe=False)


class CarrierViewSet(viewsets.ModelViewSet):
    queryset = Carrier.objects.all()
    serializer_class = CarrierSerializer
    filter_backends = (
        filters.SearchFilter,
        django_filters.rest_framework.DjangoFilterBackend,
        filters.OrderingFilter,
    )
    filterset_class = CarrierFilter
    ordering_fields = [field.name for field in Carrier._meta.get_fields()] + [
        "article__manufacturer__name",
        "article__manufacturer_description",
        "article__description",
        "article__sap_number",
    ]
    search_fields = [
        "name",
        "article__sap_number",
        "article__description",
        "article__manufacturer__name",
        "article__provider1__name",
        "article__provider2__name",
        "article__provider3__name",
        "article__provider4__name",
        "article__provider5__name",
        "article__manufacturer_description",
        "article__provider1_description",
        "article__provider2_description",
        "article__provider3_description",
        "article__provider4_description",
        "article__provider5_description",
        "diameter",
        "width",
        "container_type",
        "quantity_original",
        "quantity_current",
        "lot_number",
        "storage_slot_qr_value",
    ]

    def get_queryset(self):
        return Carrier.objects.all()


class JobViewSet(viewsets.ModelViewSet):
    queryset = Job.objects.all()
    serializer_class = JobSerializer
    filterset_class = JobFilter
    filter_backends = (
        filters.SearchFilter,
        django_filters.rest_framework.DjangoFilterBackend,
        filters.OrderingFilter,
    )
    ordering_fields = "__all__"
    search_fields = [
        "name",
        "description",
        "board__name",
        "machine__name",
        "project",
        "customer",
        "start_at",
        "finish_at",
        "status",
    ]

    def get_queryset(self):
        queryset = super().get_queryset()
        ordering = self.request.query_params.get("ordering", None)
        if ordering:
            queryset = queryset.order_by(ordering)
        return queryset


class MachineViewSet(viewsets.ModelViewSet):
    queryset = Machine.objects.all()
    serializer_class = MachineSerializer


class MachineSlotViewSet(viewsets.ModelViewSet):
    queryset = MachineSlot.objects.all()
    serializer_class = MachineSlotSerializer


class ManufacturerNameViewSet(generics.ListAPIView):
    model = Manufacturer

    def get(self, request):
        queryset = Manufacturer.objects.all()
        serializer = ManufacturerNameSerializer(queryset, many=True)
        data = [{k: v for k, v in c.items()} for c in serializer.data]
        return JsonResponse(data, safe=False)


class ManufacturerViewSet(viewsets.ModelViewSet):
    queryset = Manufacturer.objects.all()
    serializer_class = ManufacturerSerializer
    filterset_class = ManufacturerFilter
    filter_backends = (
        filters.SearchFilter,
        django_filters.rest_framework.DjangoFilterBackend,
        filters.OrderingFilter,
    )

    ordering_fields = "__all__"
    search_fields = "__all__"


class ProviderNameViewSet(generics.ListAPIView):
    model = Provider

    def get(self, request):
        queryset = Provider.objects.all()
        serializer = ProviderNameSerializer(queryset, many=True)
        data = [{k: v for k, v in c.items()} for c in serializer.data]
        return JsonResponse(data, safe=False)


class ProviderViewSet(viewsets.ModelViewSet):
    queryset = Provider.objects.all()
    serializer_class = ProviderSerializer


class StorageViewSet(viewsets.ModelViewSet):
    queryset = Storage.objects.all()
    serializer_class = StorageSerializer


class StorageSlotViewSet(viewsets.ModelViewSet):
    queryset = StorageSlot.objects.all()
    serializer_class = StorageSlotSerializer
    filter_backends = (
        django_filters.rest_framework.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    )
    filterset_class = StorageSlotFilter
    ordering_fields = ["name", "led_state", "diameter", "width", "storage__name"]
    search_fields = [
        "qr_value",
        "storage__name",
    ]


class ListFreeSlotsAPI(generics.ListAPIView):
    """List Free Storage Slots API - returns slots without carriers"""

    serializer_class = StorageSlotSerializer

    def get_queryset(self):
        """Retrieve free storage slots for a specific storage"""
        storage_name = self.kwargs.get("storage")
        print(f"DEBUG: Finding free slots for storage: '{storage_name}'")
        
        # First verify the storage exists
        try:
            storage = Storage.objects.get(name=storage_name)
            print(f"DEBUG: Found storage object: {storage}")
        except Storage.DoesNotExist:
            print(f"DEBUG: Storage '{storage_name}' does not exist!")
            return StorageSlot.objects.none()

        # Get all slots for this storage
        all_slots = StorageSlot.objects.filter(storage=storage)
        print(f"DEBUG: Total slots for storage '{storage_name}': {all_slots.count()}")
        
        # Find slots without carriers using the correct relationship
        # Since Carrier has a OneToOneField to StorageSlot, we check if no carrier references this slot
        free_slots = all_slots.filter(carrier__isnull=True).order_by("name")
        
        print(f"DEBUG: Free slots query: {free_slots.query}")
        print(f"DEBUG: Free slots found: {free_slots.count()}")
        print(f"DEBUG: First 5 free slots: {list(free_slots.values('id', 'name', 'storage__name')[:5])}")

        return free_slots

    def get(self, request, *args, **kwargs):
        """Override get method to add additional metadata"""
        print(f"DEBUG: Processing GET request with kwargs: {kwargs}")
        
        storage_name = self.kwargs.get("storage")
        
        # Verify storage exists first
        try:
            storage = Storage.objects.get(name=storage_name)
        except Storage.DoesNotExist:
            return Response({
                "error": f"Storage '{storage_name}' not found",
                "available_storages": list(Storage.objects.values_list('name', flat=True))
            }, status=404)
        
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)

        total_slots = StorageSlot.objects.filter(storage=storage).count()
        free_slots_count = queryset.count()
        occupied_slots_count = total_slots - free_slots_count

        print(f"DEBUG: Total slots: {total_slots}")
        print(f"DEBUG: Free slots: {free_slots_count}")
        print(f"DEBUG: Occupied slots: {occupied_slots_count}")

        response_data = {
            "storage_name": storage_name,
            "total_slots": total_slots,
            "free_slots_count": free_slots_count,
            "occupied_slots_count": occupied_slots_count,
            "free_slots": serializer.data,
        }

        return Response(response_data)
