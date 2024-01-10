from django.contrib import admin
from django.urls import path, include, reverse
from django.contrib.auth import views as auth_views



urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(next_page='/admin'),name='login'),#requires /templates/registration/login.html for GET ; login.html needs to POST username, password, csrfmiddlewaretoken and next
    path('api/', include('smt_management_app.urls')),

]
