from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path , include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('customer/', include('customer_dashboard.urls')),
    path('solar/', include('solardashboard.urls')),
    path('account/', include('accounts.urls')),
    path('core/',include('core.urls')),
    path('open_access/',include('open_access.urls')),
]

# Only add this in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])