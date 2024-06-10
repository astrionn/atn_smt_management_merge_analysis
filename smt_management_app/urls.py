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

# we overwrite the drf url for the http patch method here to allow the 'path' in the url which allows encoded special characters like '%2F'->'/'
urlpatterns.append(
    path(
        "carrier/<path:pk>/",
        views.CarrierViewSet.as_view({"patch": "partial_update"}),
    )
)
urlpatterns.append(
    path(
        "article/<path:pk>/",
        views.ArticleViewSet.as_view({"patch": "partial_update", "get": "retrieve"}),
    )
)
urlpatterns.append(
    path(
        "job/<path:pk>/",
        views.JobViewSet.as_view({"patch": "partial_update"}),
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
urlpatterns.append(
    path(
        "get_storage_content/<storage>/",
        views.ListStoragesAPI.as_view(),
        name="get_storage_content",
    )
)
######### helpers ###########
urlpatterns.append(
    path("create_qr_code/<path:code>/", views.create_qr_code, name="create_qr_code")
)


urlpatterns.append(path("get_csrf_token/", views.get_csrf_token, name="get_csrf_token"))

urlpatterns.append(
    path(
        "check_unique/<path:field>/<path:value>/",
        views.check_unique,
        name="check_unique",
    )
)

urlpatterns.append(
    path(
        "check_pk_unique/<model_name>/<path:value>/",
        views.check_pk_unique,
        name="check_pk_unique",
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
        "print_carrier/<path:carrier_name>/",
        views.print_carrier,
        name="print_carrier",
    )
)

urlpatterns.append(
    path(
        "archive_carrier/<path:carrier_name>/",
        views.archive_carrier,
        name="archive_carrier",
    )
)

urlpatterns.append(
    path(
        "get_collect_queue/",
        views.get_collect_queue,
        name="get_collect_queue",
    )
)
######### collecting ###########
urlpatterns.append(
    path(
        "collect_single_carrier/<path:carrier_name>/",
        views.collect_single_carrier,
        name="collect_single_carrier",
    )
)
urlpatterns.append(
    path(
        "collect_single_carrier_confirm/<path:carrier_name>/",
        views.collect_single_carrier_confirm,
        name="collect_single_carrier_confirm",
    )
)

urlpatterns.append(
    path(
        "collect_single_carrier_cancel/<path:carrier_name>/",
        views.collect_single_carrier_cancel,
        name="collect_single_carrier_cancel",
    )
)

urlpatterns.append(
    path(
        "collect_carrier/<path:carrier_name>/",
        views.collect_carrier,
        name="collect_carrier",
    )
)
urlpatterns.append(
    path(
        "collect_carrier_confirm/<path:carrier_name>/<storage_name>/<slot_name>/",
        views.collect_carrier_confirm,
        name="collect_carrier_confirm",
    )
)
urlpatterns.append(
    path(
        "collect_carrier_cancel/<path:carrier_name>/",
        views.collect_carrier_cancel,
        name="collect_carrier_cancel",
    )
)

urlpatterns.append(
    path(
        "collect_carrier_by_article/<path:article_name>/",
        views.collect_carrier_by_article,
        name="collect_carrier_by_article",
    )
)

urlpatterns.append(
    path(
        "collect_carrier_by_article_confirm/<path:carrier_name>/",
        views.collect_carrier_by_article_confirm,
        name="collect_carrier_by_article_confirm",
    )
)

urlpatterns.append(
    path(
        "collect_carrier_by_article_cancel/<path:article_name>/",
        views.collect_carrier_by_article_cancel,
        name="collect_carrier_by_article_cancel",
    )
)
urlpatterns.append(
    path("collect_job/<path:job_name>/", views.collect_job, name="collect_job")
)

######### storing ###########
urlpatterns.append(
    path(
        "store_carrier/<path:carrier_name>/<storage_name>/",
        views.store_carrier,
        name="store_carrier",
    )
)
urlpatterns.append(
    path(
        "store_carrier_confirm/<path:carrier_name>/<storage_name>/<slot_name>/",
        views.store_carrier_confirm,
        name="store_carrier_confirm",
    )
)
urlpatterns.append(
    path(
        "store_carrier_cancel/<path:carrier_name>/",
        views.store_carrier_cancel,
        name="store_carrier_cancel",
    )
)

urlpatterns.append(
    path(
        "store_carrier_choose_slot/<path:carrier_name>/<storage_name>/",
        views.store_carrier_choose_slot,
        name="store_carrier_choose_slot",
    )
)
urlpatterns.append(
    path(
        "store_carrier_choose_slot_confirm/<path:carrier_name>/<storage_name>/<slot_name>/",
        views.store_carrier_choose_slot_confirm,
        name="store_carrier_choose_slot_confirm",
    )
)

urlpatterns.append(
    path(
        "store_carrier_choose_slot_cancel/<path:carrier_name>/<storage_name>/",
        views.store_carrier_choose_slot_cancel,
        name="store_carrier_choose_slot_cancel",
    )
)
######### extra shelf interactions ###########
urlpatterns.append(
    path(
        "test_leds/",
        views.test_leds,
        name="test_leds",
    )
)

urlpatterns.append(
    path(
        "reset_leds/<storage_name>/",
        views.reset_leds,
        name="reset_leds",
    )
)

urlpatterns.append(
    path(
        "change_slot_color/<storage_name>/<slot_name>/<color>/",
        views.change_slot_color,
        name="change_slot_color",
    )
)


######### views ###########
urlpatterns.append(
    path(
        "assign_carrier_to_job/<path:job_name>/<path:carrier_name>/",
        views.assign_carrier_to_job,
        name="assign_carrier_to_job",
    )
)

urlpatterns.append(
    path(
        "deliver_all_carriers", views.deliver_all_carriers, name="deliver_all_carriers"
    )
)

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
