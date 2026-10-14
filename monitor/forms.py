from django import forms
from .models import Note, Comment
from django.contrib.auth.models import User


class DeviceFilterForm(forms.Form):
    name = forms.CharField(required=False, label="Имя")
    device_type = forms.ChoiceField(
        required=False,
        label="Тип",
        choices=[
            ("", "Все"),
            ("router", "Маршрутизатор"),
            ("server", "Сервер"),
            ("switch", "Коммутатор"),
            ("client", "Клиент"),
            ("unknown", "Неизвестный"),
        ],
    )
    status = forms.ChoiceField(
        required=False,
        label="Статус",
        choices=[("", "Все"), ("online", "Online"), ("offline", "Offline")],
    )


class NoteForm(forms.ModelForm):
    class Meta:
        model = Note
        fields = ['title', 'content']
        labels = {
            'title': 'Заголовок',
            'content': 'Текст заметки',
        }


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content']
        labels = {
            'content': 'Добавить комментарий',
        }


class StepOneForm(forms.Form):
    username = forms.CharField(max_length=150, label="Имя пользователя")
    password = forms.CharField(widget=forms.PasswordInput, label="Пароль")


class StepTwoForm(forms.Form):
    phone_number = forms.CharField(max_length=20, label="Номер телефона")
    email = forms.EmailField(label="Email")
