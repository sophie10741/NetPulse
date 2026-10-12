from django.urls import include, path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
	path('devices/<int:pk>/ssh/', views.ssh_command_view, name='ssh_command'),

]
