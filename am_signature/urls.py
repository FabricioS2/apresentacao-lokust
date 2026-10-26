"""
URL configuration for am_signature project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from products.views import product_list
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('', product_list, name='home'),
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('products/', include('products.urls')),
    path('orders/', include('orders.urls')),


]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


# =========================================================
# Servir /media/ — setup_all.py
# Em DEBUG o Django já serve via static(). Em produção
# (gunicorn atrás de proxy sem nginx) precisamos desta rota.
# Para produção séria: use nginx ou Cloudinary.
# =========================================================
from django.views.static import serve as _media_serve
from django.urls import re_path as _media_re_path

urlpatterns += [
    _media_re_path(
        r"^media/(?P<path>.*)$",
        _media_serve,
        {"document_root": settings.MEDIA_ROOT},
    ),
]
