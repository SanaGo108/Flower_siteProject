from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Profile

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, label="Email")
    telegram_username = forms.CharField(max_length=50, required=True, label="Telegram Username")

    class Meta:
        model = User
        fields = ["username", "email", "telegram_username", "password1", "password2"]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]

        if commit:
            user.save()
            # Проверяем, существует ли профиль
            profile, created = Profile.objects.get_or_create(user=user)
            if created:
                profile.telegram_username = self.cleaned_data["telegram_username"]
                profile.save()

        return user
