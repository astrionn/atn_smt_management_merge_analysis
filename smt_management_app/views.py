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
    StorageSlotSerializer,
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
    collect_job,
)

from .storing import (
    store_carrier,
    store_carrier_confirm,
    store_carrier_cancel,
    store_carrier_choose_slot,
    store_carrier_choose_slot_confirm,
    store_carrier_choose_slot_cancel,
)

from .extra_shelf_interactions import test_leds, reset_leds


def assign_carrier_to_job(request, job_name, carrier_name):
    job = Job.objects.filter(name=job_name).first()
    carrier = Carrier.objects.filter(name=carrier_name, archived=False).first()

    if job and carrier:
        job.carriers.add(carrier)
        if job.carriers.count() == job.board.articles.count():
            job.status = 1
        job.save()
        carrier.reserved = True
        carrier.save()
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
        map_ = {v:k for k,v in map_.items() if v and k}
        match lf.upload_type:
            case "article":
                return JsonResponse(process_article_file(lf.file_object.path,lf.delimiter,map_))
            case "carrier":
                return JsonResponse(process_carrier_file(lf.file_object.path,lf.delimiter,map_,lf.lot_number))
            case "board":
                return JsonResponse(process_board_file(lf.file_object.path,lf.delimiter,map_,lf.board_name))

        
def process_article_file(file_path,delimiter,map_):
    
    message = {"created": {'article':[],
                           'manufacturer':[],
                           'provider':[]},
                "fail": {'article':[],
                           'manufacturer':[],
                           'provider':[]}
                           }
    with open(file_path, "r", encoding="utf-8") as f:
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
                manufacturer, manufacturer_created = (
                    Manufacturer.objects.get_or_create(name=manufacturer_name)
                )
                article_dict["manufacturer"] = manufacturer
                if manufacturer_created:
                    message["created"]['manufacturer'].append({k:v for k,v in manufacturer.__dict__.items() if k != '_state'})

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
                        message["created"]['provider'].append({k:v for k,v in provider.__dict__.items() if k != '_state'})
            try:
                article = Article.objects.create(**article_dict)
                message["created"]['article'].append({k:v for k,v in article_dict_only_strings.__dict__.items()})
            except Exception as e:
                failed_article = article_dict_only_strings
                failed_article["error"] = str(e)
                message["fail"]['article'].append(failed_article)

    return message

def process_carrier_file(file_path,delimiter,map_,lot_number):
    print('process_carrier_file')
    print(f'file_path: {file_path}')
    print(f'delimiter: {delimiter}')
    print(f'map_:')
    pp(map_)
    print(f'lot_number: {lot_number}')

    message = {"created": {'carrier':[]},
                "fail": {'carrier':[]}}
    with open(file_path, "r", encoding="utf-8") as f:
        csv_reader = csv.reader(f, delimiter=delimiter)
        headers = next(csv_reader)
        print('headers')
        print(headers)
        for row in csv_reader:
            print('row')
            print(row)
            carrier_dict = {}
            for i, col_name in enumerate(headers):
                alternate_col = map_.get(col_name)
                if alternate_col:
                    carrier_dict[alternate_col] = row[i]
            
            if lot_number:
                carrier_dict['lot_number'] = lot_number
                print('carrier_dict replace lot number')
                pp(carrier_dict)
            
            carrier_dict_only_strings = carrier_dict.copy()
            print('carrier_dict only strings')
            pp(carrier_dict_only_strings)


            article_name = carrier_dict.get("article")
            if article_name:
                try:
                    article= Article.objects.get(name=article_name)
                    carrier_dict["article"] = article
                except Exception as e:
                    print('article e',article_name,e)
                    failed_carrier = carrier_dict_only_strings.copy()
                    failed_carrier["error"] = str(e) + f" {article_name}"
                    message["fail"]['carrier'].append(failed_carrier)
                    continue
            print('carrier_dict replace article obj')
            pp(carrier_dict)
            integer_fields = ['diameter', 'width', 'container_type','quantity_original','quantity_current','reserved','delivered','collecting']
            try:
                for field in integer_fields:
                    if field not in carrier_dict.keys(): continue
                    carrier_dict[field] = int(carrier_dict[field]) if carrier_dict[field] else ''
            except Exception as e:
                print('integer e',carrier_dict['name'],field,e)
                failed_carrier = carrier_dict_only_strings.copy()
                failed_carrier["error"] = str(e) + f" {carrier_dict['name']} {field}"
                message["fail"]['carrier'].append(failed_carrier)
                continue
            print('carrier_dict ensure numerics')
            pp(carrier_dict)
            try:
                carrier = Carrier.objects.create(**carrier_dict)
                message["created"]['carrier'].append({k:v for k,v in carrier_dict_only_strings.items()})
            except Exception as e:
                print('carrier e',e)
                failed_carrier = {k:v for k,v in carrier_dict_only_strings.items()}
                failed_carrier["error"] = str(e)
                message["fail"]['carrier'].append(failed_carrier)
    return message
def process_board_file(file_path,delimiter,map_,board_name):
    
    message = {"created": {'board':[],'boardarticle':[]},
                "fail": {'board':[],'boardarticle':[]}}
    
    board = Board.objects.get(name=board_name)

    with open(file_path, "r", encoding="utf-8") as f:
        csv_reader = csv.reader(f, delimiter=delimiter)
        headers = next(csv_reader)
        for row in csv_reader:
            board_article_dict = {}
            for i, col_name in enumerate(headers):
                alternate_col = map_.get(col_name)
                if alternate_col:
                    board_article_dict[alternate_col] = row[i]

            board_article_dict_only_strings = board_article_dict.copy()
            print('board_article_dict only strings')
            pp(board_article_dict_only_strings)

            board_article_dict['board'] = board

            article_name = board_article_dict.get("article")
            if article_name:
                try:
                    article= Article.objects.get(name=article_name)
                    board_article_dict["article"] = article
                    board_article_dict["name"] = f"{board.name}_{article.name}"
                except Exception as e:
                    print('article e',article_name,e)
                    failed_board_article = board_article_dict_only_strings.copy()
                    failed_board_article["error"] = str(e) + f" {article_name}"
                    message["fail"]['boardarticle'].append(failed_board_article)
                    continue
                print('board_article_dict replace article obj')
                pp(board_article_dict)
            try:
                board_article_dict['count'] = int(board_article_dict['count'])
            except Exception as e:
                print('integer e',board_article_dict['name'],'count',e)
                failed_board_article = board_article_dict_only_strings.copy()
                failed_board_article["error"] = str(e) + f" {board_article_dict['name']} count"
                message["fail"]['boardarticle'].append(failed_board_article)
                continue
            print('board_article_dict ensure numerics')
            pp(board_article_dict)

            try:
                board_article = BoardArticle.objects.create(**board_article_dict)
                message["created"]['boardarticle'].append({k:v for k,v in board_article_dict_only_strings.items()})
            except Exception as e:
                print('board_article e',e)
                failed_board_article = {k:v for k,v in board_article_dict_only_strings.items()}
                failed_board_article["error"] = str(e)
                message["fail"]['boardarticle'].append(failed_board_article)
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

    def create(self, *args, **kwargs):

        serializer = self.get_serializer(data=self.request.data)
        manufacturer_name = self.request.data.pop("manufacturer", None)
        provider1_name = self.request.data.pop("provider1", None)
        provider2_name = self.request.data.pop("provider2", None)
        provider3_name = self.request.data.pop("provider3", None)
        provider4_name = self.request.data.pop("provider4", None)
        provider5_name = self.request.data.pop("provider5", None)

        if not serializer.is_valid():
            print(serializer.errors)
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer_kwargs = {}
        if provider1_name:
            provider1, _ = Provider.objects.get_or_create(name=provider1_name["name"])
            serializer_kwargs["provider1"] = provider1

        if provider2_name:
            provider2, _ = Provider.objects.get_or_create(name=provider2_name["name"])
            serializer_kwargs["provider2"] = provider2

        if provider3_name:
            provider3, _ = Provider.objects.get_or_create(name=provider3_name["name"])
            serializer_kwargs["provider3"] = provider3

        if provider4_name:
            provider4, _ = Provider.objects.get_or_create(name=provider4_name["name"])
            serializer_kwargs["provider4"] = provider4

        if provider5_name:
            provider5, _ = Provider.objects.get_or_create(name=provider5_name["name"])
            serializer_kwargs["provider5"] = provider5

        if manufacturer_name:
            manufacturer, _ = Manufacturer.objects.get_or_create(
                name=manufacturer_name["name"]
            )
            serializer_kwargs["manufacturer"] = manufacturer
        if serializer_kwargs:
            serializer.save(**serializer_kwargs)

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
    search_fields = "__all__"

    def get_queryset(self):
        name = self.request.GET.get("name")
        lot_number = self.request.GET.get("lot_number")
        storage = self.request.GET.get("storage")
        filter_args = {
            "name__icontains": name,
            "lot_number__icontains": lot_number,
            "storage__name__icontains": storage,
        }
        filter_args = dict(
            (k, v)
            for k, v in filter_args.items()
            if (v is not None and v != "" and v != [])
        )
        carriers = Carrier.objects.filter(**filter_args)
        return carriers


class JobViewSet(viewsets.ModelViewSet):
    queryset = Job.objects.all()
    serializer_class = JobSerializer
    filterset_class = JobFilter
    ordering_fields = "__all__"

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
