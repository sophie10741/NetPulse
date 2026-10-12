from django.contrib import admin
from django.urls import path
from django.views.generic import RedirectView

from monitor import views

urlpatterns = [
    path('', views.home, name='home'),
    path('admin/', admin.site.urls),
    path('favicon.ico', RedirectView.as_view(url='/static/images/favicon.ico'), name='favicon'),

    # Авторизация и регистрация
    path('login/', views.login_ajax, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('access-denied/', views.access_denied, name='access_denied'),
    path('validate_user/', views.validate_user, name='validate_user'),
    path('complete_registration/', views.complete_registration, name='complete_registration'),
    path('register/step-one/', views.register_step_one, name='register_step_one'),
    path('register/step-two/', views.register_step_two, name='register_step_two'),

    # Устройства, сканирование, топология
    path('devices/', views.device_list, name='device_list'),
    path('devices/<int:pk>/ssh/', views.ssh_command_view, name='ssh_command'),
    path('devices/<int:pk>/template/', views.execute_template_view, name='execute_template'),
    path('select-interface/<int:device_id>/<str:action>/', views.select_interface, name='select_interface'),
    path('network_topology/', views.network_topology_view, name='network_topology'),
    path('api/network_topology/', views.network_topology_data, name='network_topology_data'),
    path('scan/start/', views.start_scan, name='start_scan'),
    path('scan/progress/', views.scan_progress, name='scan_progress'),
    path('scan/status/', views.scan_status, name='scan_status'),

    # Калькуляторы
    path('calculator/', views.calculator, name='calculator'),
    path('calculators/', views.calculators, name='calculators'),
    path('calculators/subnet/', views.subnet_calculator, name='subnet_calculator'),
    path('calculators/server/', views.server_calculator, name='server_calculator'),
    path('calculators/storage/', views.storage_calculator, name='storage_calculator'),

    # Полезности
    path('useful/', views.useful, name='useful'),
    path('useful/<int:utility_id>', views.useful_detail, name='useful_detail'),

    # Заметки
    path('notes/', views.notes_list, name='notes_list'),
    path('notes/<int:pk>/', views.note_detail, name='note_detail'),
    path('notes/add/', views.add_note, name='add_note'),
    path('notes/<int:pk>/edit/', views.edit_note, name='edit_note'),
    path('notes/<int:pk>/delete/', views.delete_note, name='delete_note'),
]