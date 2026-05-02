from unittest.mock import Mock, patch

from django.test import TestCase


class MailtrapChecksTests(TestCase):
	@patch('django_app.core.mailtrap_checks.requests.post')
	def test_mailtrap_check_warns_on_unauthorized_token(self, mock_post):
		mock_response = Mock(status_code=401)
		mock_post.return_value = mock_response

		from django_app.core.mailtrap_checks import check_mailtrap_configuration

		with patch.dict('os.environ', {'RUN_MAIN': 'true', 'MAILTRAP_API_TOKEN': 'realistic-test-token'}):
			warnings = check_mailtrap_configuration(app_configs=None)

		self.assertEqual(len(warnings), 1)
		self.assertEqual(warnings[0].id, 'mailtrap.W003')

	@patch('django_app.core.mailtrap_checks.requests.post')
	def test_mailtrap_check_is_clean_when_request_succeeds(self, mock_post):
		mock_response = Mock(status_code=200)
		mock_post.return_value = mock_response

		from django_app.core.mailtrap_checks import check_mailtrap_configuration

		with patch.dict('os.environ', {'RUN_MAIN': 'true', 'MAILTRAP_API_TOKEN': 'realistic-test-token'}):
			warnings = check_mailtrap_configuration(app_configs=None)

		self.assertEqual(warnings, [])
