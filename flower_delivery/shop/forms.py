from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True, label="Email")
    telegram_username = forms.CharField(
        required=True,
        label="Имя в Telegram",
        help_text="Введите ваше имя пользователя в Telegram (без @).",
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'telegram_username', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        # Добавляем имя в Telegram в поле профиля пользователя
        user.profile.telegram_username = self.cleaned_data['telegram_username']
        if commit:
            user.save()
        return user
