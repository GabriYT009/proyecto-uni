from django import forms
from .models import Producto, Categoria

class ProductForm(forms.ModelForm):
    
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
        instance = super().save(commit=False)
        

        # cambié 'nombre_producto' en lugar de 'title'
        nombre_lower = (instance.nombre_producto or "").lower()
        
        nombre_cat_asignar = 'Electrónica' # Valor por defecto

        if any(word in nombre_lower for word in ['teclado', 'audífonos', 'computadora', 'celular', 'tablet', 'mouse', 'monitor', 'impresora', 'router', 'cámara', 'drone', 'consola', 'juego']):
            nombre_cat_asignar = 'Electrónica'
        elif any(word in nombre_lower for word in ['camisa', 'pantalón', 'zapatos', 'sombrero', 'bolso', 'ropa', 'vestido', 'chaqueta']):
            nombre_cat_asignar = 'Ropa'
        elif any(word in nombre_lower for word in ['mesa', 'silla', 'sofá', 'cama', 'cocina', 'baño', 'hogar', 'decoración']):
            nombre_cat_asignar = 'Hogar'
        

        # Usamos get_or_create solo con el nombre.
        categoria_obj, created = Categoria.objects.get_or_create(
            nombre_categoria=nombre_cat_asignar,
            defaults={'descripcion_categoria': 'Categoría asignada automáticamente'}
        )
        
        instance.categoria = categoria_obj

        if commit:
            instance.save()
        return instance