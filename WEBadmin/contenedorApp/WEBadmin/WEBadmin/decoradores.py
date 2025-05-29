from django.shortcuts import redirect
from django.utils import timezone
from datetime import timedelta

def verificar_login(vista):
    def interna(request, *args, **kargs):
        if not request.session.get('logueado', False):
            return redirect('/login')
        return vista(request, *args, **kargs)
    return interna
    
def verificar_login_otp(vista):
    def interna(request, *args, **kargs):
        if not request.session.get('logueado_otp', False):
            return redirect('/loginotp')
        return vista(request, *args, **kargs)
    return interna