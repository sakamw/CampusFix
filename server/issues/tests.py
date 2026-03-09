from django.test import TestCase
from unittest import mock

from . import ai_services


class GeminiAIServiceTests(TestCase):
    def setUp(self):
        # ensure service has no API key so we can configure manually
        self.service = ai_services.GeminiAIService()
        # override api_key to avoid external calls
        self.service.api_key = 'fake'

    def test_generate_with_fallback_on_quota(self):
        # simulate primary model raising quota error first, then free model succeeding
        prompt = 'test prompt'

        class DummyResponse:
            def __init__(self, text):
                self.text = text

        def primary_generate(content):
            raise Exception('Quota exceeded: 429')

        def free_generate(content):
            return DummyResponse('free model text')

        with mock.patch('google.generativeai.GenerativeModel') as MockModel:
            # primary instance
            instance_primary = mock.MagicMock()
            instance_primary.generate_content.side_effect = primary_generate
            # free instance
            instance_free = mock.MagicMock()
            instance_free.generate_content.side_effect = free_generate

            # configure return values for successive calls
            MockModel.side_effect = [instance_primary, instance_free]

            result = self.service._generate_with_fallback(prompt)
            # primary should have failed, so free response must appear
            self.assertIn('free model text', result)
            # our helper attaches a note when fallback is used
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

    def test_secondary_fallback_when_free_model_invalid(self):
        # primary quota error, free model 404, then secondary fallback succeeds
        prompt = 'another prompt'
        class DummyResponse:
            def __init__(self, text):
                self.text = text

        def primary_generate(content):
            raise Exception('Quota exceeded: 429')

        def free_generate_fail(content):
            raise Exception('404 model not found')

        def secondary_generate(content):
            return DummyResponse('secondary success')

        with mock.patch('google.generativeai.GenerativeModel') as MockModel:
            # order: primary, free, secondary
            primary_inst = mock.MagicMock()
            primary_inst.generate_content.side_effect = primary_generate
            free_inst = mock.MagicMock()
            free_inst.generate_content.side_effect = free_generate_fail
            secondary_inst = mock.MagicMock()
            secondary_inst.generate_content.side_effect = secondary_generate
            MockModel.side_effect = [primary_inst, free_inst, secondary_inst]

            # temporarily set free_model to something invalid
            self.service.free_model = 'models/text-bison-001'

            result = self.service._generate_with_fallback(prompt)
            self.assertIn('secondary success', result)
            self.assertIn("configured free model 'models/text-bison-001'", result)
