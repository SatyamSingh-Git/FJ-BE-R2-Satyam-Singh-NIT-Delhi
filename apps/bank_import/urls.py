from django.urls import path
from . import views

app_name = 'bank_import'

urlpatterns = [
    path('', views.import_list, name='list'),
    path('upload/', views.upload_statement, name='upload'),
    path('<int:pk>/', views.import_detail, name='detail'),
    path('<int:pk>/process/', views.process_import, name='process'),
    path('<int:pk>/approve/', views.approve_transactions, name='approve'),
    path('rules/', views.categorization_rules, name='rules'),
    path('rules/create/', views.create_rule, name='create_rule'),
    path('rules/<int:pk>/delete/', views.delete_rule, name='delete_rule'),
]
