from django.contrib import admin
from .models import Cliente, SecurityQuestion, UserSecurityAnswer, ProductoTallaStock


@admin.register(SecurityQuestion)
class SecurityQuestionAdmin(admin.ModelAdmin):
	list_display = ('id', 'text')


@admin.register(UserSecurityAnswer)
class UserSecurityAnswerAdmin(admin.ModelAdmin):
	list_display = ('id', 'user', 'question')
	readonly_fields = ('answer_hash',)


@admin.register(ProductoTallaStock)
class ProductoTallaStockAdmin(admin.ModelAdmin):
	list_display = ('id', 'producto', 'talla', 'stock_disponible')
	list_filter = ('talla',)
	search_fields = ('producto__nombre_producto', 'talla')

# Register existing models
admin.site.register(Cliente)
