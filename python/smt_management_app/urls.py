from django.urls import path
from . import views
from rest_framework.routers import DefaultRouter

router = DefaultRouter()

router.register(r"article", views.ArticleViewSet, "article")
router.register(r"board", views.BoardViewSet, "board")
router.register(r"boardarticle", views.BoardArticleViewSet, "boardarticle")
router.register(r"carrier", views.CarrierViewSet, "carrier")
router.register(r"job", views.JobViewSet, "job")
router.register(r"machine", views.MachineViewSet, "machine")
router.register(r"machineslot", views.MachineSlotViewSet, "machineslot")
router.register(r"manufacturer", views.ManufacturerViewSet, "manufacturer")
router.register(r"provider", views.ProviderViewSet, "provider")
router.register(r"storage", views.StorageViewSet, "storage")
router.register(r"storageslot", views.StorageSlotViewSet, "storageslot")

name = "smt_management_app"
urlpatterns = router.urls
urlpatterns.append(
    path(
        "save_file_and_get_headers/",
        views.save_file_and_get_headers,
        name="save_file_and_get_headers",
    )
)
urlpatterns.append(
    path(
        "user_mapping_and_file_processing/",
        views.user_mapping_and_file_processing,
        name="user_mapping_and_file_processing",
    )
)
urlpatterns.append(
    path(
        "get_storage_content/<storage>/",
        views.ListStoragesAPI.as_view(),
        name="get_storage_content",
    )
)
urlpatterns.append(
    path("collect_carrier/<carrier>/", views.collect_carrier, name="collect_carrier")
)
urlpatterns.append(
    path(
        "collect_carrier_confirm/<carrier>/<slot>/",
        views.collect_carrier_confirm,
        name="collect_carrier_confirm",
    )
)
urlpatterns.append(
    path(
        "store_carrier/<carrier>/<storage>/", views.store_carrier, name="store_carrier"
    )
)
urlpatterns.append(
    path(
        "store_carrier_confirm/<carrier>/<slot>/",
        views.store_carrier_confirm,
        name="store_carrier_confirm",
    )
)

urlpatterns.append(
    path(
        "store_carrier_choose_slot/<carrier>/<storage>/",
        views.store_carrier_choose_slot,
        name="store_carrier_choose_slot",
    )
)
urlpatterns.append(
    path(
        "store_carrier_choose_slot_confirm/<carrier>/<slot>/",
        views.store_carrier_choose_slot_confirm,
        name="store_carrier_choose_slot_confirm",
    )
)

urlpatterns.append(
    path("articlelist/", views.ArticleNameViewSet.as_view(), name="articlelist")
)
urlpatterns.append(
    path("carrierlist/", views.CarrierNameViewSet.as_view(), name="carrierlist")
)

urlpatterns.append(
    path("providerlist/", views.ProviderNameViewSet.as_view(), name="providerlist")
)


urlpatterns.append(
    path(
        "manufacturerlist/",
        views.ManufacturerNameViewSet.as_view(),
        name="manufacturerlist",
    )
)

urlpatterns.append(path("get_csrf_token/", views.get_csrf_token, name="get_csrf_token"))
urlpatterns.append(
    path(
        "check_pk_unique/<model_name>/<value>/",
        views.check_pk_unique,
        name="check_pk_unique",
    )
)

urlpatterns.append(
    path(
        "check_unique/<field>/<value>/",
        views.check_unique,
        name="check_unique",
    )
)

urlpatterns.append(
    path(
        "reset_leds/<storage>/",
        views.reset_leds,
        name="reset_leds",
    )
)

urlpatterns.append(
    path(
        "dashboard_data/",
        views.dashboard_data,
        name="dashboard_data",
    )
)

urlpatterns.append(
    path(
        "test_leds/",
        views.test_leds,
        name="test_leds",
    )
)

urlpatterns.append(
    path(
        "collectCarrierByArticle/<storage>/<article>/",
        views.collect_carrier_by_article,
        name="collect_carrier_by_article",
    )
)

urlpatterns.append(
    path(
        "confirmCarrierByArticle/<storage>/<article>/<carrier>/",
        views.confirm_carrier_by_article,
        name="confirm_carrier_by_article",
    )
)

urlpatterns.append(
    path(
        "print_carrier/<carrier>/",
        views.print_carrier,
        name="print_carrier",
    )
)
