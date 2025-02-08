from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Camera, Alert


class CameraForm(forms.ModelForm):
    class Meta:
        model = Camera
        fields = ['name', 'location', 'ip_address', 'port', 'username', 'password', 'is_active']
        widgets = {
            'password': forms.PasswordInput(),
        }

class AlertFilterForm(forms.Form):
    camera = forms.ModelChoiceField(
        queryset=Camera.objects.all(),
        required=False,
        empty_label="All Cameras"
    )
    threat_type = forms.ChoiceField(
        choices=[('', 'All Types')] + Alert.THREAT_TYPES,
        required=False
    )
    date_from = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    date_to = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))




class VideoUploadForm(forms.Form):
    video = forms.FileField(
        label='Select Video',
        help_text='Upload a video file for crime detection analysis.',
        widget=forms.FileInput(attrs={
            'accept': 'video/*',
            'class': 'form-control'
        })
    )

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        max_length=254,
        required=True,
        help_text='Required. Enter a valid email address.',
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('This email address is already in use.')
        return email

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add form-control class to all fields for better styling
        for fieldname in ['username', 'email', 'password1', 'password2']:
            self.fields[fieldname].widget.attrs['class'] = 'form-control'