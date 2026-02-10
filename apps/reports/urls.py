from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.reports_home, name='home'),
    path('monthly/', views.monthly_report, name='monthly'),
    path('category/', views.category_report, name='category'),
    path('chart-data/', views.chart_data, name='chart_data'),
    path('export/csv/', views.export_csv, name='export_csv'),
    path('export/pdf/', views.export_pdf, name='export_pdf'),
]
