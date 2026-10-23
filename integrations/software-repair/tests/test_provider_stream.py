import asyncio
import importlib.util
import json
from pathlib import Path
import sys
import urllib.error

import httpx
import pytest

spec = importlib.util.spec_from_file_location('stream_fixture', Path(__file__).parents[3] / 'scripts/provider_stream.py')
stream = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stream)


def event(**updates):
    value = {'id': 'offline-fixture-id', 'choices': [{'index': 0, 'delta': {'content': '{"op":"read"}'}, 'finish_reason': None}]}
    value.update(updates)
    return b'data: ' + json.dumps(value).encode() + b'\n\n'


def valid_bytes():
    return (event() + event(choices=[{'index': 0, 'delta': {'reasoning_content': 'test reasoning'}, 'finish_reason': 'stop'}])
            + event(choices=[], usage={'prompt_tokens': 10, 'completion_tokens': 20}) + b'data: [DONE]\n\n')


class Bytes(httpx.AsyncByteStream):
    def __init__(self, body):
        self.body, self.closed = body, False
    async def __aiter__(self):
        for index in range(0, len(self.body), 7):
            yield self.body[index:index + 7]
    async def aclose(self):
        self.closed = True


def request(body, status=200):
    channel, observed = Bytes(body), []
    def handler(req):
        observed.append(req)
        return httpx.Response(status, headers={'content-type': 'text/event-stream'}, stream=channel)
    result = asyncio.run(stream.stream_call('offline-placeholder', {'model': 'frozen-fixture'}, 1,
                                           transport=httpx.MockTransport(handler)))
    return result, channel, observed


def test_fragmented_stream_preserves_content_reasoning_identity_and_total_usage():
    result, channel, observed = request(valid_bytes())
    assert result['id'] == 'offline-fixture-id' and result['usage']['completion_tokens'] == 20
    assert result['choices'][0]['message'] == {'role': 'assistant', 'content': '{"op":"read"}', 'reasoning_content': 'test reasoning'}
    assert result['choices'][0]['finish_reason'] == 'stop' and channel.closed
    assert len(observed) == 1 and str(observed[0].url) == stream.BASE + '/chat/completions'
    body = json.loads(observed[0].content)
    assert body['stream'] is True and body['stream_options'] == {'include_usage': True}


@pytest.mark.parametrize('body', [event() + b'data: [DONE]\n\n',
    valid_bytes().replace(b'offline-fixture-id', b'other-fixture-id', 1),
    valid_bytes().replace(b'data: [DONE]\n\n', b''), b'data: {bad}\n\n',
    valid_bytes().replace(b'"completion_tokens": 20', b'"completion_tokens": true'),
    valid_bytes() + event(), b'data: {"error":{"message":"private fixture"}}\n\n'])
def test_incomplete_malformed_or_ambiguous_stream_never_becomes_a_reply(body):
    with pytest.raises((ValueError, stream.StreamProtocolError)):
        request(body)


@pytest.mark.parametrize('status', [307, 401, 403, 504])
def test_http_failure_is_not_retried_redirected_or_converted_to_model_output(status):
    observed = []
    def handler(req):
        observed.append(req)
        return httpx.Response(status, headers={'location': 'https://example.invalid/'}, content=b'private error body')
    with pytest.raises(urllib.error.HTTPError) as error:
        asyncio.run(stream.stream_call('offline-placeholder', {}, 1, transport=httpx.MockTransport(handler)))
    assert error.value.code == status and len(observed) == 1
    assert 'private error body' not in str(error.value)


def test_actual_async_deadline_cancels_stalled_body_and_closes_transport():
    class Stalled(httpx.AsyncByteStream):
        closed = False
        async def __aiter__(self):
            yield event()
            await asyncio.Event().wait()
        async def aclose(self):
            self.closed = True
    channel = Stalled()
    transport = httpx.MockTransport(lambda req: httpx.Response(200, headers={'content-type': 'text/event-stream'}, stream=channel))
    with pytest.raises(TimeoutError):
        asyncio.run(stream.stream_call('offline-placeholder', {}, .02, transport=transport))
    assert channel.closed


def test_extended_wait_remains_bounded_without_changing_transport_or_usage_checks():
    channel = Bytes(valid_bytes())
    transport = httpx.MockTransport(lambda req: httpx.Response(200,
        headers={'content-type': 'text/event-stream'}, stream=channel))
    reply = asyncio.run(stream.stream_call('offline-placeholder', {}, 360, transport=transport))
    assert reply['usage']['completion_tokens'] == 20 and channel.closed
    for timeout in (0, -1, 361, float('inf'), float('nan'), True):
        with pytest.raises(ValueError, match='bounded'):
            asyncio.run(stream.stream_call('offline-placeholder', {}, timeout, transport=transport))


def test_stream_bytes_and_line_limits_remain_bounded(monkeypatch):
    monkeypatch.setattr(stream, 'MAX_BYTES', 80)
    with pytest.raises(stream.StreamProtocolError, match='too large'):
        request(valid_bytes())
    monkeypatch.setattr(stream, 'MAX_BYTES', 1000)
    monkeypatch.setattr(stream, 'MAX_LINE_BYTES', 30)
    with pytest.raises(stream.StreamProtocolError, match='line too large'):
        request(b'data: ' + b'x' * 31)


def test_protocol_failure_codes_are_fixed_and_do_not_disclose_provider_text():
    for message, code in stream.STREAM_FAILURE_CODES.items():
        assert stream.StreamProtocolError(message).safe_code == code
        assert code.startswith("stream_")
    private = "untrusted body with Bearer sentinel-secret"
    assert stream.StreamProtocolError(private).safe_code == "stream_protocol_error"
    assert private not in stream.StreamProtocolError(private).safe_code


def test_incomplete_stream_still_rejected_with_precise_code():
    with pytest.raises(stream.StreamProtocolError) as error:
        stream.Accumulator().result()
    assert error.value.safe_code == "stream_incomplete_stream"
