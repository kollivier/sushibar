from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as AuthUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from .models import BarUser


class MyUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = BarUser


class MyUserCreationForm(UserCreationForm):

    error_message = UserCreationForm.error_messages.update({
        'duplicate_username': 'This username has already been taken.'
    })

    class Meta(UserCreationForm.Meta):
        model = BarUser

    def clean_username(self):
        username = self.cleaned_data["username"]
        try:
            BarUser.objects.get(username=username)
        except BarUser.DoesNotExist:
            return username
        raise forms.ValidationError(self.error_messages['duplicate_username'])


@admin.register(BarUser)
class MyUserAdmin(AuthUserAdmin):
    form = MyUserChangeForm
    add_form = MyUserCreationForm
    fieldsets = (
            ('User Profile', {'fields': ('name',)}),
    ) + AuthUserAdmin.fieldsets
    list_display = ('username', 'name', 'is_superuser')
    search_fields = ['name']
