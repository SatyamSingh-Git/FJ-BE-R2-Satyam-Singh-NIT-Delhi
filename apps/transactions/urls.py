from django.urls import path
from . import views

app_name = 'transactions'

urlpatterns = [
    path('', views.transaction_list, name='list'),
    path('create/', views.transaction_create, name='create'),
    path('<int:pk>/', views.transaction_detail, name='detail'),
    path('<int:pk>/update/', views.transaction_update, name='update'),
    path('<int:pk>/delete/', views.transaction_delete, name='delete'),
    
    # API endpoints for dashboard charts
    path('api/summary/', views.api_summary, name='api_summary'),
    path('api/monthly-trend/', views.api_monthly_trend, name='api_monthly_trend'),
]
