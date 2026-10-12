"""
URL configuration for NetworkManager project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
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


from monitor import views
from django.contrib import admin
from django.urls import path, include
from monitor.views import home, calculator, useful, useful_detail, validate_user, complete_registration
from django.urls import path
from monitor.views import calculators, subnet_calculator, server_calculator, storage_calculator
from monitor.views import network_topology_data, device_list, network_topology_view
from monitor.views import notes_list, note_detail, add_note, edit_note, delete_note
from monitor.views import register_step_one, register_step_two
from monitor.views import start_scan, scan_progress, scan_status
from monitor.views import select_interface
from monitor.views import login_ajax
from monitor.views import access_denied, user_logout
from django.views.generic import RedirectView
urlpatterns = [
    path('', views.home, name='home'),
    path('admin/', admin.site.urls),
    path('logout/', user_logout, name='logout'),
path('devices/', device_list, name='device_list'),
    path('devices/<int:pk>/ssh/', views.ssh_command_view, name='ssh_command'),
    path('devices/<int:pk>/template/', views.execute_template_view, name='execute_template'),
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('calculator/', calculator, name='calculator'),
    path('useful/', useful, name='useful'),
    path('useful/<int:utility_id>', views.useful_detail, name='useful_detail'),
    path('accounts/', include('django.contrib.auth.urls')),  # Вход/выход
    path('calculators/', calculators, name='calculators'),
    path('calculators/subnet/', subnet_calculator, name='subnet_calculator'),
    path('calculators/server/', server_calculator, name='server_calculator'),
    path('calculators/storage/', storage_calculator, name='storage_calculator'),
    path('network_topology/', network_topology_view, name='network_topology'),
    path('api/network_topology/', network_topology_data, name='network_topology_data'),
    path('notes/', notes_list, name='notes_list'),
    path('notes/<int:pk>/', note_detail, name='note_detail'),
    path('notes/add/', add_note, name='add_note'),
    path('notes/<int:pk>/edit/', edit_note, name='edit_note'),
    path('notes/<int:pk>/delete/', delete_note, name='delete_note'),
    path('register/step-one/', register_step_one, name='register_step_one'),
    path('register/step-two/', register_step_two, name='register_step_two'),
    path('scan/start/', start_scan, name='start_scan'),
    path('scan/progress/', scan_progress, name='scan_progress'),
    path('scan/status/', scan_status, name='scan_status'),
    path("select-interface/<int:device_id>/<str:action>/", views.select_interface, name="select_interface"),
    path("login/", login_ajax, name="login"),
    path("logout/", user_logout, name="logout"),
    path("access-denied/", access_denied, name="access_denied"),
    path("validate_user/", validate_user, name="validate_user"),
    path("complete_registration/", complete_registration, name="complete_registration"),
    path(r'^favicon\.ico$', RedirectView.as_view(url='/static/images/favicon.ico'), name='favicon'),

]
