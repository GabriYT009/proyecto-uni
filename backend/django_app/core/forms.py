from django import forms
from django.db.models import Case, When, IntegerField
from .models import Producto, Categoria

ALLOWED_CATEGORY_NAMES = [
    'Cajas',
    'Toppers',
    'Sublimación',
    'Impresión',
    'Personalización',
    'Papelería',
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
        self.fields['categoria'].queryset = (
            Categoria.objects
            .filter(nombre_categoria__isnull=False)
            .exclude(nombre_categoria='')
            .exclude(nombre_categoria__startswith='-')
            .filter(nombre_categoria__in=ALLOWED_CATEGORY_NAMES)
            .order_by(order_case, 'nombre_categoria')
        )
    
    class Meta:
        model = Producto  # Modelo actualizado
    
        fields = ['nombre_producto','marca_producto', 'precio_venta', 'imagen_producto', 'descripcion', 'categoria', 'status_producto', 'cantidad_disponible']
        
        widgets = {
            'nombre_producto': forms.TextInput(attrs={
                'placeholder': 'Nombre de producto', 
                'class': 'form-control'
            }),
            'marca_producto': forms.TextInput(attrs={
                'placeholder': 'Marca del producto', 
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

    def save(self, commit=True):
        # Respetar la categoria seleccionada en el formulario.
        return super().save(commit=commit)