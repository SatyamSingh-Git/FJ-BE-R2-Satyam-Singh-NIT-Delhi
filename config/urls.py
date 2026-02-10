from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Authentication (allauth)
    path('accounts/', include('allauth.urls')),
    
    # App URLs
    path('', include('apps.accounts.urls')),
    path('categories/', include('apps.categories.urls')),
    path('transactions/', include('apps.transactions.urls')),
    path('budgets/', include('apps.budgets.urls')),
    path('reports/', include('apps.reports.urls')),
    path('notifications/', include('apps.notifications.urls')),
    path('ai/', include('apps.ai_features.urls')),
    path('import/', include('apps.bank_import.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
