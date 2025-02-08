from django.conf.urls.static import static
from django.urls import path
from . import views
from django.conf import settings

urlpatterns = [
                  path('', views.dashboard, name='dashboard'),
                  path('cameras/', views.camera_list, name='camera_list'),
                  path('alerts/', views.alert_list, name='alert_list'),
                  path('login/', views.login_view, name='login'),  # Define login URL here
                  path('register/', views.register_view, name='register'),  # Add the register URL here
                  path('upload/', views.upload_video, name='upload_video'),
                  path('results/', views.view_results, name='view_results'),
                  path('alerts/filter/', views.filter_alerts, name='filter_alerts'),  # Filtered list
                  path('', views.video_feed, name='video_feed'),  # Changed to video_feed
                  path('video_feed/', views.video_feed, name='video_feed'),
                  path('', views.video_feedCCTV, name='video_feedCCTV'),  # Changed to video_feed
                  path('video_feedCCTV/', views.video_feedCCTV, name='video_feedCCTV'),  # Added an index path

              ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
