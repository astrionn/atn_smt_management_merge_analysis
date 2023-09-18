from django.urls import path
from . import views
from rest_framework.routers import DefaultRouter

router = DefaultRouter()

router.register(r'article', views.ArticleViewSet,'article')
router.register(r'board', views.BoardViewSet,'board')
router.register(r'boardarticle', views.BoardArticleViewSet,'boardarticle')
router.register(r'carrier', views.CarrierViewSet,'carrier')
router.register(r'job', views.JobViewSet,'job')
router.register(r'machine', views.MachineViewSet,'machine')
router.register(r'machineslot', views.MachineSlotViewSet,'machineslot')
router.register(r'manufacturer', views.ManufacturerViewSet,'manufacturer')
router.register(r'provider', views.ProviderViewSet,'provider')
router.register(r'storage', views.StorageViewSet,'storage')
router.register(r'storageslot', views.StorageSlotViewSet,'storageslot')

name = "smt_management_app"

urlpatterns = router.urls
urlpatterns.append(path("save_file_and_get_headers/",views.save_file_and_get_headers, name='save_file_and_get_headers'))
urlpatterns.append(path("user_mapping_and_file_processing/",views.user_mapping_and_file_processing, name='user_mapping_and_file_processing'))
urlpatterns.append(path("get_storage_content/<storage>/",views.ListStoragesAPI.as_view(),name='get_storage_content'))
urlpatterns.append(path("collect_carrier/<carrier>/",views.collect_carrier,name='collect_carrier'))
urlpatterns.append(path("collect_carrier_confirm/<carrier>/<slot>/",views.collect_carrier_confirm,name='collect_carrier_confirm'))
urlpatterns.append(path("store_carrier/<carrier>/<storage>/",views.store_carrier,name='store_carrier'))
urlpatterns.append(path("store_carrier_confirm/<carrier>/<storage>/",views.store_carrier_confirm,name='store_carrier_confirm'))