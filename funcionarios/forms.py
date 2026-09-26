from django import forms


class SolicitarCodigoForm(forms.Form):
    email = forms.EmailField(label='Correo electrónico', widget=forms.EmailInput(attrs={'autocomplete': 'email'}))


class ValidarCodigoForm(forms.Form):
    codigo = forms.RegexField(
        label='Código de 6 dígitos', regex=r'^\d{6}$', max_length=6,
        error_messages={'invalid': 'El código debe tener 6 dígitos.'},
        widget=forms.TextInput(attrs={'inputmode': 'numeric', 'autocomplete': 'one-time-code'}),
    )
