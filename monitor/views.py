from django.shortcuts import render, get_object_or_404, redirect
from .models import NetworkDevice, Connection, NetworkInterface
from .forms import DeviceFilterForm
from .ssh_manager import execute_ssh_command
from .command_templates import command_templates
from .command_builder import build_command, extract_parameters, PARAMETER_HINTS
from django.http import JsonResponse
from .network_scanner_1 import scan_full_network, determine_device_type
import ipaddress
import math
from .models import Category, Utility
from django.contrib.auth.decorators import login_required
from .models import Note, Comment
from .forms import NoteForm, CommentForm
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import LoginView
from django.views.generic import TemplateView
from django.contrib.auth.models import User
from .forms import StepOneForm, StepTwoForm
from django.contrib import messages
from .models import Profile
from django.core.paginator import Paginator
import threading
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import update_session_auth_hash
from django.views.decorators.csrf import csrf_exempt
import json

scan_in_progress = False
def get_topology_data(devices=None):
    nodes = []
    edges = []
    type_styles = {
        "server": {"color": "blue"},
        "router": {"color": "red"},
        "switch": {"color": "green"},
        "client": {"color": "orange"},
        "unknown": {"color": "gray"}
    }
    # Если devices не передан, берём все устройства
    if devices is None:
        devices = NetworkDevice.objects.all()

    # Добавляем устройства (узлы)
    for device in devices:
        device_type = device.device_type
        style = type_styles.get(device_type, type_styles["unknown"])
        nodes.append({
            "data": {
                "id": str(device.id),
                "label": device.name,
                "color": style["color"],
                "device_type": device.device_type
            }
        })

    # Добавляем связи (рёбра)
    for connection in Connection.objects.all():
        edges.append({
            "data": {
                "source": str(connection.source.id),
                "target": str(connection.target.id)
            }
        })

    return {"nodes": nodes, "edges": edges}

@login_required
def network_topology_data(request):
    """ Отдаёт JSON-данные для визуализации сети в Cytoscape.js. """
    topology_data = get_topology_data()
    return JsonResponse(topology_data)

@login_required
def network_topology_view(request):
    """ Представление для отображения графической топологии. """
    return render(request, 'monitor/network_topology.html')

@login_required
def home(request):
    devices = NetworkDevice.objects.prefetch_related("networkinterface_set")
    form = DeviceFilterForm(request.GET)

    if form.is_valid():
        name = form.cleaned_data.get('name')
        device_type = form.cleaned_data.get('device_type')
        status = form.cleaned_data.get('status')

        if name:
            devices = devices.filter(name__icontains=name)
        if device_type:
            devices = devices.filter(device_type=device_type)
        if status:
            devices = devices.filter(status=status)

    has_devices = NetworkDevice.objects.exists()
    context = {
        "devices": devices,
        "has_devices": has_devices,
        "form": form,
        # Схема всегда строится по всем устройствам, фильтр действует только на таблицу
        "topology_data": get_topology_data() if has_devices else None,
    }
    return render(request, 'monitor/home.html', context)

@login_required
def select_interface(request, device_id, action):
    # Получаем устройство по ID
    device = get_object_or_404(NetworkDevice, id=device_id)

    # Получаем все интерфейсы этого устройства
    interfaces = device.networkinterface_set.all()

    # Если форма отправлена, обрабатываем данные
    if request.method == "POST":
        selected_interface = request.POST.get('interface')
        # Делаем что-то с выбранным интерфейсом, например, переадресовываем на страницу с настройкой шаблона
        return redirect(f'/devices/{device.id}/template/?template={action}&interface={selected_interface}')

    return render(request, 'monitor/select_interface.html', {
        'device': device,
        'interfaces': interfaces,
        'action': action
    })

@login_required
def device_list(request):
    devices = NetworkDevice.objects.all()
    form = DeviceFilterForm(request.GET)

    if form.is_valid():
        name = form.cleaned_data.get('name')
        device_type = form.cleaned_data.get('device_type')
        status = form.cleaned_data.get('status')

        if name:
            devices = devices.filter(name__icontains=name)
        if device_type:
            devices = devices.filter(device_type=device_type)
        if status:
            devices = devices.filter(status=status)  # Теперь фильтруем по полю

    return render(request, 'monitor/device_list.html', {'devices': devices, 'form': form})

@login_required
def ssh_command_view(request, pk):
    device = NetworkDevice.objects.get(pk=pk)
    result = None

    if request.method == "POST":
        command = request.POST.get("command")
        if command:
            result = execute_ssh_command(
                host=device.ip_address,
                username=device.ssh_username,
                command=command,
            )
    return render(request, "monitor/ssh_command.html", {
        "device": device,
        "result": result
    })


@login_required
def execute_template_view(request, pk):
    """Выполнение команды по шаблону с проверкой параметров."""
    device = get_object_or_404(NetworkDevice, pk=pk)
    result = None
    errors = {}
    template_name = request.GET.get("template", None)
    template = command_templates.get(template_name, None)
    parameters = extract_parameters(template["command"]) if template else []

    if request.method == "POST" and template:
        command, errors = build_command(template["command"], request.POST)
        if command:
            result = execute_ssh_command(
                host=device.ip_address,
                username=device.ssh_username,
                command=command,
            )

    fields = [
        {
            "name": name,
            "hint": PARAMETER_HINTS.get(name, ""),
            "type": "password" if name == "password" else "text",
            # пароль обратно в форму не подставляем
            "value": "" if name == "password" else request.POST.get(name, ""),
        }
        for name in parameters
    ]
    return render(request, "monitor/execute_template.html", {
        "device": device,
        "template_name": template_name,
        "template": template,
        "parameters": parameters,
        "fields": fields,
        "errors": errors,
        "result": result,
    })

def parse_keywords(value):
    """' srv, sw ,' -> ['srv', 'sw']"""
    return [word.strip() for word in value.split(",") if word.strip()]


@login_required
def start_scan(request):
    """Запуск сканирования и переход на страницу прогресса."""
    global scan_in_progress

    if request.method == "POST":
        start_ip = request.POST.get("start_ip", "").strip()
        server_type = parse_keywords(request.POST.get("server_type", ""))
        router_type = parse_keywords(request.POST.get("router_type", ""))
        switch_type = parse_keywords(request.POST.get("switch_type", ""))
        client_type = parse_keywords(request.POST.get("client_type", ""))

        if not all([start_ip, server_type, router_type, switch_type, client_type]):
            messages.error(request, "Заполните все поля: IP-адрес и ключевые слова для каждого типа устройств.")
            return redirect("home")

        try:
            ipaddress.ip_address(start_ip)
        except ValueError:
            messages.error(request, f"Некорректный IP-адрес: {start_ip}")
            return redirect("home")

        # Запуск сканирования в отдельном потоке
        if not scan_in_progress:
            scan_in_progress = True

            def scan():
                global scan_in_progress
                try:
                    scan_full_network(start_ip, server_type, router_type, switch_type, client_type)
                finally:
                    scan_in_progress = False

            threading.Thread(target=scan).start()
            return redirect("scan_progress")

    return redirect("home")

@login_required
def scan_progress(request):
    """Показывает страницу прогресса сканирования."""
    return render(request, "monitor/scan_progress.html")

@login_required
def scan_status(request):
    """Проверяет состояние сканирования."""
    global scan_in_progress
    return JsonResponse({"scan_in_progress": scan_in_progress})

@login_required
def calculator(request):
    return render(request, 'calculator.html')

@login_required
def useful(request):
    category_id = request.GET.get('category')  # Получаем ID категории из запроса
    categories = Category.objects.all()

    if category_id:
        utilities = Utility.objects.filter(category_id=category_id)
    else:
        utilities = Utility.objects.all()

    paginator = Paginator(utilities, 5)  # 5 полезностей на странице
    page_number = request.GET.get('page')
    utilities_list = paginator.get_page(page_number)

    return render(request, 'monitor/useful/useful.html', {
        'categories': categories,
        'utilities': utilities_list,
        'selected_category': int(category_id) if category_id else None,
    })

@login_required
def useful_detail(request, utility_id):
    utility = Utility.objects.get(id=utility_id)
    return render(request, 'monitor/useful/useful_detail.html', {'utility': utility})

@login_required
def calculators(request):
    return render(request, 'monitor/calculators.html')

@login_required
def subnet_calculator(request):
    result = None

    if request.method == "POST":
        ip_input = request.POST.get("ip")
        try:
            network = ipaddress.ip_network(ip_input, strict=False)
            result = {
                "network_address": str(network.network_address),
                "broadcast_address": str(network.broadcast_address),
                "netmask": str(network.netmask),
                "num_hosts": network.num_addresses - 2,  # Вычитаем сеть и broadcast
                "ip_range": f"{network.network_address + 1} - {network.broadcast_address - 1}"
            }
        except ValueError:
            result = {"error": "Неверный IP-адрес или маска!"}

    return render(request, "monitor/calculators/subnet_calculator.html", {"result": result})

@login_required
def server_calculator(request):
    result = None

    if request.method == "POST":
        try:
            users = int(request.POST.get("users"))
            cpu_per_user = float(request.POST.get("cpu_per_user"))
            ram_per_user = float(request.POST.get("ram_per_user"))
            server_cpu = float(request.POST.get("server_cpu"))
            server_ram = float(request.POST.get("server_ram"))

            # Расчет минимального числа серверов
            total_cpu_needed = users * cpu_per_user
            total_ram_needed = users * ram_per_user

            servers_by_cpu = math.ceil(total_cpu_needed / server_cpu)
            servers_by_ram = math.ceil(total_ram_needed / server_ram)

            total_servers = max(servers_by_cpu, servers_by_ram)  # Берем большее из двух значений

            result = {
                "servers_by_cpu": servers_by_cpu,
                "servers_by_ram": servers_by_ram,
                "total_servers": total_servers
            }
        except (ValueError, TypeError):
            result = {"error": "Ошибка ввода данных!"}

    return render(request, "monitor/calculators/server_calculator.html", {"result": result})

@login_required
def storage_calculator(request):
    result = None
    if request.method == 'POST':
        try:
            # Получаем данные с формы
            users = int(request.POST['users'])
            ram_per_user = float(request.POST['ram_per_user'])
            disk_per_user = float(request.POST['disk_per_user'])

            # Рассчитываем требуемые ресурсы
            total_ram = users * ram_per_user
            total_disk = users * disk_per_user

            result = {
                'total_ram': total_ram,
                'total_disk': total_disk,
            }
        except ValueError:
            result = {'error': 'Пожалуйста, введите корректные данные.'}
    return render(request, 'monitor/calculators/storage_calculator.html', {"result": result})





@login_required
def notes_list(request):
    notes = Note.objects.all().order_by('-created_at')
    paginator = Paginator(notes, 5)  # 5 заметок на странице

    page_number = request.GET.get('page')
    notes_p = paginator.get_page(page_number)
    return render(request, 'monitor/notes/notes_list.html', {'notes': notes_p})


@login_required
def note_detail(request, pk):
    note = get_object_or_404(Note, pk=pk)
    comments = note.comments.all().order_by('created_at')
    comment_form = CommentForm()

    if request.method == "POST":
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.note = note
            comment.author = request.user
            comment.save()
            return redirect('note_detail', pk=pk)

    return render(request, 'monitor/notes/note_detail.html',
                  {'note': note, 'comments': comments, 'comment_form': comment_form})


@login_required
def add_note(request):
    if request.method == "POST":
        form = NoteForm(request.POST)
        if form.is_valid():
            note = form.save(commit=False)
            note.author = request.user
            note.save()
            return redirect('notes_list')
    else:
        form = NoteForm()

    return render(request, 'monitor/notes/note_form.html', {'form': form})


@login_required
def edit_note(request, pk):
    note = get_object_or_404(Note, pk=pk)
    if request.user != note.author:
        return redirect('notes_list')

    if request.method == "POST":
        form = NoteForm(request.POST, instance=note)
        if form.is_valid():
            form.save()
            return redirect('note_detail', pk=pk)
    else:
        form = NoteForm(instance=note)

    return render(request, 'monitor/notes/note_form.html', {'form': form})


@login_required
def delete_note(request, pk):
    note = get_object_or_404(Note, pk=pk)
    if request.user == note.author:
        note.delete()
    return redirect('notes_list')


def register_step_one(request):
    if request.method == "POST":
        form = StepOneForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            # Проверяем, существует ли пользователь с таким именем
            user = authenticate(username=username, password=password)
            if user is not None:
                request.session['username'] = username
                return redirect('register_step_two')
            else:
                messages.error(request, 'Неверные данные для входа')

    else:
        form = StepOneForm()

    return render(request, 'monitor/register_step_one.html', {'form': form})


def register_step_two(request):
    username = request.session.get('username')
    if not username:
        return redirect('register_step_one')

    if request.method == "POST":
        form = StepTwoForm(request.POST)
        if form.is_valid():
            phone_number = form.cleaned_data['phone_number']
            email = form.cleaned_data['email']

            user = User.objects.get(username=username)
            user.email = email
            profile, created = Profile.objects.get_or_create(user=user)
            profile.phone_number = phone_number
            profile.save()
            user.save()

            login(request, user)
            messages.success(request, 'Регистрация завершена!')
            return redirect('notes_list')  # Или на другую страницу

    else:
        form = StepTwoForm()

    return render(request, 'monitor/register_step_two.html', {'form': form})

# Защищённая страница (если не вошел, то редирект на "Доступ запрещен")
class SomeView(LoginRequiredMixin, TemplateView):
    template_name = "some_template.html"
    login_url = "/access-denied/"  # Редирект на страницу "Упс..."

# class CustomLoginView(LoginView):
#     def form_invalid(self, form):
#         return JsonResponse({"success": False, "errors": form.errors}, status=400)
#
#     def form_valid(self, form):
#         self.user = form.get_user()
#         return JsonResponse({"success": True})

# def user_login(request):
#     if request.user.is_authenticated:
#         return redirect('home')  # Если уже вошел, редирект на главную
#
#     form = AuthenticationForm()
#
#     if request.method == 'POST':
#         form = AuthenticationForm(data=request.POST)
#         if form.is_valid():
#             user = form.get_user()
#             login(request, user)
#             return redirect('home')
#
#     return render(request, 'monitor/login.html', {'form': form})

def login_ajax(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return JsonResponse({"success": True})
        else:
            return JsonResponse({"success": False, "error": "Неверные данные"})

    return redirect("access_denied")  # Если кто-то просто откроет /login/

def access_denied(request):
    return render(request, "monitor/access_denied.html")


def user_logout(request):
    logout(request)
    return redirect("access_denied")  # После выхода отправляем на страницу входа


def validate_user(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(username=username, password=password)

        if user:
            request.session['username'] = username
            return JsonResponse({"success": True})
        return JsonResponse({"success": False, "error": "Неверный логин или пароль"})

    return JsonResponse({"success": False, "error": "Неверный запрос"})

def complete_registration(request):
    username = request.session.get('username')
    if request.method == "POST":
        # username = request.POST.get("username")
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        if new_password != confirm_password:
            return JsonResponse({"success": False, "error": "Пароли не совпадают"})

        try:
            user = User.objects.get(username=username)
            user.set_password(new_password)
            user.email = email
            user.profile.phone_number = phone
            user.save()

            update_session_auth_hash(request, user)

            return JsonResponse({"success": True})
        except User.DoesNotExist:
            return JsonResponse({"success": False, "error": "Пользователь не найден"})

    return JsonResponse({"success": False, "error": "Неверный запрос"})