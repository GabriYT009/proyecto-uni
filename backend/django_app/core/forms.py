from django import forms
from .models import Producto, Categoria

class ProductForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Mostrar categorias con nombre valido y ordenadas alfabeticamente.
        self.fields['categoria'].queryset = (
            Categoria.objects
            .filter(nombre_categoria__isnull=False)
            .exclude(nombre_categoria='')
            .order_by('nombre_categoria')
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