from django import forms
from django_recaptcha.fields import ReCaptchaField


class LoginForm(forms.Form):
    usuario = forms.CharField(max_length=100, label='Usuario')
    passwd = forms.CharField(widget=forms.PasswordInput(), label='Contraseña')
    captcha = ReCaptchaField()