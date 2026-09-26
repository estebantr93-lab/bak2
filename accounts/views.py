from django.contrib.auth.views import LoginView

from .forms import LoginForm


class IngresoView(LoginView):
    template_name = 'registration/login.html'
    authentication_form = LoginForm
