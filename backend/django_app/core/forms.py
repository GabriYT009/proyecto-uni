from django import forms
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

        marca_producto = forms.ModelChoiceField(
        queryset=Marca_producto.objects.all(),
        empty_label="Selecciona una marca",
        widget=forms.Select(attrs={'class': 'form-control'}) # Opcional: para clases CSS
    )
        
    
    class Meta:
        model = Producto  # Modelo actualizado
    
        fields = ['nombre_producto','marca_producto', 'precio_venta', 'imagen_producto', 'descripcion', 'categoria', 'status_producto', 'cantidad_disponible']
        
        widgets = {
            'nombre_producto': forms.TextInput(attrs={
                'placeholder': 'Nombre de producto', 
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