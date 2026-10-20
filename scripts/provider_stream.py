"""Bounded HF-router SSE transport; same route, environment-only credential.

Usage is required before a stream becomes a completed response. Disconnects,
malformed chunks and missing usage never become successful model completions.
"""
import asyncio
import json
import math
import urllib.error

import httpx

BASE = 'https://router.huggingface.co/v1'
MAX_BYTES = 2_000_000
MAX_LINE_BYTES = 100_000


class StreamProtocolError(ValueError):
    pass


class Accumulator:
    def __init__(self):
        self.identifier = None
        self.parts = {'content': [], 'reasoning': [], 'reasoning_content': []}
        self.finish = None
        self.usage = None
        self.done = False

    def event(self, raw):
        if self.done:
            raise StreamProtocolError('data after terminal marker')
        if raw == b'[DONE]':
            self.done = True
            return
        value = json.loads(raw)
        if not isinstance(value, dict) or 'error' in value:
            raise StreamProtocolError('provider stream error')
        identifier = value.get('id')
        if identifier:
            if not isinstance(identifier, str) or self.identifier not in (None, identifier):
                raise StreamProtocolError('response identity changed')
            self.identifier = identifier
        usage = value.get('usage')
        if usage is not None:
            if self.usage is not None or not isinstance(usage, dict):
                raise StreamProtocolError('ambiguous stream usage')
            self.usage = usage
        choices = value.get('choices')
        if not isinstance(choices, list) or len(choices) > 1:
            raise StreamProtocolError('ambiguous stream choice')
        if not choices:
            return
        choice = choices[0]
        if not isinstance(choice, dict) or type(choice.get('index')) is not int or choice['index'] != 0:
            raise StreamProtocolError('unexpected stream choice')
        delta = choice.get('delta')
        if not isinstance(delta, dict) or delta.get('tool_calls') or delta.get('function_call'):
            raise StreamProtocolError('unsupported stream delta')
        for key, parts in self.parts.items():
            text = delta.get(key)
            if text is not None:
                if not isinstance(text, str) or (self.finish is not None and text):
                    raise StreamProtocolError('invalid text delta')
                parts.append(text)
        finish = choice.get('finish_reason')
        if finish is not None:
            if self.finish is not None or finish not in ('stop', 'length', 'tool_calls', 'content_filter'):
                raise StreamProtocolError('invalid finish marker')
            self.finish = finish

    def result(self):
        if not self.done or not self.identifier or self.finish is None or self.usage is None:
            raise StreamProtocolError('incomplete stream')
        for key in ('prompt_tokens', 'completion_tokens'):
            if type(self.usage.get(key)) is not int or self.usage[key] < 0:
                raise StreamProtocolError('unverified stream usage')
        message = {'role': 'assistant', 'content': ''.join(self.parts['content'])}
        for key in ('reasoning', 'reasoning_content'):
            if self.parts[key]:
                message[key] = ''.join(self.parts[key])
        return {'id': self.identifier, 'usage': self.usage,
                'choices': [{'message': message, 'finish_reason': self.finish}]}


async def stream_call(token, payload, timeout, *, transport=None):
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= 180:
        raise ValueError('bounded stream deadline required')
    body = {**payload, 'stream': True, 'stream_options': {'include_usage': True}}
    accumulator = Accumulator()
    buffer, event_lines, received = b'', [], 0
    async with asyncio.timeout(timeout):
        async with httpx.AsyncClient(trust_env=False, follow_redirects=False,
                                     timeout=timeout, transport=transport) as client:
            async with client.stream('POST', BASE + '/chat/completions', json=body,
                    headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'}) as response:
                if response.status_code != 200:
                    raise urllib.error.HTTPError(BASE + '/chat/completions', response.status_code,
                                                 'provider stream HTTP failure', None, None)
                if not response.headers.get('content-type', '').lower().startswith('text/event-stream'):
                    raise StreamProtocolError('expected SSE response')
                async for chunk in response.aiter_bytes():
                    received += len(chunk)
                    if received > MAX_BYTES:
                        raise StreamProtocolError('stream response too large')
                    buffer += chunk
                    while b'\n' in buffer:
                        line, buffer = buffer.split(b'\n', 1)
                        line = line.rstrip(b'\r')
                        if len(line) > MAX_LINE_BYTES:
                            raise StreamProtocolError('stream line too large')
                        if not line:
                            if event_lines:
                                accumulator.event(b'\n'.join(event_lines))
                                event_lines = []
                        elif line.startswith(b'data:'):
                            event_lines.append(line[5:].lstrip(b' '))
                        elif line.startswith(b':'):
                            continue
                        elif not line.startswith((b'event:', b'id:', b'retry:')):
                            raise StreamProtocolError('invalid SSE field')
                    if len(buffer) > MAX_LINE_BYTES:
                        raise StreamProtocolError('stream line too large')
                if buffer or event_lines:
                    raise StreamProtocolError('unterminated SSE event')
    return accumulator.result()


def provider_call(opener, base_url, token, payload, timeout):
    if base_url != BASE:
        raise ValueError('fixed HF route required')
    return asyncio.run(stream_call(token, payload, timeout))
