from django.contrib import admin
from .models import Cliente, SecurityQuestion, UserSecurityAnswer


@admin.register(SecurityQuestion)
class SecurityQuestionAdmin(admin.ModelAdmin):
	list_display = ('id', 'text')


@admin.register(UserSecurityAnswer)
class UserSecurityAnswerAdmin(admin.ModelAdmin):
	list_display = ('id', 'user', 'question')
	readonly_fields = ('answer_hash',)

# Register existing models
admin.site.register(Cliente)
