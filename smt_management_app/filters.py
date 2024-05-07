import django_filters
from django.db.models import Q

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


class ArticleFilter(django_filters.rest_framework.FilterSet):
    provider1__name = django_filters.rest_framework.CharFilter(method="provider_filter")
    provider2__name = django_filters.rest_framework.CharFilter(method="provider_filter")
    provider3__name = django_filters.rest_framework.CharFilter(method="provider_filter")
    provider4__name = django_filters.rest_framework.CharFilter(method="provider_filter")
    provider5__name = django_filters.rest_framework.CharFilter(method="provider_filter")

    class Meta:
        model = Article
        fields = {
            "name": ["exact", "contains"],
            "description": ["exact", "contains"],
            "manufacturer__name": ["exact", "contains"],
            "manufacturer_description": ["exact", "contains"],
            "provider1__name": ["exact", "contains"],
            "provider1_description": ["exact", "contains"],
            "provider2__name": ["exact", "contains"],
            "provider2_description": ["exact", "contains"],
            "provider3__name": ["exact", "contains"],
            "provider3_description": ["exact", "contains"],
            "provider4__name": ["exact", "contains"],
            "provider4_description": ["exact", "contains"],
            "provider5__name": ["exact", "contains"],
            "provider5_description": ["exact", "contains"],
            "sap_number": ["exact", "contains"],
            "created_at": ["exact", "contains", "gte", "lte", "lt", "gt"],
            "updated_at": ["exact", "contains", "gte", "lte", "lt", "gt"],
            "archived": ["exact"],
        }

    def provider_filter(self, queryset, name, value):
        qs = queryset.filter(
            Q(provider1__name__contains=value)
            | Q(provider2__name__contains=value)
            | Q(provider3__name__contains=value)
            | Q(provider4__name__contains=value)
            | Q(provider5__name__contains=value)
        )
        return qs


class BoardArticleFilter(django_filters.rest_framework.FilterSet):
    class Meta:
        model = BoardArticle
        fields = "__all__"


class BoardFilter(django_filters.rest_framework.FilterSet):
    class Meta:
        model = Board
        fields = "__all__"


class CarrierFilter(django_filters.FilterSet):
    article__provider1__name = django_filters.rest_framework.CharFilter(
        method="article_provider_filter"
    )
    article__provider2__name = django_filters.rest_framework.CharFilter(
        method="article_provider_filter"
    )
    article__provider3__name = django_filters.rest_framework.CharFilter(
        method="article_provider_filter"
    )
    article__provider4__name = django_filters.rest_framework.CharFilter(
        method="article_provider_filter"
    )
    article__provider5__name = django_filters.rest_framework.CharFilter(
        method="article_provider_filter"
    )

    storage_slot_is_null = django_filters.rest_framework.BooleanFilter(
        field_name="storage_slot__isnull"
    )

    class Meta:
        model = Carrier
        fields = {
            "name": ["exact", "contains"],
            "diameter": ["exact", "gt", "lt", "lte", "gte"],
            "width": ["exact", "gt", "lt", "lte", "gte"],
            "container_type": ["exact", "gt", "lt"],
            "quantity_original": ["exact", "gt", "lt", "lte", "gte"],
            "quantity_current": ["exact", "gt", "lt", "lte", "gte"],
            "lot_number": ["exact", "contains"],
            "reserved": ["exact"],
            "delivered": ["exact"],
            "collecting": ["exact"],
            "article__name": ["exact", "contains"],
            "article__description": ["exact", "contains"],
            "article__manufacturer__name": ["exact", "contains"],
            "article__manufacturer_description": ["exact", "contains"],
            "article__provider1__name": ["exact", "contains"],
            "article__provider2__name": ["exact", "contains"],
            "article__provider3__name": ["exact", "contains"],
            "article__provider4__name": ["exact", "contains"],
            "article__provider5__name": ["exact", "contains"],
            "article__sap_number": ["exact", "contains"],
            "storage_slot": ["isnull"],
            "storage_slot__name": ["exact", "contains"],
            "storage__name": ["exact", "contains"],
            "machine_slot__name": ["exact", "contains"],
            "archived": ["exact"],
            "created_at": ["exact", "contains", "gte", "lte", "lt", "gt"],
            "updated_at": ["exact", "contains", "gte", "lte", "lt", "gt"],
        }

    def article_provider_filter(self, queryset, name, value):
        qs = queryset.filter(
            Q(article__provider1__name__contains=value)
            | Q(article__provider2__name__contains=value)
            | Q(article__provider3__name__contains=value)
            | Q(article__provider4__name__contains=value)
            | Q(article__provider5__name__contains=value)
        )
        return qs


class JobFilter(django_filters.FilterSet):
    class Meta:
        model = Job
        fields = {
            "name": ["exact", "contains"],
            "board__name": ["exact", "icontains"],
            "machine__name": ["exact", "icontains"],
            "project": ["exact", "icontains"],
            "customer": ["exact", "icontains"],
            "count": ["exact", "gt", "lt", "lte", "gte"],
            "start_at": ["exact", "gte", "lte"],
            "finish_at": ["exact", "gte", "lte"],
            "status": ["exact"],
            "archived": ["exact"],
            "created_at": ["exact", "contains", "gte", "lte", "lt", "gt"],
            "updated_at": ["exact", "contains", "gte", "lte", "lt", "gt"],
        }


class ManufacturerFilter(django_filters.rest_framework.FilterSet):
    class Meta:
        model = Manufacturer
        fields = {
            "name": ["exact", "contains"],
        }
