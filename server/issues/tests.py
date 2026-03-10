from django.test import TestCase
from unittest import mock

from . import ai_services


class GeminiAIServiceTests(TestCase):
    def setUp(self):
        # ensure service has API key so fallback logic runs
        self.service = ai_services.GeminiAIService()
        self.service.api_key = 'fake'
        self.service.model = 'models/gemini-1.5-flash'
        self.service.fallback_models = ['models/gemini-2.0-flash', 'models/gemini-pro']

    def test_generate_with_fallback_on_quota(self):
        # simulate primary model raising quota error, then fallback succeeds
        prompt = 'test prompt'

        class DummyResponse:
            def __init__(self, text):
                self.text = text

        def primary_generate(content):
            raise Exception('Quota exceeded: 429')

        def fallback_generate(content):
            return DummyResponse('fallback result')

        with mock.patch('google.generativeai.GenerativeModel') as MockModel:
            # primary instance
            instance_primary = mock.MagicMock()
            instance_primary.generate_content.side_effect = primary_generate
            # fallback instance
            instance_fallback = mock.MagicMock()
            instance_fallback.generate_content.side_effect = fallback_generate

            # configure return values for successive calls
            MockModel.side_effect = [instance_primary, instance_fallback]

            result = self.service._generate_with_fallback(prompt)
            self.assertIn('fallback result', result)
            self.assertIn('AI quota exceeded on the primary model', result)

    def test_generate_no_quota_uses_primary(self):
        prompt = 'hello'
        class DummyResponse:
            def __init__(self, text):
                self.text = text
        with mock.patch('google.generativeai.GenerativeModel') as MockModel:
            inst = mock.MagicMock()
            inst.generate_content.return_value = DummyResponse('primary result')
            MockModel.return_value = inst
            result = self.service._generate_with_fallback(prompt)
            self.assertEqual(result, 'primary result')

    def test_tries_multiple_fallbacks_on_quota(self):
        # primary quota, first fallback quota, second fallback succeeds
        prompt = 'another prompt'
        class DummyResponse:
            def __init__(self, text):
                self.text = text

        def primary_quota(content):
            raise Exception('Quota exceeded: 429')

        def fallback1_quota(content):
            raise Exception('Quota exceeded: 429')

        def fallback2_succeed(content):
            return DummyResponse('third time lucky')

        with mock.patch('google.generativeai.GenerativeModel') as MockModel:
            # order: primary, fallback1, fallback2
            instances = [mock.MagicMock() for _ in range(3)]
            instances[0].generate_content.side_effect = primary_quota
            instances[1].generate_content.side_effect = fallback1_quota
            instances[2].generate_content.side_effect = fallback2_succeed
            MockModel.side_effect = instances

            result = self.service._generate_with_fallback(prompt)
            self.assertIn('third time lucky', result)
            # should report which fallback was used
            self.assertIn('models/gemini-pro', result)
