from django.urls import path
from . import views

app_name = 'ai_features'

urlpatterns = [
    path('insights/', views.insights_list, name='insights'),
    path('insights/generate/', views.generate_insights, name='generate_insights'),
    path('insights/<int:pk>/dismiss/', views.dismiss_insight, name='dismiss_insight'),
    path('chat/', views.chat_assistant, name='chat'),
    path('chat/send/', views.chat_send, name='chat_send'),
    path('chat/clear/', views.chat_clear, name='chat_clear'),
    path('anomalies/', views.anomaly_list, name='anomalies'),
    path('anomalies/<int:pk>/review/', views.anomaly_review, name='anomaly_review'),
    path('categorize/', views.auto_categorize, name='auto_categorize'),
]
