from django.shortcuts import redirect
from django.utils import timezone
from datetime import timedelta

def verificar_login(vista):
    def interna(request, *args, **kargs):
        if not request.session.get('logueado', False):
            return redirect('/login')
        return vista(request, *args, **kargs)
    return interna
    
