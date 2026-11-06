import json
import unittest
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from PIL import Image
from streamlit.testing.v1 import AppTest
from services import (validate_chat_id, validate_image, clean_recap, send_telegram,
                      friendly_error, TelegramError, validate_study_request,
                      MAX_SESSION_TURNS, MAX_SESSION_IMAGE_BYTES)
from services import export_study_session


class ServiceTests(unittest.TestCase):
    def test_session_export_keeps_learning_but_omits_personalized_welcome(self):
        report = export_study_session([
            {'role': 'assistant', 'text': 'Hi Private Student Name!'},
            {'role': 'user', 'text': 'Explain 1/4 + 1/2', 'image': b'private-photo'},
            {'role': 'assistant', 'text': 'Use a common denominator.\nTry it yourself.'},
        ])
        self.assertNotIn('Private Student Name', report)
        self.assertNotIn('private-photo', report)
        self.assertIn('photo omitted', report)
        self.assertIn('Explain 1/4 + 1/2', report)
        self.assertIn('Use a common denominator.\nTry it yourself.', report)

    def test_recap_preserves_readable_lines(self):
        self.assertEqual(clean_recap('  Topic: fractions  \n\n  Next:   practise  '),
                         'Topic: fractions\n\nNext: practise')

    def test_session_limits_are_enforced_before_provider(self):
        with self.assertRaisesRegex(ValueError, '12 questions'):
            validate_study_request('Question', None, ['user', 'model'] * MAX_SESSION_TURNS, [])
        with self.assertRaisesRegex(ValueError, '12,000'):
            validate_study_request('x' * 12001, None, [], [])
        image = BytesIO()
        Image.new('RGB', (20, 20)).save(image, format='PNG')
        previous_image = MagicMock()
        previous_image.__len__.return_value = MAX_SESSION_IMAGE_BYTES
        with self.assertRaisesRegex(ValueError, '15 MB'):
            validate_study_request('Question', image.getvalue(), [], [{'image': previous_image}])
        self.assertEqual(validate_study_request('Question', image.getvalue(), [], []), 'image/png')

    def test_authentication_error_is_specific_and_private(self):
        message = friendly_error(SimpleNamespace(code=401, message='private-key'))
        self.assertIn('GEMINI_API_KEY', message)
        self.assertIn('401', message)
        self.assertNotIn('private-key', message)

    def test_chat_validation(self):
        self.assertEqual(validate_chat_id(' 123456789 '), '123456789')
        self.assertEqual(validate_chat_id('-100123456789'), '-100123456789')
        for invalid in ('@student', '+15555550123', '0', 'hello'):
            with self.assertRaises(ValueError):
                validate_chat_id(invalid)

    def test_photo_validation(self):
        data = BytesIO()
        Image.new('RGB', (20, 20)).save(data, format='PNG')
        self.assertEqual(validate_image(data.getvalue()), 'image/png')
        with self.assertRaises(ValueError):
            validate_image(b'not an image')
        with self.assertRaises(ValueError):
            validate_image(b'x' * (10 * 1024 * 1024 + 1))

    def test_telegram_payload(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps({'ok': True, 'result': {'message_id': 42}}).encode()
        with patch('services.urlopen', return_value=response) as request:
            self.assertEqual(send_telegram('123456789:' + 'x' * 35, '123456789', 'Student', 'Revise fractions.'), 42)
            payload = json.loads(request.call_args.args[0].data)
            self.assertEqual(payload['chat_id'], '123456789')
            self.assertIn('Revise fractions.', payload['text'])
            self.assertNotIn('parse_mode', payload)
        self.assertEqual(len(clean_recap('x' * 2000)), 1500)
        with self.assertRaises(ValueError):
            clean_recap(' ')

    def test_telegram_error_does_not_expose_token(self):
        self.assertIn('bot token', friendly_error(TelegramError(401), service='Telegram'))
        self.assertIn('/start', friendly_error(TelegramError(400), service='Telegram'))



class AppTests(unittest.TestCase):
    def setUp(self):
        import streamlit as st
        st.cache_resource.clear()
        self.factory_patch = patch('google.genai.Client')
        self.factory = self.factory_patch.start()
        self.client = self.factory.return_value
        self.client.models.generate_content.return_value = SimpleNamespace(text='A force equals mass times acceleration.')
        self.at = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=20)
        self.at.secrets['GEMINI_API_KEY'] = 'test-key'
        self.at.secrets['TELEGRAM_BOT_TOKEN'] = ''

    def tearDown(self):
        self.factory_patch.stop()

    def onboard(self):
        self.at.run()
        self.at.text_input[0].set_value('Student')
        self.at.text_input[1].set_value('123456789')
        self.at.checkbox[0].check()
        self.at.button(key='onboard_submit').click().run()
        self.assertFalse(self.at.exception)

    def test_onboarding_and_reset(self):
        self.at.run()
        self.at.button(key='onboard_submit').click().run()
        self.assertTrue(self.at.warning)
        self.onboard()
        self.assertTrue(self.at.session_state.onboarded)
        self.assertTrue(self.at.button(key='recap').disabled)
        self.at.button(key='reset').click().run()
        self.assertFalse(self.at.exception)
        self.assertEqual(len(self.at.text_input), 2)

    def test_text_photo_memory_recap_and_send(self):
        self.onboard()
        self.at.chat_input[0].set_value('Explain Newton second law').run()
        self.assertFalse(self.at.exception)
        self.assertEqual(len(self.at.session_state.history), 2)
        data = BytesIO()
        Image.new('RGB', (20, 20)).save(data, format='PNG')
        self.at.session_state.pending = {'text': 'Explain this diagram', 'image': data.getvalue(),
                                         'mime_type': 'image/png', 'mode': 'Explain step by step'}
        self.at.run()
        self.assertFalse(self.at.exception)
        call = self.client.models.generate_content.call_args.kwargs
        self.assertEqual(len(call['contents']), 3)
        self.assertEqual(call['contents'][-1].parts[0].inline_data.mime_type, 'image/png')
        self.assertEqual(len(self.at.session_state.history), 4)
        self.client.models.generate_content.return_value = SimpleNamespace(text='Revise F = ma. Practise one force calculation.')
        self.at.button(key='recap').click().run()
        self.assertFalse(self.at.exception)
        self.assertEqual(len(self.at.session_state.history), 4)
        self.assertTrue(self.at.session_state.summary)
        self.assertTrue(self.at.button(key='send').disabled)
        self.at.secrets['TELEGRAM_BOT_TOKEN'] = '123456789:' + 'x' * 35
        self.at.run()
        with patch('services.telegram_request', return_value={'message_id': 42}) as request:
            self.at.button(key='send').click().run()
            self.assertFalse(self.at.exception)
            self.assertTrue(self.at.success)
            self.assertEqual(request.call_count, 1)
            self.assertIn('Revise F = ma', request.call_args.args[2]['text'])
        self.at.run()
        self.assertTrue(self.at.button(key='send').disabled)

    def test_failure_does_not_corrupt_history(self):
        self.onboard()
        self.client.models.generate_content.side_effect = RuntimeError('secret-data')
        self.at.chat_input[0].set_value('Explain a fraction').run()
        self.assertFalse(self.at.exception)
        self.assertTrue(self.at.error)
        self.assertNotIn('secret-data', self.at.error[0].value)
        self.assertEqual(len(self.at.session_state.history), 0)
        self.assertIsNotNone(self.at.session_state.pending)
        calls_after_error = self.client.models.generate_content.call_count
        self.at.selectbox[0].select('Give me a hint').run()
        self.assertEqual(self.client.models.generate_content.call_count, calls_after_error)
        self.client.models.generate_content.side_effect = None
        self.at.button(key='retry').click().run()
        self.assertFalse(self.at.exception)
        self.assertEqual(len(self.at.session_state.history), 2)

    def test_study_without_telegram_and_add_destination_later(self):
        self.at.run()
        self.at.text_input[0].set_value('Student')
        self.at.checkbox[0].check()
        self.at.button(key='onboard_submit').click().run()
        self.assertFalse(self.at.exception)
        self.assertTrue(self.at.session_state.onboarded)
        self.assertEqual(self.at.session_state.telegram_chat_id, '')
        self.at.chat_input[0].set_value('Explain fractions').run()
        calls = self.client.models.generate_content.call_count
        self.assertEqual(self.at.get('download_button')[0].label, 'Download study session')
        self.at.run()
        self.assertEqual(self.client.models.generate_content.call_count, calls)
        self.at.button(key='recap').click().run()
        self.assertTrue(self.at.session_state.summary)
        self.assertTrue(self.at.button(key='send').disabled)
        self.at.secrets['TELEGRAM_BOT_TOKEN'] = '123456789:' + 'x' * 35
        self.at.text_input(key='delivery_chat_id').set_value('123456789').run()
        self.assertFalse(self.at.button(key='send').disabled)
        self.at.text_input(key='delivery_chat_id').set_value('@wrong').run()
        self.assertTrue(self.at.button(key='send').disabled)
        self.assertFalse(self.at.exception)

    def test_session_limit_keeps_recap_available(self):
        self.onboard()
        self.at.session_state.history = ['user', 'model'] * MAX_SESSION_TURNS
        self.at.run()
        self.assertTrue(self.at.chat_input[0].disabled)
        self.assertFalse(self.at.button(key='recap').disabled)
        calls = self.client.models.generate_content.call_count
        self.at.session_state.pending = {'text': 'Extra question', 'image': None,
                                         'mime_type': None, 'mode': 'Quiz me', 'attempt': True}
        self.at.run()
        self.assertFalse(self.at.exception)
        self.assertEqual(self.client.models.generate_content.call_count, calls)

    def test_mode_switch_recap_does_not_call_model_and_send_failure_is_retryable(self):
        self.onboard()
        self.at.chat_input[0].set_value('Explain fractions').run()
        calls = self.client.models.generate_content.call_count
        self.at.selectbox[0].select('Quiz me').run()
        self.assertEqual(self.client.models.generate_content.call_count, calls)
        self.at.chat_input[0].set_value('Ask one practice question').run()
        request = self.client.models.generate_content.call_args.kwargs
        self.assertIn('Learning mode: Quiz me', request['contents'][-1].parts[-1].text)
        self.assertEqual(request['config'].max_output_tokens, 2048)
        self.at.button(key='recap').click().run()
        self.at.secrets['TELEGRAM_BOT_TOKEN'] = '123456789:' + 'x' * 35
        self.at.run()
        with patch('services.telegram_request', side_effect=TelegramError('connection')) as delivery:
            self.at.button(key='send').click().run()
            self.assertTrue(self.at.error)
            self.assertEqual(self.at.session_state.sent_summary, '')
            self.at.run()
            self.assertEqual(delivery.call_count, 1)
        self.assertFalse(self.at.button(key='send').disabled)

    def test_sent_recap_is_tracked_per_destination(self):
        self.onboard()
        self.at.chat_input[0].set_value('Explain fractions').run()
        self.at.button(key='recap').click().run()
        self.at.secrets['TELEGRAM_BOT_TOKEN'] = '123456789:' + 'x' * 35
        self.at.run()
        with patch('services.telegram_request', return_value={'message_id': 42}):
            self.at.button(key='send').click().run()
        self.at.run()
        self.assertTrue(self.at.button(key='send').disabled)
        self.at.text_input(key='delivery_chat_id').set_value('987654321').run()
        self.assertFalse(self.at.button(key='send').disabled)

    def test_empty_provider_answer_can_be_discarded_without_history_change(self):
        self.onboard()
        self.client.models.generate_content.return_value = SimpleNamespace(text='')
        self.at.chat_input[0].set_value('Explain fractions').run()
        self.assertTrue(self.at.error)
        self.assertEqual(self.at.session_state.history, [])
        self.at.button(key='discard').click().run()
        self.assertIsNone(self.at.session_state.pending)
        self.assertFalse(self.at.chat_input[0].disabled)


if __name__ == '__main__':
    unittest.main()
