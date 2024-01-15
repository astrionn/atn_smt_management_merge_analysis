from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(next_page='/admin'), name='login'),
    path('api/', include('smt_management_app.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
