from django.urls import path
from . import views

app_name = 'budgets'

urlpatterns = [
    path('', views.budget_list, name='list'),
    path('create/', views.budget_create, name='create'),
    path('<int:pk>/', views.budget_detail, name='detail'),
    path('<int:pk>/update/', views.budget_update, name='update'),
    path('<int:pk>/delete/', views.budget_delete, name='delete'),
]
