from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views


urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(next_page='/admin'), name='login'),
    path('api/', include('smt_management_app.urls')),

]
