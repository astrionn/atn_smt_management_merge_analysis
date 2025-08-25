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
from django.db.models import Q
from rest_framework.decorators import action
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
    assign_carrier_to_job,
    deliver_all_carriers,
)

from .collecting import (
    collect_single_carrier,
    collect_single_carrier_confirm,
    collect_single_carrier_cancel,
    collect_carrier,
    collect_carrier_confirm,
    collect_carrier_cancel,
    collect_carrier_by_article,
    collect_carrier_by_article_select,
    collect_carrier_by_article_confirm,
    collect_carrier_by_article_cancel,
    collect_job,
)

from .storing import (
    store_carrier,
    store_carrier_confirm,
    store_carrier_cancel,
    store_carrier_choose_slot,
    store_carrier_choose_slot_confirm,
    store_carrier_choose_slot_confirm_by_qr,
    store_carrier_choose_slot_cancel,
    get_free_slots,
    fetch_available_storages_for_auto,
    store_carrier_choose_slot_all_storages,
    store_auto_with_storage_selection,
)

from .extra_shelf_interactions import test_leds, reset_leds, change_slot_color


# Functions moved to helpers.py


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
def user_mapping_and_file_processing_old(request):
    """
    first of all i am sorry for this monster, feel free to refactor when bored
    this function is the abstraction for the user uploading csv files to create model instances with them,
    but the csv headers names do not have to correspond with
    """
    # the models field names, because the user creates a mapping from the csv header names to the models field names in the frontend

    if request.method == "POST":
        file_name = request.POST.get("file_name")

        lf = LocalFile.objects.get(name=file_name)

        map_json = json.loads(request.POST["map"])

        map_l = [
            (k, v) for k, v in map_json.items() if v
        ]  # remove fields that have empty values

        msg = {"created": [], "fail": []}

        with open(lf.file_object.path, "r", encoding="ISO-8859-1") as f:

            csv_reader = csv.reader(f, delimiter=lf.delimiter)
            a_headers = next(csv_reader)

            index_map = {value: index for index, value in enumerate(a_headers)}
            map_ordered_l = sorted(map_l, key=lambda x: index_map[x[1]])

            for item in csv_reader:
                if lf.upload_type == "board":
                    if not lf.board_name or not Board.objects.filter(
                        name=lf.board_name
                    ):
                        msg["fail"].append(f"Board {lf.board_name} does not exist.")
                        break
                    board = Board.objects.get(name=lf.board_name)

                    board_article_dict = {
                        key[0]: item[a_headers.index(key[1])] for key in map_ordered_l
                    }
                    board_article_dict["board"] = board

                    article_name = board_article_dict["article"]
                    article_exists = Article.objects.filter(name=article_name).exists()

                    if not article_exists:
                        article_count = board_article_dict.get("count")
                        if not article_count or not article_count.isnumeric():
                            msg["fail"].append(f"{article_name} has an invalid count.")
                            break

                        board_article_dict["name"] = f"{board.name}_{article_name}"
                        BoardArticle.objects.create(**board_article_dict)
                        msg["created"].append(board_article_dict["name"])

                elif lf.upload_type == "carrier":
                    carrier_dict = {
                        key[0]: item[a_headers.index(key[1])] for key in map_ordered_l
                    }

                    article_name = carrier_dict.get("article")
                    if article_name:

                        article = Article.objects.filter(name=article_name).first()
                        if article:
                            carrier_dict["article"] = article
                        else:
                            msg["fail"].append(f"{article_name} does not exist.")
                            continue

                    # Set default values if not provided
                    carrier_dict.setdefault("storage_slot", None)
                    carrier_dict.setdefault("storage", None)
                    carrier_dict.setdefault("machine_slot", None)
                    carrier_dict.setdefault("diameter", 7)
                    carrier_dict.setdefault("width", 8)
                    carrier_dict.setdefault("quantity_current", 0)
                    carrier_dict.setdefault("quantity_original", 0)

                    numeric_fields = [
                        "diameter",
                        "width",
                        "quantity_current",
                        "quantity_original",
                    ]
                    for numeric_field in numeric_fields:
                        try:
                            carrier_dict[numeric_field] = int(
                                carrier_dict[numeric_field]
                            )
                        except Exception as e:
                            print(e)
                            msg["fail"].append(
                                f"invalid {numeric_field}: {carrier_dict[numeric_field]}"
                            )
                            carrier_dict.pop(numeric_field)

                    container_type = carrier_dict.get("container_type", "").lower()
                    carrier_dict["container_type"] = {
                        "reel": 0,
                        "tray": 1,
                        "bag": 2,
                        "single": 3,
                    }.get(container_type, 0)

                    carrier_name = carrier_dict["name"]
                    if not Carrier.objects.filter(name=carrier_name).exists():
                        new_carrier = Carrier.objects.create(**carrier_dict)
                        msg["created"].append(new_carrier.name)
                    else:
                        msg["fail"].append(
                            f" failed to create {carrier_name} ({carrier_dict})"
                        )

                elif lf.upload_type == "article":
                    article_dict = {
                        key[0]: item[a_headers.index(key[1])] for key in map_ordered_l
                    }

                    manufacturer_name = article_dict.get("manufacturer")
                    if manufacturer_name:
                        manufacturer, manufacturer_created = (
                            Manufacturer.objects.get_or_create(name=manufacturer_name)
                        )
                        article_dict["manufacturer"] = manufacturer
                        if manufacturer_created:
                            msg["created"].append(manufacturer.name)

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
                                msg["created"].append(provider.name)

                    if "boardarticle" in article_dict and article_dict["boardarticle"]:
                        del article_dict["boardarticle"]

                    article_name = article_dict["name"]
                    article_exists = Article.objects.filter(name=article_name).exists()

                    if not article_exists:
                        new_article = Article.objects.create(
                            **{
                                key: value
                                for key, value in article_dict.items()
                                if key and value
                            }
                        )

                        if new_article:
                            msg["created"].append(new_article.name)
                    else:
                        msg["fail"].append(article_name)

        return JsonResponse(msg, safe=False)
    return JsonResponse({"success": "false"})


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
    """Get storage content with combined slots support"""

    def get(self, request, storage):
        try:
            storage_obj = Storage.objects.get(name=storage)
        except Storage.DoesNotExist:
            return JsonResponse({"error": "Storage not found"}, status=404)

        # Get all slots with their carriers
        slots = StorageSlot.objects.filter(storage=storage_obj).select_related(
            "carrier"
        )

        # Build logical view of slots
        logical_slots = {}
        seen_names = set()

        for slot in slots:
            if slot.name in seen_names:
                continue

            all_names = slot.get_all_slot_names()
            seen_names.update(all_names)

            # Get carrier info if any slot in the group has one
            carrier_info = None
            for name in all_names:
                try:
                    check_slot = StorageSlot.objects.get(storage=storage_obj, name=name)
                    if hasattr(check_slot, "carrier") and check_slot.carrier:
                        carrier_info = {
                            "name": check_slot.carrier.name,
                            "article": check_slot.carrier.article.name,
                            "quantity": check_slot.carrier.quantity_current,
                            "lot": check_slot.carrier.lot_number,
                        }
                        break
                except StorageSlot.DoesNotExist:
                    continue

            logical_slots[str(slot.name)] = {
                "name": slot.name,
                "qr_value": slot.qr_value,
                "all_qr_codes": slot.get_all_qr_codes(),
                "related_slots": all_names,
                "is_combined": len(all_names) > 1,
                "diameter": slot.diameter,
                "width": slot.width,
                "carrier": carrier_info,
                "led_state": slot.led_state,
            }

        return JsonResponse(
            {
                "storage": storage,
                "physical_slots": slots.count(),
                "logical_slots": len(logical_slots),
                "slots": logical_slots,
            }
        )


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

    def create(self, *args, **kwargs):

        request_data = self.request.data.copy()

        serializer_kwargs = {}

        provider1_name = request_data.pop("provider1", None)
        print("provider1_name", provider1_name)
        if provider1_name and provider1_name not in [
            [""],
            {"name": ""},
            None,
            {"name": None},
            "",
        ]:
            print(f"creating provider1_name name: {provider1_name}")
            # Handle both string and dict formats
            if isinstance(provider1_name, dict):
                provider_name = provider1_name.get("name")
            else:
                provider_name = provider1_name

            if provider_name:
                provider1, _ = Provider.objects.get_or_create(name=provider_name)
                serializer_kwargs["provider1"] = provider1

        provider2_name = request_data.pop("provider2", None)
        print("provider2_name", provider2_name)
        if provider2_name and provider2_name not in [
            [""],
            {"name": ""},
            None,
            {"name": None},
            "",
        ]:
            print(f"creating provider2_name name: {provider2_name}")
            # Handle both string and dict formats
            if isinstance(provider2_name, dict):
                provider_name = provider2_name.get("name")
            else:
                provider_name = provider2_name

            if provider_name:
                provider2, _ = Provider.objects.get_or_create(name=provider_name)
                serializer_kwargs["provider2"] = provider2

        provider3_name = request_data.pop("provider3", None)
        print("provider3_name", provider3_name)
        if provider3_name and provider3_name not in [
            [""],
            {"name": ""},
            None,
            {"name": None},
            "",
        ]:
            print(f"creating provider3_name name: {provider3_name}")
            # Handle both string and dict formats
            if isinstance(provider3_name, dict):
                provider_name = provider3_name.get("name")
            else:
                provider_name = provider3_name

            if provider_name:
                provider3, _ = Provider.objects.get_or_create(name=provider_name)
                serializer_kwargs["provider3"] = provider3

        provider4_name = request_data.pop("provider4", None)
        print("provider4_name", provider4_name)
        if provider4_name and provider4_name not in [
            [""],
            {"name": ""},
            None,
            {"name": None},
            "",
        ]:
            print(f"creating provider4_name name: {provider4_name}")
            # Handle both string and dict formats
            if isinstance(provider4_name, dict):
                provider_name = provider4_name.get("name")
            else:
                provider_name = provider4_name

            if provider_name:
                provider4, _ = Provider.objects.get_or_create(name=provider_name)
                serializer_kwargs["provider4"] = provider4

        provider5_name = request_data.pop("provider5", None)
        print("provider5_name", provider5_name)
        if provider5_name and provider5_name not in [
            [""],
            {"name": ""},
            None,
            {"name": None},
            "",
        ]:
            print(f"creating provider5_name name: {provider5_name}")
            # Handle both string and dict formats
            if isinstance(provider5_name, dict):
                provider_name = provider5_name.get("name")
            else:
                provider_name = provider5_name

            if provider_name:
                provider5, _ = Provider.objects.get_or_create(name=provider_name)
                serializer_kwargs["provider5"] = provider5

        manufacturer_name = request_data.pop("manufacturer", None)
        print("manufacturer_name", manufacturer_name)
        if manufacturer_name and manufacturer_name not in [
            [""],
            {"name": ""},
            None,
            {"name": None},
            "",
        ]:
            print(f"creating manufacturer_name name: {manufacturer_name}")
            # Handle both string and dict formats
            if isinstance(manufacturer_name, dict):
                manuf_name = manufacturer_name.get("name")
            else:
                manuf_name = manufacturer_name

            if manuf_name:
                manufacturer, _ = Manufacturer.objects.get_or_create(name=manuf_name)
                serializer_kwargs["manufacturer"] = manufacturer

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
        return Carrier.objects.select_related(
            'article',
            'article__manufacturer',
            'article__provider1',
            'article__provider2', 
            'article__provider3',
            'article__provider4',
            'article__provider5',
            'storage',
            'storage_slot'
        ).all()


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
    serializer_class = StorageSlotSerializer

    def get_queryset(self):
        queryset = StorageSlot.objects.all()

        # Add filter for finding slots by any QR code
        qr_code = self.request.query_params.get("qr_code", None)
        if qr_code:
            # Search in both primary qr_value and qr_codes array
            queryset = queryset.filter(
                Q(qr_value=qr_code) | Q(qr_codes__contains=qr_code)
            )

        # Add filter for combined slots only
        combined_only = self.request.query_params.get("combined_only", None)
        if combined_only and combined_only.lower() == "true":
            # Filter for slots that have related_names (are combined)
            queryset = queryset.exclude(related_names=[])

        # Add filter for storage
        storage = self.request.query_params.get("storage", None)
        if storage:
            queryset = queryset.filter(storage__name=storage)

        return queryset.order_by("storage__name", "name")

    @action(detail=True, methods=["get"])
    def combined_group(self, request, pk=None):
        """Get all slots in the same combined group"""
        slot = self.get_object()
        all_slot_names = slot.get_all_slot_names()

        # Get all slots in the group
        group_slots = StorageSlot.objects.filter(
            storage=slot.storage, name__in=all_slot_names
        ).order_by("name")

        serializer = self.get_serializer(group_slots, many=True)
        return Response(
            {
                "primary_slot": slot.name,
                "group_size": len(all_slot_names),
                "slots": serializer.data,
            }
        )

    @action(detail=False, methods=["get"])
    def logical_view(self, request):
        """
        Return slots grouped logically (combined slots appear as one).
        This view is useful for UI display where combined slots should appear as single entries.
        """
        storage = request.query_params.get("storage", None)

        queryset = self.get_queryset()
        if storage:
            queryset = queryset.filter(storage__name=storage)

        # Group slots logically
        seen_slots = set()
        logical_slots = []

        for slot in queryset:
            if slot.name in seen_slots:
                continue

            # Get all related slots
            all_names = slot.get_all_slot_names()
            seen_slots.update(all_names)

            # Use the slot with the lowest name as the representative
            if len(all_names) > 1:
                representative = (
                    StorageSlot.objects.filter(storage=slot.storage, name__in=all_names)
                    .order_by("name")
                    .first()
                )
            else:
                representative = slot

            logical_slots.append(representative)

        # Serialize with pagination
        page = self.paginate_queryset(logical_slots)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(logical_slots, many=True)
        return Response(serializer.data)


# Functions moved to storing.py and collecting.py modules
