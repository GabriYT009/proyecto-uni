from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Case, When, IntegerField
from .models import Producto, Categoria,Marca_producto

ALLOWED_CATEGORY_NAMES = [
    'Cajas',
    'Toppers',
    'Sublimación',
    'Impresión',
    'Personalización',
    'Papelería',
    'Camisas',
    'Tazas',
]

class ProductForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for category_name in ALLOWED_CATEGORY_NAMES:
            Categoria.objects.get_or_create(
                nombre_categoria=category_name,
                defaults={'descripcion_categoria': f'Categoria {category_name}'},
            )

        order_case = Case(
            *[When(nombre_categoria=name, then=pos) for pos, name in enumerate(ALLOWED_CATEGORY_NAMES)],
            output_field=IntegerField(),
        )
        # Mostrar categorias con nombre valido y ordenadas alfabeticamente.
        categorias = list(
            Categoria.objects
            .filter(nombre_categoria__isnull=False)
            .exclude(nombre_categoria='')
            .exclude(nombre_categoria__startswith='-')
            .filter(nombre_categoria__in=ALLOWED_CATEGORY_NAMES)
            .order_by(order_case, 'nombre_categoria')
        )
        # Agregar opción 'Otros' al final
        self.fields['categoria'].choices = [
            (cat.pk, cat.nombre_categoria) for cat in categorias
        ] + [('otros', 'Otros')]

        self.fields['marca_producto'] = forms.ModelChoiceField(
            queryset=Marca_producto.objects.all(),
            empty_label="Selecciona una marca",
            required=False, # Ponlo en True si es obligatorio
            widget=forms.Select(attrs={'class': 'form-control'})
        )

    
        
    
    class Meta:
        model = Producto  # Modelo actualizado
    
        fields = ['codigo_producto', 'nombre_producto','marca_producto', 'precio_venta', 'imagen_producto', 'descripcion', 'categoria', 'status_producto', 'cantidad_disponible']
        
        widgets = {
            'codigo_producto': forms.TextInput(attrs={
                'placeholder': 'Código del producto',
                'class': 'form-control'
            }),
            'nombre_producto': forms.TextInput(attrs={
                'placeholder': 'Nombre de producto', 
                'class': 'form-control'
            }),
            'marca_producto': forms.Select(attrs={
                'placeholder': 'Marca', 
                'class': 'form-control'
            }),

            'precio_venta': forms.NumberInput(attrs={
                'step': '0.01', 
                'placeholder': 'Precio', 
                'class': 'form-control'
            }),

            'descripcion': forms.TextInput(attrs={
                'placeholder': 'Descripción (Máx 45 caracteres)', 
                'class': 'form-control'
            }),
            'imagen_producto': forms.ClearableFileInput(attrs={
                'placeholder': 'Imagen', 
                'accept': 'image/*', 
                'class': 'form-control'
            }),   
            'categoria': forms.Select(attrs={
                'placeholder': 'Categoría', 
                'class': 'form-control'
            }),
            'status_producto': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'cantidad_disponible': forms.NumberInput(attrs={
                'placeholder': 'Cantidad inicial', 
                'class': 'form-control',
                'min': '0'
            }),
        }

    # Validación (antes clean_title)
    def clean_nombre_producto(self):
        nombre = self.cleaned_data.get('nombre_producto')

        # Verificamos si existe usando el nuevo nombre de campo
        if Producto.objects.filter(nombre_producto__iexact=nombre).exists():
            raise forms.ValidationError("Ya existe un producto con este nombre.")
        return nombre

    def clean_imagen_producto(self):
        imagen = self.cleaned_data.get('imagen_producto')
        # En creacion forzamos imagen para evitar productos nuevos sin foto.
        if not self.instance.pk and not imagen:
            raise forms.ValidationError("Debes seleccionar una imagen para el producto.")
        return imagen

    def save(self, commit=True):
        # Respetar la categoria seleccionada en el formulario.
        return super().save(commit=commit)


class PasswordRecoveryForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nombre de usuario',
            'autocomplete': 'username',
        }),
    )
    email = forms.EmailField(
        widget=forms.CharField(attrs={
            'class': 'form-control',
            'placeholder': 'Correo electrónico registrado',
            'type': 'email',
            'autocomplete': 'email',
        }),
    )
    new_password = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nueva contraseña',
            'autocomplete': 'new-password',
            'minlength': '8',
        }),
    )
    new_password_confirm = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirmar nueva contraseña',
            'autocomplete': 'new-password',
            'minlength': '8',
        }),
    )
    # verification_code removed: we now use security questions flow

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('new_password')
        password_confirm = cleaned_data.get('new_password_confirm')

        if password and password_confirm and password != password_confirm:
            raise ValidationError('Las contraseñas no coinciden.')

        return cleaned_data