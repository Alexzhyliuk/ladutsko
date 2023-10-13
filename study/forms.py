from django import forms
from accounts.forms import ProfileEditForm
from .models import Group
from django.contrib.auth.models import User


class AdminProfileEditForm(ProfileEditForm):

    def __init__(self, *args, **kwargs):
        super(ProfileEditForm, self).__init__(*args, **kwargs)

        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form__input'

        self.fields['group'] = forms.ModelChoiceField(
            queryset=Group.objects.all(),
            label='Группа',
        )
        self.fields['group'].required = False


class GroupForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ("name", )
        labels = {"name": "Название"}

    def __init__(self, *args, **kwargs):
        super(GroupForm, self).__init__(*args, **kwargs)

        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form__input'

        self.fields['owner'] = forms.ModelChoiceField(
            queryset=User.objects.filter(profile__type=2).all(),
            label='Владелец',
        )
        self.fields['owner'].required = False
